from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def section(): return APP[APP.index("input.page === 'pancreatitis'"):APP.index("input.page === 'anthro'")]
def test_pancreatitis_navigation_and_topics():
    assert '"pancreatitis":"Acute Pancreatitis"' in APP
    for x in ("Can oral feeding start?","NG or NJ?","Which enteral formula?","Pancreatic enzymes?"): assert x in section()
def test_early_oral_feeding_and_lipase_safeguard():
    sec=section()
    assert "as soon as clinically tolerated" in sec
    assert "Do not wait for serum lipase to normalize" in sec
def test_en_timing_and_preference():
    sec=section()
    assert "within 24–72 hours of admission" in sec
    assert "prefer EN to PN" in sec
def test_ng_first_nj_for_intolerance():
    sec=section()
    assert "nasogastric tube as the usual initial route" in sec
    assert "Prefer nasojejunal feeding" in sec
def test_polymeric_formula_and_pn_safeguards():
    sec=section()
    assert "standard polymeric enteral formula" in sec
    assert "PN is not first-line nutrition support" in sec
def test_no_routine_pert_for_diagnosis_alone():
    assert "Do not prescribe pancreatic enzyme replacement routinely" in section()
