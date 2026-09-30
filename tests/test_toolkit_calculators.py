import pytest
from core.calculators import (
    ideal_body_weight_devine, adjusted_body_weight, fluid_balance,
    formula_free_water, pn_macronutrient_energy, respiratory_quotient,
    convert_units, electrolyte_mmol_mEq,
)

def test_devine_male_70_inches():
    assert ideal_body_weight_devine(177.8, "male").value == pytest.approx(73.0)

def test_adjusted_weight():
    assert adjusted_body_weight(100, 70, 0.4).value == pytest.approx(82)

def test_fluid_balance_can_be_negative():
    assert fluid_balance(1800, 2200).value == pytest.approx(-400)

def test_free_water():
    assert formula_free_water(1200, 80).value == pytest.approx(960)

def test_pn_energy_customizable_density():
    assert pn_macronutrient_energy(200, 80, 50).value == pytest.approx(1500)

def test_rq():
    assert respiratory_quotient(250, 200).value == pytest.approx(0.8)

def test_common_unit_conversions():
    assert convert_units(1, "kg", "lb").value == pytest.approx(2.2046226218)
    assert convert_units(1, "L", "mL").value == pytest.approx(1000)
    assert convert_units(100, "kcal", "kJ").value == pytest.approx(418.4)

def test_electrolyte_valence_conversion():
    assert electrolyte_mmol_mEq(10, 2).value == pytest.approx(20)
    assert electrolyte_mmol_mEq(20, 2, "mEq_to_mmol").value == pytest.approx(10)

def test_validation():
    with pytest.raises(ValueError): formula_free_water(1000, 120)
    with pytest.raises(ValueError): convert_units(1, "kg", "mL")
    with pytest.raises(ValueError): electrolyte_mmol_mEq(10, 0)
