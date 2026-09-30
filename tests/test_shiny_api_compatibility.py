from pathlib import Path


def test_patient_documentation_download_is_absent_in_pocket_guide():
    source = (Path(__file__).parents[1] / "app.py").read_text()
    assert "patient-nutrition-summary.html" not in source
    assert "download_patient_summary" not in source

def test_no_express_download_button_call():
    source = (Path(__file__).parents[1] / "app.py").read_text()
    assert "ui.download_button(" not in source
