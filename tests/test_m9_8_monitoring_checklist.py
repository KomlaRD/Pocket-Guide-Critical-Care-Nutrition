from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def section(): return APP[APP.index("input.page === 'monitoring_check'"):APP.index("input.page === 'anthro'")]
def test_monitoring_navigation_and_phases():
    assert '"monitoring_check":"Monitoring Checklist"' in APP
    for x in ("Before starting / changing nutrition","First 72 hours & advancement","Established enteral nutrition","Established parenteral nutrition","Prolonged ICU stay / weekly review"): assert x in section()
def test_non_documenting_contract():
    sec=section()
    assert "no checklist responses or patient information are stored" in sec
    assert "does not save completion status" in sec
def test_early_monitoring_delivery_and_no_catchup():
    sec=section()
    assert "Actual energy and protein delivered" in sec
    assert "do not compensate for early under-delivery by abruptly overfeeding" in sec
    assert "Avoid catch-up overfeeding" in sec
def test_pn_monitoring_core_items():
    sec=section()
    for x in ("Verify PN indication daily","Glucose and insulin","Triglycerides","line complications"): assert x in sec
def test_refeeding_frequency_and_thiamin():
    sec=section()
    assert "every 12 hours for the first 3 days" in sec and "thiamin" in sec
def test_daily_review_framework():
    sec=section()
    for x in ("Route:","Delivery:","Tolerance & safety:","Biochemistry:","Trajectory:"): assert x in sec
