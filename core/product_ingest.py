"""Offline manufacturer-product staging; never self-certifies clinical data."""
from __future__ import annotations
import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_PRODUCT = ('product_id','manufacturer','product_name','category','subcategory','route','physical_form','market','verification_status','active')
REQUIRED_PREP = ('preparation_id','product_id','preparation_name','preparation_type','basis_quantity','basis_unit','notes')
REQUIRED_NUTRIENT = ('product_id','preparation_id','nutrient_id','amount','unit','basis_quantity','basis_unit','data_quality')
REQUIRED_SOURCE = ('source_id','product_id','source_type','source_title','verification_status','notes','source_url','accessed_on','document_version','reviewed_by','reviewed_on')

@dataclass(frozen=True)
class Finding:
    level: str
    table: str
    row: int
    message: str

@dataclass(frozen=True)
class StagingReport:
    findings: tuple[Finding, ...]
    product_count: int
    nutrient_count: int
    @property
    def passed(self): return not any(f.level == 'ERROR' for f in self.findings)
    def as_dict(self): return {'passed':self.passed,'product_count':self.product_count,'nutrient_count':self.nutrient_count,'findings':[asdict(f) for f in self.findings]}

def read_table(path, required, findings):
    if not path.exists():
        findings.append(Finding('ERROR',path.name,0,'Required CSV is missing.'))
        return []
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        missing=set(required)-set(reader.fieldnames or [])
        if missing:
            findings.append(Finding('ERROR',path.name,1,'Missing columns: '+', '.join(sorted(missing))))
            return []
        return list(reader)

def validate_staging(directory: str | Path, known_nutrients: set[str] | None = None) -> StagingReport:
    """Validate staging files. A successful check means structurally ready for review, NOT verified."""
    folder=Path(directory); findings=[]
    tables={
      'products':read_table(folder/'products.csv',REQUIRED_PRODUCT,findings),
      'preparations':read_table(folder/'product_preparations.csv',REQUIRED_PREP,findings),
      'nutrients':read_table(folder/'product_nutrients.csv',REQUIRED_NUTRIENT,findings),
      'sources':read_table(folder/'product_sources.csv',REQUIRED_SOURCE,findings),
    }
    def error(table,row,msg): findings.append(Finding('ERROR',table,row,msg))
    if not tables['products']: error('products',0,'No products to validate; populate a staging batch first.')
    def unique(table,fields):
        seen=set()
        for index,row in enumerate(tables[table],2):
            key=tuple((row.get(f) or '').strip() for f in fields)
            if not all(key): error(table,index,'Missing identity field: '+', '.join(fields))
            elif key in seen: error(table,index,'Duplicate identity: '+repr(key))
            seen.add(key)
    for table,fields in [('products',('product_id',)),('preparations',('preparation_id',)),('sources',('source_id',)),('nutrients',('product_id','preparation_id','nutrient_id'))]: unique(table,fields)
    products={r['product_id'] for r in tables['products']}; preps={r['preparation_id']:r['product_id'] for r in tables['preparations']}
    for table in ('preparations','nutrients','sources'):
        for i,r in enumerate(tables[table],2):
            if r['product_id'] not in products: error(table,i,'Unknown product_id: '+r['product_id'])
    for i,r in enumerate(tables['nutrients'],2):
        if r['preparation_id'] not in preps or preps.get(r['preparation_id']) != r['product_id']: error('nutrients',i,'Preparation must belong to this product.')
        if known_nutrients is not None and r['nutrient_id'] not in known_nutrients: error('nutrients',i,'Unknown nutrient_id: '+r['nutrient_id'])
        for key in ('amount','basis_quantity'):
            try:
                if float(r[key]) < 0 or (key == 'basis_quantity' and float(r[key]) == 0): raise ValueError
            except ValueError: error('nutrients',i,key+' must be a valid nonnegative number (basis > 0).')
        if not r['unit'].strip() or not r['basis_unit'].strip(): error('nutrients',i,'Nutrient and basis units are required.')
        if r['data_quality'] != 'PENDING_VERIFICATION': error('nutrients',i,'New composition must remain PENDING_VERIFICATION until independent review.')
    for i,r in enumerate(tables['preparations'],2):
        try:
            if float(r['basis_quantity']) <= 0: raise ValueError
        except ValueError: error('preparations',i,'basis_quantity must be positive.')
    for i,r in enumerate(tables['products'],2):
        if r['verification_status'] != 'PENDING_VERIFICATION': error('products',i,'Staged products must remain PENDING_VERIFICATION.')
        if r['active'].lower() != 'false': error('products',i,'Staged products must be inactive pending verification.')
        if not r['market'].strip(): error('products',i,'Market/country is required.')
    sourced={r['product_id'] for r in tables['sources']}
    for i,r in enumerate(tables['products'],2):
        if r['product_id'] not in sourced: error('products',i,'At least one traceable source is required.')
    for i,r in enumerate(tables['sources'],2):
        if r['verification_status'] != 'PENDING_VERIFICATION': error('sources',i,'Staged sources cannot claim verification.')
        source_type=(r.get('source_type') or '').strip()
        source_url=(r.get('source_url') or '').strip()
        if source_type == 'MANUFACTURER_PDF':
            if source_url:
                url=urlparse(source_url)
                if url.scheme != 'https' or not url.netloc: error('sources',i,'If supplied, manufacturer PDF URL must be HTTPS.')
            if not (r.get('document_version') or '').strip(): error('sources',i,'Uploaded manufacturer PDF requires a document/page locator.')
        else:
            url=urlparse(source_url)
            if url.scheme != 'https' or not url.netloc: error('sources',i,'A direct HTTPS source URL is required.')
        try:
            if date.fromisoformat(r['accessed_on']) > date.today(): raise ValueError
        except ValueError: error('sources',i,'accessed_on must be a valid non-future ISO date.')
        if not r['source_title'].strip() or not r['document_version'].strip(): error('sources',i,'Source title and version/date are required.')
        if r['reviewed_by'].strip() or r['reviewed_on'].strip(): error('sources',i,'Review fields must remain blank until an independent review occurs.')
    if tables['products'] and not tables['nutrients']: findings.append(Finding('WARNING','nutrients',0,'No nutrient values supplied; composition is unknown.'))
    return StagingReport(tuple(findings),len(tables['products']),len(tables['nutrients']))

def main():
    parser=argparse.ArgumentParser(description='Validate unverified manufacturer product staging CSVs; does not approve clinical use.')
    parser.add_argument('directory',type=Path)
    parser.add_argument('--nutrient-catalog',type=Path,help='Path to bundled nutrients.csv')
    parser.add_argument('--json',type=Path,help='Write machine-readable validation report')
    args=parser.parse_args()
    catalog=None
    if args.nutrient_catalog:
        with args.nutrient_catalog.open(encoding='utf-8',newline='') as f: catalog={r['nutrient_id'] for r in csv.DictReader(f)}
    report=validate_staging(args.directory,catalog)
    payload=json.dumps(report.as_dict(),indent=2)
    if args.json: args.json.write_text(payload+'\n',encoding='utf-8')
    print(payload)
    raise SystemExit(0 if report.passed else 1)
if __name__ == '__main__': main()
