"""Build the Windows portable bundle.

Produces ``releases/OnePieceTCGAssistant-<version>-win64.zip``: a folder the
end user unzips anywhere and runs via ``OnePieceTCGAssistant.exe``.

Layout of the bundle:
    OnePieceTCGAssistant/
        OnePieceTCGAssistant.exe   launcher (tkinter, stdlib only)
        run_app.py                 backend entry point
        python/                    embedded Python 3.11
        .deps/                     site-packages (torch, chromadb, ...)
        app/                       backend source
        alembic/                   DB migrations
        frontend/dist/             built React frontend
        Datos/                     read-only game data
        models/                    sentence-transformers model (offline)

Usage (from the repo root):
    python deploy/windows/build_portable.py [--skip-frontend] [--skip-deps]

Requirements on the build machine: Python 3.11+ with pip, Node.js 18+, and
internet access for the first run (downloads are cached in deploy/windows/cache).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WINDOWS_DIR = Path(__file__).resolve().parent
CACHE_DIR = WINDOWS_DIR / "cache"
RELEASES_DIR = REPO_ROOT / "releases"
BUILD_DIR = RELEASES_DIR / "OnePieceTCGAssistant"
BUILD_VENV = CACHE_DIR / "build-venv"

PYTHON_VERSION = "3.11.9"
PYTHON_EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/"
    f"python-{PYTHON_VERSION}-embed-amd64.zip"
)
GETPIP_URL = "https://bootstrap.pypa.io/get-pip.py"

EMBEDDED_PTH = """\
python311.zip
.
Lib\\site-packages
..\\.deps
..
"""

MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def run(cmd: list[str], **kwargs) -> None:
    log(" ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def which(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"'{name}' not found on PATH (Node.js required to build)")
    return found


def reset_build_dir(keep: list[str]) -> None:
    if not BUILD_DIR.exists():
        BUILD_DIR.mkdir(parents=True)
        return
    for child in BUILD_DIR.iterdir():
        if child.name in keep:
            continue
        log(f"cleaning {child.name}")
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def download(url: str, dest: Path) -> None:
    if dest.exists():
        log(f"cached: {dest.name}")
        return
    log(f"downloading {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)  # noqa: S310


def venv_python() -> Path:
    exe = BUILD_VENV / "Scripts" / "python.exe"
    if not exe.exists():
        log("creating build venv (pyinstaller + huggingface_hub)")
        run([sys.executable, "-m", "venv", BUILD_VENV])
        run([exe, "-m", "pip", "install", "--upgrade", "pip"])
        run(
            [
                exe,
                "-m",
                "pip",
                "install",
                "pyinstaller>=6.0",
                "huggingface_hub>=0.23",
            ]
        )
    return exe


def step_embedded_python() -> None:
    zip_path = CACHE_DIR / f"python-{PYTHON_VERSION}-embed-amd64.zip"
    download(PYTHON_EMBED_URL, zip_path)
    python_dir = BUILD_DIR / "python"
    python_dir.mkdir()
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(python_dir)
    pth = python_dir / "python311._pth"
    pth.write_text(EMBEDDED_PTH, encoding="utf-8")
    log("embedded Python ready")


def step_python_deps(skip: bool) -> None:
    if skip:
        log("skipping python deps (--skip-deps)")
        return
    python_exe = BUILD_DIR / "python" / "python.exe"

    # Bootstrap pip into the embedded interpreter (the official recipe for
    # the embeddable distribution; the ._pth file already exposes
    # Lib\\site-packages).
    getpip = CACHE_DIR / "get-pip.py"
    download(GETPIP_URL, getpip)
    run([python_exe, getpip, "--no-warn-script-location"])

    deps = BUILD_DIR / ".deps"
    deps.mkdir()
    run(
        [
            python_exe,
            "-m",
            "pip",
            "install",
            "--target",
            deps,
            "--no-compile",
            "--no-warn-script-location",
            "-r",
            WINDOWS_DIR / "requirements-portable.txt",
        ]
    )


def step_frontend(skip: bool) -> None:
    dist = BUILD_DIR / "frontend" / "dist"
    if skip:
        src = REPO_ROOT / "frontend" / "dist"
        if not src.is_dir():
            raise SystemExit("--skip-frontend but frontend/dist does not exist")
    else:
        npm = which("npm")
        run([npm, "ci"], cwd=REPO_ROOT / "frontend")
        run([npm, "run", "build"], cwd=REPO_ROOT / "frontend")
        src = REPO_ROOT / "frontend" / "dist"
    shutil.copytree(src, dist)
    log("frontend copied")


def step_source() -> None:
    shutil.copytree(REPO_ROOT / "backend" / "app", BUILD_DIR / "app")
    shutil.copytree(REPO_ROOT / "backend" / "alembic", BUILD_DIR / "alembic")
    shutil.copy2(WINDOWS_DIR / "run_app.py", BUILD_DIR / "run_app.py")
    datos = REPO_ROOT / "Datos"
    if datos.is_dir():
        shutil.copytree(datos, BUILD_DIR / "Datos")
    log("source + data copied")


def step_model() -> None:
    models = BUILD_DIR / "models"
    models.mkdir()
    run(
        [
            venv_python(),
            "-c",
            "from huggingface_hub import snapshot_download; "
            f"snapshot_download('{MODEL_REPO}', cache_dir=r'{models}')",
        ]
    )
    log(f"embedding model cached into {models}")


def step_launcher_exe() -> None:
    exe = venv_python().parent / "pyinstaller.exe"
    work = CACHE_DIR / "pyinstaller"
    dist = work / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    run(
        [
            exe,
            "--noconfirm",
            "--onefile",
            "--noconsole",
            "--name",
            "OnePieceTCGAssistant",
            "--distpath",
            dist,
            "--workpath",
            work / "build",
            "--specpath",
            work,
            WINDOWS_DIR / "launcher_app.py",
        ]
    )
    shutil.copy2(dist / "OnePieceTCGAssistant.exe", BUILD_DIR / "OnePieceTCGAssistant.exe")
    log("launcher exe built")


def step_zip(version: str) -> Path:
    zip_base = RELEASES_DIR / f"OnePieceTCGAssistant-{version}-win64"
    archive = shutil.make_archive(str(zip_base), "zip", root_dir=RELEASES_DIR, base_dir=BUILD_DIR.name)
    log(f"zip created: {archive}")
    return Path(archive)


def project_version() -> str:
    with open(REPO_ROOT / "backend" / "pyproject.toml", "rb") as fh:
        data = tomllib.load(fh)
    return data["project"]["version"]


def dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-frontend", action="store_true", help="reuse existing frontend/dist")
    parser.add_argument("--skip-deps", action="store_true", help="skip pip install of .deps")
    parser.add_argument("--no-zip", action="store_true", help="leave the folder unzipped")
    args = parser.parse_args()

    version = project_version()
    log(f"building version {version}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    keep: list[str] = []
    if args.skip_deps:
        keep.append(".deps")
    if args.skip_frontend:
        keep.append("frontend")
    reset_build_dir(keep)

    step_embedded_python()
    step_python_deps(skip=args.skip_deps)
    step_frontend(skip=args.skip_frontend)
    step_source()
    step_model()
    step_launcher_exe()

    size = dir_size_mb(BUILD_DIR)
    log(f"bundle size: {size:.0f} MB")

    if not args.no_zip:
        step_zip(version)

    log(f"done: {BUILD_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
