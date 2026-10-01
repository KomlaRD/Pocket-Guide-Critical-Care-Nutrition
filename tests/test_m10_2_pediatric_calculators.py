from pathlib import Path
APP=(Path(__file__).parents[1]/"app.py").read_text()
def sec(): return APP[APP.index("input.page === 'pediatric'"):APP.index("input.page === 'anthro'")]
def test_topics(): assert '"calc":"Energy & protein calculator"' in sec() and '"growth":"Anthropometry & growth"' in sec()
def test_schofield():
 x=sec()
 for t in ("59.512*w-30.4","22.706*w+504.3","17.686*w+658.2","58.317*w-31.1","20.315*w+485.9","13.384*w+692.6"): assert t in x
def test_scope(): assert "Do not add a stress factor" in sec() and "restricted to children >1 month and <18 years" in sec()
def test_protein(): assert "protein=1.5*w" in sec() and "Reference minimum protein at 1.5 g/kg/day" in sec()
def test_growth(): assert "Do not interpret pediatric BMI using adult BMI cutoffs" in sec() and "BMI-for-age" in sec()
def test_zscore(): assert "does not calculate pediatric z-scores" in sec() and "LMS data" in sec()
