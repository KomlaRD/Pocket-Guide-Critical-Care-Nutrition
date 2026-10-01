from pathlib import Path
import pytest
from core.delivery import ProductDatabase,bolus_feeding_from_energy
ROOT=Path(__file__).parents[1]; DB=ProductDatabase(ROOT/"data/products"); APP=(ROOT/"app.py").read_text()
def test_bolus_math():
 p=bolus_feeding_from_energy(DB,"ABB_ENSURE_PLUS_GHREF",2100,6,100,"GASTRIC")
 assert p.volume_ml_day==pytest.approx(2100/350*237)
 assert p.volume_ml_feed==pytest.approx(p.volume_ml_day/6)
 assert p.protein_g_day==pytest.approx(p.volume_ml_day/237*16)
 assert p.protein_g_feed==pytest.approx(p.protein_g_day/6)
def test_small_bowel_bolus_blocked():
 with pytest.raises(ValueError,match="not appropriate for small-bowel"):
  bolus_feeding_from_energy(DB,"ABB_ENSURE_PLUS_GHREF",1800,6,90,"SMALL_BOWEL")
def test_nonliquid_bolus_blocked():
 with pytest.raises(ValueError,match="not eligible"):
  bolus_feeding_from_energy(DB,"ABB_GLU_HSP_GHREF",1800,6,90,"GASTRIC")
def test_feed_count_requires_whole_positive_number():
 with pytest.raises(ValueError,match="whole number"):
  bolus_feeding_from_energy(DB,"ABB_ENSURE_PLUS_GHREF",1800,5.5,90,"GASTRIC")
def test_no_universal_bolus_limit_claim():
 assert "not a universal safe-volume threshold" in APP
 assert "not an automatic tolerance limit" in APP
def test_bolus_inputs_include_site_and_feeds():
 assert '"bolus_feeds"' in APP and '"bolus_site"' in APP
 assert '"SMALL_BOWEL":"Small bowel"' in APP
def test_water_flush_not_inferred():
 assert "they are not inferred from formula volume" in APP
