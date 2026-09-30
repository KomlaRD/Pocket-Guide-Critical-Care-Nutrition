from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def section(): return APP[APP.index("input.page === 'liver'"):APP.index("input.page === 'anthro'")]
def test_liver_navigation_and_topics():
    assert '"liver":"Liver Disease"' in APP
    for x in ("Hepatic encephalopathy","Acute liver failure","Ascites, sodium & fluid","Micronutrients & refeeding"): assert x in section()
def test_cirrhosis_targets_present():
    sec=section()
    assert "30–35 kcal/kg/day" in sec and "1.5 g protein/kg/day" in sec
def test_no_routine_protein_restriction():
    sec=section()
    assert "Do not restrict protein in patients with hepatic encephalopathy" in sec
    assert "Chronic protein restriction can worsen" in sec
def test_alf_route_and_hyperammonemia_nuance():
    sec=section()
    assert "PN is second-line" in sec
    assert "hyperacute liver failure with severe hyperammonemia" in sec
def test_fasting_and_late_evening_snack():
    sec=section()
    assert "avoid unnecessarily long fasting periods" in sec
    assert "late-evening snack" in sec
def test_fluid_and_sodium_not_automatic():
    sec=section()
    assert "overly restrictive diet can worsen intake" in sec
    assert "Do not impose routine fluid restriction solely because ascites is present" in sec
