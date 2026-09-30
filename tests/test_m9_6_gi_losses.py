from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def section(): return APP[APP.index("input.page === 'gi_losses'"):APP.index("input.page === 'anthro'")]
def test_gi_navigation_and_topics():
    assert '"gi_losses":"GI Losses & Intestinal Failure"' in APP
    for x in ("Fluid & sodium strategy","Enterocutaneous fistula","Short bowel: anatomy matters","Escalation / red flags"): assert x in section()
def test_high_output_is_clinical_not_volume_only():
    sec=section()
    assert "not by volume alone" in sec
    assert "1.5–2.0 L/day" in sec
def test_hypotonic_fluid_safety():
    sec=section()
    assert "plain water alone can worsen sodium depletion" in sec
    assert "90–120 mmol/L" in sec
    assert "drink more water" in sec
def test_anatomy_drives_plan():
    sec=section()
    assert "colon in continuity" in sec
    assert "remaining small-bowel length" in sec
def test_pn_not_automatic():
    sec=section()
    assert "Do not use PN solely because a stoma or fistula exists" in sec
def test_monitoring_includes_urine_and_magnesium():
    sec=section()
    assert "Urine volume" in sec and "magnesium" in sec and "Urine sodium" in sec
