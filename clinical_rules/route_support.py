from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RouteSupportResult:
    code: str
    status: str
    title: str
    message: str
    recommendation_code: str
    guideline_code: str
    action_type: str = "DECISION_SUPPORT"
    automation_level: str = "CLINICIAN_CONFIRMATION_REQUIRED"


def evaluate_enteral_access(*, gastric_feeding_intolerance: Optional[bool],
                             prokinetic_strategy_attempted: Optional[bool],
                             intolerance_persists: Optional[bool],
                             high_aspiration_risk: Optional[bool]) -> list[RouteSupportResult]:
    """ESPEN 2023 R10-R12 route support. Never selects/places a tube."""
    if gastric_feeding_intolerance is None or high_aspiration_risk is None:
        return [RouteSupportResult(
            "EN_ACCESS", "INSUFFICIENT_CONTEXT", "Enteral access",
            "Confirm gastric feeding tolerance and aspiration-risk context before assessing access escalation.",
            "R10-R12", "ESPEN_ICU_2023")]

    out: list[RouteSupportResult] = []
    if not gastric_feeding_intolerance and not high_aspiration_risk:
        out.append(RouteSupportResult(
            "EN_GASTRIC", "REFERENCE", "Initial enteral access",
            "No gastric intolerance or high aspiration-risk flag is reported. ESPEN uses gastric access as the standard approach to initiate EN.",
            "R10", "ESPEN_ICU_2023"))
        return out

    if high_aspiration_risk:
        out.append(RouteSupportResult(
            "EN_ASPIRATION", "CONSIDER_POSTPYLORIC", "High aspiration-risk context",
            "High aspiration risk is reported. ESPEN recommends postpyloric, mainly jejunal, feeding in patients considered at high risk for aspiration; confirm the clinical basis and feasibility.",
            "R12", "ESPEN_ICU_2023"))

    if gastric_feeding_intolerance:
        if prokinetic_strategy_attempted is None or intolerance_persists is None:
            out.append(RouteSupportResult(
                "EN_INTOLERANCE", "INSUFFICIENT_CONTEXT", "Gastric feeding intolerance",
                "Gastric intolerance is reported. Confirm whether an appropriate prokinetic strategy has been attempted and whether intolerance persists.",
                "R11/R13-R14", "ESPEN_ICU_2023"))
        elif not prokinetic_strategy_attempted:
            out.append(RouteSupportResult(
                "EN_PROKINETIC", "CONSIDER_PROKINETIC", "Gastric feeding intolerance",
                "Gastric intolerance is reported and a prokinetic strategy is not reported as attempted. ESPEN supports prokinetic therapy for gastric feeding intolerance when clinically appropriate; medication choice, contraindications, dose and duration require clinician/pharmacy review.",
                "R13-R14", "ESPEN_ICU_2023"))
        elif intolerance_persists:
            out.append(RouteSupportResult(
                "EN_POSTPYLORIC", "CONSIDER_POSTPYLORIC", "Persistent gastric feeding intolerance",
                "Gastric feeding intolerance persists despite a reported prokinetic strategy. ESPEN recommends postpyloric feeding in this context; confirm tube-placement feasibility and exclude new abdominal complications.",
                "R11", "ESPEN_ICU_2023"))
        else:
            out.append(RouteSupportResult(
                "EN_INTOLERANCE_RESOLVED", "MONITOR", "Gastric feeding intolerance",
                "A prokinetic strategy is reported and intolerance is not reported as persistent. Continue clinical tolerance monitoring; this rule does not independently indicate postpyloric escalation.",
                "R11/R13-R14", "ESPEN_ICU_2023"))
    return out


def evaluate_pn_route(*, icu_day: Optional[float], oral_and_en_contraindicated: Optional[bool],
                      receiving_en: Optional[bool], supplemental_pn_considered: Optional[bool],
                      known_malnutrition: Optional[bool]) -> list[RouteSupportResult]:
    """Keeps ESPEN PN route guidance and ASPEN 2022 supplemental-PN guidance separate."""
    if icu_day is not None and icu_day < 0:
        raise ValueError("ICU day cannot be negative.")
    out: list[RouteSupportResult] = []

    if oral_and_en_contraindicated is None or icu_day is None:
        out.append(RouteSupportResult(
            "ESPEN_PN", "INSUFFICIENT_CONTEXT", "ESPEN PN timing",
            "Enter ICU day and whether both oral nutrition and EN are contraindicated.",
            "R6/R21", "ESPEN_ICU_2023"))
    elif oral_and_en_contraindicated:
        if 3 <= icu_day <= 7:
            msg = "Both oral nutrition and EN are reported contraindicated and ICU day is within days 3–7. ESPEN recommends implementing PN within this interval; confirm the contraindications and prescription clinically."
            status = "CONSIDER_PN"
        elif icu_day < 3:
            msg = "Both oral nutrition and EN are reported contraindicated, but ICU day is before day 3. ESPEN frames PN implementation within days 3–7; reassess the clinical course and nutrition risk rather than automatically starting full PN."
            status = "MONITOR"
        else:
            msg = "Both oral nutrition and EN are reported contraindicated and ICU day is beyond day 7. Review whether PN is indicated and why it has not been established; avoid automatic full feeding."
            status = "REASSESS"
        out.append(RouteSupportResult("ESPEN_PN", status, "ESPEN PN timing", msg, "R6/R21", "ESPEN_ICU_2023"))
    else:
        out.append(RouteSupportResult(
            "ESPEN_PN", "REFERENCE", "ESPEN PN escalation",
            "Oral nutrition/EN are not both reported contraindicated. ESPEN advises attempting reasonable strategies to improve EN tolerance before PN escalation.",
            "R21", "ESPEN_ICU_2023"))

    if receiving_en is None or supplemental_pn_considered is None or icu_day is None:
        out.append(RouteSupportResult(
            "ASPEN_SPN", "INSUFFICIENT_CONTEXT", "ASPEN supplemental PN",
            "Enter ICU day, whether EN is being received, and whether supplemental PN is being considered.",
            "Q4", "ASPEN_ICU_2022"))
    elif not receiving_en or not supplemental_pn_considered:
        out.append(RouteSupportResult(
            "ASPEN_SPN", "NOT_APPLICABLE", "ASPEN supplemental PN",
            "The ASPEN Q4 supplemental-PN rule applies to critically ill adults receiving EN when supplemental PN is being considered.",
            "Q4", "ASPEN_ICU_2022"))
    elif known_malnutrition is True:
        out.append(RouteSupportResult(
            "ASPEN_SPN", "LIMITED_APPLICABILITY", "ASPEN supplemental PN",
            "Known malnutrition is reported. The ASPEN 2022 trials informing the recommendation against supplemental PN before ICU day 7 excluded patients with malnutrition, so direct applicability is limited and individualized clinical assessment is required.",
            "Q4", "ASPEN_ICU_2022"))
    elif known_malnutrition is None:
        out.append(RouteSupportResult(
            "ASPEN_SPN", "INSUFFICIENT_CONTEXT", "ASPEN supplemental PN",
            "Confirm malnutrition status before applying the ASPEN Q4 supplemental-PN timing recommendation; the informing trials excluded patients with malnutrition.",
            "Q4", "ASPEN_ICU_2022"))
    elif icu_day < 7:
        out.append(RouteSupportResult(
            "ASPEN_SPN", "DEFER_ROUTINE_SPN", "ASPEN supplemental PN",
            "For an average critically ill adult receiving EN without known malnutrition, ASPEN recommends not initiating supplemental PN before ICU day 7.",
            "Q4", "ASPEN_ICU_2022"))
    else:
        out.append(RouteSupportResult(
            "ASPEN_SPN", "REASSESS", "ASPEN supplemental PN",
            "ICU day is 7 or later. The ASPEN Q4 recommendation against supplemental PN before day 7 no longer determines the decision; reassess EN delivery, nutrition risk, goals and clinical context.",
            "Q4", "ASPEN_ICU_2022"))
    return out
