import math
import pytest

from core.non_nutrition import (
    EnergySource,
    calculate_energy_exposure,
    iv_dextrose_energy,
    propofol_energy_from_volume,
)


def test_iv_dextrose_energy():
    assert math.isclose(iv_dextrose_energy(25), 85.0)


def test_propofol_energy_from_volume():
    assert math.isclose(propofol_energy_from_volume(240), 264.0)


def test_energy_exposure_keeps_non_nutrition_separate():
    result = calculate_energy_exposure([
        EnergySource("Enteral nutrition", 1420, "NUTRITION"),
        EnergySource("Propofol", 264, "NON_NUTRITION"),
        EnergySource("IV dextrose", 85, "NON_NUTRITION"),
    ])
    assert result.nutrition_kcal == 1420
    assert result.non_nutrition_kcal == 349
    assert result.total_kcal == 1769


def test_invalid_energy_source_type_rejected():
    with pytest.raises(ValueError, match="Unknown energy source type"):
        calculate_energy_exposure([EnergySource("Unknown", 100, "OTHER")])


def test_negative_dextrose_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        iv_dextrose_energy(-1)
