from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def section(): return APP[APP.index("input.page === 'find'"):APP.index("input.page === 'guidelines'")]
def test_find_guidance_navigation_and_index():
    assert '"find":"Find Guidance"' in APP
    for x in ("Refeeding syndrome","AKI, CKD or KRT","Acute pancreatitis","High-output stoma / fistula / short bowel","Nutrition monitoring"): assert x in section()
def test_find_guidance_is_non_documenting():
    sec=section()
    assert "stores no search history or patient information" in sec
    assert "Calculator inputs are transient bedside values" in sec
def test_index_preserves_key_safety_messages():
    sec=section()
    assert "Do not advance full EN during uncontrolled shock" in sec
    assert "GRV below 500 mL/6 h" in sec
    assert "not, by itself, an indication for routine protein restriction" in sec
def test_weight_descriptor_contract():
    sec=section()
    assert "actual, ideal and adjusted body weight" in sec
    assert "Weight descriptors, units and guideline source must remain explicit" in sec
def test_all_m9_modules_remain_navigable():
    for nav in ('"renal":"Renal & KRT"','"obesity":"Obesity in ICU"','"pancreatitis":"Acute Pancreatitis"','"liver":"Liver Disease"','"gi_losses":"GI Losses & Intestinal Failure"','"special_icu":"Trauma, Burns & Sepsis"','"monitoring_check":"Monitoring Checklist"'):
        assert nav in APP
def test_deferred_ic_module_not_reintroduced():
    assert '"ic":"Indirect Calorimetry"' not in APP
