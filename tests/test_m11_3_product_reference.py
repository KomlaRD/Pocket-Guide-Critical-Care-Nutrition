from pathlib import Path
import pytest
from core.delivery import ProductDatabase, amount_for_nutrient
ROOT=Path(__file__).parents[1]; DB=ProductDatabase(ROOT/"data/products"); APP=(ROOT/"app.py").read_text()
def test_runtime_catalogue_is_ghana_reference():
 assert len(DB.products)==15
 assert "ABB_GLU_15_GHREF" in DB.products and "ABB_PED_STD_GHREF" in DB.products
def test_runtime_policy_loaded():
 assert DB.product("ABB_GLU_15_GHREF").volume_calculation_eligible
 assert not DB.product("ABB_GLU_HSP_GHREF").volume_calculation_eligible
 assert not DB.product("ABB_GLU_BAR_GHREF").volume_calculation_eligible
def test_energy_target_math():
 amt,unit=amount_for_nutrient(DB,"ABB_GLU_15_GHREF","ENERGY",712)
 assert unit=="mL" and amt==pytest.approx(474,rel=1e-9)
def test_protein_target_math():
 amt,unit=amount_for_nutrient(DB,"ABB_ENSURE_PLUS_GHREF","PROTEIN",32)
 assert unit=="mL" and amt==pytest.approx(474,rel=1e-9)
def test_product_reference_page():
 assert '"products":"Product Reference"' in APP
 assert "It does not determine the nutrition prescription." in APP
 assert "Unknown / not reported" in APP
def test_delivery_blocks_non_liquid_products():
 assert "is not eligible for liquid delivery calculations" in APP
def test_demo_warning_removed():
 assert "bundled products are demonstration data only" not in APP
 assert "Replace demonstration compositions with verified manufacturer data" not in APP
