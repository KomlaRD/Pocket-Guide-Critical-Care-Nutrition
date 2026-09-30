"""Offline, explicit two-person approval gate for staged manufacturer product data.

Approval is an attestation by a qualified human reviewer, NOT automated source verification.
Output is a separate import candidate; live bundled products are never silently modified.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from .product_ingest import validate_staging

FILES = ("products.csv", "product_preparations.csv", "product_nutrients.csv", "product_sources.csv")


def batch_digest(folder: str | Path) -> str:
    """Bind the review to exact CSV bytes, including source provenance and nutrients."""
    folder = Path(folder)
    digest = hashlib.sha256()
    for filename in FILES:
        raw = (folder / filename).read_bytes()
        digest.update(filename.encode('utf-8') + b"\0" + len(raw).to_bytes(8, 'big') + raw)
    return digest.hexdigest()


def _rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def approve_batch(staging, attestation, output, known_nutrients=None):
    """Create reviewed import candidate only after explicit independent attestation.

    Requires review of ALL supplied nutrients, sources, formulation and market.
    No approval is inferred from successful structural validation.
    """
    staging, attestation, output = Path(staging), Path(attestation), Path(output)
    report = validate_staging(staging, known_nutrients)
    if not report.passed:
        raise ValueError('Staging validation failed: ' + '; '.join(f.message for f in report.findings if f.level == 'ERROR'))
    review = json.loads(attestation.read_text(encoding='utf-8'))
    expected = batch_digest(staging)
    if review.get('batch_sha256') != expected:
        raise ValueError('Source CSVs changed after review; review the current batch and regenerate its SHA-256 digest.')
    submitter = str(review.get('submitted_by', '')).strip()
    reviewer = str(review.get('reviewed_by', '')).strip()
    if not submitter or not reviewer or submitter.casefold() == reviewer.casefold():
        raise ValueError('A named reviewer different from the submitter is required.')
    try:
        reviewed_on = date.fromisoformat(review.get('reviewed_on', ''))
        if reviewed_on > date.today(): raise ValueError
    except (ValueError, TypeError):
        raise ValueError('reviewed_on must be a valid non-future ISO date.') from None
    required_checks = ('source_authenticity', 'market_and_variant', 'serving_basis', 'every_supplied_nutrient', 'clinical_release_authorized')
    missing = [key for key in required_checks if review.get('checks', {}).get(key) is not True]
    if missing: raise ValueError('Explicit independent reviewer confirmation required: ' + ', '.join(missing))
    if not str(review.get('review_notes', '')).strip():
        raise ValueError('Document source comparison and any limitations in review_notes.')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output folder must be empty; reviewed exports cannot silently overwrite existing data.')
    output.mkdir(parents=True, exist_ok=True)
    try:
        for filename in FILES:
            columns, rows = _rows(staging / filename)
            if filename == 'products.csv':
                for row in rows:
                    row['verification_status'] = 'VERIFIED_CURRENT'
                    row['active'] = 'true'
            elif filename == 'product_nutrients.csv':
                for row in rows: row['data_quality'] = 'VERIFIED_CURRENT'
            elif filename == 'product_sources.csv':
                for row in rows:
                    row['verification_status'] = 'VERIFIED_CURRENT'
                    row['reviewed_by'] = reviewer
                    row['reviewed_on'] = reviewed_on.isoformat()
            with (output / filename).open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader(); writer.writerows(rows)
        manifest = {'schema_version': 1, 'status': 'REVIEWED_IMPORT_CANDIDATE',
                    'batch_sha256': expected, 'submitted_by': submitter, 'reviewed_by': reviewer,
                    'reviewed_on': reviewed_on.isoformat(), 'checks': {k: True for k in required_checks},
                    'review_notes': review['review_notes'], 'products': report.product_count,
                    'nutrient_records': report.nutrient_count,
                    'caution': 'Human attestation; not automated proof of source authenticity. Review deployment controls before clinical use.'}
        manifest['export_file_sha256'] = {filename: hashlib.sha256((output / filename).read_bytes()).hexdigest() for filename in FILES}
        (output / 'review_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    except Exception:
        for file in output.iterdir():
            if file.is_file(): file.unlink()
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description='Generate a separate human-reviewed nutrition product import candidate.')
    parser.add_argument('staging', type=Path)
    parser.add_argument('attestation', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--nutrient-catalog', type=Path)
    args = parser.parse_args()
    catalog = None
    if args.nutrient_catalog:
        with args.nutrient_catalog.open(encoding='utf-8', newline='') as handle:
            catalog = {r['nutrient_id'] for r in csv.DictReader(handle)}
    print(json.dumps(approve_batch(args.staging, args.attestation, args.output, catalog), indent=2))

if __name__ == '__main__': main()
