from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def test_safety_topics_present():
    for x in ("Gastric residual volume & intolerance","Aspiration risk","Diarrhea","Constipation","Electrolytes & refeeding","Triglycerides & IV lipid","PN safety"): assert x in APP
def test_grv_safeguard_present():
    assert "below 500 mL over 6 hours" in APP
    assert "reassessment rather than automatic permanent cessation" in APP
def test_diarrhea_does_not_reflexively_stop_en():
    assert "Avoid reflexively stopping EN solely because diarrhea is present" in APP
def test_triglyceride_threshold_not_invented():
    assert "does not invent a universal triglyceride cutoff" in APP
def test_safety_is_non_documenting():
    sec=APP[APP.index("input.page === 'safety'"):APP.index("input.page === 'metabolic'")]
    assert "does not create treatment orders or patient records" in sec
