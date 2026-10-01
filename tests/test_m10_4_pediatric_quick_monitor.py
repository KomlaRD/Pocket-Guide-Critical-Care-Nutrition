from pathlib import Path
APP=(Path(__file__).parents[1]/"app.py").read_text()
def sec(): return APP[APP.index("input.page === 'pediatric'"):APP.index("input.page === 'anthro'")]
def test_topics(): assert '"quick":"Quick reference"' in sec() and '"phase_monitor":"Phase-based monitoring"' in sec()
def test_quick_core(): 
 x=sec()
 for t in ("within 24 h","within 24–48 h","1.5 g/kg/day","about 1 week","uncontrolled shock"): assert t in x
def test_neonatal_boundary(): assert "excludes neonates" in sec() and "Do not use this quick reference as a neonatal prescription" in sec()
def test_phase_monitoring(): 
 x=sec()
 for t in ("Acute / early PICU","Stable / advancing nutrition","Recovery, rehabilitation & growth","After interruption or clinical deterioration"): assert t in x
def test_recovery_not_acute_restriction(): assert "Do not continue acute-phase energy restriction automatically" in sec()
def test_non_documenting(): assert "Responses are transient and are not stored" in sec()
def test_question_zone(): assert 'class_="question-zone"' in sec()
