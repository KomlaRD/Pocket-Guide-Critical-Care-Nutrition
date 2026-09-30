from pathlib import Path
from clinical_rules.engine import GuidelineRepository, PatientContext

DATA = Path(__file__).parents[1] / "data" / "guidelines"

def repo(): return GuidelineRepository(DATA)

def test_aspen_energy_calculates_range():
    ev = repo().evaluate("ASPEN22_Q1_RULE", PatientContext(weight_kg=70, icu_day=3))
    assert ev.status == "APPLICABLE"
    assert "840" in ev.result_text and "1750" in ev.result_text

def test_aspen_energy_outside_day_window():
    ev = repo().evaluate("ASPEN22_Q1_RULE", PatientContext(weight_kg=70, icu_day=11))
    assert ev.status == "NOT_APPLICABLE"

def test_missing_day_is_not_same_as_not_applicable():
    ev = repo().evaluate("ASPEN22_Q1_RULE", PatientContext(weight_kg=70))
    assert ev.status == "INSUFFICIENT_CONTEXT"

def test_espen_early_measured_ee_ceiling():
    ev = repo().evaluate("ESPEN23_R17_RULE", PatientContext(icu_day=2, measured_ee_kcal=2000))
    assert ev.status == "APPLICABLE"
    assert "1400" in ev.result_text

def test_espen_after_day3_measured_ee_range():
    ev = repo().evaluate("ESPEN23_R18_RULE", PatientContext(icu_day=4, measured_ee_kcal=2000))
    assert ev.status == "APPLICABLE"
    assert "1600" in ev.result_text and "2000" in ev.result_text

def test_espen_protein_target():
    ev = repo().evaluate("ESPEN23_R22_RULE", PatientContext(weight_kg=70))
    assert ev.status == "APPLICABLE"
    assert "91.0" in ev.result_text

def test_spn_requires_en_context():
    ev = repo().evaluate("ASPEN22_Q4_RULE", PatientContext(icu_day=5, receiving_en=None))
    assert ev.status == "INSUFFICIENT_CONTEXT"

def test_spn_not_applicable_without_en():
    ev = repo().evaluate("ASPEN22_Q4_RULE", PatientContext(icu_day=5, receiving_en=False))
    assert ev.status == "NOT_APPLICABLE"
