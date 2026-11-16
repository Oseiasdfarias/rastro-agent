import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[2] / "src" / "rootcause"


def _internal_imports(folder: str) -> set[str]:
    found = set()
    for f in (PKG / folder).rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("rootcause"):
                    found.add(node.module)
            elif isinstance(node, ast.Import):
                found |= {a.name for a in node.names if a.name.startswith("rootcause")}
    return found


def test_domain_imports_nothing_internal():
    assert {m for m in _internal_imports("domain") if not m.startswith("rootcause.domain")} == set()


def test_application_only_imports_domain_and_application():
    bad = {
        m
        for m in _internal_imports("application")
        if not m.startswith(("rootcause.domain", "rootcause.application"))
    }
    assert bad == set()
