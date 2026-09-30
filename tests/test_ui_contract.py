from pathlib import Path
from core.ui_contract import audit_ui_contract

ROOT = Path(__file__).parents[1]


def test_current_app_passes_static_ui_contract():
    assert audit_ui_contract(ROOT / "app.py") == []


def _audit(tmp_path, source):
    path = tmp_path / "app.py"
    path.write_text(source)
    return audit_ui_contract(path)


def test_detects_express_output_ui(tmp_path):
    issues = _audit(tmp_path, 'ui.output_ui("x")')
    assert any(i.code == "EXPRESS_API" for i in issues)


def test_detects_positional_layout_columns(tmp_path):
    issues = _audit(tmp_path, 'ui.layout_columns(ui.div("A"), ui.div("B"), col_widths=(6,6))')
    assert any(i.code == "LAYOUT_COLUMNS_POSITIONAL" for i in issues)


def test_detects_duplicate_input_ids(tmp_path):
    issues = _audit(tmp_path, 'ui.input_numeric("weight", "A", 1)\nui.input_text("weight", "B")')
    assert any(i.code == "DUPLICATE_INPUT_ID" for i in issues)


def test_detects_manual_and_rendered_download_duplicate(tmp_path):
    source = '''\ncore_ui.download_button("report", "Download")\n@render.download(filename="x.html")\ndef report():\n    yield "x"\n'''
    issues = _audit(tmp_path, source)
    assert any(i.code == "DUPLICATE_DOWNLOAD_ID" for i in issues)
