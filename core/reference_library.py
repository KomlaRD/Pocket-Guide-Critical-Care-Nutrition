from dataclasses import dataclass
from pathlib import Path
import csv

@dataclass(frozen=True)
class ReferenceItem:
    reference_id: str
    category: str
    topic: str
    title: str
    summary: str
    formula: str
    units: str
    source_id: str
    evidence_status: str
    source_locator: str
    verified_on: str

class ReferenceLibrary:
    def __init__(self, data_dir):
        p=Path(data_dir)
        self.sources={r['source_id']:r for r in csv.DictReader((p/'reference_sources.csv').open(encoding='utf-8'))}
        self.items=[ReferenceItem(**r) for r in csv.DictReader((p/'reference_items.csv').open(encoding='utf-8'))]
    def search(self, query='', category='ALL'):
        q=(query or '').strip().lower()
        out=[]
        for x in self.items:
            if category!='ALL' and x.category!=category: continue
            hay=' '.join([x.topic,x.title,x.summary,x.formula,x.evidence_status]).lower()
            if q and q not in hay: continue
            out.append(x)
        return out
    def source(self, source_id): return self.sources[source_id]
