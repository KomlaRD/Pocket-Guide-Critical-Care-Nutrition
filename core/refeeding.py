"""ASPEN 2020 adult refeeding syndrome bedside reference logic.

This module implements only transparent classification/arithmetic used by the
pocket guide. It does not store patient data or issue treatment orders.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class RefeedingRiskResult:
    level: str
    moderate_criteria: int
    significant_criteria: int
    note: str

def adult_refeeding_risk(criteria: dict[str, str]) -> RefeedingRiskResult:
    """Classify ASPEN adult risk from caller-supplied criterion severities.

    Each value must be 'none', 'moderate', or 'significant'. ASPEN adult
    consensus: moderate risk requires 2 moderate criteria; significant risk
    requires 1 significant criterion. This is a screening aid, not diagnosis.
    """
    allowed={"none","moderate","significant"}
    bad={k:v for k,v in criteria.items() if v not in allowed}
    if bad:
        raise ValueError("Risk criteria must be none, moderate, or significant.")
    sig=sum(v=="significant" for v in criteria.values())
    mod=sum(v=="moderate" for v in criteria.values())
    if sig>=1:
        level="Significant risk"
    elif mod>=2:
        level="Moderate risk"
    else:
        level="Criteria entered do not meet ASPEN moderate/significant threshold"
    return RefeedingRiskResult(level,mod,sig,"Electrolytes can be normal despite total-body deficiency.")

def diagnostic_severity(max_electrolyte_drop_percent: float, organ_dysfunction: bool=False,
                        thiamin_related_organ_dysfunction: bool=False, within_five_days: bool=True) -> str:
    if max_electrolyte_drop_percent < 0:
        raise ValueError("Electrolyte decrease cannot be negative.")
    if not within_five_days:
        return "Does not meet ASPEN timing criterion"
    if organ_dysfunction or thiamin_related_organ_dysfunction or max_electrolyte_drop_percent > 30:
        return "Severe"
    if 20 <= max_electrolyte_drop_percent <= 30:
        return "Moderate"
    if 10 <= max_electrolyte_drop_percent < 20:
        return "Mild"
    return "Does not meet ASPEN diagnostic decrement threshold"

def initial_calorie_range(weight_kg: float) -> tuple[float,float]:
    if weight_kg <= 0:
        raise ValueError("Weight must be greater than zero.")
    return (10*weight_kg,20*weight_kg)
