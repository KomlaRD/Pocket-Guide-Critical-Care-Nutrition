from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv

@dataclass(frozen=True)
class AuditIssue:
    severity: str
    dataset: str
    message: str

@dataclass(frozen=True)
class AuditReport:
    issues: tuple[AuditIssue, ...]
    @property
    def errors(self): return tuple(x for x in self.issues if x.severity == 'ERROR')
    @property
    def warnings(self): return tuple(x for x in self.issues if x.severity == 'WARNING')
    @property
    def passed(self): return not self.errors

def _rows(path: Path):
    with path.open(newline='', encoding='utf-8') as f: return list(csv.DictReader(f))

def _unique(rows, key, dataset, issues):
    seen=set()
    for i,r in enumerate(rows,2):
        v=(r.get(key) or '').strip()
        if not v: issues.append(AuditIssue('ERROR',dataset,f'row {i}: missing {key}'))
        elif v in seen: issues.append(AuditIssue('ERROR',dataset,f'duplicate {key}: {v}'))
        seen.add(v)

def audit_data(root: Path) -> AuditReport:
    root=Path(root); issues=[]
    files={
      'products':root/'products/products.csv','preparations':root/'products/product_preparations.csv',
      'product_nutrients':root/'products/product_nutrients.csv','product_sources':root/'products/product_sources.csv',
      'nutrients':root/'metadata/nutrients.csv','guideline_sources':root/'guidelines/guideline_sources.csv',
      'recommendations':root/'guidelines/recommendations.csv','rules':root/'guidelines/recommendation_rules.csv',
      'reference_sources':root/'reference/reference_sources.csv','reference_items':root/'reference/reference_items.csv'}
    data={}
    for name,p in files.items():
        if not p.exists(): issues.append(AuditIssue('ERROR',name,f'missing dataset: {p.name}'))
        else: data[name]=_rows(p)
    if issues: return AuditReport(tuple(issues))
    ids={'products':'product_id','preparations':'preparation_id','product_sources':'source_id',
         'nutrients':'nutrient_id','guideline_sources':'guideline_code','recommendations':'recommendation_id','rules':'rule_id',
         'reference_sources':'source_id','reference_items':'reference_id'}
    for d,k in ids.items(): _unique(data[d],k,d,issues)
    seen=set()
    for i,r in enumerate(data['product_nutrients'],2):
        key=(r.get('product_id'),r.get('preparation_id'),r.get('nutrient_id'))
        if key in seen: issues.append(AuditIssue('ERROR','product_nutrients',f'row {i}: duplicate product/preparation/nutrient combination: {key}'))
        seen.add(key)
    product_ids={r['product_id'] for r in data['products']}; prep_ids={r['preparation_id'] for r in data['preparations']}; nutrient_ids={r['nutrient_id'] for r in data['nutrients']}
    for d in ('preparations','product_nutrients','product_sources'):
        for r in data[d]:
            if r.get('product_id') not in product_ids: issues.append(AuditIssue('ERROR',d,f"orphan product_id: {r.get('product_id')}"))
    for r in data['product_nutrients']:
        if r.get('preparation_id') not in prep_ids: issues.append(AuditIssue('ERROR','product_nutrients',f"orphan preparation_id: {r.get('preparation_id')}"))
        if r.get('nutrient_id') not in nutrient_ids: issues.append(AuditIssue('ERROR','product_nutrients',f"orphan nutrient_id: {r.get('nutrient_id')}"))
    rec_ids={r['recommendation_id'] for r in data['recommendations']}; guide_ids={r['guideline_code'] for r in data['guideline_sources']}
    for r in data['recommendations']:
        if r.get('guideline_code') not in guide_ids: issues.append(AuditIssue('ERROR','recommendations',f"orphan guideline_code: {r.get('guideline_code')}"))
    for r in data['rules']:
        if r.get('recommendation_id') not in rec_ids: issues.append(AuditIssue('ERROR','rules',f"orphan recommendation_id: {r.get('recommendation_id')}"))
    ref_source_ids={r['source_id'] for r in data['reference_sources']}
    for r in data['reference_items']:
        sid=(r.get('source_id') or '').strip()
        if sid and sid not in ref_source_ids: issues.append(AuditIssue('ERROR','reference_items',f'orphan source_id: {sid}'))
    for r in data['guideline_sources']:
        for field in ('organization','full_title','publication_year','status','last_checked'):
            if not (r.get(field) or '').strip(): issues.append(AuditIssue('ERROR','guideline_sources',f"{r.get('guideline_code')}: missing {field}"))
    for r in data['reference_sources']:
        if r.get('source_type')=='GUIDELINE':
            for field in ('organization','title','year','url','verification_status','verified_on'):
                if not (r.get(field) or '').strip(): issues.append(AuditIssue('ERROR','reference_sources',f"{r.get('source_id')}: missing {field}"))
    allowed={'DEMO_ONLY','VERIFIED_CURRENT','VERIFIED_OUTDATED','PENDING_VERIFICATION','USER_ENTERED'}
    for r in data['products']:
        if r.get('verification_status') not in allowed: issues.append(AuditIssue('ERROR','products',f"{r.get('product_id')}: invalid verification_status"))
        if r.get('verification_status')=='DEMO_ONLY': issues.append(AuditIssue('WARNING','products',f"{r.get('product_id')}: demonstration composition only; not manufacturer-verified"))
    return AuditReport(tuple(issues))
