import csv
import hashlib
import json
from datetime import date
from pathlib import Path
import pytest
from core.product_review import approve_batch
from core.product_promotion import promote_candidate
from test_product_ingest import batch
from test_product_review import attestation

DATA=Path(__file__).resolve().parents[1]/'data'
FILES=('products.csv','product_preparations.csv','product_nutrients.csv','product_sources.csv')


def prepared(tmp_path):
    staging=tmp_path/'staging'; staging.mkdir(); batch(staging)
    reviewed=tmp_path/'reviewed'
    manifest=approve_batch(staging,attestation(tmp_path,staging),reviewed,{'ENERGY'})
    authorization={'candidate_batch_sha256':manifest['batch_sha256'],
        'candidate_file_sha256':{f:hashlib.sha256((reviewed/f).read_bytes()).hexdigest() for f in FILES},
        'released_by':'Institutional authorizer','released_on':date.today().isoformat(),
        'checks':{'institutional_release_approved':True,'catalog_conflicts_checked':True},
        'release_notes':'Institutional authorization recorded; compare against original manufacturer source.'}
    approval=tmp_path/'authorization.json'; approval.write_text(json.dumps(authorization))
    return reviewed, approval, authorization


def test_creates_new_audited_catalog_without_touching_original(tmp_path):
    reviewed,approval,_=prepared(tmp_path)
    original=(DATA/'products/products.csv').read_bytes()
    output=tmp_path/'release'
    result=promote_candidate(reviewed,DATA,approval,output)
    assert result['status']=='RELEASE_CANDIDATE_NOT_DEPLOYED'
    assert result['audit']['passed']
    assert result['added_products']==1
    assert (DATA/'products/products.csv').read_bytes()==original
    assert (output/'release_manifest.json').exists()
    with (output/'products/products.csv').open() as f:
        assert len(list(csv.DictReader(f)))==5


def test_refuses_tampered_candidate(tmp_path):
    reviewed,approval,_=prepared(tmp_path)
    with (reviewed/'product_nutrients.csv').open('a') as f:f.write('\n')
    with pytest.raises(ValueError,match='digests differ'):
        promote_candidate(reviewed,DATA,approval,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_requires_distinct_release_authorizer(tmp_path):
    reviewed,approval,data=prepared(tmp_path)
    data['released_by']='Independent clinical reviewer'; approval.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='distinct'):
        promote_candidate(reviewed,DATA,approval,tmp_path/'out')


def test_requires_explicit_release_checks(tmp_path):
    reviewed,approval,data=prepared(tmp_path)
    data['checks']['institutional_release_approved']=False; approval.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='Explicit'):
        promote_candidate(reviewed,DATA,approval,tmp_path/'out')


def test_refuses_identity_collision(tmp_path):
    reviewed,approval,data=prepared(tmp_path)
    products=reviewed/'products.csv'
    content=products.read_text()
    # Existing demonstration product ID must not be replaced, even by an approved export.
    products.write_text(content.replace('P1,','DEMO_EN_15,'))
    data['candidate_file_sha256']['products.csv']=hashlib.sha256(products.read_bytes()).hexdigest()
    approval.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='collision'):
        promote_candidate(reviewed,DATA,approval,tmp_path/'out')


def test_refuses_existing_output(tmp_path):
    reviewed,approval,_=prepared(tmp_path)
    output=tmp_path/'out'; output.mkdir()
    with pytest.raises(ValueError,match='must not already exist'):
        promote_candidate(reviewed,DATA,approval,output)


def test_cannot_reauthorize_post_review_edit(tmp_path):
    reviewed, approval, data = prepared(tmp_path)
    product = reviewed/'products.csv'
    product.write_text(product.read_text().replace('Formula','Changed Formula'))
    data['candidate_file_sha256']['products.csv'] = hashlib.sha256(product.read_bytes()).hexdigest()
    approval.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='reviewed export manifest'):
        promote_candidate(reviewed, DATA, approval, tmp_path/'out')
