from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def test_guideline_topics_present():
    for x in ("Route & timing of nutrition","Energy expenditure & progression","Protein provision","EN intolerance & gastric residual volume","Parenteral & supplemental PN","Kidney disease / renal replacement therapy"): assert x in APP
def test_espen_icu_source_provenance_present():
    assert "Clinical Nutrition. 2023;42:1671–1689" in APP
    assert "ESPEN_practical_and_partially_revised_guideline_Clinical_nutrition_in_the_intensive_care_unit.pdf" in APP
def test_high_yield_energy_safeguards_present():
    for x in ("indirect calorimetry","below 70%","80–100%","non-nutritional calories"): assert x in APP
def test_no_generic_obesity_dosing_rule():
    assert "do not apply a normal-BMI kcal/kg or protein rule indiscriminately" in APP
def test_guidelines_remain_non_documenting():
    section=APP[APP.index("input.page === 'guidelines'"):APP.index("input.page === 'refeeding'")]
    assert "patient record" not in section.lower()
    assert "documentation" not in section.lower()
