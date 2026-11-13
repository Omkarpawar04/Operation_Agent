import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_domain_does_not_import_framework_persistence_or_providers() -> None:
    forbidden = ("fastapi", "sqlalchemy", "google", "app.adapters", "app.api")
    for source in (APP_ROOT / "domain").rglob("*.py"):
        imports = _imports(source)
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in imports
            for prefix in forbidden
        ), source


def test_application_does_not_import_concrete_infrastructure() -> None:
    forbidden = ("app.adapters", "sqlalchemy", "fastapi", "google")
    for source in (APP_ROOT / "application").rglob("*.py"):
        imports = _imports(source)
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in imports
            for prefix in forbidden
        ), source


def test_http_route_modules_do_not_query_database_or_call_providers() -> None:
    forbidden = ("sqlalchemy", "app.db", "app.adapters", "app.ports.llm")
    for source in (APP_ROOT / "api" / "v1").glob("*.py"):
        imports = _imports(source)
        assert not any(
            module == prefix or module.startswith(prefix + ".")
            for module in imports
            for prefix in forbidden
        ), source
