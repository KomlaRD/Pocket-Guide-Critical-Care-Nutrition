from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def section():
    return APP[APP.index("input.page === 'obesity'"):APP.index("input.page === 'anthro'")]
def test_obesity_nav_and_topics():
    assert '"obesity":"Obesity in ICU"' in APP
    for x in ("Assessment & body composition","ESPEN adjusted body weight","ASPEN obesity guidance"): assert x in section()
def test_indirect_calorimetry_preferred():
    assert "Guide energy intake by indirect calorimetry whenever available" in section()
def test_espen_protein_fallback_present():
    assert "1.3 g/kg adjusted body weight/day" in section()
def test_adjusted_weight_formula_and_guard_present():
    sec=section()
    assert "20–25% of excess weight" in sec
    assert "Actual weight is below the entered ideal/reference weight" in sec
def test_aspen_framework_kept_separate():
    sec=section()
    assert "50–70% of estimated energy requirements or <14 kcal/kg actual weight" in sec
    assert "2–2.5 g/kg ideal body weight" in sec
    assert "Do not calculate energy with one society's weight convention" in sec
