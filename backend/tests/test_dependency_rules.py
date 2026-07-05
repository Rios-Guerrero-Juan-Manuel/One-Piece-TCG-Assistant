import ast
from pathlib import Path


def get_imports(filepath: Path) -> list[str]:
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def test_domain_does_not_import_infrastructure():
    domain_dir = Path(__file__).resolve().parents[1] / "app" / "domain"
    if not domain_dir.exists():
        return
    forbidden = ["app.infrastructure", "app.presentation", "fastapi", "sqlalchemy"]
    for pyfile in domain_dir.rglob("*.py"):
        if pyfile.name == "__init__.py":
            continue
        imports = get_imports(pyfile)
        for imp in imports:
            for prefix in forbidden:
                assert not imp.startswith(prefix), (
                    f"domain imports {prefix}: {pyfile.name} -> {imp}"
                )

def test_domain_does_not_import_pydantic():
    domain_dir = Path(__file__).resolve().parents[1] / "app" / "domain"
    if not domain_dir.exists():
        return
    for pyfile in domain_dir.rglob("*.py"):
        if pyfile.name == "__init__.py":
            continue
        imports = get_imports(pyfile)
        for imp in imports:
            assert not imp.startswith("pydantic"), (
                f"domain imports pydantic: {pyfile.name} -> {imp}"
            )
