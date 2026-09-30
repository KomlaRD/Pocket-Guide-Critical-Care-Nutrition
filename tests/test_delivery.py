import math
from pathlib import Path
import pytest
from core.delivery import ProductDatabase, NutritionSource, calculate_delivery, volume_delivery_percent

DATA = Path(__file__).parents[1] / "data" / "products"
UNITS = {"ENERGY":"kcal", "PROTEIN":"g", "PHOSPHORUS":"mg", "MAGNESIUM":"mg"}

def test_database_loads():
    db = ProductDatabase(DATA)
    assert "DEMO_EN_15" in db.products
    assert db.product("DEMO_PROTEIN").basis_unit == "g"

def test_single_source_scaling():
    db = ProductDatabase(DATA)
    totals = calculate_delivery(db, [NutritionSource("DEMO_EN_15", 850, "mL")], UNITS)
    assert math.isclose(totals["ENERGY"].amount, 1275)
    assert math.isclose(totals["PROTEIN"].amount, 53.55)
    assert totals["PHOSPHORUS"].completeness == "COMPLETE"
    assert totals["MAGNESIUM"].completeness == "UNAVAILABLE"

def test_multiple_sources_partial_nutrient():
    db = ProductDatabase(DATA)
    totals = calculate_delivery(db, [
        NutritionSource("DEMO_EN_15", 500, "mL"),
        NutritionSource("DEMO_EN_HP", 500, "mL"),
    ], UNITS)
    assert math.isclose(totals["ENERGY"].amount, 1375)
    assert math.isclose(totals["PROTEIN"].amount, 69)
    assert math.isclose(totals["PHOSPHORUS"].amount, 450)
    assert totals["PHOSPHORUS"].completeness == "PARTIAL"

def test_modular_uses_grams():
    db = ProductDatabase(DATA)
    totals = calculate_delivery(db, [NutritionSource("DEMO_PROTEIN", 30, "g")], UNITS)
    assert math.isclose(totals["PROTEIN"].amount, 25.5)

def test_missing_is_not_zero():
    db = ProductDatabase(DATA)
    totals = calculate_delivery(db, [NutritionSource("DEMO_ONS", 200, "mL")], UNITS)
    assert totals["PHOSPHORUS"].amount is None
    assert totals["PHOSPHORUS"].completeness == "UNAVAILABLE"

def test_volume_delivery():
    assert math.isclose(volume_delivery_percent(850, 1200), 70.8333333333, rel_tol=1e-6)

def test_wrong_unit_rejected():
    db = ProductDatabase(DATA)
    with pytest.raises(ValueError, match="expects amounts"):
        calculate_delivery(db, [NutritionSource("DEMO_PROTEIN", 30, "mL")], UNITS)

def test_custom_and_combined_delivery():
    from core.delivery import CustomNutritionSource, calculate_custom_delivery, combine_nutrient_totals
    db = ProductDatabase(DATA)
    commercial = calculate_delivery(db, [NutritionSource("DEMO_EN_15", 500, "mL")], UNITS)
    custom = calculate_custom_delivery(CustomNutritionSource(
        "Custom feed", 200, "mL", 100, "mL",
        {"ENERGY": (100, "kcal"), "PROTEIN": (4, "g")}
    ), UNITS)
    total = combine_nutrient_totals([commercial, custom], UNITS)
    assert math.isclose(total["ENERGY"].amount, 950)
    assert math.isclose(total["PROTEIN"].amount, 39.5)
    assert total["PHOSPHORUS"].completeness == "PARTIAL"
