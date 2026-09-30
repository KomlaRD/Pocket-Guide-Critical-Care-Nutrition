import csv
import json
from datetime import date
import pytest
from core.product_review import approve_batch, batch_digest
from test_product_ingest import batch


def attestation(tmp_path, folder, **overrides):
    review = {'batch_sha256': batch_digest(folder), 'submitted_by': 'Data collector',
              'reviewed_by': 'Independent clinical reviewer', 'reviewed_on': date.today().isoformat(),
              'checks': {key: True for key in ('source_authenticity','market_and_variant','serving_basis','every_supplied_nutrient','clinical_release_authorized')},
              'review_notes': 'Compared all supplied values, serving basis and market variant to the source.'}
    review.update(overrides)
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(review))
    return path


def test_explicit_review_produces_separate_candidate(tmp_path):
    folder = tmp_path / 'stage'; folder.mkdir(); batch(folder)
    review = attestation(tmp_path, folder)
    output = tmp_path / 'candidate'
    result = approve_batch(folder, review, output, {'ENERGY'})
    assert result['status'] == 'REVIEWED_IMPORT_CANDIDATE'
    with (output / 'products.csv').open() as f: assert next(csv.DictReader(f))['verification_status'] == 'VERIFIED_CURRENT'
    with (folder / 'products.csv').open() as f: assert next(csv.DictReader(f))['verification_status'] == 'PENDING_VERIFICATION'
    with (output / 'product_sources.csv').open() as f: assert next(csv.DictReader(f))['reviewed_by'] == 'Independent clinical reviewer'


def test_review_digest_detects_any_edit(tmp_path):
    folder = tmp_path / 'stage'; folder.mkdir(); batch(folder)
    review = attestation(tmp_path, folder)
    with (folder / 'product_nutrients.csv').open('a') as f: f.write('\n')
    with pytest.raises(ValueError, match='changed after review'): approve_batch(folder, review, tmp_path / 'out')


def test_reviewer_must_be_independent(tmp_path):
    folder = tmp_path / 'stage'; folder.mkdir(); batch(folder)
    review = attestation(tmp_path, folder, reviewed_by='DATA COLLECTOR')
    with pytest.raises(ValueError, match='different'): approve_batch(folder, review, tmp_path / 'out')


def test_every_check_is_mandatory(tmp_path):
    folder = tmp_path / 'stage'; folder.mkdir(); batch(folder)
    review = attestation(tmp_path, folder, checks={'source_authenticity': True})
    with pytest.raises(ValueError, match='reviewer confirmation'): approve_batch(folder, review, tmp_path / 'out')


def test_invalid_staging_cannot_be_approved(tmp_path):
    folder = tmp_path / 'stage'; folder.mkdir(); batch(folder)
    review = attestation(tmp_path, folder)
    (folder / 'products.csv').write_text((folder / 'products.csv').read_text().replace('PENDING_VERIFICATION,false', 'VERIFIED_CURRENT,true'))
    with pytest.raises(ValueError, match='Staging validation failed'): approve_batch(folder, review, tmp_path / 'out')


def test_existing_export_not_overwritten(tmp_path):
    folder = tmp_path / 'stage'; folder.mkdir(); batch(folder)
    review = attestation(tmp_path, folder)
    out = tmp_path / 'out'; out.mkdir(); (out / 'existing.txt').write_text('preserve')
    with pytest.raises(ValueError, match='empty'): approve_batch(folder, review, out)
    assert (out / 'existing.txt').read_text() == 'preserve'
