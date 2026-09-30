from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def section(): return APP[APP.index("input.page === 'special_icu'"):APP.index("input.page === 'anthro'")]
def test_navigation_and_special_topics():
    assert '"special_icu":"Trauma, Burns & Sepsis"' in APP
    for x in ("Sepsis & septic shock","Major trauma","Major burns","Postoperative / surgical ICU","Open abdomen & wound losses"): assert x in section()
def test_shock_safety_and_progression():
    sec=section()
    assert "uncontrolled shock" in sec and "low-dose EN" in sec and "Avoid early full-dose energy delivery" in sec
def test_burns_no_generic_energy_rule():
    sec=section()
    assert "Avoid relying on a single generic kcal/kg rule" in sec
    assert "local burn-center protocols" in sec
def test_postop_no_unnecessary_fasting():
    sec=section()
    assert "Avoid unnecessary postoperative fasting" in sec
    assert "Anastomosis alone is not a reason for prolonged starvation" in sec
def test_protein_energy_separate():
    sec=section()
    assert "energy and protein are separate prescription decisions" in sec
    assert "approximately 1.3 g protein/kg/day" in sec
    assert "Do not use a high protein target as justification for energy overfeeding" in sec
def test_monitoring_includes_losses_and_refeeding():
    sec=section()
    assert "screen for refeeding risk" in sec and "Wound, drain, fistula or burn losses" in sec
