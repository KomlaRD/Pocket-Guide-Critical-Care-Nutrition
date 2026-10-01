from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text(); CSS=(ROOT/"www/styles.css").read_text()
def sec(): return APP[APP.index("input.page === 'pediatric'"):APP.index("input.page === 'anthro'")]
def test_nav_scope():
 assert '"pediatric":"Pediatric Critical Care"' in APP and ">1 month and <18 years" in sec() and "does not cover neonates" in sec()
def test_en():
 x=sec(); assert "within 24 hours" in x and "24–48 hours" in x and "Advance stepwise" in x
def test_energy():
 x=sec(); assert "should not exceed resting energy expenditure" in x and "without added stress factors" in x and "Harris–Benedict" in x
def test_protein():
 x=sec(); assert "1.5 g/kg/day" in x and "insufficient evidence" in x and "aggressively exceed" in x
def test_pn():
 x=sec(); assert "does not recommend initiating PN within the first 24 hours" in x and "about 1 week" in x and "severely malnourished" in x
def test_layout_zones():
 x=sec(); assert 'class_="question-zone"' in x and 'class_="evidence-zone"' in x and ".question-zone" in CSS and ".evidence-zone" in CSS
def test_no_documentation():
 x=sec(); assert "MRN" not in x and "patient record" not in x
