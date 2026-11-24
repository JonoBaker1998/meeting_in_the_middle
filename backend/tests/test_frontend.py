import re

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_site_served_with_demo_label_and_all_scripts():
    c = TestClient(create_app())
    html = c.get("/")
    assert html.status_code == 200 and "Demo data" in html.text
    assert 'type="module" src="js/app.js"' in html.text
    assert c.get("/styles.css").status_code == 200
    for name in ("config", "api", "state", "map", "panel", "app"):
        assert c.get(f"/js/{name}.js").status_code == 200


def test_modules_only_import_files_that_exist():
    c = TestClient(create_app())
    for name in ("api", "map", "panel", "app"):
        src = c.get(f"/js/{name}.js").text
        for dep in re.findall(r'from "\./([\w-]+\.js)"', src):
            assert c.get(f"/js/{dep}").status_code == 200, f"{name}.js imports missing {dep}"


TEXT_FIELDS = r"\.(name|area|type|price|id)\b"


def _unescaped(src: str) -> list[str]:
    """Interpolations of text fields in template literals that aren't wrapped in esc(...)."""
    bad = []
    for expr in re.findall(r"\$\{([^}]*)\}", src):
        if "===" in expr:  # a comparison, not text being inserted
            continue
        if re.search(TEXT_FIELDS, expr) and not expr.strip().startswith("esc("):
            bad.append(expr)
    return bad


def test_map_and_panel_escape_text_before_inserting_html():
    c = TestClient(create_app())
    for name in ("map", "panel"):
        src = c.get(f"/js/{name}.js").text
        assert _unescaped(src) == [], f"{name}.js inserts unescaped text: {_unescaped(src)}"
