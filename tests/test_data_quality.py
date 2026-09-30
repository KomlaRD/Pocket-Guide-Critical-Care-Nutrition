from pathlib import Path
import csv, shutil
from core.data_quality import audit_data
ROOT=Path(__file__).resolve().parents[1]

def test_bundled_data_has_no_structural_errors():
    report=audit_data(ROOT/'data')
    assert report.passed, [x.message for x in report.errors]
    assert any('demonstration composition' in x.message for x in report.warnings)

def test_duplicate_product_id_fails_closed(tmp_path):
    shutil.copytree(ROOT/'data', tmp_path/'data')
    p=tmp_path/'data/products/products.csv'
    rows=list(csv.DictReader(p.open()))
    with p.open('a') as f:
        r=rows[0]; f.write(','.join(r[k] for k in rows[0].keys())+'\n')
    report=audit_data(tmp_path/'data')
    assert not report.passed
    assert any('duplicate product_id' in x.message for x in report.errors)

def test_orphan_product_nutrient_fails_closed(tmp_path):
    shutil.copytree(ROOT/'data', tmp_path/'data')
    p=tmp_path/'data/products/product_nutrients.csv'
    rows=list(csv.DictReader(p.open()))
    rows[0]['product_id']='MISSING_PRODUCT'
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    report=audit_data(tmp_path/'data')
    assert not report.passed
    assert any('orphan product_id' in x.message for x in report.errors)
