from pathlib import Path
import csv
from core.product_ingest import validate_staging
ROOT=Path(__file__).parents[1]; B=ROOT/"staging"/"abbott_ghana_2026"
def rows(n):
 with (B/n).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def test_catalogue_size_and_glucerna_forms():
 p=rows("products.csv"); assert len(p)==15
 names={x["product_name"] for x in p}
 expected={"Glucerna 1.0 Cal","Glucerna 1.2 Cal","Glucerna 1.5 Cal","Glucerna 30g Protein Shake","Glucerna Hunger Smart Meal Size Shake","Glucerna Hunger Smart Powder","Glucerna Hunger Smart Shake","Glucerna Mini Treats Bars","Glucerna Shake","Glucerna Snack Bars","Glucerna Snack Shake","Glucerna Therapeutic Nutrition Shake"}
 assert expected <= names
def test_standard_pediasure_only():
 names={x["product_name"] for x in rows("products.csv") if "PediaSure" in x["product_name"]}
 assert names=={"PediaSure Enteral Formula 1.0 Cal"}
def test_ghana_reference_market():
 assert all(x["market"]=="GHANA_REFERENCE" for x in rows("products.csv"))
def test_solid_and_powder_not_liquid_volume_calculations():
 p={x["product_id"]:x for x in rows("products.csv")}; pol={x["product_id"]:x for x in rows("product_use_policy.csv")}
 for pid,x in p.items():
  if x["physical_form"] in {"BAR","POWDER"}: assert pol[pid]["volume_calculation_eligible"]=="false"
def test_key_source_values():
 n={(x["product_id"],x["nutrient_id"]):(x["amount"],x["basis_quantity"],x["basis_unit"]) for x in rows("product_nutrients.csv")}
 assert n[("ABB_GLU_10_GHREF","ENERGY")]==("237","237","mL")
 assert n[("ABB_GLU_12_GHREF","PROTEIN")]==("14.2","237","mL")
 assert n[("ABB_GLU_15_GHREF","ENERGY")]==("356","237","mL")
 assert n[("ABB_GLU_30P_GHREF","PROTEIN")]==("30","330","mL")
 assert n[("ABB_GLU_HSP_GHREF","PROTEIN")]==("22","33","g")
 assert n[("ABB_PED_STD_GHREF","ENERGY")]==("240","237","mL")
def test_staging_validates(): assert validate_staging(B).passed
