from pathlib import Path
import pytest
from core.delivery import ProductDatabase,compare_liquid_formula,continuous_feeding_from_energy
ROOT=Path(__file__).parents[1]; DB=ProductDatabase(ROOT/"data/products"); APP=(ROOT/"app.py").read_text()
def test_glucerna_energy_density():
 x=compare_liquid_formula(DB,"ABB_GLU_15_GHREF")
 assert x.kcal_per_ml==pytest.approx(356/237)
 assert x.protein_g_per_1000_kcal==pytest.approx(19.6/356*1000)
def test_comparison_preserves_missing_values():
 x=compare_liquid_formula(DB,"ABB_GLU_30P_GHREF")
 assert x.water_ml_per_1000_kcal is None
def test_non_liquid_comparison_rejected():
 with pytest.raises(ValueError,match="not eligible"):
  compare_liquid_formula(DB,"ABB_GLU_HSP_GHREF")
def test_continuous_energy_plan():
 p=continuous_feeding_from_energy(DB,"ABB_GLU_15_GHREF",1800,24,90)
 assert p.volume_ml_day==pytest.approx(1800/356*237)
 assert p.rate_ml_hr==pytest.approx(p.volume_ml_day/24)
 assert p.protein_g_day==pytest.approx(p.volume_ml_day/237*19.6)
 assert p.protein_adequacy_percent==pytest.approx(p.protein_g_day/90*100)
def test_feeding_hours_validation():
 with pytest.raises(ValueError,match="no more than 24"):
  continuous_feeding_from_energy(DB,"ABB_GLU_15_GHREF",1800,25,90)
def test_ui_separates_energy_and_protein():
 assert '"compare_products":"Compare Formulas"' in APP
 assert "Meeting the energy target does not mean the protein target is met." in APP
 assert "does not select a preferred formula" in APP
def test_selector_separate_from_evidence():
 section=APP[APP.index("input.page === 'compare_products'"):APP.index("input.page === 'delivery'")]
 assert 'class_="question-zone"' in section
 assert 'class_="evidence-zone"' in section
