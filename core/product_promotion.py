"""M6.3: controlled, offline promotion into a NEW audited product catalog.

Never changes live datasets; institutional deployment is a separate explicit action.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from datetime import date
from pathlib import Path
from .data_quality import audit_data
from .product_review import FILES


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _table(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or ()), list(reader)


def promote_candidate(candidate, data_root, authorization, output):
    """Merge reviewed candidate into a separate full data tree after independent release authorization."""
    candidate, data_root, authorization, output = map(Path, (candidate, data_root, authorization, output))
    if not data_root.is_dir() or not (data_root/'products').is_dir():
        raise ValueError('A complete existing data directory is required.')
    if output.exists():
        raise ValueError('Output path must not already exist; never overwrite a previous release.')
    if output.resolve() == data_root.resolve() or data_root.resolve() in output.resolve().parents:
        raise ValueError('Output must be outside the existing data tree.')
    manifest = json.loads((candidate/'review_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('status') != 'REVIEWED_IMPORT_CANDIDATE' or manifest.get('schema_version') != 1:
        raise ValueError('Expected an M6.2 independently reviewed candidate manifest.')
    if not manifest.get('reviewed_by') or not manifest.get('batch_sha256'):
        raise ValueError('Candidate review provenance is incomplete.')
    approval = json.loads(authorization.read_text(encoding='utf-8'))
    operator = str(approval.get('released_by', '')).strip()
    if not operator or operator.casefold() in {str(manifest.get('submitted_by','')).casefold(), str(manifest['reviewed_by']).casefold()}:
        raise ValueError('A distinct named release authorizer is required.')
    if approval.get('candidate_batch_sha256') != manifest['batch_sha256']:
        raise ValueError('Release authorization does not match the reviewed batch digest.')
    try:
        released_on = date.fromisoformat(approval['released_on'])
        if released_on > date.today() or released_on < date.fromisoformat(manifest['reviewed_on']): raise ValueError
    except (KeyError, ValueError, TypeError):
        raise ValueError('released_on must be valid, non-future and not earlier than review.') from None
    if approval.get('checks', {}).get('institutional_release_approved') is not True or approval.get('checks', {}).get('catalog_conflicts_checked') is not True:
        raise ValueError('Explicit institutional release and catalog conflict checks are required.')
    if not str(approval.get('release_notes','')).strip():
        raise ValueError('Document the release authorization and limitations in release_notes.')
    original_audit = audit_data(data_root)
    if not original_audit.passed:
        raise ValueError('Existing catalog audit failed; resolve structural errors before promotion.')
    merged = {}
    for filename in FILES:
        oldcols, oldrows = _table(data_root/'products'/filename)
        newcols, newrows = _table(candidate/filename)
        if not newrows and filename == 'products.csv': raise ValueError('Candidate contains no products.')
        if not set(oldcols).issubset(newcols):
            raise ValueError(f'{filename}: candidate is missing existing catalog columns.')
        merged[filename] = (newcols, oldrows, newrows)
    existing = {f: rows for f, (_, rows, _) in merged.items()}
    incoming = {f: rows for f, (_, _, rows) in merged.items()}
    identities = {'products.csv':('product_id',), 'product_preparations.csv':('preparation_id',),
                  'product_nutrients.csv':('product_id','preparation_id','nutrient_id'), 'product_sources.csv':('source_id',)}
    for filename, keys in identities.items():
        old_ids = {tuple(r.get(k) for k in keys) for r in existing[filename]}
        new_ids = [tuple(r.get(k) for k in keys) for r in incoming[filename]]
        if len(set(new_ids)) != len(new_ids) or any(not all(key) for key in new_ids):
            raise ValueError(f'{filename}: duplicate or incomplete candidate identities.')
        conflict = old_ids.intersection(new_ids)
        if conflict: raise ValueError(f'{filename}: existing catalog identity collision: {sorted(conflict)[0]}. No silent replacements allowed.')
    if not incoming['product_sources.csv']:
        raise ValueError('Candidate requires traceable product sources.')
    for row in incoming['products.csv']:
        if row.get('verification_status') != 'VERIFIED_CURRENT' or row.get('active','').lower() != 'true':
            raise ValueError('Candidate contains an inactive or unreviewed product.')
    for row in incoming['product_sources.csv']:
        if row.get('verification_status') != 'VERIFIED_CURRENT' or row.get('reviewed_by') != manifest['reviewed_by']:
            raise ValueError('Candidate source review does not match its manifest.')
    # Do not trust a candidate that was edited after approval: the release authorizer
    # must bind the SHA256 of every exported CSV, not just the original staging digest.
    expected = approval.get('candidate_file_sha256', {})
    if manifest.get('export_file_sha256') != expected:
        raise ValueError('Candidate CSV digests do not match the independently reviewed export manifest.')
    if set(expected) != set(FILES) or any(expected[f] != _digest(candidate/f) for f in FILES):
        raise ValueError('Candidate CSV digests differ from release authorization; review the exact export.')
    # Build and audit in a private temporary directory before publishing any output.
    with tempfile.TemporaryDirectory(prefix='pocket-release-') as temp:
        staged = Path(temp)/'data'
        shutil.copytree(data_root, staged)
        for filename, (columns, oldrows, newrows) in merged.items():
            with (staged/'products'/filename).open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
                writer.writeheader(); writer.writerows(oldrows+newrows)
        report = audit_data(staged)
        if not report.passed:
            raise ValueError('Merged catalog audit failed: '+'; '.join(issue.message for issue in report.errors))
        release = {'schema_version':1,'status':'RELEASE_CANDIDATE_NOT_DEPLOYED',
                   'reviewed_batch_sha256':manifest['batch_sha256'],
                   'candidate_file_sha256':expected,'reviewed_by':manifest['reviewed_by'],
                   'released_by':operator,'released_on':released_on.isoformat(),
                   'release_notes':approval['release_notes'],
                   'added_products':len(incoming['products.csv']),
                   'added_nutrient_records':len(incoming['product_nutrients.csv']),
                   'audit':{'passed':report.passed,'errors':len(report.errors),'warnings':len(report.warnings)},
                   'warning':'Not deployed. Institutional clinical approval and local product verification remain human responsibilities.'}
        (staged/'release_manifest.json').write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8')
        shutil.copytree(staged, output)
    return release


def main():
    parser=argparse.ArgumentParser(description='Create a separately audited product catalog release candidate; never auto-deploy.')
    parser.add_argument('candidate',type=Path); parser.add_argument('data_root',type=Path)
    parser.add_argument('authorization',type=Path); parser.add_argument('output',type=Path)
    args=parser.parse_args()
    print(json.dumps(promote_candidate(args.candidate,args.data_root,args.authorization,args.output),indent=2))

if __name__ == '__main__': main()
