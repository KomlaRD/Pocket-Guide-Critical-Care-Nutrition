from pathlib import Path
APP=(Path(__file__).parents[1]/"app.py").read_text()
def sec(): return APP[APP.index("input.page === 'pediatric'"):APP.index("input.page === 'anthro'")]
def test_en_topics(): assert '"en_calc":"EN delivery & adequacy"' in sec() and '"en_safe":"EN advancement & safety"' in sec()
def test_en_math(): 
 x=sec()
 for t in ("vol=rate*hrs","kcal=vol*kcal100/100","protein=vol*prot100/100","vol/w"): assert t in x
def test_no_product_assumption(): assert "verified product label" in sec() and "no product values are assumed or stored" in sec()
def test_adequacy_not_goal_validation(): assert "do not validate that the goal itself is appropriate" in sec()
def test_stepwise_not_invented_rate(): assert "No universal mL/kg/hour advancement schedule is embedded" in sec() and "protocolized stepwise advancement" in sec()
def test_hemodynamic_safety(): assert "Vasoactive medication is not, by itself, an automatic contraindication" in sec() and "uncontrolled shock" in sec()
def test_fluid_awareness(): assert "Fluid from EN" in sec() and "IV fluids, flushes, PN" in sec()
