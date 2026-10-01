from pathlib import Path
import csv
from core.product_ingest import validate_staging
ROOT=Path(__file__).parents[1]; BATCH=ROOT/"staging"/"abbott_ghana_2026"
def rows(name):
 with (BATCH/name).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def test_original_scope_remains_present():
 names={x["product_name"] for x in rows("products.csv")}
 assert {"Ensure Original Shake","Ensure Plus Nutrition Shake","Glucerna Shake","PediaSure Enteral Formula 1.0 Cal"} <= names
def test_exact_manufacturer_basis_is_preserved():
 n=rows("product_nutrients.csv")
 assert all(float(x["basis_quantity"])>0 and x["basis_unit"] in {"mL","g"} for x in n)
def test_inequality_not_invented():
 n=rows("product_nutrients.csv"); keys={(x["product_id"],x["nutrient_id"]) for x in n}
 assert ("ABB_ENSURE_ORIGINAL_GHREF","FIBRE") not in keys
def test_uploaded_manufacturer_pdf_is_valid_traceable_source():
 assert validate_staging(BATCH).passed
def test_all_values_pending_independent_review():
 assert all(x["data_quality"]=="PENDING_VERIFICATION" for x in rows("product_nutrients.csv"))
 assert all(x["verification_status"]=="PENDING_VERIFICATION" for x in rows("product_sources.csv"))
