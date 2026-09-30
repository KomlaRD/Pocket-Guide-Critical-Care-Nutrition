from pathlib import Path
import pytest
from core.calculators import en_rate, propofol_energy, percent_weight_loss
ROOT=Path(__file__).parents[1]
def test_en_feeding_duration_cannot_exceed_day():
    with pytest.raises(ValueError,match="24 hours"): en_rate(1800,1.5,25)
def test_propofol_daily_duration_cannot_exceed_day():
    with pytest.raises(ValueError,match="24 hours"): propofol_energy(10,25)
def test_weight_gain_is_explicit_not_mislabeled_loss():
    r=percent_weight_loss(70,75)
    assert r.value < 0 and r.warnings and "weight gain" in r.warnings[0]
def test_anthropometry_is_self_contained_and_transient():
    app=(ROOT/"app.py").read_text()
    sec=app[app.index("input.page === 'anthro'"):app.index("input.page === 'requirements'")]
    assert "Transient bedside calculations only" in sec
    assert "anth_weight" in sec and "anth_height" in sec
    assert "current session weight" not in sec.lower()
def test_weight_tools_not_duplicated_in_toolkit():
    app=(ROOT/"app.py").read_text()
    sec=app[app.index("input.page === 'toolkit'"):app.index("input.page === 'anthro'")]
    assert 'card_header("Weight Tools")' not in sec
