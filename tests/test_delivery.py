import math
from pathlib import Path
import pytest
from core.delivery import ProductDatabase, NutritionSource, calculate_delivery, volume_delivery_percent

DATA = Path(__file__).parents[1] / "data" / "products"
UNITS = {"ENERGY":"kcal", "PROTEIN":"g", "PHOSPHORUS":"mg", "MAGNESIUM":"mg"}

def test_database_loads():
    db = ProductDatabase(DATA)
    assert "ABB_GLU_15_GHREF" in db.products
    assert db.product("ABB_GLU_HSP_GHREF").basis_unit == "g"

def test_single_source_scaling():
    db = ProductDatabase(DATA)
    totals = calculate_delivery(db, [NutritionSource("ABB_GLU_15_GHREF", 850, "mL")], UNITS)
    assert math.isclose(totals["ENERGY"].amount, 850/237*356)
    assert math.isclose(totals["PROTEIN"].amount, 850/237*19.6)
    assert totals["PHOSPHORUS"].completeness == "COMPLETE"
    assert totals["MAGNESIUM"].completeness == "COMPLETE"

def test_multiple_sources_partial_nutrient():
    db = ProductDatabase(DATA)
    totals = calculate_delivery(db, [
        NutritionSource("ABB_GLU_15_GHREF", 500, "mL"),
        NutritionSource("ABB_ENSURE_PLUS_GHREF", 500, "mL"),
    ], UNITS)
    assert math.isclose(totals["ENERGY"].amount, 500/237*(356+350))
    assert math.isclose(totals["PROTEIN"].amount, 500/237*(19.6+16))
    assert math.isclose(totals["PHOSPHORUS"].amount, 500/237*(240+250))
    assert totals["PHOSPHORUS"].completeness == "COMPLETE"

def test_modular_uses_grams():
    db = ProductDatabase(DATA)
    totals = calculate_delivery(db, [NutritionSource("ABB_GLU_HSP_GHREF", 30, "g")], UNITS)
    assert math.isclose(totals["PROTEIN"].amount, 20)

def test_missing_is_not_zero():
    db = ProductDatabase(DATA)
    totals = calculate_delivery(db, [NutritionSource("ABB_ENSURE_PLUS_GHREF", 200, "mL")], UNITS)
    assert math.isclose(totals["PHOSPHORUS"].amount, 200/237*250)
    assert totals["PHOSPHORUS"].completeness == "COMPLETE"

def test_volume_delivery():
    assert math.isclose(volume_delivery_percent(850, 1200), 70.8333333333, rel_tol=1e-6)

def test_wrong_unit_rejected():
    db = ProductDatabase(DATA)
    with pytest.raises(ValueError, match="expects amounts"):
        calculate_delivery(db, [NutritionSource("ABB_GLU_HSP_GHREF", 30, "mL")], UNITS)

def test_custom_and_combined_delivery():
    from core.delivery import CustomNutritionSource, calculate_custom_delivery, combine_nutrient_totals
    db = ProductDatabase(DATA)
    commercial = calculate_delivery(db, [NutritionSource("ABB_GLU_15_GHREF", 500, "mL")], UNITS)
    custom = calculate_custom_delivery(CustomNutritionSource(
        "Custom feed", 200, "mL", 100, "mL",
        {"ENERGY": (100, "kcal"), "PROTEIN": (4, "g")}
    ), UNITS)
    total = combine_nutrient_totals([commercial, custom], UNITS)
    assert math.isclose(total["ENERGY"].amount, 500/237*356+200)
    assert math.isclose(total["PROTEIN"].amount, 500/237*19.6+8)
    assert total["PHOSPHORUS"].completeness == "PARTIAL"
