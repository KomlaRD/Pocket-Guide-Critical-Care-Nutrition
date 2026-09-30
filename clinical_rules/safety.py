from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SafetyResult:
    code: str
    status: str
    title: str
    message: str
    recommendation_code: str
    guideline_code: str = "ESPEN_ICU_2023"
    action_type: str = "DECISION_SUPPORT"
    automation_level: str = "CLINICIAN_CONFIRMATION_REQUIRED"


def _bool_flag(value: Optional[bool], code: str, title: str, message: str, recommendation: str):
    if value is None:
        return SafetyResult(code, "INSUFFICIENT_CONTEXT", title, "Confirm whether this condition is present.", recommendation)
    if value:
        return SafetyResult(code, "ALERT", title, message, recommendation)
    return SafetyResult(code, "NOT_TRIGGERED", title, "Condition not reported.", recommendation)


def evaluate_en_safety(*, uncontrolled_shock=False, uncontrolled_life_threatening_gas_exchange=False,
                       active_upper_gi_bleed=False, overt_bowel_ischemia=False,
                       high_output_fistula_without_distal_access=False,
                       abdominal_compartment_syndrome=False, grv_ml_6h: Optional[float]=None):
    results = [
        _bool_flag(uncontrolled_shock, "EN_SHOCK", "Uncontrolled shock", "ESPEN advises delaying EN while shock is uncontrolled and perfusion goals are not reached; low-dose EN may be considered once shock is controlled, with vigilance for bowel ischemia.", "R38"),
        _bool_flag(uncontrolled_life_threatening_gas_exchange, "EN_GAS", "Uncontrolled life-threatening hypoxemia/hypercapnia/acidosis", "ESPEN advises delaying EN during uncontrolled life-threatening gas-exchange or acid-base derangement.", "R38"),
        _bool_flag(active_upper_gi_bleed, "EN_GIB", "Active upper GI bleeding", "ESPEN advises delaying EN during active upper GI bleeding and reconsidering after bleeding has stopped without evidence of re-bleeding.", "R38"),
        _bool_flag(overt_bowel_ischemia, "EN_ISCHEMIA", "Overt bowel ischemia", "ESPEN advises delaying EN when overt bowel ischemia is present.", "R38"),
        _bool_flag(high_output_fistula_without_distal_access, "EN_FISTULA", "High-output intestinal fistula without distal access", "ESPEN advises delaying EN when reliable feeding access distal to a high-output fistula is not achievable.", "R38"),
        _bool_flag(abdominal_compartment_syndrome, "EN_ACS", "Abdominal compartment syndrome", "ESPEN advises delaying EN in abdominal compartment syndrome.", "R38"),
    ]
    if grv_ml_6h is None:
        results.append(SafetyResult("EN_GRV", "INSUFFICIENT_CONTEXT", "Gastric aspirate volume", "Enter a 6-hour gastric aspirate volume if it is being used to assess feeding intolerance.", "R38"))
    elif grv_ml_6h < 0:
        raise ValueError("Gastric aspirate volume cannot be negative.")
    elif grv_ml_6h > 500:
        results.append(SafetyResult("EN_GRV", "ALERT", "Gastric aspirate volume", f"Reported gastric aspirate volume is {grv_ml_6h:g} mL/6 h, above the ESPEN >500 mL/6 h delay threshold. Assess the abdomen and feeding intolerance; the guideline discusses prokinetic strategies when appropriate.", "R38"))
    else:
        results.append(SafetyResult("EN_GRV", "NOT_TRIGGERED", "Gastric aspirate volume", f"Reported gastric aspirate volume is {grv_ml_6h:g} mL/6 h; the >500 mL/6 h ESPEN delay threshold is not triggered.", "R38"))
    return results


def evaluate_early_en(*, oral_possible: Optional[bool], hours_since_icu_admission: Optional[float], en_started: Optional[bool]):
    if oral_possible is None or hours_since_icu_admission is None or en_started is None:
        return SafetyResult("EARLY_EN", "INSUFFICIENT_CONTEXT", "Early EN timing", "Enter oral-feeding feasibility, hours since ICU admission, and whether EN has started.", "R4")
    if hours_since_icu_admission < 0:
        raise ValueError("Hours since ICU admission cannot be negative.")
    if oral_possible:
        return SafetyResult("EARLY_EN", "NOT_APPLICABLE", "Early EN timing", "This rule applies when oral intake is not possible.", "R4")
    if en_started:
        return SafetyResult("EARLY_EN", "NOT_TRIGGERED", "Early EN timing", "EN is reported as started. ESPEN recommends early EN within 48 hours when oral intake is not possible, subject to contraindications and safety context.", "R4")
    if hours_since_icu_admission >= 48:
        return SafetyResult("EARLY_EN", "ALERT", "Early EN timing", "Oral intake is not possible and EN is not reported as started at ≥48 hours. Review EN feasibility and contraindications; ESPEN recommends early EN within 48 hours rather than delaying EN.", "R4")
    return SafetyResult("EARLY_EN", "MONITOR", "Early EN timing", f"EN has not started at {hours_since_icu_admission:g} hours. ESPEN recommends initiation within 48 hours when oral intake is not possible, if clinically appropriate.", "R4")


def evaluate_refeeding(*, current_phosphate_mmol_l: Optional[float], previous_phosphate_mmol_l: Optional[float]=None):
    if current_phosphate_mmol_l is None:
        return SafetyResult("REFEED_PHOS", "INSUFFICIENT_CONTEXT", "Refeeding hypophosphatemia", "Enter current phosphate to assess the ESPEN refeeding hypophosphatemia threshold.", "R56", action_type="MONITOR")
    if current_phosphate_mmol_l < 0 or (previous_phosphate_mmol_l is not None and previous_phosphate_mmol_l < 0):
        raise ValueError("Phosphate values cannot be negative.")
    drop = None if previous_phosphate_mmol_l is None else previous_phosphate_mmol_l - current_phosphate_mmol_l
    triggered = current_phosphate_mmol_l < 0.65 or (drop is not None and drop > 0.16)
    if triggered:
        detail = f"Current phosphate {current_phosphate_mmol_l:g} mmol/L"
        if drop is not None:
            detail += f"; fall {drop:g} mmol/L"
        return SafetyResult("REFEED_PHOS", "ALERT", "Refeeding hypophosphatemia", detail + ". ESPEN defines refeeding hypophosphatemia as phosphate <0.65 mmol/L or a fall >0.16 mmol/L and recommends more frequent electrolyte monitoring with supplementation as needed; energy progression requires clinician-directed management.", "R56", action_type="MONITOR")
    return SafetyResult("REFEED_PHOS", "NOT_TRIGGERED", "Refeeding hypophosphatemia", "The entered phosphate values do not trigger the ESPEN R56 threshold. Continue clinically appropriate electrolyte monitoring; ESPEN recommends at least daily potassium, magnesium and phosphate during the first week.", "R56", action_type="MONITOR")


def carbohydrate_rate_mg_kg_min(carbohydrate_g_day: float, weight_kg: float) -> float:
    if carbohydrate_g_day < 0:
        raise ValueError("Carbohydrate delivery cannot be negative.")
    if weight_kg <= 0:
        raise ValueError("Dosing weight must be greater than 0 kg.")
    return carbohydrate_g_day * 1000 / (weight_kg * 1440)


def evaluate_carbohydrate_limit(carbohydrate_g_day: float, weight_kg: float):
    rate = carbohydrate_rate_mg_kg_min(carbohydrate_g_day, weight_kg)
    status = "ALERT" if rate > 5 else "WITHIN_LIMIT"
    msg = f"Tracked carbohydrate/glucose exposure is {rate:.2f} mg/kg/min. "
    msg += "This exceeds the ESPEN 5 mg/kg/min ceiling." if rate > 5 else "This does not exceed the ESPEN 5 mg/kg/min ceiling."
    return SafetyResult("CARB_LIMIT", status, "Carbohydrate/glucose limit", msg, "R23", action_type="CHECK_LIMIT", automation_level="CALCULATED_RESULT")


def evaluate_iv_lipid_limit(iv_lipid_g_day: float, weight_kg: float):
    if iv_lipid_g_day < 0:
        raise ValueError("IV lipid delivery cannot be negative.")
    if weight_kg <= 0:
        raise ValueError("Dosing weight must be greater than 0 kg.")
    dose = iv_lipid_g_day / weight_kg
    status = "ALERT" if dose > 1.5 else "WITHIN_LIMIT"
    msg = f"Tracked IV lipid exposure is {dose:.2f} g/kg/day. "
    msg += "This exceeds the ESPEN 1.5 g/kg/day ceiling." if dose > 1.5 else "This does not exceed the ESPEN 1.5 g/kg/day ceiling."
    return SafetyResult("IV_LIPID_LIMIT", status, "IV lipid limit", msg, "R25", action_type="CHECK_LIMIT", automation_level="CALCULATED_RESULT")
