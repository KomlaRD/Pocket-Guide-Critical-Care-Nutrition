from pathlib import Path
ROOT=Path(__file__).parents[1]
APP=(ROOT/"app.py").read_text()
def renal_section():
    return APP[APP.index("input.page === 'renal'"):APP.index("input.page === 'metabolic'")]
def test_renal_navigation_present():
    assert '"renal":"Renal & KRT"' in APP
def test_critical_renal_protein_ranges_present():
    sec=renal_section()
    for x in ("up to 1.3 g/kg/day","1.3–1.5 g/kg/day","1.5–1.7 g/kg/day"): assert x in sec
def test_protein_not_restricted_to_delay_krt():
    assert "Do not reduce protein prescription simply to avoid or delay" in renal_section()
def test_actual_weight_warning_present():
    assert "Actual body weight should not be used for protein prescription" in renal_section()
def test_ckrt_losses_are_not_fixed_replacement_orders():
    sec=renal_section()
    assert "15–20 g/day" in sec and "Do not translate quoted extracorporeal losses directly into a fixed replacement prescription" in sec
def test_renal_module_is_non_documenting():
    sec=renal_section().lower()
    assert "patient name" not in sec and "mrn" not in sec
