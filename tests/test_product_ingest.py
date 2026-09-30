import csv
from pathlib import Path
from core.product_ingest import validate_staging

HEADERS={
'products.csv':'product_id,manufacturer,product_name,category,subcategory,route,physical_form,market,verification_status,active',
'product_preparations.csv':'preparation_id,product_id,preparation_name,preparation_type,basis_quantity,basis_unit,notes',
'product_nutrients.csv':'product_id,preparation_id,nutrient_id,amount,unit,basis_quantity,basis_unit,data_quality',
'product_sources.csv':'source_id,product_id,source_type,source_title,verification_status,notes,source_url,accessed_on,document_version,reviewed_by,reviewed_on'}
ROWS={
'products.csv':'P1,Manufacturer,Formula,ENTERAL_FORMULA,STANDARD,ENTERAL,LIQUID,GH,PENDING_VERIFICATION,false',
'product_preparations.csv':'PREP1,P1,Ready to feed,READY_TO_FEED,100,mL,',
'product_nutrients.csv':'P1,PREP1,ENERGY,100,kcal,100,mL,PENDING_VERIFICATION',
'product_sources.csv':'S1,P1,MANUFACTURER,Product technical sheet,PENDING_VERIFICATION,,https://example.com/technical.pdf,2026-09-01,2026 edition,,'}

def batch(tmp_path):
    for filename,header in HEADERS.items(): (tmp_path/filename).write_text(header+'\n'+ROWS[filename]+'\n')
    return tmp_path

def test_valid_staging_is_not_clinically_verified(tmp_path):
    report=validate_staging(batch(tmp_path),{'ENERGY'})
    assert report.passed and report.product_count == 1 and report.nutrient_count == 1

def test_staging_cannot_self_approve(tmp_path):
    batch(tmp_path)
    p=tmp_path/'products.csv';p.write_text(p.read_text().replace('PENDING_VERIFICATION,false','VERIFIED_CURRENT,true'))
    assert not validate_staging(tmp_path).passed

def test_orphan_preparation_rejected(tmp_path):
    batch(tmp_path)
    p=tmp_path/'product_nutrients.csv';p.write_text(p.read_text().replace('PREP1','UNKNOWN'))
    assert not validate_staging(tmp_path).passed

def test_missing_source_rejected(tmp_path):
    batch(tmp_path)
    p=tmp_path/'product_sources.csv';p.write_text(HEADERS['product_sources.csv']+'\n')
    assert not validate_staging(tmp_path).passed

def test_unknown_nutrient_rejected(tmp_path):
    assert not validate_staging(batch(tmp_path),{'PROTEIN'}).passed

def test_negative_nutrient_rejected(tmp_path):
    batch(tmp_path)
    p=tmp_path/'product_nutrients.csv';p.write_text(p.read_text().replace(',100,kcal,',',-1,kcal,'))
    assert not validate_staging(tmp_path).passed

def test_unreviewed_staging_rejects_review_claim(tmp_path):
    batch(tmp_path)
    p=tmp_path/'product_sources.csv';p.write_text(p.read_text().replace('2026 edition,,','2026 edition,Reviewer,2026-09-01'))
    assert not validate_staging(tmp_path).passed

def test_empty_batch_not_reported_as_valid(tmp_path):
    for name,header in HEADERS.items(): (tmp_path/name).write_text(header+'\n')
    assert not validate_staging(tmp_path).passed
