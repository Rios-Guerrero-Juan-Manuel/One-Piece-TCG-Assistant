"""Entry point for the Windows portable bundle.

Run by the bundled embedded Python (``python\\pythonw.exe``):

    python\\pythonw.exe run_app.py

Responsibilities:
- prepare the environment (user data dir in %LOCALAPPDATA%, bundled embedding
  model, offline mode)
- redirect stdout/stderr to a log file (pythonw has no console)
- apply database migrations (fallback: create_all)
- start uvicorn on a free port and open the browser when healthy
"""

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parent

HEALTH_CHECK_TIMEOUT = 180.0


def _prepare_env() -> Path:
    sys.path.insert(0, str(BUNDLE_ROOT))

    from app.core.paths import default_portable_data_dir

    data_path = Path(os.environ.get("OPTCG_DATA_DIR", "").strip() or default_portable_data_dir())
    os.environ["OPTCG_DATA_DIR"] = str(data_path)
    (data_path / "logs").mkdir(parents=True, exist_ok=True)

    models_dir = BUNDLE_ROOT / "models"
    if models_dir.is_dir():
        os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(models_dir))
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    url_file = data_path / "app_url.txt"
    url_file.unlink(missing_ok=True)
    return url_file


def _redirect_output(data_path: Path) -> None:
    log_path = data_path / "logs" / "run_app.log"
    if sys.stdout is None or sys.stderr is None:
        handle = open(log_path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = handle
        sys.stderr = handle


def _free_port(start: int) -> int:
    for port in range(start, start + 25):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    return start


def _open_browser_when_ready(port: int, url_file: Path) -> None:
    import urllib.request

    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + HEALTH_CHECK_TIMEOUT
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=2) as resp:
                if resp.status == 200:
                    break
        except OSError:
            time.sleep(0.5)
    else:
        return

    try:
        url_file.write_text(url, encoding="utf-8")
    except OSError:
        pass
    webbrowser.open(url)


def main() -> int:
    url_file = _prepare_env()
    data_path = Path(os.environ["OPTCG_DATA_DIR"])
    _redirect_output(data_path)

    print(f"[run_app] data dir: {data_path}", flush=True)

    try:
        from app.infrastructure.persistence.migrations import run_migrations

        run_migrations()
    except Exception:
        print("[run_app] migrations failed — falling back to create_all", flush=True)
        import traceback

        traceback.print_exc()
        try:
            from app.infrastructure.persistence.session import init_db

            init_db()
        except Exception:
            print("[run_app] create_all failed too", flush=True)
            traceback.print_exc()

    port = _free_port(8000)
    print(f"[run_app] starting server on port {port}", flush=True)

    browser = threading.Thread(
        target=_open_browser_when_ready, args=(port, url_file), daemon=True
    )
    browser.start()

    import uvicorn

    uvicorn.run("app.presentation.main:app", host="127.0.0.1", port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
