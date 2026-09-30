from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Optional

from core.calculators import weight_based_range

@dataclass(frozen=True)
class PatientContext:
    weight_kg: Optional[float] = None
    icu_day: Optional[int] = None
    measured_ee_kcal: Optional[float] = None
    receiving_en: Optional[bool] = None

@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    recommendation_id: str
    guideline_code: str
    recommendation_code: str
    status: str
    action_type: str
    automation_level: str
    summary: str
    result_text: str
    evidence: str
    source_url: str

class GuidelineRepository:
    def __init__(self, data_dir: str | Path):
        root = Path(data_dir)
        self.sources = self._load(root / "guideline_sources.csv", "guideline_code")
        self.recommendations = self._load(root / "recommendations.csv", "recommendation_id")
        self.rules = self._load(root / "recommendation_rules.csv", "rule_id")

    @staticmethod
    def _load(path: Path, key: str):
        with path.open(encoding="utf-8", newline="") as f:
            return {row[key]: row for row in csv.DictReader(f)}

    def list_recommendations(self, guideline_code: str | None = None):
        rows = list(self.recommendations.values())
        if guideline_code and guideline_code != "ALL":
            rows = [r for r in rows if r["guideline_code"] == guideline_code]
        return rows

    def evaluate(self, rule_id: str, context: PatientContext) -> RuleEvaluation:
        rule = self.rules[rule_id]
        rec = self.recommendations[rule["recommendation_id"]]
        source = self.sources[rec["guideline_code"]]
        status, result = self._evaluate_rule(rule, context)
        evidence_bits = [x for x in [rec.get("evidence_grade"), rec.get("recommendation_strength")] if x]
        return RuleEvaluation(rule_id, rec["recommendation_id"], rec["guideline_code"], rec["recommendation_code"], status,
                              rule["action_type"], rule["automation_level"], rec["summary"], result,
                              " · ".join(evidence_bits), source["official_url"])

    def _evaluate_rule(self, rule, ctx):
        day_min = int(rule["icu_day_min"]) if rule["icu_day_min"] else None
        day_max = int(rule["icu_day_max"]) if rule["icu_day_max"] else None
        if (day_min is not None or day_max is not None) and ctx.icu_day is None:
            return "INSUFFICIENT_CONTEXT", "Enter ICU day to assess applicability."
        if day_min is not None and ctx.icu_day < day_min:
            return "NOT_APPLICABLE", f"This rule applies from ICU day {day_min}."
        if day_max is not None and ctx.icu_day > day_max:
            return "NOT_APPLICABLE", f"This rule applies through ICU day {day_max}."
        if rule["requires_receiving_en"].lower() == "true":
            if ctx.receiving_en is None:
                return "INSUFFICIENT_CONTEXT", "Confirm whether the patient is receiving enteral nutrition."
            if not ctx.receiving_en:
                return "NOT_APPLICABLE", "This rule applies to patients receiving enteral nutrition."
        calc = rule["calculator"]
        if calc == "weight_based":
            if ctx.weight_kg is None or ctx.weight_kg <= 0:
                return "INSUFFICIENT_CONTEXT", "Enter a clinician-selected dosing weight."
            lo = float(rule["value_min"] or rule["value_target"])
            hi = float(rule["value_max"] or rule["value_target"])
            out_unit = "kcal/day" if "kcal" in rule["unit"] else "g/day"
            low, high = weight_based_range(ctx.weight_kg, lo, hi, rule["unit"], out_unit)
            if lo == hi:
                text = f"Candidate target: {low.value:.1f} {out_unit} ({lo:g} {rule['unit']})."
            else:
                text = f"Candidate range: {low.value:.0f}–{high.value:.0f} {out_unit} ({lo:g}–{hi:g} {rule['unit']})."
            return "APPLICABLE", text + " Clinician confirmation required."
        if calc == "measured_ee_fraction":
            if ctx.measured_ee_kcal is None or ctx.measured_ee_kcal <= 0:
                return "INSUFFICIENT_CONTEXT", "Enter measured energy expenditure to calculate this rule."
            lo = float(rule["value_min"]) if rule["value_min"] else None
            hi = float(rule["value_max"])
            if lo is None:
                return "APPLICABLE", f"Candidate ceiling: ≤{ctx.measured_ee_kcal * hi:.0f} kcal/day ({hi*100:.0f}% measured EE). Clinician confirmation required."
            return "APPLICABLE", f"Candidate range: {ctx.measured_ee_kcal*lo:.0f}–{ctx.measured_ee_kcal*hi:.0f} kcal/day ({lo*100:.0f}–{hi*100:.0f}% measured EE). Clinician confirmation required."
        if rule["action_type"] in {"CHECK_LIMIT", "REFERENCE", "DECISION_SUPPORT", "ALERT"}:
            return "APPLICABLE", "Reference/limit rule available; no autonomous treatment decision is made."
        return "APPLICABLE", "Rule is applicable."
