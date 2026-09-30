"""ESPEN micronutrient bedside reference loader.

Values summarize routine adult medical-nutrition provision from Table 3 of the
2024 ESPEN practical short micronutrient guideline. They are reference values,
not individualized treatment prescriptions.
"""
from dataclasses import dataclass
from pathlib import Path
import csv

@dataclass(frozen=True)
class MicronutrientReference:
    id: str
    name: str
    category: str
    en_1500kcal: str
    pn_home_longterm: str
    clinical_note: str

def load_micronutrients(path: Path) -> list[MicronutrientReference]:
    with Path(path).open(encoding="utf-8", newline="") as f:
        rows=list(csv.DictReader(f))
    required={"id","name","category","en_1500kcal","pn_home_longterm","clinical_note"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Micronutrient reference dataset is missing required fields.")
    ids=[r["id"].strip() for r in rows]
    if any(not x for x in ids) or len(ids)!=len(set(ids)):
        raise ValueError("Micronutrient reference IDs must be nonblank and unique.")
    return [MicronutrientReference(**{k:r[k].strip() for k in required}) for r in rows]

def micronutrient_choices(items):
    return {x.id: x.name for x in items}
