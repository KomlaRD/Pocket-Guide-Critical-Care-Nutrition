from pathlib import Path
from core.refeeding import adult_refeeding_risk, diagnostic_severity, initial_calorie_range
from core.micronutrients import load_micronutrients, micronutrient_choices

from shiny.express import input, render, ui
from shiny import reactive

from core.delivery import (
    ProductDatabase, NutritionSource, CustomNutritionSource,
    calculate_delivery, calculate_custom_delivery, combine_nutrient_totals,
    volume_delivery_percent, amount_for_nutrient, compare_liquid_formula, continuous_feeding_from_energy, bolus_feeding_from_energy,
)

from core.non_nutrition import EnergySource, calculate_energy_exposure, iv_dextrose_energy, propofol_energy_from_volume
from core.reference_library import ReferenceLibrary


from clinical_rules.safety import evaluate_carbohydrate_limit, evaluate_iv_lipid_limit
from core.formulation_tools import (
    FORMULATIONS, get_formulation, mass_mg_to_compound_mmol, compound_mmol_to_mass_mg, ion_amounts,
    dextrose_concentration_percent, infusion_rate_ml_hr, pn_distribution,
)

from core.calculators import (
    adequacy,
    bmi,
    en_rate,
    gir,
    nitrogen_balance,
    npc_n_ratio,
    percent_weight_loss,
    propofol_energy,
    weight_based_range,
    weir_energy,
    ideal_body_weight_devine, adjusted_body_weight, fluid_balance, formula_free_water,
    pn_macronutrient_energy, respiratory_quotient, convert_units, electrolyte_mmol_mEq,
)

ui.page_opts(title="Pocket Guide | Critical Care Nutrition", fillable=False)
ui.include_css(Path(__file__).parent / "www" / "styles.css")

PRODUCT_DB = ProductDatabase(Path(__file__).parent / "data" / "products")
NUTRIENT_UNITS = {
    "ENERGY": "kcal", "PROTEIN": "g", "CARBOHYDRATE": "g", "FAT": "g",
    "FIBRE": "g", "WATER": "mL", "SODIUM": "mg", "POTASSIUM": "mg",
    "PHOSPHORUS": "mg", "MAGNESIUM": "mg",
}
PRODUCT_CHOICES = PRODUCT_DB.choices()
LIQUID_CHOICES = {pid:p.name for pid,p in PRODUCT_DB.products.items() if p.volume_calculation_eligible and p.basis_unit=="mL"}
REFERENCES = ReferenceLibrary(Path(__file__).parent / "data" / "reference")
MICRONUTRIENTS = load_micronutrients(Path(__file__).parent / "data" / "reference" / "espen_micronutrients.csv")
MICRONUTRIENT_BY_ID = {x.id: x for x in MICRONUTRIENTS}
def num(value, digits=1):
    return f"{value:,.{digits}f}"


def missing_inputs(*values):
    """True while one or more transient UI fields are empty."""
    return any(value is None or (isinstance(value, str) and not value.strip()) for value in values)


def enter_prompt(*field_names):
    names = [name for name in field_names if name]
    if not names:
        return ui.div("Complete the required fields to calculate.", class_="input-prompt")
    if len(names) == 1:
        text = f"Enter {names[0]} to calculate."
    else:
        text = "Complete the required fields to calculate: " + ", ".join(names) + "."
    return ui.div(text, class_="input-prompt")


def clinician_error_message(exc):
    """Return a clinician-readable message without exposing Python exception text."""
    raw = str(exc).strip().lower()

    # Map expected calculation/data problems to bedside language. Raw exception
    # text is deliberately never returned to the user interface.
    if not raw:
        return "Please review the entered values and try again."
    if "unknown nutrition product" in raw or "basis unit mismatch" in raw or "unit conversion is required" in raw:
        return "The selected product cannot be calculated safely with the available formulation data. Confirm the exact product or choose another verified formulation."
    if "not eligible for continuous" in raw:
        return "This product cannot be used for the continuous-feeding calculation. Select a liquid enteral formula with a verified volume basis."
    if "not eligible for liquid bolus" in raw or "bolus feeding calculation requires" in raw:
        return "This product cannot be used for the bolus-feeding calculation. Select a liquid enteral formula with a verified volume basis."
    if "not eligible for liquid formula comparison" in raw:
        return "This product cannot be included in the liquid-formula comparison. Select a liquid formulation with a verified volume basis."
    if "not eligible for liquid delivery" in raw:
        return "This product cannot be used for the liquid-delivery calculation. Select a liquid formulation with a verified volume basis."
    if "small-bowel" in raw and "bolus" in raw:
        return "Bolus feeding is intended for gastric delivery in this tool. For small-bowel feeding, use an appropriate continuous or intermittent regimen according to the enteral access and local protocol."
    if "feeds per day" in raw:
        return "Enter the planned number of feeds per day as a whole number of at least 1."
    if "feeding hours" in raw or "feeding duration" in raw or "duration cannot exceed 24" in raw:
        return "Enter a feeding duration greater than 0 and no more than 24 hours per day."
    if "protein target" in raw:
        return "Enter a protein target greater than zero."
    if "energy target" in raw:
        return "Enter an energy target greater than zero."
    if "dosing weight" in raw or "weight must be greater" in raw:
        return "Enter a valid body weight greater than zero."
    if "delivered amount cannot be negative" in raw:
        return "The delivered amount cannot be less than zero. Check the entered delivery value."
    if "prescribed amount" in raw:
        return "Enter a prescribed amount greater than zero."
    if "cannot be negative" in raw or "cannot be less than zero" in raw:
        return "One or more entered values are below zero. Check the highlighted clinical inputs and try again."
    if "unsupported conversion" in raw or "direction must be" in raw:
        return "That conversion is not available. Check the selected units and conversion direction."
    if "sex must be" in raw:
        return "Select Male or Female to use the Devine ideal body weight equation."
    if "risk criteria must be" in raw:
        return "Select one of the available refeeding-risk categories before continuing."
    if "correction factor" in raw:
        return "Enter an adjusted-weight correction factor between 0 and 1."
    if "minimum dose cannot exceed maximum dose" in raw:
        return "The minimum dose is higher than the maximum dose. Review the entered dose range."
    if "protein-derived energy must be less than total energy" in raw:
        return "Protein-derived energy is equal to or greater than total energy. Review the entered total energy and protein values."
    if "water content must be between" in raw:
        return "Enter formula water content between 0 and 100 mL per 100 mL."
    if "absolute ionic valence" in raw:
        return "Enter the absolute ionic valence as a number greater than zero."
    if "at least one pn macronutrient" in raw:
        return "Enter an amount greater than zero for at least one PN macronutrient."
    return "The calculation could not be completed with the values entered. Review the clinical inputs and try again."

def safe_result(fn):
    try:
        return fn(), None
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        return None, clinician_error_message(exc)


def result_card(label, value, unit, note=""):
    return ui.div(
        ui.div(label, class_="result-label"),
        ui.div(value, ui.span(f" {unit}", class_="result-unit"), class_="result-value"),
        ui.div(note, class_="result-note") if note else None,
        class_="result-card",
    )


with ui.sidebar(open="desktop"):
    ui.div(
        ui.div("PG", class_="brand-mark", aria_label="Pocket Guide"),
        ui.div(ui.h4("Pocket Guide"), ui.p("CRITICAL CARE NUTRITION", class_="brand-subtitle")),
        class_="brand-lockup",
    )
    ui.div("QUICK ACCESS", class_="nav-section-label")
    ui.input_radio_buttons(
        "page", None,
        {
            "home":"Home",
            "find":"Find Guidance",
            "reference":"Quick Reference",
            "pediatric":"Pediatric Critical Care",
            "guidelines":"Critical Care Guidelines",
            "refeeding":"Refeeding Syndrome",
            "micronutrients":"Micronutrients",
            "safety":"Safety",
            "monitoring_check":"Monitoring Checklist",
            "renal":"Renal & KRT",
            "obesity":"Obesity in ICU",
            "pancreatitis":"Acute Pancreatitis",
            "liver":"Liver Disease",
            "gi_losses":"GI Losses & Intestinal Failure",
            "special_icu":"Trauma, Burns & Sepsis",
            "requirements":"Energy & Protein",
            "support":"Nutrition Support",
            "adequacy":"Nutrition Adequacy",
            "delivery":"Nutrition Delivery",
            "anthro":"Anthropometry",
            "toolkit":"Calculators & Conversions",
            "metabolic":"Metabolic Calculators",
            "products":"Product Reference",
            "compare_products":"Compare Formulas",
        },
        selected="home",
    )
    ui.p("Reference and bedside calculation tool. No patient identifiers or records are collected.", class_="small-note")
    ui.div(
        ui.span("Developer: Eric Anku"),
        ui.span(" · "),
        ui.a("GitHub: KomlaRD", href="https://github.com/KomlaRD", target="_blank", rel="noopener noreferrer"),
        class_="developer-note",
    )


with ui.panel_conditional("input.page === 'home'"):
    ui.div(
        ui.div("BEDSIDE CLINICAL TOOLKIT", class_="hero-eyebrow"),
        ui.h1("Critical care nutrition,\nmade clearer."),
        ui.p("Evidence-informed guideline references and bedside nutrition calculations in one compact clinical pocket guide."),
        ui.div(ui.span("Evidence-informed", class_="hero-chip"), ui.span("Clinician-confirmed", class_="hero-chip"), class_="hero-chips"),
        class_="hero",
    )
    ui.h3("Bedside tools", class_="section-heading")
    ui.div(
        ui.div(ui.div("01", class_="feature-number"), ui.h4("Energy & Protein"), ui.p("Weight-based targets and Weir energy expenditure."), class_="feature-card"),
        ui.div(ui.div("02", class_="feature-number"), ui.h4("Nutrition Support"), ui.p("EN rate, propofol calories and glucose infusion rate."), class_="feature-card"),
        ui.div(ui.div("03", class_="feature-number"), ui.h4("Metabolic"), ui.p("Nitrogen balance and non-protein calorie:nitrogen ratio."), class_="feature-card"),
        ui.div(ui.div("04", class_="feature-number"), ui.h4("Refeeding & Micronutrients"), ui.p("Rapid access to ASPEN refeeding and ESPEN micronutrient guidance."), class_="feature-card"),
        class_="card-grid",
    )
    ui.div(
        ui.strong("Clinical use & limitations"),
        ui.p("This pocket guide is an evidence-informed clinical reference and decision-support tool. It does not replace individualized nutrition assessment, professional clinical judgment, current product labeling, institutional policies, or locally applicable protocols."),
        ui.p("Recommendations and calculations must be interpreted in the context of the individual patient, including diagnosis, age, clinical phase, organ function, route of nutrition support, laboratory data, fluid status, treatment goals, contraindications, and response to therapy."),
        ui.p("Guidelines, product formulations, and clinical evidence may change. Clinicians should verify information against the current primary source, manufacturer information, and local policy when this could affect care."),
        ui.p(ui.strong("Professional responsibility: "), "The treating clinician remains responsible for verifying the appropriateness and accuracy of information used from this application and for all clinical decisions, prescriptions, monitoring, and patient care arising from its use."),
        class_="limitation-box",
    )
    ui.div(
        ui.h4("Developer"),
        ui.p("Eric Anku — Registered Dietitian and developer of Pocket Guide Critical Care."),
        ui.a("GitHub · KomlaRD", href="https://github.com/KomlaRD", target="_blank", rel="noopener noreferrer"),
        class_="developer-card",
    )


with ui.panel_conditional("input.page === 'reference'"):
    ui.h2("Quick Reference")
    ui.p("Searchable bedside references. Informational entries do not become executable clinical rules unless separately modeled and tested.", class_="section-intro")
    ui.input_text("reference_query", "Search", placeholder="e.g. refeeding, GIR, protein, conversion")
    ui.input_select("reference_category", "Category", {"ALL":"All", "Energy":"Energy", "Protein":"Protein", "Route & timing":"Route & timing", "Macronutrients":"Macronutrients", "Monitoring":"Monitoring", "Weight & obesity":"Weight & obesity", "Fluid & electrolytes":"Fluid & electrolytes", "Parenteral nutrition":"Parenteral nutrition", "Indirect calorimetry":"Indirect calorimetry", "Renal / KRT":"Renal / KRT", "Refeeding":"Refeeding", "Micronutrients":"Micronutrients", "Formula":"Formula", "Conversion":"Conversion"}, selected="ALL")
    @render.ui
    def reference_results():
        items=REFERENCES.search(input.reference_query(), input.reference_category())
        if not items:
            return ui.div("No matching reference entries. Try a broader search or select All categories.", class_="warning-box")
        cards=[]
        for x in items:
            src=REFERENCES.source(x.source_id)
            cards.append(ui.div(
                ui.h4(x.title),
                ui.div(x.category + " · " + x.topic, class_="small-note"),
                ui.p(x.summary),
                ui.div(ui.strong("Formula / threshold: "), x.formula + ((" " + x.units) if x.units else "")) if x.formula else None,
                ui.div(ui.strong("Evidence status: "), x.evidence_status.replace("_", " ").title()),
                ui.div(ui.strong("Source: "), src["organization"] + " · " + src["title"] + " · " + src["year"]),
                ui.div("Verified " + x.verified_on + " · " + x.source_locator, class_="small-note"),
                class_="feature-card"))
        return ui.div(*cards, class_="reference-list")

def guideline_label(value: str) -> str:
    """Sentence-case headings while preserving standard clinical abbreviations."""
    acronyms = {"EN", "PN", "ICU", "IV", "EE", "ESPEN", "ASPEN", "GPP"}
    words = str(value).replace("_", " ").split()
    return " ".join(w.upper() if w.upper() in acronyms else (w.capitalize() if i == 0 else w.lower()) for i, w in enumerate(words))


with ui.panel_conditional("input.page === 'find'"):
    ui.h2("Find Guidance")
    ui.p("Fast bedside index to the pocket guide. Choose the clinical question that best matches what you need; this page stores no search history or patient information.",class_="section-intro")

    ui.input_select("find_topic","I need guidance on…",{
        "start_en":"Starting or advancing EN",
        "shock":"Feeding during shock / vasopressors",
        "intolerance":"EN intolerance / gastric residuals",
        "refeeding":"Refeeding syndrome",
        "electrolytes":"Electrolytes & micronutrients",
        "targets":"Energy & protein targets",
        "obesity":"Obesity / dosing weight",
        "renal":"AKI, CKD or KRT",
        "liver":"Liver disease / encephalopathy",
        "pancreas":"Acute pancreatitis",
        "gi":"High-output stoma / fistula / short bowel",
        "special":"Trauma, burns, sepsis or surgery",
        "pn":"PN indication & monitoring",
        "monitor":"Nutrition monitoring",
        "anthro":"Anthropometry / weight estimation",
        "calc":"Calculators & conversions",
    },selected="start_en")

    with ui.panel_conditional("input.find_topic === 'start_en'"):
        with ui.card():
            ui.card_header("Starting or advancing EN")
            ui.p("Go to Critical Care Guidelines → Route & Timing. For day-to-day review, also use Monitoring Checklist → First 72 hours & advancement.")
            ui.p("Core orientation: when oral intake is not possible, favor early EN when the gastrointestinal tract is usable and the patient is sufficiently stabilized.",class_="small-note")
    with ui.panel_conditional("input.find_topic === 'shock'"):
        with ui.card():
            ui.card_header("Shock / vasopressors")
            ui.p("Go to Safety and Trauma, Burns & Sepsis → Sepsis & septic shock.")
            ui.p("Do not advance full EN during uncontrolled shock. After shock is controlled, low-dose EN may be introduced progressively with close tolerance monitoring.",class_="small-note")
    with ui.panel_conditional("input.find_topic === 'intolerance'"):
        with ui.card():
            ui.card_header("EN intolerance")
            ui.p("Go to Safety and Critical Care Guidelines → EN intolerance.")
            ui.p("Assess the whole clinical picture; do not stop EN solely for a GRV below 500 mL/6 h in the absence of other intolerance.",class_="small-note")
    with ui.panel_conditional("input.find_topic === 'refeeding'"):
        with ui.card():
            ui.card_header("Refeeding syndrome")
            ui.p("Go to Refeeding Syndrome for ASPEN risk classification, initiation, electrolyte/thiamin monitoring and response to falling electrolytes.")
    with ui.panel_conditional("input.find_topic === 'electrolytes'"):
        with ui.card():
            ui.card_header("Electrolytes & micronutrients")
            ui.p("Go to Micronutrients for the ESPEN reference and Safety for electrolyte/refeeding context. Missing nutrient data should be treated as unknown, not assumed to be zero.")
    with ui.panel_conditional("input.find_topic === 'targets'"):
        with ui.card():
            ui.card_header("Energy & protein")
            ui.p("Go to Energy & Protein for calculations and Critical Care Guidelines for phase-of-illness interpretation. Keep energy and protein as separate prescription decisions.")
    with ui.panel_conditional("input.find_topic === 'obesity'"):
        with ui.card():
            ui.card_header("Obesity / dosing weight")
            ui.p("Go to Obesity in ICU. Weight conventions differ by recommendation; do not silently substitute actual, ideal and adjusted body weight.")
    with ui.panel_conditional("input.find_topic === 'renal'"):
        with ui.card():
            ui.card_header("Renal dysfunction / KRT")
            ui.p("Go to Renal & KRT for protein guidance by KRT situation, weight selection, CKRT/PIKRT losses and monitoring.")
    with ui.panel_conditional("input.find_topic === 'liver'"):
        with ui.card():
            ui.card_header("Liver disease")
            ui.p("Go to Liver Disease. Hepatic encephalopathy is not, by itself, an indication for routine protein restriction.")
    with ui.panel_conditional("input.find_topic === 'pancreas'"):
        with ui.card():
            ui.card_header("Acute pancreatitis")
            ui.p("Go to Acute Pancreatitis for oral feeding, EN timing, NG/NJ route, formula and PN decisions.")
    with ui.panel_conditional("input.find_topic === 'gi'"):
        with ui.card():
            ui.card_header("GI losses / intestinal failure")
            ui.p("Go to GI Losses & Intestinal Failure for high-output stoma, fistula, short-bowel anatomy, fluid/sodium strategy and escalation.")
    with ui.panel_conditional("input.find_topic === 'special'"):
        with ui.card():
            ui.card_header("Trauma, burns, sepsis & surgery")
            ui.p("Go to Trauma, Burns & Sepsis for condition-specific modifiers layered on the general ICU nutrition guidance.")
    with ui.panel_conditional("input.find_topic === 'pn'"):
        with ui.card():
            ui.card_header("Parenteral nutrition")
            ui.p("Go to Nutrition Support for calculations, Critical Care Guidelines for indication/timing, Safety for PN safeguards, and Monitoring Checklist for established PN review.")
    with ui.panel_conditional("input.find_topic === 'monitor'"):
        with ui.card():
            ui.card_header("Monitoring")
            ui.p("Go to Monitoring Checklist and select the current phase: initiation, first 72 hours, established EN/PN, refeeding risk, prolonged stay or post-interruption.")
    with ui.panel_conditional("input.find_topic === 'anthro'"):
        with ui.card():
            ui.card_header("Anthropometry")
            ui.p("Go to Anthropometry for BMI, weight change, dosing-weight concepts and the external AnthroPredictor tool.")
    with ui.panel_conditional("input.find_topic === 'calc'"):
        with ui.card():
            ui.card_header("Calculators")
            ui.p("Go to Calculators & Conversions, Metabolic Calculators or Nutrition Adequacy depending on the calculation required.")

    with ui.card():
        ui.card_header("Pocket-guide safety contract")
        ui.tags.ul(
            ui.tags.li("No patient identifiers, records, search history or completion status are stored."),
            ui.tags.li("Calculator inputs are transient bedside values, not a patient record."),
            ui.tags.li("Guideline values support—not replace—clinical judgment and local policy."),
            ui.tags.li("Weight descriptors, units and guideline source must remain explicit when they affect interpretation."),
        )


with ui.panel_conditional("input.page === 'guidelines'"):
    ui.h2("Critical Care Nutrition Guidelines")
    ui.p("High-yield adult ICU recommendations organized for bedside use. ESPEN and ASPEN guidance remains source-labelled; recommendations are not merged when their scope, evidence base, or wording differs.", class_="section-intro")

    with ui.card():
        ui.card_header("Start Here")
        with ui.layout_columns(col_widths=(4,4,4)):
            ui.div(ui.h4("Route & Timing"), ui.p("Oral intake when possible; otherwise consider early EN when oral intake is not possible, unless a contraindication exists."), class_="feature-card")
            ui.div(ui.h4("Energy"), ui.p("Prefer indirect calorimetry when available. Avoid early full feeding; progress according to illness phase and measured or estimated expenditure."), class_="feature-card")
            ui.div(ui.h4("Protein"), ui.p("Progress protein provision rather than treating calorie and protein targets as interchangeable endpoints."), class_="feature-card")

    ui.input_select("guideline_topic", "Bedside topic", {
        "route":"Route & timing of nutrition",
        "energy":"Energy expenditure & progression",
        "protein":"Protein provision",
        "intolerance":"EN intolerance & gastric residual volume",
        "pn":"Parenteral & supplemental PN",
        "obesity":"Obesity",
        "renal":"Kidney disease / renal replacement therapy",
        "liver":"Liver failure",
        "special":"Other special ICU situations",
    }, selected="route")

    with ui.panel_conditional("input.guideline_topic === 'route'"):
        with ui.card():
            ui.card_header("Route & Timing · ESPEN 2023")
            ui.tags.ul(
                ui.tags.li("Use oral diet rather than EN or PN in critically ill patients able to eat."),
                ui.tags.li("When oral intake is not possible, initiate early EN within 48 hours rather than delaying EN."),
                ui.tags.li("Prefer early EN over early PN when oral intake is not possible and there is no contraindication to EN."),
                ui.tags.li("Delay EN in uncontrolled shock when hemodynamic and tissue-perfusion goals are not reached; low-dose EN may start once shock is controlled with fluids and vasopressors/inotropes."),
                ui.tags.li("Delay EN with uncontrolled life-threatening hypoxemia, hypercapnia or acidosis; stable hypoxemia and compensated/permissive hypercapnia do not by themselves preclude EN."),
            )

    with ui.panel_conditional("input.guideline_topic === 'energy'"):
        with ui.card():
            ui.card_header("Energy · ESPEN 2023")
            ui.tags.ul(
                ui.tags.li("Determine energy expenditure with indirect calorimetry in mechanically ventilated critically ill adults when available."),
                ui.tags.li("If indirect calorimetry is unavailable, VO2 from a pulmonary artery catheter or ventilator-derived VCO2 provides a better estimate than predictive equations."),
                ui.tags.li("When predictive equations are used, prefer hypocaloric nutrition below 70% of estimated needs during the first ICU week."),
                ui.tags.li("After ICU day 3, energy delivery may be progressively increased to 80–100% of measured energy expenditure."),
                ui.tags.li("Account for non-nutritional calories, including sources such as propofol, citrate and glucose-containing solutions."),
            )
            ui.div("Predictive equations can be substantially inaccurate in ICU patients. Weight-based estimates are pragmatic fallbacks, not equivalents to measured energy expenditure.", class_="warning-box")

    with ui.panel_conditional("input.guideline_topic === 'protein'"):
        with ui.card():
            ui.card_header("Protein · ESPEN 2023")
            ui.tags.ul(
                ui.tags.li("Approximately 1.3 g/kg/day protein equivalents can be delivered progressively during critical illness."),
                ui.tags.li("Protein should be progressed rather than automatically coupled to achievement of full energy provision."),
                ui.tags.li("Interpret protein targets in the context of illness phase, organ support, nitrogen losses and tolerance."),
            )

    with ui.panel_conditional("input.guideline_topic === 'intolerance'"):
        with ui.card():
            ui.card_header("EN Intolerance · ESPEN 2023")
            ui.tags.ul(
                ui.tags.li("Use IV erythromycin as first-line prokinetic therapy for gastric feeding intolerance; IV metoclopramide or a combination may be used as alternatives according to the guideline."),
                ui.tags.li("Consider postpyloric feeding when gastric feeding intolerance persists despite prokinetic therapy."),
                ui.tags.li("Use postpyloric feeding in patients considered at high risk of aspiration."),
                ui.tags.li("Do not use a single isolated sign to define gastrointestinal dysfunction; integrate the overall clinical picture."),
            )

    with ui.panel_conditional("input.guideline_topic === 'pn'"):
        with ui.card():
            ui.card_header("PN & Supplemental PN · ESPEN 2023")
            ui.tags.ul(
                ui.tags.li("When oral intake and EN are contraindicated, PN should generally be implemented within 3–7 days."),
                ui.tags.li("In severely malnourished patients, early and progressive PN may be considered when EN is contraindicated."),
                ui.tags.li("Avoid early full-dose EN or PN; progressive delivery is important because overfeeding carries risk."),
                ui.tags.li("The optimal timing of supplemental PN depends on the energy deficit, illness phase and ability to advance EN; it should not be treated as an automatic response to a single low-intake day."),
            )

    with ui.panel_conditional("input.guideline_topic === 'obesity'"):
        with ui.card():
            ui.card_header("Obesity · ESPEN 2023")
            ui.p("Prefer indirect calorimetry to determine energy expenditure. If unavailable, guideline-specific weight conventions are required; do not apply a normal-BMI kcal/kg or protein rule indiscriminately to patients with obesity.", class_="warning-box")
            ui.p("The ESPEN ICU guideline provides obesity-specific approaches to energy and protein estimation. Verify the exact weight descriptor and equation before applying a calculated target.", class_="small-note")

    with ui.panel_conditional("input.guideline_topic === 'renal'"):
        with ui.card():
            ui.card_header("Kidney Disease & Renal Replacement Therapy")
            ui.tags.ul(
                ui.tags.li("Do not routinely restrict protein solely to avoid or delay renal replacement therapy in critically ill patients."),
                ui.tags.li("Renal replacement therapies can create additional amino-acid and micronutrient losses; account for treatment modality and intensity."),
                ui.tags.li("Fluid, electrolyte and protein decisions require integration with renal function, dialysis prescription and metabolic tolerance."),
            )
            ui.p("For detailed kidney-specific dosing, consult the current ESPEN kidney disease guideline in addition to the ICU guideline.", class_="small-note")

    with ui.panel_conditional("input.guideline_topic === 'liver'"):
        with ui.card():
            ui.card_header("Liver Failure")
            ui.p("Avoid reflexive protein restriction in critically ill patients with liver disease. Energy/protein provision, encephalopathy, ammonia, glucose control, fluid status and route tolerance should be considered together.", class_="info-box")
            ui.p("Use the dedicated ESPEN liver disease guideline for disease-specific recommendations; this card is a navigation prompt rather than a substitute for that guideline.", class_="small-note")

    with ui.panel_conditional("input.guideline_topic === 'special'"):
        with ui.card():
            ui.card_header("Special ICU Situations")
            ui.tags.ul(
                ui.tags.li("Extracorporeal therapies, burns, trauma, sepsis, post-operative critical illness and prolonged ICU stays can materially alter nutrition requirements and losses."),
                ui.tags.li("Refeeding syndrome and micronutrient management have dedicated modules in this pocket guide."),
                ui.tags.li("Use condition-specific guidelines where they supersede or add detail to general ICU recommendations."),
            )

    with ui.card():
        ui.card_header("Source Provenance")
        ui.p("Primary ICU source: Singer P, Reintam Blaser A, Berger MM, et al. ESPEN practical and partially revised guideline: Clinical nutrition in the intensive care unit. Clinical Nutrition. 2023;42:1671–1689.")
        ui.a("Open ESPEN 2023 ICU guideline", href="https://www.espen.org/files/ESPEN-Guidelines/ESPEN_practical_and_partially_revised_guideline_Clinical_nutrition_in_the_intensive_care_unit.pdf", target="_blank")
        ui.p("The existing rule engine retains separately labelled ASPEN/ESPEN source records. This bedside topic library does not imply that recommendations from different societies are interchangeable.", class_="small-note")

with ui.panel_conditional("input.page === 'refeeding'"):
    ui.h2("ASPEN Refeeding Syndrome")
    ui.p("Adult bedside screening and management reference based on the ASPEN 2020 consensus recommendations and the published erratum. This tool uses transient inputs only and does not create or store a patient record.", class_="section-intro")

    with ui.card():
        ui.card_header("1. Identify Adult Risk")
        ui.p("For each domain, select the highest criterion that applies. Moderate risk requires 2 moderate criteria; significant risk requires 1 significant criterion.", class_="small-note")
        risk_choices={"none":"Does not meet criterion","moderate":"Moderate-risk criterion","significant":"Significant-risk criterion"}
        with ui.layout_columns(col_widths=(6,6)):
            ui.input_select("rf_bmi","BMI",risk_choices)
            ui.input_select("rf_weight_loss","Weight loss",risk_choices)
            ui.input_select("rf_intake","Caloric intake",risk_choices)
            ui.input_select("rf_electrolytes","Prefeeding K, phosphorus or Mg",risk_choices)
            ui.input_select("rf_fat","Subcutaneous fat loss",risk_choices)
            ui.input_select("rf_muscle","Muscle mass loss",risk_choices)
            ui.input_select("rf_comorbidity","Higher-risk comorbidity",risk_choices)
        @render.ui
        def refeeding_risk_result():
            r=adult_refeeding_risk({
                "bmi":input.rf_bmi(),"weight_loss":input.rf_weight_loss(),"intake":input.rf_intake(),
                "electrolytes":input.rf_electrolytes(),"fat":input.rf_fat(),"muscle":input.rf_muscle(),
                "comorbidity":input.rf_comorbidity(),
            })
            return ui.div(
                result_card("ASPEN adult risk screen",r.level,"",f"{r.moderate_criteria} moderate; {r.significant_criteria} significant criteria selected"),
                ui.div(r.note,class_="warning-box"),
            )
        with ui.accordion():
            with ui.accordion_panel("Corrected ASPEN adult criteria"):
                ui.tags.ul(
                    ui.tags.li("BMI: moderate 16–18.5 kg/m²; significant <16 kg/m²."),
                    ui.tags.li("Weight loss: moderate 5% in 1 month; significant 7.5% in 3 months or >10% in 6 months."),
                    ui.tags.li("Intake: moderate—none/negligible 5–6 days, or <75% need >7 days during acute illness/injury, or <75% >1 month; significant—none/negligible >7 days, or <50% need >5 days during acute illness/injury, or <50% >1 month."),
                    ui.tags.li("Electrolytes (erratum): moderate—minimally low or normal currently with recent low levels requiring minimal/single-dose supplementation; significant—moderately/significantly low or minimally low/normal currently with recent low levels requiring significant/multiple-dose supplementation."),
                    ui.tags.li("Fat loss: moderate loss vs severe loss. Muscle loss: mild/moderate vs severe. Higher-risk comorbidity: moderate vs severe disease."),
                )

    with ui.card():
        ui.card_header("2. Recognize Refeeding Syndrome")
        ui.p("ASPEN diagnosis is based on the percentage decrease in phosphorus, potassium and/or magnesium after calories are reintroduced or substantially increased, within 5 days.", class_="small-note")
        with ui.layout_columns(col_widths=(4,4,4)):
            ui.input_numeric("rf_drop","Largest electrolyte decrease (%)",0,min=0,step=1)
            ui.input_checkbox("rf_organ","Related organ dysfunction",False)
            ui.input_checkbox("rf_thiamin_organ","Organ dysfunction due to thiamin deficiency",False)
        ui.input_checkbox("rf_timing","Occurred within 5 days of calorie reintroduction/increase",True)
        @render.ui
        def refeeding_diagnosis_result():
            s=diagnostic_severity(input.rf_drop(),input.rf_organ(),input.rf_thiamin_organ(),input.rf_timing())
            return result_card("ASPEN diagnostic severity",s,"","Mild: 10–<20%; moderate: 20–30%; severe: >30% and/or relevant organ dysfunction")

    with ui.card():
        ui.card_header("3. Before Starting or Increasing Calories")
        ui.tags.ul(
            ui.tags.li("Check serum potassium, magnesium and phosphorus."),
            ui.tags.li("Consider holding initiation or calorie increases when moderate/high risk coexists with low electrolytes until supplementation and/or normalization."),
            ui.tags.li("Delay initiation or increases when phosphorus, potassium or magnesium is severely low until corrected."),
            ui.tags.li("Count calories from IV dextrose solutions and medications infused in dextrose."),
            ui.tags.li("Give thiamin 100 mg before feeding or before dextrose-containing IV fluids in patients at risk."),
        )

    with ui.card():
        ui.card_header("4. Initial Calories and Advancement")
        ui.input_numeric("rf_weight","Weight for kcal/kg reference (kg)",70,min=0.1,step=0.1)
        @render.ui
        def refeeding_calorie_reference():
            lo,hi=initial_calorie_range(input.rf_weight())
            return ui.div(
                result_card("First 24 h reference",f"{lo:,.0f}–{hi:,.0f}","kcal", "ASPEN: 10–20 kcal/kg or 100–150 g dextrose"),
                ui.div("Advance by approximately 33% of goal every 1–2 days, adapting to electrolyte response and the clinical picture.",class_="info-box"),
            )

    with ui.card():
        ui.card_header("5. Electrolytes, Thiamin and Multivitamins")
        ui.tags.ul(
            ui.tags.li("For high-risk patients, monitor potassium, magnesium and phosphorus every 12 hours for the first 3 days; monitor more frequently when clinically indicated."),
            ui.tags.li("Replete low electrolytes according to established standards of care. ASPEN makes no recommendation for prophylactic electrolyte dosing when prefeeding levels are normal."),
            ui.tags.li("Continue thiamin 100 mg/day for 5–7 days or longer with severe starvation, chronic alcohol use, other high deficiency risk, or signs of thiamin deficiency."),
            ui.tags.li("For PN, include daily multivitamin unless contraindicated while PN continues; for oral/EN nourishment, ASPEN recommends a complete oral/enteral multivitamin daily for 10 days or longer according to clinical status."),
        )

    with ui.card():
        ui.card_header("6. If Electrolytes Fall or Are Difficult to Correct")
        ui.div("ASPEN recommends reducing calories/dextrose by 50% when electrolytes become difficult to correct or fall precipitously during nutrition initiation, then advancing by approximately 33% of goal every 1–2 days according to the clinical response. Severe or life-threatening abnormalities may warrant considering cessation of nutrition support.",class_="warning-box")
        ui.p("These are consensus recommendations and require clinician judgment, particularly with renal impairment and other special populations.",class_="small-note")

    with ui.card():
        ui.card_header("7. Monitoring")
        ui.tags.ul(
            ui.tags.li("Vital signs every 4 hours for the first 24 hours after calorie initiation in patients at risk."),
            ui.tags.li("Cardiorespiratory monitoring for unstable patients or those with severe deficiencies according to standards of care."),
            ui.tags.li("Daily weight and monitored intake/output."),
            ui.tags.li("Reassess nutrition goals daily during the first several days until stabilized."),
        )

    with ui.card():
        ui.card_header("Source & Correction")
        ui.p("Primary source: da Silva JSV, Seres DS, Sabino K, et al. ASPEN Consensus Recommendations for Refeeding Syndrome. Nutrition in Clinical Practice. 2020;35(2):178–195.")
        ui.p("The June 2020 erratum corrected the adult electrolyte-risk wording in Table 3. The corrected wording is used in this pocket guide.",class_="info-box")
        ui.a("Open ASPEN consensus article",href="https://aspenjournals.onlinelibrary.wiley.com/doi/10.1002/ncp.10474",target="_blank")
        ui.span(" · ")
        ui.a("Open published erratum",href="https://aspenjournals.onlinelibrary.wiley.com/doi/10.1002/ncp.10491",target="_blank")

with ui.panel_conditional("input.page === 'micronutrients'"):
    ui.h2("ESPEN Micronutrient Reference")
    ui.p("Bedside reference based primarily on the ESPEN practical short micronutrient guideline (2024), with the 2022 comprehensive guideline as the scientific source. Values below summarize routine adult medical-nutrition provision and are not individualized deficiency-treatment prescriptions.", class_="section-intro")

    with ui.card():
        ui.card_header("Core Interpretation Principles")
        ui.tags.ul(
            ui.tags.li("Provide essential vitamins and trace elements from the beginning of medical nutrition."),
            ui.tags.li("Interpret micronutrient measurements alongside C-reactive protein (CRP) and the clinical inflammatory state."),
            ui.tags.li("Distinguish routine provision from treatment of proven or strongly suspected deficiency."),
            ui.tags.li("Consider route, duration of nutrition support, organ dysfunction, abnormal losses and toxicity risk."),
        )
        ui.div("Inflammation can substantially change circulating micronutrient concentrations. A low plasma concentration does not automatically establish whole-body deficiency.", class_="warning-box")

    with ui.card():
        ui.card_header("Micronutrient Lookup")
        ui.input_select("mn_selected", "Select micronutrient", micronutrient_choices(MICRONUTRIENTS), selected="thiamine")
        @render.ui
        def micronutrient_detail():
            m = MICRONUTRIENT_BY_ID[input.mn_selected()]
            return ui.div(
                ui.div(ui.span(m.category, class_="status-badge"), ui.h3(m.name), class_="mn-title"),
                ui.div(
                    result_card("Enteral nutrition", m.en_1500kcal, "", "Routine provision in approximately 1500 kcal/day EN"),
                    result_card("Parenteral nutrition", m.pn_home_longterm, "", "Home/long-term routine PN reference"),
                    class_="result-grid",
                ),
                ui.div(ui.strong("Clinical interpretation: "), m.clinical_note, class_="info-box"),
                ui.p("Use the source guideline for biomarker selection, deficiency treatment, high-requirement states, toxicity, organ-specific considerations and recommendation grades.", class_="small-note"),
            )

    with ui.card():
        ui.card_header("Quick Index")
        with ui.layout_columns(col_widths=(4,4,4)):
            ui.div(ui.h4("Trace Elements"), ui.p("Chromium · Copper · Fluoride · Iodine · Iron · Manganese · Molybdenum · Selenium · Zinc"), class_="feature-card")
            ui.div(ui.h4("Water-Soluble Vitamins"), ui.p("Thiamin (B1) · Riboflavin (B2) · Niacin (B3) · Pantothenic acid (B5) · Vitamin B6 · Biotin (B7) · Folate (B9) · Vitamin B12 · Vitamin C"), class_="feature-card")
            ui.div(ui.h4("Fat-Soluble Vitamins"), ui.p("Vitamin A · Vitamin D · Vitamin E · Vitamin K"), class_="feature-card")

    with ui.card():
        ui.card_header("Special Compounds Addressed by ESPEN")
        ui.p("The practical guideline also discusses L-carnitine, choline and coenzyme Q10 separately. These are not presented above as routine essential-vitamin/trace-element provision targets; consult the guideline for their specific indications.", class_="small-note")

    with ui.card():
        ui.card_header("Source & Provenance")
        ui.p("Primary bedside source: Berger MM, Shenkin A, Dizdar OS, et al. ESPEN practical short micronutrient guideline. Clinical Nutrition. 2024;43:825–857.")
        ui.p("Scientific source: Berger MM, Shenkin A, et al. ESPEN micronutrient guideline. Clinical Nutrition. 2022;41:1357–1424.")
        ui.a("Open ESPEN 2024 practical short guideline", href="https://2022.espen.org/files/ESPEN-Guidelines/ESPEN-practical-short-micronutrient-guideline.pdf", target="_blank")
        ui.span(" · ")
        ui.a("Open ESPEN 2022 full guideline", href="https://www.espen.org/files/ESPEN-Guidelines/ESPEN_micronutrient_guideline.pdf", target="_blank")

with ui.panel_conditional("input.page === 'toolkit'"):
    ui.h2("Bedside Calculators & Conversions")
    ui.p("Bedside arithmetic and unit conversions. Outputs are calculated estimates or conversions, not prescriptions; select clinical inputs and dosing conventions deliberately.", class_="section-intro")

    with ui.card():
        ui.card_header("Fluid Tools")
        with ui.layout_columns(col_widths=(6, 6, 6, 6)):
            ui.input_numeric("tk_fluid_in", "Total input (mL)", 2200, min=0, step=50)
            ui.input_numeric("tk_fluid_out", "Total output (mL)", 1800, min=0, step=50)
            ui.input_numeric("tk_formula_vol", "Formula volume (mL)", 1000, min=0, step=50)
            ui.input_numeric("tk_water_100", "Water (mL per 100 mL)", 80, min=0, max=100, step=1)
        @render.ui
        def toolkit_fluid():
            b,e=safe_result(lambda: fluid_balance(input.tk_fluid_in(),input.tk_fluid_out()))
            w,e2=safe_result(lambda: formula_free_water(input.tk_formula_vol(),input.tk_water_100()))
            if e or e2: return ui.div(e or e2,class_="error-box")
            return ui.div(result_card("Fluid balance",num(b.value,0),b.unit,b.method),result_card("Formula free water",num(w.value,0),w.unit,w.method),class_="result-grid")

    with ui.card():
        ui.card_header("PN Macronutrient Energy")
        with ui.layout_columns(col_widths=(6, 6, 6, 6)):
            ui.input_numeric("tk_dextrose", "Dextrose (g)", 200, min=0, step=10)
            ui.input_numeric("tk_aa", "Amino acids (g)", 80, min=0, step=5)
            ui.input_numeric("tk_lipid", "Lipid (g)", 50, min=0, step=5)
            ui.input_numeric("tk_lipid_density", "Lipid energy density (kcal/g)", 10, min=0.1, step=0.1)
        @render.ui
        def toolkit_pn():
            r,err=safe_result(lambda: pn_macronutrient_energy(input.tk_dextrose(),input.tk_aa(),input.tk_lipid(),lipid_kcal_g=input.tk_lipid_density()))
            if err: return ui.div(err,class_="error-box")
            return result_card("PN macronutrient energy",num(r.value,0),r.unit,"Confirm product-specific composition and energy density")

    with ui.card():
        ui.card_header("Indirect Calorimetry")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("tk_vo2","VO2 (mL/min)",250,min=0.1)
            ui.input_numeric("tk_vco2","VCO2 (mL/min)",200,min=0.1)
        @render.ui
        def toolkit_ic():
            rq,e=safe_result(lambda: respiratory_quotient(input.tk_vo2(),input.tk_vco2()))
            ee,e2=safe_result(lambda: weir_energy(input.tk_vo2(),input.tk_vco2()))
            if e or e2: return ui.div(e or e2,class_="error-box")
            return ui.div(result_card("Respiratory quotient",num(rq.value,2),"",rq.method),result_card("Weir EE",num(ee.value,0),ee.unit,ee.method),class_="result-grid")

    with ui.card():
        ui.card_header("General Unit Converter")
        choices={"kg":"kg","lb":"lb","cm":"cm","in":"in","L":"L","mL":"mL","kcal":"kcal","kJ":"kJ"}
        with ui.layout_columns(col_widths=(4, 4, 4)):
            ui.input_numeric("tk_convert_value","Value",1,step=0.1)
            ui.input_select("tk_from","From",choices,selected="kg")
            ui.input_select("tk_to","To",choices,selected="lb")
        @render.ui
        def toolkit_convert():
            r,err=safe_result(lambda: convert_units(input.tk_convert_value(),input.tk_from(),input.tk_to()))
            if err: return ui.div(err,class_="error-box")
            return result_card("Converted value",num(r.value,3),r.unit,r.method)

    with ui.card():
        ui.card_header("Electrolyte mmol ↔ mEq")
        ui.p("This arithmetic requires the absolute ionic valence. It does not convert mass (mg) to mmol; mass conversions require the compound-specific molecular weight.",class_="small-note")
        with ui.layout_columns(col_widths=(4, 4, 4)):
            ui.input_numeric("tk_elect_amount","Amount",10,min=0,step=0.1)
            ui.input_numeric("tk_valence","Absolute valence",1,min=1,step=1)
            ui.input_select("tk_elect_dir","Direction",{"mmol_to_mEq":"mmol → mEq","mEq_to_mmol":"mEq → mmol"})
        @render.ui
        def toolkit_electrolyte():
            r,err=safe_result(lambda: electrolyte_mmol_mEq(input.tk_elect_amount(),int(input.tk_valence()),input.tk_elect_dir()))
            if err: return ui.div(err,class_="error-box")
            return result_card("Converted electrolyte amount",num(r.value,2),r.unit,r.method)

    with ui.card():
        ui.card_header("Formulation-Aware Electrolyte Conversion")
        ui.p("Select the exact chemical form. Commercial concentrations and hydration states vary; confirm the product label before clinical use.", class_="small-note")
        fchoices={k:v.name for k,v in FORMULATIONS.items()}
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_select("tk_formulation","Chemical formulation",fchoices)
            ui.input_numeric("tk_form_mass","Mass (mg)",584.4,min=0,step=1)
        @render.ui
        def toolkit_formulation():
            def calc():
                fid=input.tk_formulation(); mmol=mass_mg_to_compound_mmol(input.tk_form_mass(),fid); return get_formulation(fid),mmol,ion_amounts(mmol,fid)
            result,err=safe_result(calc)
            if err: return ui.div(err,class_="error-box")
            f,mmol,ions=result
            ion_text=" · ".join(f"{name}: {vals['mmol']:.2f} mmol / {vals['mEq']:.2f} mEq" for name,vals in ions.items())
            return ui.div(result_card("Compound amount",num(mmol,2),"mmol",f.name),ui.p(ion_text,class_="small-note"),ui.p(f.note,class_="small-note") if f.note else ui.span())

    with ui.card():
        ui.card_header("PN Concentration, Rate & Energy Distribution")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("tk_pn_volume","Final PN volume (mL)",1500,min=0.1,step=50)
            ui.input_numeric("tk_pn_hours","Infusion duration (hours)",24,min=0.1,step=1)
        @render.ui
        def toolkit_pn_advanced():
            def calc():
                conc=dextrose_concentration_percent(input.tk_dextrose(),input.tk_pn_volume()); rate=infusion_rate_ml_hr(input.tk_pn_volume(),input.tk_pn_hours()); dist=pn_distribution(input.tk_dextrose(),input.tk_aa(),input.tk_lipid(),lipid_kcal_g=input.tk_lipid_density()); return conc,rate,dist
            result,err=safe_result(calc)
            if err: return ui.div(err,class_="error-box")
            conc,rate,d=result
            return ui.div(result_card("Dextrose concentration",num(conc,1),"% w/v","g per 100 mL final volume"),result_card("PN infusion rate",num(rate,1),"mL/hour","final volume / duration"),result_card("Energy distribution",f"CHO {d['dextrose_percent']:.0f}% · AA {d['amino_acid_percent']:.0f}% · lipid {d['lipid_percent']:.0f}%","",f"Total {d['total_kcal']:.0f} kcal; confirm product-specific energy densities"),class_="result-grid")

with ui.panel_conditional("input.page === 'obesity'"):
    ui.h2("Obesity in Critical Illness")
    ui.p("Adult ICU bedside reference. Prefer measured energy expenditure and individualized assessment; BMI alone does not describe lean mass, sarcopenia or metabolic demand.",class_="section-intro")

    ui.input_select("obesity_topic","Bedside question",{
        "assessment":"Assessment & body composition",
        "energy":"Energy",
        "protein":"Protein",
        "abw":"ESPEN adjusted body weight",
        "aspen":"ASPEN obesity guidance",
        "monitoring":"Monitoring & safeguards",
    },selected="assessment")

    with ui.panel_conditional("input.obesity_topic === 'assessment'"):
        with ui.card():
            ui.card_header("Assessment")
            ui.tags.ul(
                ui.tags.li("Obesity defined by BMI is heterogeneous; high BMI does not establish high lean body mass."),
                ui.tags.li("Actively consider sarcopenic obesity and recent loss of muscle or function."),
                ui.tags.li("Fluid accumulation can further distort body weight and BMI in critical illness."),
                ui.tags.li("When feasible, combine clinical assessment with muscle/body-composition information rather than relying on BMI alone."),
            )

    with ui.panel_conditional("input.obesity_topic === 'energy'"):
        with ui.card():
            ui.card_header("Energy · ESPEN ICU 2023")
            ui.tags.ul(
                ui.tags.li("Guide energy intake by indirect calorimetry whenever available."),
                ui.tags.li("Predictive equations are particularly uncertain in obesity; avoid assuming that actual body weight multiplied by a generic kcal/kg factor represents measured expenditure."),
                ui.tags.li("If indirect calorimetry is unavailable, ESPEN allows an adjusted-body-weight approach as a pragmatic fallback."),
                ui.tags.li("Continue general ICU safeguards against early full feeding and overfeeding."),
            )
            ui.div("Measured energy expenditure is preferred over a weight-based obesity equation.",class_="warning-box")

    with ui.panel_conditional("input.obesity_topic === 'protein'"):
        with ui.card():
            ui.card_header("Protein · ESPEN ICU 2023")
            ui.tags.ul(
                ui.tags.li("Prefer urinary nitrogen losses or lean-body-mass determination to guide protein delivery where feasible."),
                ui.tags.li("If those are unavailable, ESPEN states that protein intake can be 1.3 g/kg adjusted body weight/day."),
                ui.tags.li("Energy and protein are separate therapeutic dimensions: avoiding overfeeding does not justify inadvertent low-protein feeding."),
            )

    with ui.panel_conditional("input.obesity_topic === 'abw'"):
        with ui.card():
            ui.card_header("ESPEN Pragmatic Adjusted Body Weight")
            ui.p("ESPEN describes a pragmatic fallback that adds 20–25% of excess weight (actual weight − ideal weight) to ideal body weight when indirect calorimetry is unavailable.")
            with ui.layout_columns(col_widths=(4,4,4)):
                ui.input_numeric("ob_actual","Actual weight (kg)",120,min=0.1,step=0.1)
                ui.input_numeric("ob_ideal","Ideal/reference weight (kg)",70,min=0.1,step=0.1)
                ui.input_numeric("ob_fraction","Excess-weight fraction",0.25,min=0.20,max=0.25,step=0.01)
            @render.ui
            def obesity_abw_result():
                if missing_inputs(input.ob_actual(), input.ob_ideal(), input.ob_fraction()):
                    return enter_prompt("actual weight, ideal/reference weight, and adjustment factor")
                actual=float(input.ob_actual()); ideal=float(input.ob_ideal()); f=float(input.ob_fraction())
                if actual < ideal:
                    return ui.div("Actual weight is below the entered ideal/reference weight. Adjusted body weight is therefore not appropriate here. Review the entered weights or use the clinically appropriate weight descriptor.",class_="error-box")
                value=ideal+f*(actual-ideal)
                return result_card("Adjusted body weight",num(value,1),"kg",f"IBW + {f:.0%} × (actual weight − IBW)")
            ui.p("This calculator does not decide whether adjusted weight is appropriate. Use it only when the selected guideline/method calls for this ESPEN fallback.",class_="small-note")

    with ui.panel_conditional("input.obesity_topic === 'aspen'"):
        with ui.card():
            ui.card_header("ASPEN Obesity Guidance — Keep Separate")
            ui.p("ASPEN guidance for hospitalized adults with obesity supports a trial of hypocaloric, high-protein feeding in appropriate patients without severe renal or hepatic dysfunction. This is a different framework from the ESPEN adjusted-weight fallback and should not be silently combined with it.")
            ui.tags.ul(
                ui.tags.li("ASPEN describes hypocaloric feeding as approximately 50–70% of estimated energy requirements or <14 kcal/kg actual weight."),
                ui.tags.li("High-protein feeding may begin around 1.2 g/kg actual weight or 2–2.5 g/kg ideal body weight, with adjustment using nitrogen-balance information when available."),
                ui.tags.li("The ASPEN recommendation is weak and based on low-quality evidence; renal/hepatic dysfunction and individual tolerance require additional consideration."),
            )
            ui.div("Choose one guideline framework deliberately. Do not calculate energy with one society's weight convention and protein with another society's convention without a clinical rationale.",class_="warning-box")

    with ui.panel_conditional("input.obesity_topic === 'monitoring'"):
        with ui.card():
            ui.card_header("Monitoring & Safeguards")
            ui.tags.ul(
                ui.tags.li("Track actual energy and protein delivered separately."),
                ui.tags.li("Include propofol, IV dextrose and other non-nutritional calories when evaluating total energy exposure."),
                ui.tags.li("Monitor glucose and triglycerides when clinically relevant and reassess for overfeeding."),
                ui.tags.li("Follow gastrointestinal tolerance, fluid balance and weight trend, recognizing that edema can obscure tissue loss."),
                ui.tags.li("Reassess muscle mass/function when feasible; weight stability does not exclude muscle loss."),
                ui.tags.li("If nitrogen balance is used, interpret it cautiously in changing renal function and extracorporeal therapies."),
            )

    with ui.card():
        ui.card_header("Sources & Scope")
        ui.p("Primary ICU source: Singer P, Reintam Blaser A, Berger MM, et al. ESPEN practical and partially revised guideline: Clinical nutrition in the intensive care unit. Clinical Nutrition. 2023;42:1671–1689.")
        ui.a("Open ESPEN ICU guideline",href="https://www.espen.org/files/ESPEN-Guidelines/ESPEN_practical_and_partially_revised_guideline_Clinical_nutrition_in_the_intensive_care_unit.pdf",target="_blank",rel="noopener noreferrer")
        ui.p("ASPEN comparison: Clinical Guidelines: Nutrition Support of Hospitalized Adult Patients With Obesity. The ASPEN card is intentionally labelled separately so its dosing conventions are not merged with ESPEN.",class_="small-note")


with ui.panel_conditional("input.page === 'pancreatitis'"):
    ui.h2("Acute Pancreatitis Nutrition")
    ui.p("Adult bedside nutrition pathway based on the 2024 ESPEN practical guideline. This section addresses nutrition support decisions rather than diagnosis or general medical management of acute pancreatitis.",class_="section-intro")

    ui.input_select("ap_topic","Bedside question",{
        "oral":"Can oral feeding start?",
        "en":"When is EN needed?",
        "route":"NG or NJ?",
        "formula":"Which enteral formula?",
        "pn":"When is PN appropriate?",
        "severe":"Severe/necrotizing disease",
        "enzymes":"Pancreatic enzymes?",
        "monitor":"What should I monitor?",
    },selected="oral")

    with ui.panel_conditional("input.ap_topic === 'oral'"):
        with ui.card():
            ui.card_header("Early Oral Feeding")
            ui.tags.ul(
                ui.tags.li("In predicted mild acute pancreatitis, offer oral feeding as soon as clinically tolerated."),
                ui.tags.li("Do not wait for serum lipase to normalize before refeeding."),
                ui.tags.li("When restarting oral feeding in mild acute pancreatitis, ESPEN recommends a low-fat soft diet rather than a stepwise clear-liquid progression."),
            )
            ui.div("Pain resolution, bowel movement and normalization of pancreatic enzymes are not mandatory prerequisites for oral refeeding when the patient is clinically able to eat.",class_="info-box")

    with ui.panel_conditional("input.ap_topic === 'en'"):
        with ui.card():
            ui.card_header("Enteral Nutrition")
            ui.tags.ul(
                ui.tags.li("If oral feeding is not tolerated or is not feasible, prefer EN to PN."),
                ui.tags.li("When EN is required because oral feeding is not tolerated, start it early—within 24–72 hours of admission."),
                ui.tags.li("EN remains the primary nutrition-support route in severe acute pancreatitis when the gastrointestinal tract can be used."),
            )
            ui.div("Do not keep a patient nil-by-mouth solely to 'rest the pancreas' when oral or enteral feeding is clinically tolerated.",class_="warning-box")

    with ui.panel_conditional("input.ap_topic === 'route'"):
        with ui.card():
            ui.card_header("Nasogastric First; Nasojejunal When Needed")
            ui.tags.ul(
                ui.tags.li("When EN is required, ESPEN recommends administration via a nasogastric tube as the usual initial route."),
                ui.tags.li("Prefer nasojejunal feeding when there is digestive intolerance such as persistent pain or vomiting with gastric feeding."),
                ui.tags.li("Routine post-pyloric placement is therefore not required solely because the diagnosis is acute pancreatitis."),
            )

    with ui.panel_conditional("input.ap_topic === 'formula'"):
        with ui.card():
            ui.card_header("Enteral Formula")
            ui.tags.ul(
                ui.tags.li("Use a standard polymeric enteral formula for acute pancreatitis."),
                ui.tags.li("Evidence does not support routine use of a specialized semi-elemental formula for all patients."),
                ui.tags.li("A semi-elemental formula may be considered in selected severe disease when malabsorption or intolerance is clinically important."),
            )
            ui.div("Pancreatitis alone is not an indication for an elemental or semi-elemental formula.",class_="info-box")

    with ui.panel_conditional("input.ap_topic === 'pn'"):
        with ui.card():
            ui.card_header("Parenteral Nutrition")
            ui.tags.ul(
                ui.tags.li("Use PN when EN is contraindicated, not tolerated, or cannot meet targeted nutritional requirements despite appropriate attempts."),
                ui.tags.li("EN should remain the preferred route when the gastrointestinal tract is usable."),
                ui.tags.li("When PN is necessary, apply the same critical-care safeguards for progressive delivery, refeeding risk, glucose, electrolytes, triglycerides, fluid balance and line-related complications."),
            )
            ui.div("PN is not first-line nutrition support simply because pancreatitis is severe.",class_="warning-box")

    with ui.panel_conditional("input.ap_topic === 'severe'"):
        with ui.card():
            ui.card_header("Severe / Necrotizing Acute Pancreatitis")
            ui.tags.ul(
                ui.tags.li("Prioritize enteral over parenteral nutrition whenever feasible."),
                ui.tags.li("Reassess gastric tolerance; use jejunal access when gastric feeding is not tolerated."),
                ui.tags.li("After minimally invasive necrosectomy, oral intake may be initiated within the first 24 hours when hemodynamic status, septic parameters and gastric emptying allow."),
                ui.tags.li("Consider the broader ICU context: organ failure, abdominal pressure/compartment pathology, procedures, fluid status and refeeding risk can alter the nutrition plan."),
            )

    with ui.panel_conditional("input.ap_topic === 'enzymes'"):
        with ui.card():
            ui.card_header("Pancreatic Enzyme Replacement")
            ui.p("Do not prescribe pancreatic enzyme replacement routinely for acute pancreatitis solely on the basis of the diagnosis.")
            ui.tags.ul(
                ui.tags.li("Consider pancreatic exocrine insufficiency when there is persistent maldigestion/malabsorption, steatorrhea, unexplained weight loss or other compatible evidence, particularly after necrotizing disease or pancreatic intervention."),
                ui.tags.li("If pancreatic enzyme replacement therapy is indicated, enzymes should accompany meals and snacks so that enzymes mix with chyme."),
                ui.tags.li("Dose and product selection should follow the clinical indication and local pancreatic-exocrine-insufficiency guidance rather than an acute-pancreatitis diagnosis alone."),
            )

    with ui.panel_conditional("input.ap_topic === 'monitor'"):
        with ui.card():
            ui.card_header("Nutrition Monitoring")
            ui.tags.ul(
                ui.tags.li("Oral/EN tolerance: pain pattern, nausea/vomiting, gastric intolerance and abdominal findings."),
                ui.tags.li("Actual energy and protein delivered versus the intended nutrition plan."),
                ui.tags.li("Fluid balance and gastrointestinal losses."),
                ui.tags.li("Glucose, potassium, magnesium and phosphorus; apply the refeeding pathway when risk is present."),
                ui.tags.li("Triglycerides when clinically relevant, including hypertriglyceridemia-associated pancreatitis or IV lipid exposure."),
                ui.tags.li("Weight and muscle/nutrition-status trajectory during prolonged or severe disease."),
                ui.tags.li("Evidence of maldigestion or pancreatic exocrine insufficiency during recovery when clinically suspected."),
            )

    with ui.card():
        ui.card_header("Source & Scope")
        ui.p("Primary source: Arvanitakis M, Ockenga J, Bezmarevic M, et al. ESPEN practical guideline on clinical nutrition in acute and chronic pancreatitis. Clinical Nutrition. 2024;43:395–412.")
        ui.a("Open ESPEN pancreatitis guideline",href="https://www.espen.org/files/ESPEN-Guidelines/ESPEN-practical-guideline-on-clinical-nutrition-in-acute-and-chronic-pancreatitis.pdf",target="_blank",rel="noopener noreferrer")
        ui.p("This pocket-guide module focuses on acute pancreatitis in adults. Detailed chronic-pancreatitis dietary management is outside this module.",class_="small-note")


with ui.panel_conditional("input.page === 'liver'"):
    ui.h2("Liver Disease in Critical Illness")
    ui.p("Adult bedside nutrition reference based primarily on the ESPEN practical guideline on clinical nutrition in liver disease, with ICU principles applied when critically ill. Nutrition therapy should be individualized to disease phase, nutritional status, organ support and tolerance.",class_="section-intro")

    ui.input_select("liver_topic","Bedside question",{
        "assessment":"Nutrition risk & assessment",
        "cirrhosis":"Cirrhosis: energy & protein",
        "he":"Hepatic encephalopathy",
        "alf":"Acute liver failure",
        "route":"Oral, EN or PN?",
        "fasting":"Meal pattern & fasting",
        "fluid":"Ascites, sodium & fluid",
        "micro":"Micronutrients & refeeding",
        "monitor":"What should I monitor?",
    },selected="assessment")

    with ui.panel_conditional("input.liver_topic === 'assessment'"):
        with ui.card():
            ui.card_header("Nutrition Risk & Assessment")
            ui.tags.ul(
                ui.tags.li("Malnutrition and sarcopenia are common in advanced liver disease and are clinically important even when BMI is normal or high."),
                ui.tags.li("Ascites and edema can make body weight, BMI and recent weight change misleading; use estimated dry weight when appropriate and interpret anthropometry cautiously."),
                ui.tags.li("Assess intake, recent fasting, muscle loss/function, gastrointestinal symptoms, alcohol history when relevant, and the severity/trajectory of liver disease."),
                ui.tags.li("Do not use serum albumin as a stand-alone marker of nutrition status in liver disease."),
            )

    with ui.panel_conditional("input.liver_topic === 'cirrhosis'"):
        with ui.card():
            ui.card_header("Cirrhosis · Energy & Protein")
            ui.tags.ul(
                ui.tags.li("For malnourished and/or sarcopenic patients with cirrhosis, ESPEN recommends about 30–35 kcal/kg/day and 1.5 g protein/kg/day."),
                ui.tags.li("For non-malnourished patients with compensated cirrhosis, use an individualized intake appropriate to nutritional status and activity rather than assuming all cirrhosis requires high-calorie feeding."),
                ui.tags.li("Use dry or clinically appropriate reference weight when fluid retention makes actual weight misleading."),
            )
            ui.div("Avoid protein restriction as a routine response to cirrhosis or hepatic encephalopathy.",class_="warning-box")

    with ui.panel_conditional("input.liver_topic === 'he'"):
        with ui.card():
            ui.card_header("Hepatic Encephalopathy")
            ui.tags.ul(
                ui.tags.li("Do not restrict protein in patients with hepatic encephalopathy as a routine strategy."),
                ui.tags.li("Maintain adequate energy and protein to limit catabolism and muscle loss; skeletal muscle contributes to ammonia handling."),
                ui.tags.li("Vegetable and dairy protein sources may be useful when conventional protein sources are poorly tolerated."),
                ui.tags.li("In selected protein-intolerant patients, vegetable protein or branched-chain amino acid supplementation may help achieve adequate nitrogen intake."),
                ui.tags.li("When severe encephalopathy prevents safe oral intake, provide nutrition by an appropriate enteral route when the airway is protected; PN is an alternative when EN cannot be used adequately."),
            )
            ui.div("Chronic protein restriction can worsen negative nitrogen balance and sarcopenia. Mental-status change should trigger clinical evaluation—not automatic protein withdrawal.",class_="warning-box")

    with ui.panel_conditional("input.liver_topic === 'alf'"):
        with ui.card():
            ui.card_header("Acute Liver Failure")
            ui.tags.ul(
                ui.tags.li("Use the oral route when feasible; if oral intake is not possible, EN is generally preferred when the gastrointestinal tract can be used."),
                ui.tags.li("PN is second-line when adequate oral/enteral feeding is not possible."),
                ui.tags.li("In hyperacute liver failure with severe hyperammonemia, very high protein loads may be poorly tolerated in a small subgroup; reassess dynamically rather than imposing prolonged blanket protein restriction."),
                ui.tags.li("Avoid overfeeding and integrate nutrition with glucose control, cerebral/neurologic status and the broader critical-care plan."),
            )

    with ui.panel_conditional("input.liver_topic === 'route'"):
        with ui.card():
            ui.card_header("Oral → EN → PN")
            ui.tags.ul(
                ui.tags.li("Use oral diet plus oral nutrition supplements when safe and sufficient."),
                ui.tags.li("Use EN when oral intake is inadequate and the gastrointestinal tract is usable."),
                ui.tags.li("Esophageal varices are not, by themselves, an absolute contraindication to nasogastric tube placement for EN; consider the individual bleeding/procedural context."),
                ui.tags.li("Use PN when oral and EN are contraindicated or fail to provide adequate intake."),
            )

    with ui.panel_conditional("input.liver_topic === 'fasting'"):
        with ui.card():
            ui.card_header("Avoid Prolonged Fasting")
            ui.tags.ul(
                ui.tags.li("Cirrhosis is associated with accelerated starvation physiology; avoid unnecessarily long fasting periods."),
                ui.tags.li("Distribute intake across multiple meals/snacks during the day."),
                ui.tags.li("Provide a late-evening snack to shorten the overnight fasting interval, particularly in patients at nutrition risk."),
            )
            ui.div("Meal timing is part of nutrition therapy in cirrhosis; adequate daily totals delivered after long fasting intervals are not necessarily metabolically equivalent.",class_="info-box")

    with ui.panel_conditional("input.liver_topic === 'fluid'"):
        with ui.card():
            ui.card_header("Ascites, Sodium & Fluid")
            ui.tags.ul(
                ui.tags.li("Interpret weight in the context of ascites, edema, paracentesis and diuretic therapy."),
                ui.tags.li("Sodium restriction for ascites must be balanced against palatability and adequate food intake; an overly restrictive diet can worsen intake."),
                ui.tags.li("Do not impose routine fluid restriction solely because ascites is present; fluid strategy depends particularly on serum sodium and the medical plan."),
                ui.tags.li("When fluid volume is constrained, consider nutrient-dense oral/enteral options while still accounting for sodium and overall tolerance."),
            )

    with ui.panel_conditional("input.liver_topic === 'micro'"):
        with ui.card():
            ui.card_header("Micronutrients & Refeeding")
            ui.tags.ul(
                ui.tags.li("Suspect micronutrient deficiencies when there is poor intake, alcohol-associated disease, prolonged decompensation, malabsorption or other compatible risk."),
                ui.tags.li("Thiamin deserves particular attention in patients with alcohol-use history or significant malnutrition, especially before carbohydrate delivery when refeeding risk is present."),
                ui.tags.li("Do not infer a specific micronutrient deficiency from liver disease alone; use clinical context, laboratory assessment where appropriate and the dedicated Micronutrients reference."),
                ui.tags.li("Use the ASPEN Refeeding pathway for patients at risk rather than accelerating calories simply because intake has been poor."),
            )

    with ui.panel_conditional("input.liver_topic === 'monitor'"):
        with ui.card():
            ui.card_header("Bedside Nutrition Monitoring")
            ui.tags.ul(
                ui.tags.li("Actual energy and protein intake/delivery and interruptions."),
                ui.tags.li("Oral/EN tolerance, nausea, early satiety and gastrointestinal losses."),
                ui.tags.li("Estimated dry-weight and muscle/function trajectory rather than scale weight alone."),
                ui.tags.li("Fluid balance, ascites/edema, serum sodium, potassium, magnesium and phosphorus."),
                ui.tags.li("Glucose and clinically relevant triglycerides; include non-nutritional calories in ICU patients."),
                ui.tags.li("Mental status in context—do not use encephalopathy alone as evidence that protein is excessive."),
                ui.tags.li("Refeeding risk and micronutrient concerns when intake has been markedly reduced."),
            )

    with ui.card():
        ui.card_header("Sources & Scope")
        ui.p("Primary source: Bischoff SC, Bernal W, Dasarathy S, et al. ESPEN practical guideline: Clinical nutrition in liver disease. Clinical Nutrition. 2020;39:3533–3562.")
        ui.a("Open ESPEN liver guideline",href="https://academy.espen.org/files/ESPEN-Guidelines/ESPEN_practical_guideline_Clinical_nutrition_in_liver_disease.pdf",target="_blank",rel="noopener noreferrer")
        ui.p("Additional context: EASL Clinical Practice Guidelines on nutrition in chronic liver disease. General ICU nutrition principles should also be applied when the patient is critically ill.",class_="small-note")


with ui.panel_conditional("input.page === 'gi_losses'"):
    ui.h2("GI Losses, High-Output Stoma & Intestinal Failure")
    ui.p("Adult bedside nutrition and fluid reference. Management depends on anatomy, remaining bowel, output, renal function and the underlying cause; early specialist surgical/gastroenterology/intestinal-failure input is important when losses are persistent or severe.",class_="section-intro")

    ui.input_select("gi_topic","Bedside question",{
        "recognize":"Is the output clinically important?",
        "assess":"What should I assess first?",
        "fluids":"Fluid & sodium strategy",
        "oral":"Food & oral fluids",
        "route":"Oral/EN or PN?",
        "fistula":"Enterocutaneous fistula",
        "sbs":"Short bowel: anatomy matters",
        "monitor":"What should I monitor?",
        "redflags":"Escalation / red flags",
    },selected="recognize")

    with ui.panel_conditional("input.gi_topic === 'recognize'"):
        with ui.card():
            ui.card_header("Recognize High Output")
            ui.tags.ul(
                ui.tags.li("A high-output stoma/fistula is clinically defined by output sufficient to cause water, sodium and often magnesium depletion—not by volume alone."),
                ui.tags.li("In practice, small-bowel stoma output above about 1.5–2.0 L/day commonly becomes clinically important, but the patient's intake, anatomy and absorptive capacity determine the consequence."),
                ui.tags.li("Look for thirst, postural symptoms, low urine output, rising creatinine/urea, weight change, cramps and electrolyte depletion."),
            )
            ui.div("Do not interpret stoma output in isolation. A patient drinking large volumes of hypotonic fluid may have both high output and worsening sodium/water depletion.",class_="warning-box")

    with ui.panel_conditional("input.gi_topic === 'assess'"):
        with ui.card():
            ui.card_header("Assess Before Escalating Nutrition")
            ui.tags.ul(
                ui.tags.li("Measure 24-hour oral/enteral intake, stoma/fistula output and urine output where feasible."),
                ui.tags.li("Clarify anatomy: jejunostomy versus ileostomy, colon in continuity, bowel length if known, ileocecal valve, recent resection and fistula location."),
                ui.tags.li("Exclude reversible causes of increased output such as infection, obstruction/stricture, active inflammation, medication effects or abrupt withdrawal of output-reducing medicines."),
                ui.tags.li("Assess nutrition status, recent weight trajectory, muscle loss, hydration and renal function."),
                ui.tags.li("Review sodium, potassium, magnesium and renal indices; consider urine sodium as a useful hydration/sodium-depletion marker when clinically appropriate."),
            )

    with ui.panel_conditional("input.gi_topic === 'fluids'"):
        with ui.card():
            ui.card_header("Fluid & Sodium Strategy")
            ui.tags.ul(
                ui.tags.li("Small-bowel effluent contains substantial sodium; replacing losses with plain water alone can worsen sodium depletion."),
                ui.tags.li("When high output persists, restrict excessive hypotonic fluids such as plain water, tea, coffee and many low-sodium drinks rather than advising unrestricted free water."),
                ui.tags.li("Use a glucose-saline oral rehydration solution with sodium concentration approximately 90–120 mmol/L for patients who require high-output stoma replacement strategies."),
                ui.tags.li("Avoid relying on hypertonic sugary beverages as rehydration; they may increase intestinal fluid losses in susceptible patients."),
                ui.tags.li("Severe dehydration or renal impairment may require IV sodium-containing fluid before an oral strategy is adequate."),
            )
            ui.div("A standard 'drink more water' instruction can be harmful in high-output jejunostomy/ileostomy. Replace water and sodium together using an appropriate strategy.",class_="warning-box")

    with ui.panel_conditional("input.gi_topic === 'oral'"):
        with ui.card():
            ui.card_header("Food & Oral Intake")
            ui.tags.ul(
                ui.tags.li("Encourage adequate energy and protein intake using small, frequent meals when oral feeding is feasible."),
                ui.tags.li("Separate individualized high-output fluid advice from general healthy-eating advice; the fluid strategy may be counterintuitive."),
                ui.tags.li("Do not impose unnecessary dietary restriction that reduces overall intake."),
                ui.tags.li("If substantial colon remains in continuity, dietary strategy differs from an end-jejunostomy because the colon can salvage fluid and energy from carbohydrate fermentation."),
                ui.tags.li("Consider additional salt with food when clinically appropriate and not contraindicated, particularly with high small-bowel sodium losses."),
            )

    with ui.panel_conditional("input.gi_topic === 'route'"):
        with ui.card():
            ui.card_header("Use the Gut When It Is Functional")
            ui.tags.ul(
                ui.tags.li("Use oral/enteral nutrition when sufficient functional gastrointestinal tract is available and intake/absorption can meet requirements."),
                ui.tags.li("EN may support intestinal adaptation, but route, rate, concentration and formula need individualization when output is high."),
                ui.tags.li("PN is indicated when intestinal absorption is insufficient to maintain nutrition and/or fluid-electrolyte balance despite optimized oral/enteral management."),
                ui.tags.li("Do not use PN solely because a stoma or fistula exists; anatomy, output, tolerance and absorptive capacity determine intestinal failure."),
            )

    with ui.panel_conditional("input.gi_topic === 'fistula'"):
        with ui.card():
            ui.card_header("Enterocutaneous Fistula")
            ui.tags.ul(
                ui.tags.li("Define fistula location and output and look for sepsis, abscess, obstruction and skin/wound complications."),
                ui.tags.li("Replace fluid and electrolyte losses and address sepsis before assuming that escalating calories alone will correct deterioration."),
                ui.tags.li("Use oral/EN when feasible and anatomically appropriate; distal feeding/fistuloclysis may be considered in specialist settings when suitable access and bowel are available."),
                ui.tags.li("High-output proximal fistula or inability to maintain fluid/nutrition balance enterally commonly requires PN."),
            )
            ui.div("Nutrition route in fistula is an anatomy-and-function decision, not a blanket 'EN versus PN' rule.",class_="info-box")

    with ui.panel_conditional("input.gi_topic === 'sbs'"):
        with ui.card():
            ui.card_header("Short Bowel: Anatomy Changes the Plan")
            ui.tags.ul(
                ui.tags.li("Record remaining small-bowel length and whether colon is in continuity whenever this information is available."),
                ui.tags.li("End-jejunostomy physiology carries a particularly high risk of sodium, water and magnesium depletion."),
                ui.tags.li("Patients with colon in continuity may salvage additional energy and fluid; dietary composition and oxalate considerations differ from patients without colon continuity."),
                ui.tags.li("The need for long-term parenteral support depends on functional absorption and anatomy, not bowel length alone."),
                ui.tags.li("Persistent intestinal failure warrants specialist multidisciplinary follow-up for adaptation, micronutrients, medications and parenteral support."),
            )

    with ui.panel_conditional("input.gi_topic === 'monitor'"):
        with ui.card():
            ui.card_header("Bedside Monitoring")
            ui.tags.ul(
                ui.tags.li("24-hour stoma/fistula output and trend."),
                ui.tags.li("Urine volume, fluid balance, thirst/postural symptoms and clinically appropriate weight trend."),
                ui.tags.li("Sodium, potassium, magnesium, creatinine/urea and acid-base status; phosphorus when nutrition risk/refeeding is relevant."),
                ui.tags.li("Urine sodium when useful to assess sodium depletion and response to treatment."),
                ui.tags.li("Actual energy/protein intake and evidence of malabsorption or progressive weight/muscle loss."),
                ui.tags.li("Longer-term intestinal failure: micronutrients and trace elements according to anatomy, losses and parenteral therapy."),
            )

    with ui.panel_conditional("input.gi_topic === 'redflags'"):
        with ui.card():
            ui.card_header("Escalate Early")
            ui.tags.ul(
                ui.tags.li("Oliguria, acute kidney injury, severe thirst/postural symptoms or inability to maintain hydration."),
                ui.tags.li("Persistent or rapidly increasing high output despite initial measures."),
                ui.tags.li("Severe or refractory magnesium, sodium, potassium or acid-base disturbance."),
                ui.tags.li("Suspected obstruction, ischemia, intra-abdominal sepsis or uncontrolled fistula-related infection."),
                ui.tags.li("Progressive malnutrition or inability to meet fluid/nutrition requirements enterally."),
                ui.tags.li("Need for home/parenteral support or complex short-bowel management."),
            )

    with ui.card():
        ui.card_header("Sources & Scope")
        ui.p("Primary bedside source: Nightingale JMD. How to manage a high-output stoma. Frontline Gastroenterology. 2022;13:140–151. Broader intestinal-failure principles are aligned with ESPEN guidance on chronic intestinal failure.")
        ui.a("Open high-output stoma review",href="https://fg.bmj.com/content/13/2/140",target="_blank",rel="noopener noreferrer")
        ui.p("This module supports bedside recognition and nutrition/fluid decisions. Drug regimens, exact IV replacement orders and long-term home parenteral nutrition prescriptions require individualized specialist management.",class_="small-note")


with ui.panel_conditional("input.page === 'special_icu'"):
    ui.h2("Trauma, Burns, Sepsis & Special ICU Situations")
    ui.p("Adult bedside nutrition modifiers for selected hypermetabolic and surgical ICU situations. Start with the general Critical Care Guidelines, then use this page for condition-specific considerations.",class_="section-intro")

    ui.input_select("special_topic","Clinical situation",{
        "sepsis":"Sepsis & septic shock",
        "trauma":"Major trauma",
        "burns":"Major burns",
        "surgery":"Postoperative / surgical ICU",
        "openabd":"Open abdomen & wound losses",
        "protein":"Protein: practical safeguards",
        "monitor":"What should I monitor?",
    },selected="sepsis")

    with ui.panel_conditional("input.special_topic === 'sepsis'"):
        with ui.card():
            ui.card_header("Sepsis & Septic Shock")
            ui.tags.ul(
                ui.tags.li("Do not start or advance full enteral feeding during uncontrolled shock or when tissue perfusion remains unstable."),
                ui.tags.li("After hemodynamic stabilization/control of shock, low-dose EN can be started and advanced progressively while monitoring tolerance."),
                ui.tags.li("Avoid early full-dose energy delivery; apply the progressive ICU energy strategy rather than attempting to immediately match estimated expenditure."),
                ui.tags.li("Protein delivery should also be advanced progressively and considered separately from energy delivery."),
                ui.tags.li("Account for non-nutritional calories from propofol, glucose-containing solutions and citrate where relevant."),
            )
            ui.div("New abdominal pain/distension, rising lactate in context, feeding intolerance or other concern for bowel ischemia during vasopressor-dependent illness requires urgent clinical reassessment—not automatic feed escalation.",class_="warning-box")

    with ui.panel_conditional("input.special_topic === 'trauma'"):
        with ui.card():
            ui.card_header("Major Trauma")
            ui.tags.ul(
                ui.tags.li("Once resuscitation is established and the gastrointestinal tract is usable, favor early EN in patients unable to eat."),
                ui.tags.li("Major trauma is highly catabolic; avoid prolonged under-delivery of protein while also avoiding early energy overfeeding."),
                ui.tags.li("Consider the impact of repeated operations, sedation, fasting for procedures and feed interruptions on actual delivery."),
                ui.tags.li("Fluid shifts can make measured body weight unreliable for dosing and nutrition-status interpretation."),
                ui.tags.li("Reassess requirements and delivery as the patient transitions from early acute illness toward recovery/rehabilitation."),
            )

    with ui.panel_conditional("input.special_topic === 'burns'"):
        with ui.card():
            ui.card_header("Major Burns")
            ui.tags.ul(
                ui.tags.li("Severe burns produce sustained hypermetabolism and catabolism; nutrition therapy should begin early once resuscitation and gastrointestinal perfusion permit."),
                ui.tags.li("Prefer EN when the gastrointestinal tract is functional; large burns commonly require a structured strategy to achieve substantial energy and protein needs."),
                ui.tags.li("Avoid relying on a single generic kcal/kg rule for major burns; burn size, phase of illness, procedures and clinical course substantially affect expenditure."),
                ui.tags.li("Protein requirements are increased because of catabolism and wound/exudative losses; use burn-specific specialist guidance and reassess delivery."),
                ui.tags.li("Track micronutrient status/replacement using burn-specific protocols where available rather than automatically applying routine ICU doses."),
            )
            ui.div("Major burns are a specialist exception: generic ICU calorie and micronutrient rules may be inadequate or inappropriate. Use local burn-center protocols when available.",class_="warning-box")

    with ui.panel_conditional("input.special_topic === 'surgery'"):
        with ui.card():
            ui.card_header("Postoperative / Surgical Critical Illness")
            ui.tags.ul(
                ui.tags.li("Avoid unnecessary postoperative fasting. Use oral feeding when safe and feasible."),
                ui.tags.li("When oral intake will be inadequate and the gut is usable, use EN rather than defaulting to PN."),
                ui.tags.li("Anastomosis alone is not a reason for prolonged starvation; route and timing depend on the operation, GI function and surgical plan."),
                ui.tags.li("If oral/EN is contraindicated or persistently inadequate, consider PN according to nutrition risk, expected duration and the broader ICU strategy."),
                ui.tags.li("Account for repeated procedures and fasting interruptions when judging whether prescribed nutrition is actually being delivered."),
            )

    with ui.panel_conditional("input.special_topic === 'openabd'"):
        with ui.card():
            ui.card_header("Open Abdomen & Wound / GI Losses")
            ui.tags.ul(
                ui.tags.li("Open-abdomen patients may have substantial nitrogen/protein and fluid-electrolyte losses; quantify clinically important losses where feasible."),
                ui.tags.li("Use EN when the gastrointestinal tract is viable and functional and there is no contraindication to feeding."),
                ui.tags.li("Enteric fistula, high-output stoma or proximal GI losses require anatomy-specific management; use the GI Losses & Intestinal Failure module."),
                ui.tags.li("Do not respond to wound losses by adding calories indiscriminately; reassess protein, energy, fluid and electrolyte components separately."),
            )

    with ui.panel_conditional("input.special_topic === 'protein'"):
        with ui.card():
            ui.card_header("Protein · Practical Safeguards")
            ui.tags.ul(
                ui.tags.li("Critical illness increases protein catabolism, but energy and protein are separate prescription decisions."),
                ui.tags.li("For general ICU care, ESPEN suggests progressive delivery toward approximately 1.3 g protein/kg/day; condition-specific needs may differ."),
                ui.tags.li("Major burns, large wounds and high-output losses may require individualized higher protein strategies under specialist guidance."),
                ui.tags.li("Renal dysfunction or KRT changes the protein approach; use the Renal & KRT module rather than reflexively restricting protein."),
                ui.tags.li("Do not use a high protein target as justification for energy overfeeding."),
            )

    with ui.panel_conditional("input.special_topic === 'monitor'"):
        with ui.card():
            ui.card_header("Bedside Monitoring")
            ui.tags.ul(
                ui.tags.li("Actual energy and protein delivered versus prescribed; record interruptions and non-nutritional calories."),
                ui.tags.li("Hemodynamic status and GI tolerance before and during EN advancement."),
                ui.tags.li("Glucose, potassium, magnesium and phosphorus; screen for refeeding risk after prolonged poor intake."),
                ui.tags.li("Fluid balance, edema and clinically appropriate dosing weight."),
                ui.tags.li("Wound, drain, fistula or burn losses when they materially affect protein/fluid/electrolyte needs."),
                ui.tags.li("Muscle/function and rehabilitation trajectory during prolonged critical illness."),
            )

    with ui.card():
        ui.card_header("Sources & Scope")
        ui.p("Core ICU recommendations: Singer P, Reintam Blaser A, Berger MM, et al. ESPEN practical and partially revised guideline: Clinical nutrition in the intensive care unit. Clinical Nutrition. 2023;42:1671–1689.")
        ui.a("Open ESPEN ICU guideline",href="https://www.espen.org/files/ESPEN-Guidelines/ESPEN_practical_and_partially_revised_guideline_Clinical_nutrition_in_the_intensive_care_unit.pdf",target="_blank",rel="noopener noreferrer")
        ui.p("Surgical context: ESPEN practical guideline: Clinical nutrition in surgery. Major-burn nutrition requires burn-specific expertise/protocols; this pocket guide intentionally avoids inventing a universal burn calorie or micronutrient prescription.",class_="small-note")


with ui.panel_conditional("input.page === 'monitoring_check'"):
    ui.h2("Nutrition Monitoring Checklist")
    ui.p("A non-documenting bedside prompt for adult critical-care nutrition. Use it to structure review; no checklist responses or patient information are stored.",class_="section-intro")

    ui.input_select("mon_phase","When are you reviewing?",{
        "before":"Before starting / changing nutrition",
        "early":"First 72 hours & advancement",
        "en":"Established enteral nutrition",
        "pn":"Established parenteral nutrition",
        "refeed":"Refeeding / major electrolyte risk",
        "prolonged":"Prolonged ICU stay / weekly review",
        "interrupt":"After interruption or major clinical change",
    },selected="before")

    with ui.panel_conditional("input.mon_phase === 'before'"):
        with ui.card():
            ui.card_header("Before Starting or Substantially Changing Nutrition")
            ui.tags.ul(
                ui.tags.li("Confirm the intended route and whether oral/EN is currently safe and feasible."),
                ui.tags.li("Review hemodynamic stability, GI function and contraindications to EN."),
                ui.tags.li("Identify nutrition risk, recent intake/fasting and refeeding risk."),
                ui.tags.li("Confirm the clinically appropriate dosing weight; account for edema, ascites, obesity or major fluid shifts."),
                ui.tags.li("Review potassium, magnesium, phosphorus and glucose when clinically relevant—especially before feeding a patient at refeeding risk."),
                ui.tags.li("Identify non-nutritional calories: propofol, IV glucose/dextrose and citrate where applicable."),
                ui.tags.li("Define an initial energy/protein strategy and planned progression rather than defaulting immediately to full target."),
            )
            ui.div("A calculated target is not automatically the correct starting dose. Phase of critical illness, refeeding risk and tolerance determine progression.",class_="warning-box")

    with ui.panel_conditional("input.mon_phase === 'early'"):
        with ui.card():
            ui.card_header("First 72 Hours & Feed Advancement")
            ui.tags.ul(
                ui.tags.li("Actual energy and protein delivered versus the current intended dose—not only the final target."),
                ui.tags.li("Route/access, interruptions and the reason for each clinically important interruption."),
                ui.tags.li("Hemodynamic status and evidence of GI intolerance during EN advancement."),
                ui.tags.li("Nausea/vomiting, abdominal distension/pain, stool output and other relevant GI findings."),
                ui.tags.li("Glucose and clinically indicated electrolytes; increase frequency when unstable or at refeeding risk."),
                ui.tags.li("Fluid balance and cumulative non-nutritional calories."),
                ui.tags.li("Advance progressively; do not compensate for early under-delivery by abruptly overfeeding."),
            )

    with ui.panel_conditional("input.mon_phase === 'en'"):
        with ui.card():
            ui.card_header("Established Enteral Nutrition")
            ui.tags.ul(
                ui.tags.li("Daily delivered volume, energy and protein relative to the current prescription."),
                ui.tags.li("Feeding interruptions, tube/access function and medication/procedure-related holds."),
                ui.tags.li("GI tolerance: vomiting, distension/pain, stool pattern and clinically relevant gastric intolerance."),
                ui.tags.li("Hydration/fluid balance and electrolyte abnormalities."),
                ui.tags.li("Glucose; triglycerides when clinically indicated or when substantial lipid/non-nutritional energy is relevant."),
                ui.tags.li("Weight trend interpreted with fluid status; muscle/function trajectory during prolonged care."),
            )
            ui.div("Do not stop EN solely for a gastric residual volume below 500 mL over 6 hours when there are no other signs of intolerance; use the Safety page for the full context.",class_="info-box")

    with ui.panel_conditional("input.mon_phase === 'pn'"):
        with ui.card():
            ui.card_header("Established Parenteral Nutrition")
            ui.tags.ul(
                ui.tags.li("Verify PN indication daily and reassess whether oral/EN can replace or reduce PN."),
                ui.tags.li("Delivered energy, amino acids/protein, dextrose and lipid; include non-nutritional calories."),
                ui.tags.li("Glucose and insulin requirements/trend."),
                ui.tags.li("Potassium, magnesium, phosphorus, sodium and clinically appropriate acid-base/renal parameters."),
                ui.tags.li("Triglycerides according to clinical context and IV lipid exposure."),
                ui.tags.li("Fluid volume and concentration in relation to the patient's fluid strategy."),
                ui.tags.li("Central/peripheral access and line complications; follow local catheter-care protocols."),
                ui.tags.li("Liver tests and longer-term micronutrient/trace-element considerations when PN is prolonged."),
            )
            ui.div("Monitoring frequency depends on stability. Newly initiated or unstable PN requires closer biochemical review than stable established therapy.",class_="warning-box")

    with ui.panel_conditional("input.mon_phase === 'refeed'"):
        with ui.card():
            ui.card_header("Refeeding / Major Electrolyte Risk")
            ui.tags.ul(
                ui.tags.li("Use the dedicated ASPEN Refeeding Syndrome pathway to classify risk and guide initiation."),
                ui.tags.li("Check potassium, magnesium and phosphorus before feeding when indicated and monitor closely during the high-risk early period."),
                ui.tags.li("For ASPEN high-risk patients, the consensus pathway includes electrolyte monitoring every 12 hours for the first 3 days, with greater frequency when clinically necessary."),
                ui.tags.li("Provide thiamin according to the refeeding pathway and count calories from IV dextrose."),
                ui.tags.li("Monitor vital signs, fluid balance, edema, glucose and clinical signs of organ dysfunction."),
                ui.tags.li("If electrolytes fall precipitously or are difficult to correct, reduce/hold advancement according to the refeeding pathway rather than continuing automatic escalation."),
            )

    with ui.panel_conditional("input.mon_phase === 'prolonged'"):
        with ui.card():
            ui.card_header("Prolonged ICU Stay / Structured Weekly Review")
            ui.tags.ul(
                ui.tags.li("Is the nutrition route still appropriate? Can oral intake or EN be increased and PN reduced?"),
                ui.tags.li("Review average delivered energy/protein over several days, not one isolated day."),
                ui.tags.li("Reassess dosing weight and requirements after major changes in edema, organ support, clinical phase or mobility."),
                ui.tags.li("Assess muscle mass/function and rehabilitation trajectory where feasible."),
                ui.tags.li("Review GI function, stool/stoma/fistula losses and hydration."),
                ui.tags.li("Review renal/KRT, liver, glucose and lipid context using the relevant pocket-guide modules."),
                ui.tags.li("Consider micronutrient/trace-element assessment when prolonged critical illness, large losses or long-term PN makes deficiency/excess plausible."),
                ui.tags.li("Check whether repeated procedures, fasting or workflow barriers are causing preventable cumulative nutrition deficits."),
            )

    with ui.panel_conditional("input.mon_phase === 'interrupt'"):
        with ui.card():
            ui.card_header("After an Interruption or Major Clinical Change")
            ui.tags.ul(
                ui.tags.li("Identify why feeding stopped: procedure, intolerance, shock, access problem, surgery or other clinical change."),
                ui.tags.li("Reassess whether the original route, rate and target remain appropriate before restarting."),
                ui.tags.li("After prolonged interruption or markedly reduced intake, reconsider refeeding risk before rapid escalation."),
                ui.tags.li("Recalculate non-nutritional calories and current delivered energy/protein; do not automatically 'catch up' missed calories."),
                ui.tags.li("After major fluid, renal, hepatic or GI changes, revisit the relevant condition-specific module."),
            )
            ui.div("Avoid catch-up overfeeding after interruptions. Restore nutrition progressively according to current physiology and risk.",class_="warning-box")

    with ui.card():
        ui.card_header("Quick Daily Nutrition Review")
        ui.tags.ol(
            ui.tags.li("Route: Is the current route still appropriate?"),
            ui.tags.li("Delivery: What was actually delivered?"),
            ui.tags.li("Tolerance & safety: Is advancement safe?"),
            ui.tags.li("Biochemistry: What needs monitoring today?"),
            ui.tags.li("Fluids & non-nutritional calories: What else is being delivered?"),
            ui.tags.li("Trajectory: Continue, advance, reduce, change route or reassess?"),
        )
        ui.p("This is a cognitive aid, not a patient chart. It does not save completion status.",class_="small-note")

    with ui.card():
        ui.card_header("Sources & Scope")
        ui.p("Monitoring principles integrate the ESPEN ICU guideline, ASPEN consensus recommendations for refeeding syndrome, and the condition-specific guidance already included in this pocket guide.")
        ui.a("Open ESPEN ICU guideline",href="https://www.espen.org/files/ESPEN-Guidelines/ESPEN_practical_and_partially_revised_guideline_Clinical_nutrition_in_the_intensive_care_unit.pdf",target="_blank",rel="noopener noreferrer")
        ui.p("Exact laboratory frequency should be individualized to clinical stability, therapy, organ function and local protocol. The guide intentionally avoids a universal daily laboratory panel.",class_="small-note")


with ui.panel_conditional("input.page === 'pediatric'"):
    ui.h2("Pediatric Critical Care Nutrition")
    ui.p("Pediatric-specific bedside guidance. Do not extrapolate adult ICU energy or protein targets to children.", class_="section-intro")
    ui.div(
        ui.div("CLINICAL QUESTION", class_="question-zone-label"),
        ui.input_select("ped_topic", "Choose a pediatric question", {
            "scope":"Population & scope", "assess":"Nutrition assessment & risk", "en":"Starting & advancing EN",
            "energy":"Energy prescription", "protein":"Protein", "formula":"Formula & enteral strategy",
            "hemo":"Hemodynamic support", "pn":"Parenteral nutrition", "monitor":"Monitoring & interruptions","calc":"Energy & protein calculator","growth":"Anthropometry & growth","en_calc":"EN delivery & adequacy","en_safe":"EN advancement & safety","quick":"Quick reference","phase_monitor":"Phase-based monitoring",
        }, selected="scope"), class_="question-zone",
    )
    with ui.panel_conditional("input.ped_topic === 'scope'"):
        with ui.card():
            ui.card_header("Population & scope")
            ui.tags.ul(
                ui.tags.li("ASPEN/SCCM 2017 applies to critically ill children >1 month and <18 years, generally expected to require >2–3 days in a PICU."),
                ui.tags.li("The ASPEN/SCCM guideline does not cover neonates; use neonatal/pediatric-specific guidance for that population."),
                ui.tags.li("ESPNIC 2020 includes selected recommendations for critically ill term neonates as well as infants and children."),
                ui.tags.li("Age, growth, baseline nutrition status and phase of illness materially change nutrition decisions."),
            )
    with ui.panel_conditional("input.ped_topic === 'assess'"):
        with ui.card():
            ui.card_header("Nutrition assessment & risk")
            ui.tags.ul(
                ui.tags.li("Obtain accurate weight and length/height when feasible and interpret age-appropriate growth indices."),
                ui.tags.li("Assess recent intake, weight/growth trajectory, underlying disease, GI function and evidence of malnutrition."),
                ui.tags.li("Identify pre-existing malnutrition or high risk of nutritional deterioration early; fluid shifts can distort weight."),
            )
    with ui.panel_conditional("input.ped_topic === 'en'"):
        with ui.card():
            ui.card_header("Starting & advancing EN")
            ui.tags.ul(
                ui.tags.li("EN is the preferred route when the gastrointestinal tract is usable."),
                ui.tags.li("ESPNIC recommends early EN within 24 hours of admission unless contraindicated; ASPEN/SCCM supports initiation within 24–48 hours in eligible PICU patients."),
                ui.tags.li("Advance stepwise with a feeding protocol that addresses eligibility, advancement and intolerance."),
                ui.tags.li("Minimize avoidable interruptions and prolonged fasting around procedures."),
            )
    with ui.panel_conditional("input.ped_topic === 'energy'"):
        with ui.card():
            ui.card_header("Energy · avoid acute-phase overfeeding")
            ui.tags.ul(
                ui.tags.li("During the acute phase, ESPNIC recommends energy intake should not exceed resting energy expenditure (REE)."),
                ui.tags.li("If indirect calorimetry is unavailable, pediatric guidance supports the Schofield equation; ASPEN/SCCM also accepts FAO/WHO/UNU equations without added stress factors."),
                ui.tags.li("Do not use adult predictive equations, Harris–Benedict, or healthy-child RDA energy values as the critical-illness prescription."),
                ui.tags.li("After the acute phase, account for recovery, activity, rehabilitation and growth."),
            )
            ui.div("Indirect calorimetry appears here because it is part of the pediatric guideline; this does not reintroduce the deferred dedicated IC interpretation module.", class_="info-box")
    with ui.panel_conditional("input.ped_topic === 'protein'"):
        with ui.card():
            ui.card_header("Protein · preserve guideline nuance")
            ui.tags.ul(
                ui.tags.li("ASPEN/SCCM recommends a minimum protein intake of 1.5 g/kg/day in critically ill children and cautions against using healthy-child RDA values to prescribe protein."),
                ui.tags.li("ESPNIC states that ≥1.5 g/kg/day enteral protein can be considered to avoid negative protein balance."),
                ui.tags.li("ESPNIC also found insufficient evidence that additional protein/amino-acid intake during the acute phase improves clinical outcomes."),
                ui.tags.li("Do not interpret 1.5 g/kg/day as a mandate to aggressively exceed that dose in every acutely critically ill child."),
            )
    with ui.panel_conditional("input.ped_topic === 'formula'"):
        with ui.card():
            ui.card_header("Formula & enteral strategy")
            ui.tags.ul(
                ui.tags.li("Use polymeric feeds as first choice for most critically ill children unless contraindicated."),
                ui.tags.li("Protein- and energy-dense formulations may help when fluid restriction limits volume."),
                ui.tags.li("Peptide-based feeds may be considered when polymeric feeds are poorly tolerated or contraindicated."),
            )
    with ui.panel_conditional("input.ped_topic === 'hemo'"):
        with ui.card():
            ui.card_header("Hemodynamic support")
            ui.tags.ul(
                ui.tags.li("ESPNIC supports early EN in children stable on pharmaceutical hemodynamic support and in stable children on extracorporeal life support."),
                ui.tags.li("Vasoactive medication alone is not an automatic reason to withhold all EN."),
                ui.tags.li("Do not advance feeding through uncontrolled shock or suspected intestinal ischemia."),
            )
    with ui.panel_conditional("input.ped_topic === 'pn'"):
        with ui.card():
            ui.card_header("Parenteral nutrition")
            ui.tags.ul(
                ui.tags.li("ASPEN/SCCM does not recommend initiating PN within the first 24 hours of PICU admission."),
                ui.tags.li("When EN is tolerated, advance enterally rather than routinely adding early supplemental PN."),
                ui.tags.li("With normal baseline nutrition status and low risk of deterioration, supplemental PN can be delayed until about 1 week after PICU admission."),
                ui.tags.li("If severely malnourished or at high risk of nutritional deterioration and unable to advance beyond low-volume EN, PN during the first week may be considered individually."),
                ui.tags.li("ESPNIC similarly states that withholding PN for up to one week can be considered while providing micronutrients."),
            )
    with ui.panel_conditional("input.ped_topic === 'monitor'"):
        with ui.card():
            ui.card_header("Monitoring & interruptions")
            ui.tags.ul(
                ui.tags.li("Track actual energy and protein delivered rather than prescription alone."),
                ui.tags.li("Review avoidable feeding interruptions and progress of EN advancement."),
                ui.tags.li("Monitor glucose, fluid balance and clinically relevant electrolytes according to illness severity and therapy."),
                ui.tags.li("Follow growth/weight trajectory with awareness of fluid shifts and reassess nutrition risk during prolonged admission."),
            )
    with ui.panel_conditional("input.ped_topic === 'calc'"):
        with ui.card():
            ui.card_header("Pediatric Energy & Protein Calculator")
            ui.p("For critically ill children >1 month to <18 years. Uses Schofield weight-only equations as a fallback estimate when measured REE is unavailable. Do not add a stress factor during the acute phase.")
            ui.input_numeric("ped_age","Age (years)",value=5,min=0.09,max=17.99,step=0.1)
            ui.input_radio_buttons("ped_sex","Sex used by Schofield equation",{"male":"Male","female":"Female"},selected="male",inline=True)
            ui.input_numeric("ped_weight","Weight (kg)",value=20,min=0.5,max=250,step=0.1)
            @render.ui
            def ped_calc_result():
                if missing_inputs(input.ped_age(), input.ped_weight(), input.ped_sex()):
                    return enter_prompt("age, weight, and sex")
                age=float(input.ped_age()); w=float(input.ped_weight()); sex=input.ped_sex()
                if age < (1/12) or age >= 18 or w <= 0:
                    return ui.div("This calculator is restricted to children >1 month and <18 years with a valid weight.",class_="warning-box")
                if sex == "male":
                    ree=(59.512*w-30.4) if age < 3 else ((22.706*w+504.3) if age < 10 else (17.686*w+658.2))
                else:
                    ree=(58.317*w-31.1) if age < 3 else ((20.315*w+485.9) if age < 10 else (13.384*w+692.6))
                protein=1.5*w
                return ui.div(ui.h4(f"Estimated REE: {ree:,.0f} kcal/day"),ui.p(f"Reference minimum protein at 1.5 g/kg/day: {protein:.1f} g/day"),ui.p("Protein reflects ASPEN/SCCM pediatric guidance; interpret with the nuance in the Protein section. Energy and protein remain separate prescription decisions.",class_="small-note"),class_="result-card")
            ui.div("Calculated REE is an estimate, not an automatic feeding target. During acute critical illness, avoid energy intake exceeding REE; reassess after the acute phase for recovery, activity and growth.",class_="warning-box")

    with ui.panel_conditional("input.ped_topic === 'growth'"):
        with ui.card():
            ui.card_header("Anthropometry & Growth")
            ui.tags.ul(
                ui.tags.li("Use accurate weight and recumbent length/standing height where feasible and age- and sex-appropriate pediatric growth references."),
                ui.tags.li("Do not interpret pediatric BMI using adult BMI cutoffs; use BMI-for-age where appropriate."),
                ui.tags.li("Weight-for-age alone cannot distinguish stunting from wasting and should not be the sole nutrition-status measure."),
                ui.tags.li("Consider weight-for-length/height or BMI-for-age, length/height-for-age and growth trajectory according to age and available standards."),
                ui.tags.li("MUAC can add useful information when appropriate reference standards and technique are available."),
                ui.tags.li("Edema, resuscitation and fluid accumulation can make serial weight misleading in critical illness."),
            )
            ui.div("This release does not calculate pediatric z-scores because correct interpretation requires sex-, age- and reference-specific LMS data. Do not approximate pediatric growth status with adult thresholds.",class_="warning-box")

    with ui.panel_conditional("input.ped_topic === 'en_calc'"):
        with ui.card():
            ui.card_header("Pediatric EN Delivery & Adequacy")
            ui.p("Transient bedside calculation for children >1 month to <18 years. Enter the feed composition from the verified product label; no product values are assumed or stored.")
            ui.input_numeric("ped_en_weight","Weight (kg)",value=20,min=0.5,max=250,step=0.1)
            ui.input_numeric("ped_en_rate","EN rate (mL/hour)",value=20,min=0,max=500,step=1)
            ui.input_numeric("ped_en_hours","Hours delivered per day",value=24,min=0,max=24,step=0.5)
            ui.input_numeric("ped_en_kcal100","Feed energy (kcal/100 mL)",value=100,min=1,max=500,step=1)
            ui.input_numeric("ped_en_prot100","Feed protein (g/100 mL)",value=3,min=0,max=30,step=0.1)
            ui.input_numeric("ped_en_energy_goal","Current energy goal (kcal/day)",value=1000,min=1,max=10000,step=10)
            ui.input_numeric("ped_en_protein_goal","Current protein goal (g/day)",value=30,min=0.1,max=500,step=0.5)
            @render.ui
            def ped_en_result():
                values=(input.ped_en_weight(),input.ped_en_rate(),input.ped_en_hours(),input.ped_en_kcal100(),input.ped_en_prot100(),input.ped_en_energy_goal(),input.ped_en_protein_goal())
                if missing_inputs(*values):
                    return enter_prompt("weight, EN delivery, feed composition, and current goals")
                w=float(input.ped_en_weight()); rate=float(input.ped_en_rate()); hrs=float(input.ped_en_hours())
                kcal100=float(input.ped_en_kcal100()); prot100=float(input.ped_en_prot100())
                eg=float(input.ped_en_energy_goal()); pg=float(input.ped_en_protein_goal())
                if w<=0 or hrs<0 or hrs>24 or rate<0 or kcal100<=0 or eg<=0 or pg<=0:
                    return ui.div("Check weight, rate, delivery hours and goal values. Hours delivered must be 0–24.",class_="warning-box")
                vol=rate*hrs; kcal=vol*kcal100/100; protein=vol*prot100/100
                return ui.div(
                    ui.h4(f"Delivered volume: {vol:,.0f} mL/day"),
                    ui.p(f"Fluid from EN: {vol/w:.1f} mL/kg/day"),
                    ui.p(f"Energy delivered: {kcal:,.0f} kcal/day ({100*kcal/eg:.0f}% of current goal)"),
                    ui.p(f"Protein delivered: {protein:.1f} g/day ({protein/w:.2f} g/kg/day; {100*protein/pg:.0f}% of current goal)"),
                    ui.p("EN fluid is only one component of total fluid intake. Include medications, IV fluids, flushes, PN and other sources when assessing fluid balance.",class_="small-note"),
                    class_="result-card",
                )
            ui.div("Adequacy percentages describe delivery versus the goal you entered; they do not validate that the goal itself is appropriate. In the acute phase, pediatric energy intake should not exceed REE.",class_="warning-box")

    with ui.panel_conditional("input.ped_topic === 'en_safe'"):
        with ui.card():
            ui.card_header("Pediatric EN Advancement & Safety")
            ui.tags.ol(
                ui.tags.li("Confirm EN eligibility and clinical stability; exclude a clear contraindication."),
                ui.tags.li("Commence early EN—ESPNIC recommends within 24 h unless contraindicated; ASPEN/SCCM supports 24–48 h in eligible PICU patients."),
                ui.tags.li("Use a local/institutional pediatric feeding protocol to increase EN stepwise toward the current goal."),
                ui.tags.li("At each step, review hemodynamic status, abdominal findings, vomiting and other clinically relevant intolerance rather than advancing automatically."),
                ui.tags.li("Minimize avoidable interruptions and prolonged fasting around procedures; record the practical reason for under-delivery when reviewing adequacy."),
                ui.tags.li("In fluid restriction, consider verified energy/protein-dense pediatric formulations when appropriate rather than simply increasing volume."),
            )
            ui.div("No universal mL/kg/hour advancement schedule is embedded: ESPNIC and ASPEN/SCCM recommend protocolized stepwise advancement, and the optimal rate varies with age, diagnosis, route, clinical stability and local practice.",class_="info-box")
        with ui.card():
            ui.card_header("Hemodynamic Support")
            ui.tags.ul(
                ui.tags.li("Stable children receiving pharmaceutical hemodynamic support can receive early EN according to ESPNIC."),
                ui.tags.li("Vasoactive medication is not, by itself, an automatic contraindication to EN."),
                ui.tags.li("Do not advance feeding through uncontrolled shock, inadequate systemic perfusion or concern for intestinal ischemia."),
            )
        with ui.card():
            ui.card_header("PICU Delivery Check")
            ui.tags.ul(
                ui.tags.li("What percentage of the current energy and protein goals was actually delivered?"),
                ui.tags.li("Were deficits caused by intolerance, procedures/fasting, access problems or prescription/volume limitations?"),
                ui.tags.li("Is the current goal appropriate for the illness phase, or are we chasing a target that risks overfeeding?"),
                ui.tags.li("Does fluid restriction require a more concentrated verified pediatric formula?"),
                ui.tags.li("Has the child transitioned from acute illness toward recovery, rehabilitation and growth needs?"),
            )

    with ui.panel_conditional("input.ped_topic === 'quick'"):
        with ui.card():
            ui.card_header("Pediatric Critical Care · Quick Reference")
            with ui.layout_columns(col_widths=(6,6)):
                with ui.card():
                    ui.card_header("Route & timing")
                    ui.p("Prefer EN when the GI tract is usable. ESPNIC: commence early EN within 24 h unless contraindicated. ASPEN/SCCM: early EN within 24–48 h in eligible PICU patients.")
                with ui.card():
                    ui.card_header("Energy")
                    ui.p("Acute phase: avoid energy intake exceeding REE. If measured REE is unavailable, use a pediatric equation such as Schofield without adding a stress factor.")
                with ui.card():
                    ui.card_header("Protein")
                    ui.p("ASPEN/SCCM minimum reference: 1.5 g/kg/day. Interpret alongside ESPNIC's evidence caveat; do not use protein targets to justify energy overfeeding.")
                with ui.card():
                    ui.card_header("PN")
                    ui.p("Do not routinely initiate PN in the first 24 h. In normally nourished, lower-risk children, supplemental PN may be delayed to about 1 week; individualize earlier PN for severe malnutrition/high deterioration risk when EN cannot advance.")
                with ui.card():
                    ui.card_header("Hemodynamics")
                    ui.p("Vasoactive medication alone is not an automatic EN contraindication in a stable child. Do not advance feeding during uncontrolled shock or suspected intestinal ischemia.")
                with ui.card():
                    ui.card_header("Growth & recovery")
                    ui.p("Use age- and sex-appropriate growth references. After the acute phase, reassess energy for recovery, activity, rehabilitation, catch-up needs and growth.")
            ui.div("Population reminder: the ASPEN/SCCM pediatric critical-care guideline covers children >1 month and <18 years and excludes neonates. Do not use this quick reference as a neonatal prescription.",class_="warning-box")

    with ui.panel_conditional("input.ped_topic === 'phase_monitor'"):
        ui.div(
            ui.input_select("ped_mon_phase","Current phase",{
                "acute":"Acute / early PICU",
                "stable":"Stable / advancing nutrition",
                "recovery":"Recovery, rehabilitation & growth",
                "interrupt":"After interruption or clinical deterioration",
            },selected="acute"),
            class_="question-zone",
        )
        with ui.panel_conditional("input.ped_mon_phase === 'acute'"):
            with ui.card():
                ui.card_header("Acute / Early PICU")
                ui.tags.ul(
                    ui.tags.li("Confirm current hemodynamic stability and EN eligibility before initiation or advancement."),
                    ui.tags.li("Assess baseline nutrition/growth risk and recent intake; identify severe malnutrition or risk of deterioration."),
                    ui.tags.li("Start early EN when eligible and advance stepwise according to a pediatric feeding protocol."),
                    ui.tags.li("Review actual energy/protein delivery and avoid acute-phase energy intake above REE."),
                    ui.tags.li("Monitor glucose, fluid balance and clinically relevant electrolytes according to illness severity and therapy."),
                    ui.tags.li("If prolonged poor intake or malnutrition raises refeeding concern, apply appropriate refeeding safeguards rather than rapid escalation."),
                )
        with ui.panel_conditional("input.ped_mon_phase === 'stable'"):
            with ui.card():
                ui.card_header("Stable / Advancing Nutrition")
                ui.tags.ul(
                    ui.tags.li("Compare actual delivered energy and protein with the current phase-appropriate goals."),
                    ui.tags.li("Review interruptions, fasting, access issues and GI tolerance before increasing the prescription."),
                    ui.tags.li("Reassess whether fluid restriction requires a verified energy/protein-dense pediatric formulation."),
                    ui.tags.li("Review weight with fluid status and follow age-appropriate growth/anthropometric trajectory."),
                    ui.tags.li("Reassess the need for PN as EN advances; avoid maintaining supplemental PN by inertia."),
                )
        with ui.panel_conditional("input.ped_mon_phase === 'recovery'"):
            with ui.card():
                ui.card_header("Recovery, Rehabilitation & Growth")
                ui.tags.ul(
                    ui.tags.li("Do not continue acute-phase energy restriction automatically once the child is recovering."),
                    ui.tags.li("Reassess energy needs for activity, rehabilitation, catch-up needs and normal growth."),
                    ui.tags.li("Continue adequate protein while evaluating total energy balance and oral/enteral transition."),
                    ui.tags.li("Review weight, length/height where appropriate, BMI-for-age or weight-for-length/height, and growth trajectory using suitable references."),
                    ui.tags.li("Plan transition toward oral intake when safe and feasible; reduce artificial nutrition as adequate oral intake becomes established."),
                )
        with ui.panel_conditional("input.ped_mon_phase === 'interrupt'"):
            with ui.card():
                ui.card_header("After Interruption or Clinical Deterioration")
                ui.tags.ul(
                    ui.tags.li("Identify why nutrition stopped: procedure, intolerance, access problem, hemodynamic deterioration or other cause."),
                    ui.tags.li("Reassess EN eligibility and current goals before restarting; do not automatically resume the previous rate after major deterioration."),
                    ui.tags.li("After prolonged interruption or marked undernutrition, reconsider electrolyte/refeeding risk before rapid advancement."),
                    ui.tags.li("Recalculate actual delivery and avoid aggressive catch-up feeding that could produce overfeeding."),
                )
                ui.div("A change in clinical phase should trigger reassessment of the nutrition strategy, not merely continuation of the previous prescription.",class_="warning-box")
        with ui.card():
            ui.card_header("Daily Pediatric Nutrition Review")
            ui.tags.ol(
                ui.tags.li("Phase: acute, stable/advancing, or recovery?"),
                ui.tags.li("Route: is oral/EN/PN strategy still appropriate?"),
                ui.tags.li("Delivery: what energy, protein and fluid were actually delivered?"),
                ui.tags.li("Safety/tolerance: is advancement appropriate today?"),
                ui.tags.li("Growth/trajectory: what has changed beyond today's numbers?"),
            )
            ui.p("This checklist is a bedside cognitive aid. Responses are transient and are not stored.",class_="small-note")

    ui.div(
        ui.div("EVIDENCE & SOURCES", class_="evidence-zone-label"),
        ui.div(ui.h4("ASPEN/SCCM pediatric guideline"), ui.p("Mehta NM, Skillman HE, Irving SY, et al. JPEN. 2017;41(5):706–742."), ui.a("Open PubMed record", href="https://pubmed.ncbi.nlm.nih.gov/28686844/", target="_blank", rel="noopener noreferrer"), class_="evidence-card"),
        ui.div(ui.h4("ESPNIC position statement"), ui.p("Tume LN, Valla FV, Joosten K, et al. Intensive Care Medicine. 2020;46:411–425."), ui.a("Open full text", href="https://pmc.ncbi.nlm.nih.gov/articles/PMC7067708/", target="_blank", rel="noopener noreferrer"), class_="evidence-card"),
        class_="evidence-zone",
    )


with ui.panel_conditional("input.page === 'anthro'"):
    ui.h2("Anthropometry")
    ui.p("Transient bedside calculations only. Enter the measurements used for this calculation; values are not stored as a patient record.", class_="section-intro")
    with ui.card(class_="anthropredictor-card"):
        ui.card_header("AnthroPredictor — External Anthropometric Estimation")
        ui.p("Open AnthroPredictor in a separate tab for anthropometric prediction. Review the model’s intended population and limitations before applying estimates clinically.")
        ui.a("Open AnthroPredictor ↗",href="https://KomlaRD-anthro-predictor.share.connect.posit.cloud",target="_blank",rel="noopener noreferrer",class_="anthropredictor-link",aria_label="Open AnthroPredictor in a new tab")

    with ui.card():
        ui.card_header("BMI & Weight Change")
        with ui.layout_columns(col_widths=(4,4,4)):
            ui.input_numeric("anth_weight","Current weight (kg)",70,min=0.1,step=0.1)
            ui.input_numeric("anth_height","Height (cm)",170,min=50,max=250,step=0.1)
            ui.input_numeric("usual_weight","Usual weight (kg)",80,min=0.1,step=0.1)
        @render.ui
        def anthro_results():
            if missing_inputs(input.anth_weight(), input.anth_height(), input.usual_weight()):
                return enter_prompt("current weight, height, and usual weight")
            b,e=safe_result(lambda:bmi(input.anth_weight(),input.anth_height()))
            usual=float(input.usual_weight()); current=float(input.anth_weight())
            if usual <= 0:
                return ui.div("Usual weight must be greater than zero. Check the entered usual weight.",class_="error-box")
            change_pct=(current-usual)/usual*100
            signed_change=f"{change_pct:+.1f}"
            note="Negative = weight loss; positive = weight gain."
            if e:return ui.div(e,class_="error-box")
            return ui.div(result_card("BMI",num(b.value,1),b.unit,b.method),result_card("Weight change",signed_change,"%",note),class_="result-grid")

    with ui.card():
        ui.card_header("Dosing-Weight Concepts")
        ui.p("Actual, ideal and adjusted body weight are not interchangeable. Select a weight descriptor because the specific guideline or equation calls for it—not simply because a calculator makes it available.",class_="warning-box")
        with ui.layout_columns(col_widths=(4,4,4,4)):
            ui.input_select("anth_sex","Sex for Devine equation",{"male":"Male","female":"Female"})
            ui.input_numeric("anth_ibw_height","Height for Devine (cm)",170,min=50,max=250,step=0.1)
            ui.input_numeric("anth_actual","Actual weight (kg)",90,min=0.1,step=0.1)
            ui.input_numeric("anth_factor","Adjusted-weight factor",0.4,min=0,max=1,step=0.05)
        @render.ui
        def anthro_weight_concepts():
            def calc():
                ibw=ideal_body_weight_devine(input.anth_ibw_height(),input.anth_sex())
                adj=adjusted_body_weight(input.anth_actual(),ibw.value,input.anth_factor())
                return ibw,adj
            r,e=safe_result(calc)
            if e:return ui.div(e,class_="error-box")
            ibw,adj=r
            return ui.div(result_card("Devine IBW",num(ibw.value,1),ibw.unit,"Equation-derived reference weight"),result_card("Adjusted body weight",num(adj.value,1),adj.unit,f"User-selected factor {input.anth_factor():.2f}; use only when the applicable method specifies it"),class_="result-grid")

with ui.panel_conditional("input.page === 'requirements'"):
    ui.h2("Energy & Protein")
    ui.p("Transient calculation only. Select the dosing weight required by the applicable guideline or method.", class_="section-intro")
    ui.input_numeric("req_weight", "Dosing weight (kg)", 70, min=0.1, step=0.1)
    ui.p("The dose and dosing weight remain clinician-selected. These calculators perform the arithmetic only.", class_="section-intro")
    with ui.card():
        ui.card_header("Weight-Based Energy")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("energy_min", "Minimum (kcal/kg/day)", 20, min=0.1, step=1)
            ui.input_numeric("energy_max", "Maximum (kcal/kg/day)", 25, min=0.1, step=1)
        @render.ui
        def energy_range_result():
            result, err = safe_result(lambda: weight_based_range(input.req_weight(), input.energy_min(), input.energy_max(), "kcal/kg/day", "kcal/day"))
            if err:
                return ui.div(err, class_="error-box")
            lo, hi = result
            return ui.div(
                result_card("Lower estimate", num(lo.value, 0), lo.unit, lo.method),
                result_card("Upper estimate", num(hi.value, 0), hi.unit, hi.method),
                class_="result-grid",
            )

    with ui.card():
        ui.card_header("Weight-Based Protein")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("protein_min", "Minimum (g/kg/day)", 1.2, min=0.1, step=0.1)
            ui.input_numeric("protein_max", "Maximum (g/kg/day)", 1.3, min=0.1, step=0.1)
        @render.ui
        def protein_range_result():
            result, err = safe_result(lambda: weight_based_range(input.req_weight(), input.protein_min(), input.protein_max(), "g/kg/day", "g/day"))
            if err:
                return ui.div(err, class_="error-box")
            lo, hi = result
            return ui.div(
                result_card("Lower estimate", num(lo.value, 1), lo.unit, lo.method),
                result_card("Upper estimate", num(hi.value, 1), hi.unit, hi.method),
                class_="result-grid",
            )

    with ui.card():
        ui.card_header("Weir Energy Expenditure")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("vo2", "VO2 (mL/min)", 250, min=0.1, step=1)
            ui.input_numeric("vco2", "VCO2 (mL/min)", 200, min=0.1, step=1)
        @render.ui
        def weir_result():
            r, err = safe_result(lambda: weir_energy(input.vo2(), input.vco2()))
            if err:
                return ui.div(err, class_="error-box")
            return result_card("Energy expenditure", num(r.value, 0), r.unit, "Weir equation; VO2 and VCO2 entered in mL/min")


with ui.panel_conditional("input.page === 'support'"):
    ui.h2("Nutrition Support")
    with ui.card():
        ui.card_header("Enteral Feeding Rate")
        with ui.layout_columns(col_widths=(4, 4, 4)):
            ui.input_numeric("en_energy", "Energy target (kcal/day)", 1800, min=1, step=50)
            ui.input_numeric("en_density", "Formula density (kcal/mL)", 1.5, min=0.1, step=0.1)
            ui.input_numeric("en_hours", "Feeding duration (hours/day)", 24, min=0.1, max=24, step=1)
        @render.ui
        def en_rate_result():
            r, err = safe_result(lambda: en_rate(input.en_energy(), input.en_density(), input.en_hours()))
            if err:
                return ui.div(err, class_="error-box")
            volume = r.value * input.en_hours()
            return ui.div(
                result_card("Calculated rate", num(r.value, 1), r.unit, r.method),
                result_card("Calculated volume", num(volume, 0), "mL/day", "rate × feeding duration"),
                class_="result-grid",
            )

    with ui.card():
        ui.card_header("Propofol Energy")
        with ui.layout_columns(col_widths=(4, 4, 4)):
            ui.input_numeric("prop_rate", "Rate (mL/hour)", 15, min=0.1, step=0.5)
            ui.input_numeric("prop_hours", "Duration (hours)", 24, min=0.1, max=24, step=1)
            ui.input_numeric("prop_density", "Energy density (kcal/mL)", 1.1, min=0.1, step=0.1)
        @render.ui
        def propofol_result():
            r, err = safe_result(lambda: propofol_energy(input.prop_rate(), input.prop_hours(), input.prop_density()))
            if err:
                return ui.div(err, class_="error-box")
            return result_card("Non-nutrition energy", num(r.value, 0), r.unit, "Confirm the selected product's energy density")

    with ui.card():
        ui.card_header("Glucose Infusion Rate")
        with ui.layout_columns(col_widths=(6,6)):
            ui.input_numeric("glucose_day", "IV glucose/dextrose delivered (g/day)", 300, min=0.1, step=10)
            ui.input_numeric("gir_weight", "Dosing weight (kg)", 70, min=0.1, step=0.1)
        @render.ui
        def gir_result():
            r, err = safe_result(lambda: gir(input.glucose_day(), input.gir_weight()))
            if err:
                return ui.div(err, class_="error-box")
            return result_card("GIR", num(r.value, 2), r.unit, "IV glucose mg/day / (dosing weight × 1440 min)")



    # Formula-specific feeding regimen tools
    with ui.card():
        ui.card_header("Continuous EN from clinician-entered target")
        ui.input_select("feed_product","Liquid formula",LIQUID_CHOICES,selected="ABB_GLU_15_GHREF")
        with ui.layout_columns(col_widths=(4,4,4)):
            ui.input_numeric("feed_energy","Energy target (kcal/day)",1800,min=1,step=50)
            ui.input_numeric("feed_protein","Protein target (g/day)",90,min=0.1,step=1)
            ui.input_numeric("feed_hours","Planned feeding time (hours/day)",24,min=1,max=24,step=1)
        ui.p("Energy and protein targets are clinician-entered and remain separate decisions. The rate below is derived from the energy target; protein adequacy is then checked independently.",class_="small-note")
    @render.ui
    def continuous_feeding_results():
        def compute(): return continuous_feeding_from_energy(PRODUCT_DB,input.feed_product(),input.feed_energy(),input.feed_hours(),input.feed_protein())
        plan,err=safe_result(compute)
        if err:return ui.div(err,class_="error-box")
        protein_text="Unknown" if plan.protein_g_day is None else num(plan.protein_g_day,1)
        adequacy_text="Cannot assess: protein composition unavailable." if plan.protein_adequacy_percent is None else f"{plan.protein_adequacy_percent:.1f}% of the separately entered protein target."
        water_text="Unknown / not reported" if plan.water_ml_day is None else f"{num(plan.water_ml_day,0)} mL/day"
        return ui.div(
            ui.div(
                result_card("Formula volume",num(plan.volume_ml_day,0),"mL/day",f"Calculated from {num(plan.target_energy_kcal,0)} kcal/day"),
                result_card("Continuous rate",num(plan.rate_ml_hr,1),"mL/h",f"If delivered over {num(plan.hours_per_day,0)} h/day"),
                result_card("Protein delivered",protein_text,"g/day" if plan.protein_g_day is not None else "",adequacy_text),
                result_card("Formula water",water_text,"","Formula water only; not total fluid intake"),
                class_="result-grid"),
            ui.div(ui.strong("Interpretation: "),"Meeting the energy target does not mean the protein target is met. Review both before changing the prescription.",class_="warning-box"),
        )

    with ui.card():
        ui.card_header("Gastric bolus feeding")
        ui.p("For patients selected for gastric bolus feeding, divide the clinician-entered daily target into a practical number of feeds. The calculated volume per feed is not an automatic tolerance limit.",class_="small-note")
        ui.input_select("bolus_product","Liquid formula",LIQUID_CHOICES,selected="ABB_ENSURE_PLUS_GHREF")
        with ui.layout_columns(col_widths=(3,3,3,3)):
            ui.input_numeric("bolus_energy","Energy target (kcal/day)",1800,min=1,step=50)
            ui.input_numeric("bolus_protein","Protein target (g/day)",90,min=0.1,step=1)
            ui.input_numeric("bolus_feeds","Feeds per day",6,min=1,max=12,step=1)
            ui.input_select("bolus_site","Delivery site",{"GASTRIC":"Gastric","SMALL_BOWEL":"Small bowel"},selected="GASTRIC")
        ui.p("Administration time and water flush volume should be prescribed according to enteral access, tolerance, fluid requirements and local protocol; they are not inferred from formula volume.",class_="small-note")
    @render.ui
    def bolus_feeding_results():
        def compute(): return bolus_feeding_from_energy(PRODUCT_DB,input.bolus_product(),input.bolus_energy(),input.bolus_feeds(),input.bolus_protein(),input.bolus_site())
        plan,err=safe_result(compute)
        if err:return ui.div(err,class_="error-box")
        pday="Unknown" if plan.protein_g_day is None else f"{num(plan.protein_g_day,1)} g/day"
        pfeed="Unknown" if plan.protein_g_feed is None else f"{num(plan.protein_g_feed,1)} g/feed"
        water="Unknown / not reported" if plan.water_ml_day is None else f"{num(plan.water_ml_day,0)} mL/day · {num(plan.water_ml_feed,0)} mL/feed"
        adequacy="Cannot assess protein adequacy." if plan.protein_adequacy_percent is None else f"{plan.protein_adequacy_percent:.1f}% of separate protein target"
        return ui.div(
            ui.div(
                result_card("Formula volume",num(plan.volume_ml_day,0),"mL/day",f"{plan.feeds_per_day} feeds/day"),
                result_card("Volume per feed",num(plan.volume_ml_feed,0),"mL/feed","Assess individual gastric tolerance; not a universal safe-volume threshold"),
                result_card("Protein",pday,"",f"{pfeed} · {adequacy}"),
                result_card("Formula water",water,"","Does not include prescribed water flushes or other fluids"),
                class_="result-grid"),
            ui.div(ui.strong("Bolus safety: "),"Use for gastric delivery only. Review aspiration risk, GI tolerance, positioning and the enteral access. Large boluses may worsen intolerance; do not use this calculated volume as an automatic administration order.",class_="warning-box"),
        )



with ui.panel_conditional("input.page === 'products'"):
    ui.h2("Product Reference")
    ui.p("Compare Ghana-relevant Abbott nutrition products and perform transient formulation-specific calculations. Confirm the exact product/form on the pack before applying results.", class_="section-intro")
    ui.div("Manufacturer composition reference: Abbott Nutrition Adult Nutrition Product Guide. Product forms are kept separate because Glucerna formulations encountered locally may differ.", class_="info-box")
    with ui.card():
        ui.card_header("Select exact product / formulation")
        ui.input_select("prod_ref_product", "Product", PRODUCT_CHOICES, selected="ABB_ENSURE_PLUS_GHREF")
    @render.ui
    def product_reference_details():
        def compute():
            prod=PRODUCT_DB.product(input.prod_ref_product())
            return prod,PRODUCT_DB.nutrients_for(prod.product_id)
        result,err=safe_result(compute)
        if err:return ui.div(err,class_="error-box")
        prod,nutrients=result
        labels={"ENERGY":"Energy","PROTEIN":"Protein","CARBOHYDRATE":"Carbohydrate","FAT":"Fat","FIBRE":"Fibre","WATER":"Water","SODIUM":"Sodium","POTASSIUM":"Potassium","PHOSPHORUS":"Phosphorus","MAGNESIUM":"Magnesium"}
        def line(nid):
            rec=nutrients.get(nid)
            value="Unknown / not reported" if rec is None else f"{num(rec[0],1)} {rec[1]} per {rec[2]:g} {rec[3]}"
            return ui.div(ui.span(labels[nid],class_="nutrient-name"),ui.span(value,class_="nutrient-value"),class_="nutrient-row")
        use_note=("Eligible for volume-based calculations." if prod.volume_calculation_eligible else ("Powder: serving-based calculations only until a verified prepared-volume/dilution record is available." if prod.physical_form=="POWDER" else "Solid product: serving/reference calculations only; excluded from liquid volume/rate calculations."))
        return ui.div(
            ui.div(result_card("Reference basis",f"{prod.basis_quantity:g}",prod.basis_unit,prod.name),result_card("Route",prod.route.replace("_"," / ").title(),"",prod.physical_form.replace("_"," ").title()),class_="result-grid"),
            ui.div(ui.strong("Calculation policy: "),use_note,class_="info-box"),
            ui.h4("Composition"),*[line(n) for n in NUTRIENT_UNITS],
            ui.div(ui.strong("Source: "),"Abbott Nutrition Adult Nutrition Product Guide · Ghana reference catalogue.",class_="evidence-card"),
        )
    with ui.card():
        ui.card_header("Energy / protein target calculator")
        ui.p("Shows how much of the selected product provides a clinician-entered energy or protein amount. It does not determine the nutrition prescription.",class_="small-note")
        with ui.layout_columns(col_widths=(6,6)):
            ui.input_numeric("prod_target_energy","Energy amount to provide (kcal)",500,min=1,step=50)
            ui.input_numeric("prod_target_protein","Protein amount to provide (g)",30,min=0.1,step=1)
    @render.ui
    def product_target_results():
        def compute():
            prod=PRODUCT_DB.product(input.prod_ref_product())
            return prod,amount_for_nutrient(PRODUCT_DB,prod.product_id,"ENERGY",input.prod_target_energy()),amount_for_nutrient(PRODUCT_DB,prod.product_id,"PROTEIN",input.prod_target_protein())
        result,err=safe_result(compute)
        if err:return ui.div(err,class_="error-box")
        prod,e,pr=result
        note=("These are volume calculations from the exact liquid formulation selected." if prod.volume_calculation_eligible else "This product is not eligible for liquid volume/rate calculations; results are expressed only in its source serving unit.")
        return ui.div(ui.div(result_card("For entered energy",num(e[0],0),e[1],f"Provides {num(input.prod_target_energy(),0)} kcal"),result_card("For entered protein",num(pr[0],0),pr[1],f"Provides {num(input.prod_target_protein(),1)} g protein"),class_="result-grid"),ui.div(note,class_="info-box"))



with ui.panel_conditional("input.page === 'compare_products'"):
    ui.h2("Formula Comparison")
    ui.p("Compare exact liquid formulations on a common energy basis. This tool supports product comparison only; it does not select a preferred formula or determine a feeding regimen.", class_="section-intro")
    liquid_choices=LIQUID_CHOICES
    with ui.div(class_="question-zone"):
        ui.h4("Select formulas")
        with ui.layout_columns(col_widths=(4,4,4)):
            ui.input_select("cmp_p1","Formula 1",liquid_choices,selected="ABB_GLU_10_GHREF")
            ui.input_select("cmp_p2","Formula 2",liquid_choices,selected="ABB_GLU_12_GHREF")
            ui.input_select("cmp_p3","Formula 3",liquid_choices,selected="ABB_GLU_15_GHREF")
    @render.ui
    def formula_comparison_results():
        def compute(): return [compare_liquid_formula(PRODUCT_DB,x) for x in (input.cmp_p1(),input.cmp_p2(),input.cmp_p3())]
        result,err=safe_result(compute)
        if err:return ui.div(err,class_="error-box")
        def val(v,d=1): return "—" if v is None else num(v,d)
        cards=[]
        for x in result:
            cards.append(ui.div(
                ui.h4(x.name, class_="comparison-card-title"),
                ui.div(ui.span("Energy density",class_="nutrient-name"),ui.span(f"{val(x.kcal_per_ml,2)} kcal/mL",class_="nutrient-value"),class_="nutrient-row"),
                ui.div(ui.span("Protein",class_="nutrient-name"),ui.span(f"{val(x.protein_g_per_1000_kcal)} g/1000 kcal",class_="nutrient-value"),class_="nutrient-row"),
                ui.div(ui.span("Water",class_="nutrient-name"),ui.span(f"{val(x.water_ml_per_1000_kcal,0)} mL/1000 kcal" if x.water_ml_per_1000_kcal is not None else "—",class_="nutrient-value"),class_="nutrient-row"),
                ui.div(ui.span("Carbohydrate",class_="nutrient-name"),ui.span(f"{val(x.carbohydrate_g_per_1000_kcal)} g/1000 kcal",class_="nutrient-value"),class_="nutrient-row"),
                ui.div(ui.span("Sodium",class_="nutrient-name"),ui.span(f"{val(x.sodium_mg_per_1000_kcal,0)} mg/1000 kcal",class_="nutrient-value"),class_="nutrient-row"),
                ui.div(ui.span("Potassium",class_="nutrient-name"),ui.span(f"{val(x.potassium_mg_per_1000_kcal,0)} mg/1000 kcal",class_="nutrient-value"),class_="nutrient-row"),
                ui.div(ui.span("Phosphorus",class_="nutrient-name"),ui.span(f"{val(x.phosphorus_mg_per_1000_kcal,0)} mg/1000 kcal",class_="nutrient-value"),class_="nutrient-row"),
                ui.div(ui.span("Magnesium",class_="nutrient-name"),ui.span(f"{val(x.magnesium_mg_per_1000_kcal,0)} mg/1000 kcal",class_="nutrient-value"),class_="nutrient-row"),
                class_="comparison-card",
            ))
        return ui.div(*cards,class_="comparison-grid")
    ui.div(
        ui.div("EVIDENCE & SOURCE CONTEXT",class_="evidence-zone-label"),
        ui.div(ui.h4("Product composition source"),ui.p("Abbott Nutrition Adult Nutrition Product Guide. Exact formulation identities and manufacturer composition bases are retained in the product catalogue."),class_="evidence-card"),
        class_="evidence-zone",
    )


with ui.panel_conditional("input.page === 'delivery'"):
    ui.h2("Nutrition Delivery")
    ui.p("Calculate nutrients actually delivered from selected catalogue products and optional custom sources. Confirm the exact formulation and source basis before use.", class_="section-intro")

    with ui.card():
        ui.card_header("Prescription")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("del_energy_rx", "Energy prescription (kcal/day)", 1800, min=1, step=50)
            ui.input_numeric("del_protein_rx", "Protein prescription (g/day)", 95, min=0.1, step=1)
            ui.input_numeric("del_limit_weight", "Dosing weight for guideline limit checks (kg)", 70, min=0.1, step=0.1)

    with ui.card():
        ui.card_header("Source 1")
        ui.input_select("source1_product", "Product", PRODUCT_CHOICES, selected="ABB_GLU_15_GHREF")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("source1_rx", "Prescribed amount", 1200, min=0, step=50)
            ui.input_numeric("source1_delivered", "Delivered amount", 850, min=0, step=50)
        ui.p("Enter mL for liquid products and g for powder products. The product basis is shown in the result.", class_="small-note")

    with ui.card():
        ui.card_header("Source 2 — Optional")
        ui.input_checkbox("source2_enabled", "Include a second source", False)
        ui.input_select("source2_product", "Product", PRODUCT_CHOICES, selected="ABB_ENSURE_PLUS_GHREF")
        ui.input_numeric("source2_delivered", "Delivered amount", 200, min=0, step=25)

    with ui.card():
        ui.card_header("Custom product — optional")
        ui.input_checkbox("custom_enabled", "Include a custom product", False)
        ui.input_text("custom_name", "Product name", "Custom feed")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("custom_delivered", "Delivered volume (mL)", 200, min=0, step=25)
            ui.input_numeric("custom_basis", "Composition basis (mL)", 100, min=1, step=10)
        ui.p("Enter known composition per selected basis. Leave unavailable nutrients at 0 only if the true value is zero; for this prototype, optional custom nutrient fields are limited to the core macronutrients.", class_="small-note")
        with ui.layout_columns(col_widths=(6, 6, 6, 6)):
            ui.input_numeric("custom_energy", "Energy (kcal/basis)", 100, min=0, step=5)
            ui.input_numeric("custom_protein", "Protein (g/basis)", 4, min=0, step=0.5)
            ui.input_numeric("custom_carb", "Carbohydrate (g/basis)", 15, min=0, step=0.5)
            ui.input_numeric("custom_fat", "Fat (g/basis)", 3, min=0, step=0.5)

    with ui.card():
        ui.card_header("Non-nutrition energy — optional")
        ui.input_checkbox("nn_enabled", "Include non-nutrition energy", False)
        with ui.layout_columns(col_widths=(6, 6, 6, 6, 6)):
            ui.input_numeric("del_prop_volume", "Propofol volume (mL/day)", 0, min=0, step=10)
            ui.input_numeric("del_prop_density", "Propofol energy density (kcal/mL)", 1.1, min=0.1, step=0.1)
            ui.input_numeric("del_prop_lipid_density", "Propofol lipid (g/mL; confirm product)", 0.1, min=0, step=0.01)
            ui.input_numeric("del_dextrose_g", "IV dextrose delivered (g/day)", 0, min=0, step=5)
            ui.input_numeric("del_dextrose_density", "IV dextrose energy density (kcal/g)", 3.4, min=0.1, step=0.1)
        ui.p("Confirm product/formulation values before clinical use. Non-nutrition energy contributes to total energy exposure but not to protein delivery.", class_="small-note")

    @render.ui
    def delivery_results():
        def compute():
            sources = []
            p1 = PRODUCT_DB.product(input.source1_product())
            if not p1.volume_calculation_eligible:
                raise ValueError(f"{p1.name} is not eligible for liquid delivery calculations. Use Product Reference for serving-based information.")
            sources.append(NutritionSource(p1.product_id, input.source1_delivered(), p1.basis_unit, input.source1_rx()))
            if input.source2_enabled():
                p2 = PRODUCT_DB.product(input.source2_product())
                if not p2.volume_calculation_eligible:
                    raise ValueError(f"{p2.name} is not eligible for liquid delivery calculations. Use Product Reference for serving-based information.")
                sources.append(NutritionSource(p2.product_id, input.source2_delivered(), p2.basis_unit))
            groups = [calculate_delivery(PRODUCT_DB, sources, NUTRIENT_UNITS)]
            if input.custom_enabled():
                custom = CustomNutritionSource(
                    input.custom_name(), input.custom_delivered(), "mL", input.custom_basis(), "mL",
                    {"ENERGY": (input.custom_energy(), "kcal"), "PROTEIN": (input.custom_protein(), "g"),
                     "CARBOHYDRATE": (input.custom_carb(), "g"), "FAT": (input.custom_fat(), "g")}
                )
                groups.append(calculate_custom_delivery(custom, NUTRIENT_UNITS))
            return combine_nutrient_totals(groups, NUTRIENT_UNITS), p1

        result, err = safe_result(compute)
        if err:
            return ui.div(err, class_="error-box")
        totals, p1 = result
        energy = totals["ENERGY"]
        protein = totals["PROTEIN"]
        e_pct = adequacy(energy.amount or 0, input.del_energy_rx(), "kcal").value
        p_pct = adequacy(protein.amount or 0, input.del_protein_rx(), "g").value
        vol_pct = volume_delivery_percent(input.source1_delivered(), input.source1_rx()) if input.source1_rx() > 0 else None

        nutrition_energy = energy.amount or 0
        exposure_sources = [EnergySource("Nutrition products", nutrition_energy, "NUTRITION")]
        if input.nn_enabled():
            prop_kcal = propofol_energy_from_volume(input.del_prop_volume(), input.del_prop_density())
            dex_kcal = iv_dextrose_energy(input.del_dextrose_g(), input.del_dextrose_density())
            if prop_kcal > 0:
                exposure_sources.append(EnergySource("Propofol", prop_kcal, "NON_NUTRITION"))
            if dex_kcal > 0:
                exposure_sources.append(EnergySource("IV dextrose", dex_kcal, "NON_NUTRITION"))
        exposure = calculate_energy_exposure(exposure_sources)
        total_e_pct = adequacy(exposure.total_kcal, input.del_energy_rx(), "kcal").value

        # Delivery-linked guideline checks. Missing nutrient composition remains missing rather than zero.
        carb_check = None
        carb = totals["CARBOHYDRATE"]
        if carb.amount is not None and carb.completeness == "COMPLETE":
            tracked_carb_g = carb.amount + (input.del_dextrose_g() if input.nn_enabled() else 0)
            carb_check = evaluate_carbohydrate_limit(tracked_carb_g, input.del_limit_weight())
        lipid_check = None
        if input.nn_enabled():
            tracked_iv_lipid_g = input.del_prop_volume() * input.del_prop_lipid_density()
            lipid_check = evaluate_iv_lipid_limit(tracked_iv_lipid_g, input.del_limit_weight())

        def check_card(check, unavailable_text=None):
            if check is None:
                return ui.div(unavailable_text or "Insufficient data for this limit check.", class_="small-note")
            return ui.div(ui.strong(check.title + ": "), check.message, ui.span(" " + check.status.replace("_", " ").title(), class_="status-badge"), class_="info-box")

        def nutrient_line(nid, label):
            n = totals[nid]
            value = "—" if n.amount is None else (f"≥ {num(n.amount, 0)}" if n.completeness == "PARTIAL" else num(n.amount, 0))
            return ui.div(
                ui.span(label, class_="nutrient-name"),
                ui.span(f"{value} {n.unit if n.amount is not None else ''}", class_="nutrient-value"),
                ui.span(n.completeness.title(), class_=f"status-badge status-{n.completeness.lower()}"),
                class_="nutrient-row",
            )

        return ui.div(
            ui.h3("Daily delivery"),
            ui.div(
                result_card("Nutrition energy", num(exposure.nutrition_kcal, 0), "kcal/day", f"{e_pct:.1f}% of energy prescription from nutrition sources"),
                result_card("Non-nutrition energy", num(exposure.non_nutrition_kcal, 0), "kcal/day", "Tracked separately from nutrition delivery"),
                result_card("Total energy exposure", num(exposure.total_kcal, 0), "kcal/day", f"{total_e_pct:.1f}% of clinician-entered energy prescription"),
                result_card("Protein", num(protein.amount or 0, 1), "g/day", f"{p_pct:.1f}% of clinician-entered protein prescription"),
                class_="result-grid",
            ),
            ui.h4("Energy source breakdown"),
            *[ui.div(ui.span(src.name, class_="nutrient-name"), ui.span(f"{num(src.energy_kcal, 0)} kcal", class_="nutrient-value"), ui.span(src.source_type.replace("_", " ").title(), class_="status-badge"), class_="nutrient-row") for src in exposure.sources],
            ui.div(f"Source 1 volume delivery: {vol_pct:.1f}% · Basis: {p1.basis_quantity:g} {p1.basis_unit}" if vol_pct is not None else "", class_="info-box"),
            ui.h4("Macronutrients & water"),
            nutrient_line("CARBOHYDRATE", "Carbohydrate"),
            nutrient_line("FAT", "Fat"),
            nutrient_line("FIBRE", "Fibre"),
            nutrient_line("WATER", "Free water"),
            ui.h4("Electrolytes"),
            nutrient_line("SODIUM", "Sodium"),
            nutrient_line("POTASSIUM", "Potassium"),
            nutrient_line("PHOSPHORUS", "Phosphorus"),
            nutrient_line("MAGNESIUM", "Magnesium"),
            ui.h4("Guideline-linked delivery checks"),
            check_card(carb_check, "Carbohydrate limit check unavailable because carbohydrate composition is incomplete for one or more nutrition sources."),
            check_card(lipid_check, "Enable non-nutrition energy and confirm propofol lipid concentration to evaluate tracked IV lipid exposure."),
            ui.p("These checks use tracked delivery values and the clinician-selected dosing weight. They do not alter the prescription.", class_="small-note"),
            ui.p("Partial means one or more included sources did not report that nutrient; the displayed value is the known minimum, not a complete total.", class_="small-note"),
        )


with ui.panel_conditional("input.page === 'safety'"):
    ui.h2("Safety & Monitoring Reference")
    ui.p("Problem-oriented bedside reference for common nutrition-support safety issues. Findings should be interpreted with the full clinical picture; this section does not create treatment orders or patient records.", class_="section-intro")

    ui.input_select("safety_topic", "Clinical issue", {
        "en_hold":"When EN should be delayed or held",
        "grv":"Gastric residual volume & intolerance",
        "aspiration":"Aspiration risk",
        "diarrhea":"Diarrhea",
        "constipation":"Constipation",
        "electrolytes":"Electrolytes & refeeding",
        "glucose":"Glucose",
        "triglycerides":"Triglycerides & IV lipid",
        "fluid":"Fluid balance",
        "pn":"PN safety",
    }, selected="en_hold")

    with ui.panel_conditional("input.safety_topic === 'en_hold'"):
        with ui.card():
            ui.card_header("Delay or Hold EN · ESPEN 2023")
            ui.tags.ul(
                ui.tags.li("Delay EN in uncontrolled shock while hemodynamic and tissue-perfusion goals remain unmet."),
                ui.tags.li("Delay EN with uncontrolled life-threatening hypoxemia, hypercapnia or acidosis."),
                ui.tags.li("Delay EN with active upper GI bleeding; feeding may restart after bleeding has stopped and there are no signs of rebleeding."),
                ui.tags.li("Delay EN with overt bowel ischemia, abdominal compartment syndrome, or a high-output intestinal fistula when reliable feeding access distal to the fistula is not achievable."),
            )
            ui.div("Controlled shock is different from uncontrolled shock. ESPEN allows low-dose EN once shock is controlled with fluids and vasopressors/inotropes, while watching for bowel ischemia.",class_="info-box")

    with ui.panel_conditional("input.safety_topic === 'grv'"):
        with ui.card():
            ui.card_header("GRV & Gastric Feeding Intolerance")
            ui.tags.ul(
                ui.tags.li("Do not stop EN for a gastric residual volume below 500 mL over 6 hours in the absence of other signs of feeding intolerance."),
                ui.tags.li("A GRV above 500 mL/6 h should prompt reassessment rather than automatic permanent cessation of EN."),
                ui.tags.li("Consider prokinetic therapy for gastric feeding intolerance; ESPEN identifies IV erythromycin as first-line, with IV metoclopramide or combination therapy as alternatives."),
                ui.tags.li("Consider postpyloric feeding when intolerance persists despite an appropriate prokinetic strategy."),
            )
            ui.div("GRV is one part of tolerance assessment. Abdominal examination, vomiting/regurgitation, distension, bowel ischemia risk and overall clinical trajectory matter.",class_="warning-box")

    with ui.panel_conditional("input.safety_topic === 'aspiration'"):
        with ui.card():
            ui.card_header("Aspiration Risk")
            ui.tags.ul(
                ui.tags.li("Identify modifiable risks such as positioning, sedation, vomiting/regurgitation and impaired gastric emptying."),
                ui.tags.li("Use postpyloric feeding in patients considered at high aspiration risk according to ESPEN."),
                ui.tags.li("Do not equate aspiration risk with a universal contraindication to EN; adjust route and risk-reduction strategies to the clinical context."),
            )

    with ui.panel_conditional("input.safety_topic === 'diarrhea'"):
        with ui.card():
            ui.card_header("Diarrhea During EN")
            ui.tags.ul(
                ui.tags.li("Do not assume the enteral formula is the cause. Review medications—especially antibiotics, laxatives, sorbitol-containing preparations—and infection risk."),
                ui.tags.li("Review feeding rate, formula composition/osmolality where relevant, recent changes, malabsorption, bowel disease and fecal impaction with overflow."),
                ui.tags.li("Assess hydration and losses and monitor potassium, magnesium and other electrolytes when losses are substantial."),
                ui.tags.li("Avoid reflexively stopping EN solely because diarrhea is present when the gastrointestinal tract remains usable."),
            )

    with ui.panel_conditional("input.safety_topic === 'constipation'"):
        with ui.card():
            ui.card_header("Constipation / Reduced Bowel Activity")
            ui.tags.ul(
                ui.tags.li("Review opioids, sedatives, anticholinergic drugs, immobility, hydration, electrolyte abnormalities and the bowel regimen."),
                ui.tags.li("Distinguish uncomplicated constipation from ileus, obstruction or abdominal compartment pathology."),
                ui.tags.li("Absence of bowel sounds alone should not automatically prevent EN when there is no suspected obstruction or ischemia; assess the overall gastrointestinal picture."),
            )

    with ui.panel_conditional("input.safety_topic === 'electrolytes'"):
        with ui.card():
            ui.card_header("Electrolytes & Refeeding")
            ui.tags.ul(
                ui.tags.li("Monitor phosphorus, potassium and magnesium closely when refeeding risk is present."),
                ui.tags.li("A falling electrolyte concentration after calorie introduction may require slowing nutrition progression while abnormalities are corrected."),
                ui.tags.li("Severe or rapidly worsening abnormalities require urgent clinical reassessment; consider renal function, acid-base status, medications and ongoing losses."),
            )
            ui.a("Use the dedicated ASPEN Refeeding Syndrome pathway",href="#",onclick="document.querySelector('input[value=refeeding]')?.click(); return false;")

    with ui.panel_conditional("input.safety_topic === 'glucose'"):
        with ui.card():
            ui.card_header("Glucose")
            ui.tags.ul(
                ui.tags.li("Monitor glucose during EN and PN, especially during initiation, progression, steroid therapy, sepsis and insulin treatment."),
                ui.tags.li("Hyperglycemia should prompt review of total carbohydrate/dextrose exposure, non-nutritional glucose, overfeeding, medications and insulin strategy—not automatic cessation of nutrition."),
                ui.tags.li("Hypoglycemia during continuous nutrition may occur when feeding is unexpectedly interrupted while insulin continues; coordinate nutrition interruptions with glucose-lowering therapy."),
            )

    with ui.panel_conditional("input.safety_topic === 'triglycerides'"):
        with ui.card():
            ui.card_header("Triglycerides & IV Lipid")
            ui.tags.ul(
                ui.tags.li("Monitor triglycerides when IV lipid emulsions are used, particularly with prolonged PN or impaired lipid clearance."),
                ui.tags.li("Include lipid calories from propofol when calculating total energy exposure."),
                ui.tags.li("Marked hypertriglyceridemia should prompt review of lipid dose/rate, propofol exposure, overfeeding, sepsis, medications and metabolic disease."),
            )
            ui.p("Use institutional and product-specific thresholds for modifying IV lipid; this pocket guide intentionally does not invent a universal triglyceride cutoff.",class_="small-note")

    with ui.panel_conditional("input.safety_topic === 'fluid'"):
        with ui.card():
            ui.card_header("Fluid Balance")
            ui.tags.ul(
                ui.tags.li("Include formula/PN water, medication carriers, flushes, IV fluids and other sources when reviewing total intake."),
                ui.tags.li("Interpret body weight cautiously during major fluid shifts; edema can mask loss of lean and fat mass."),
                ui.tags.li("Concentrated nutrition may be useful when fluid restriction is necessary, but electrolyte and renal considerations remain important."),
                ui.tags.li("High-output gastrointestinal losses require active replacement planning and monitoring rather than simple restriction of intake."),
            )

    with ui.panel_conditional("input.safety_topic === 'pn'"):
        with ui.card():
            ui.card_header("PN Safety")
            ui.tags.ul(
                ui.tags.li("Verify indication, route/access, formulation, infusion rate and compatibility before administration."),
                ui.tags.li("Monitor glucose, electrolytes, fluid balance, triglycerides, liver tests and clinical signs of catheter-related complications according to clinical context."),
                ui.tags.li("Account for refeeding risk before aggressive PN initiation in severely malnourished or starved patients."),
                ui.tags.li("Avoid abrupt assumptions that abnormal liver tests are caused solely by PN; review sepsis, medications, underlying hepatobiliary disease, overfeeding and duration of therapy."),
            )

    with ui.card():
        ui.card_header("Safety Sources")
        ui.p("Primary ICU reference: ESPEN practical and partially revised guideline: Clinical nutrition in the intensive care unit. Clinical Nutrition. 2023;42:1671–1689.")
        ui.p("Refeeding-specific decisions: ASPEN Consensus Recommendations for Refeeding Syndrome. Nutrition in Clinical Practice. 2020;35:178–195, including the published erratum.")
        ui.p("Use local medication, electrolyte-replacement, glycemic-control, vascular-access and PN-compounding policies alongside these nutrition guidelines.",class_="small-note")

with ui.panel_conditional("input.page === 'renal'"):
    ui.h2("Renal Dysfunction & Kidney Replacement Therapy")
    ui.p("Adult bedside reference based primarily on the 2024 ESPEN practical kidney guideline. Use transient values only; integrate nutrition with illness severity, fluid status, KRT prescription, biochemical trends and the overall clinical plan.", class_="section-intro")

    ui.input_select("renal_topic","Bedside question",{
        "protein":"Protein by clinical/KRT situation",
        "weight":"Which weight should I use?",
        "energy":"Energy & route",
        "losses":"CKRT/PIKRT losses",
        "electrolytes":"Electrolytes, fluid & acid-base",
        "monitoring":"What should I monitor?",
    },selected="protein")

    with ui.panel_conditional("input.renal_topic === 'protein'"):
        with ui.card():
            ui.card_header("Critically Ill Adults · ESPEN 2024")
            ui.tags.ul(
                ui.tags.li(ui.strong("AKI / AKI on CKD / CKD with acute critical illness, not on KRT: "), "start around 1.0 g/kg/day and progressively increase up to 1.3 g/kg/day if tolerated."),
                ui.tags.li(ui.strong("Conventional intermittent KRT: "), "1.3–1.5 g/kg/day."),
                ui.tags.li(ui.strong("CKRT or PIKRT: "), "1.5–1.7 g/kg/day."),
            )
            ui.div("Do not reduce protein prescription simply to avoid or delay initiation of KRT in critically ill patients with AKI, AKI on CKD, or CKD with kidney failure.",class_="warning-box")
            ui.p("These ranges describe guideline protein prescription, not an automatic target. Progression, tolerance, catabolic state, nitrogen losses and the KRT prescription matter.",class_="small-note")

    with ui.panel_conditional("input.renal_topic === 'weight'"):
        with ui.card():
            ui.card_header("Reference Body Weight")
            ui.p("ESPEN 2024 states that, if available, pre-hospitalization/usual body weight may be preferred over ideal body weight for protein prescription. Actual body weight should not be used for protein prescription in this critically ill kidney-disease context.",class_="warning-box")
            ui.p("Fluid overload can substantially distort measured body weight. Document mentally which weight descriptor the selected recommendation requires before calculating g/day.",class_="small-note")

    with ui.panel_conditional("input.renal_topic === 'energy'"):
        with ui.card():
            ui.card_header("Energy & Nutrition Route")
            ui.tags.ul(
                ui.tags.li("AKI itself does not justify deliberate overfeeding. Follow critical-care energy principles when the patient is critically ill."),
                ui.tags.li("Prefer indirect calorimetry when feasible in mechanically ventilated critically ill adults."),
                ui.tags.li("Avoid overfeeding in an attempt to force positive nitrogen balance."),
                ui.tags.li("Use oral/EN/PN according to gastrointestinal function and the general ICU nutrition pathway; kidney dysfunction alone does not make PN the default route."),
                ui.tags.li("Include non-nutritional calories and consider fluid concentration needs when selecting a formulation."),
            )

    with ui.panel_conditional("input.renal_topic === 'losses'"):
        with ui.card():
            ui.card_header("CKRT / PIKRT Nutrition Losses")
            ui.tags.ul(
                ui.tags.li("KRT can worsen protein balance through amino-acid and peptide/protein losses."),
                ui.tags.li("ESPEN cites amino-acid losses up to approximately 15–20 g/day and peptide/protein losses around 5–10 g/day with intensive KRT modalities; losses vary substantially with modality, membrane and prescription."),
                ui.tags.li("Prolonged CKRT/PIKRT with persistent negative nitrogen balance may require individualized reassessment rather than simply increasing calories."),
                ui.tags.li("Water-soluble micronutrients can also be lost during continuous therapies; avoid assuming that all patients require the same empirical replacement dose."),
            )
            ui.div("Do not translate quoted extracorporeal losses directly into a fixed replacement prescription. Effluent dose, modality, membrane, nutrition delivery and biochemical monitoring all matter.",class_="info-box")

    with ui.panel_conditional("input.renal_topic === 'electrolytes'"):
        with ui.card():
            ui.card_header("Electrolytes, Fluid & Acid–Base")
            ui.tags.ul(
                ui.tags.li("Interpret potassium, phosphorus and magnesium trends together with KRT modality/dose, medications, nutrition delivery, refeeding risk and ongoing gastrointestinal losses."),
                ui.tags.li("CKRT may cause or aggravate hypophosphatemia and other electrolyte depletion; intermittent dialysis can produce different temporal patterns."),
                ui.tags.li("Fluid overload can mask loss of tissue mass and distort weight-based assessment."),
                ui.tags.li("Concentrated EN or PN may help when fluid allowance is constrained, but formula electrolyte content must still match the clinical situation."),
                ui.tags.li("Metabolic acidosis and changing renal clearance affect interpretation of protein tolerance and biochemical markers."),
            )

    with ui.panel_conditional("input.renal_topic === 'monitoring'"):
        with ui.card():
            ui.card_header("Bedside Monitoring")
            ui.tags.ul(
                ui.tags.li("Nutrition delivered versus intended energy/protein provision."),
                ui.tags.li("KRT modality, treatment intensity/effluent prescription and interruptions."),
                ui.tags.li("Fluid balance, edema, urine output and weight trend interpreted together."),
                ui.tags.li("Potassium, phosphorus, magnesium, sodium, bicarbonate/acid–base status, urea and creatinine trends."),
                ui.tags.li("Glucose, triglycerides when relevant, gastrointestinal tolerance and non-nutritional calories."),
                ui.tags.li("Signs of protein-energy wasting/muscle loss; do not rely on BMI alone in substantial fluid overload."),
            )

    with ui.card():
        ui.card_header("Source & Scope")
        ui.p("Primary source: Sabatino A, Fiaccadori E, Barazzoni R, et al. ESPEN practical guideline on clinical nutrition in hospitalized patients with acute or chronic kidney disease. Clinical Nutrition. 2024;43:2238–2254.")
        ui.a("Open ESPEN 2024 kidney guideline",href="https://www.espen.org/files/ESPEN-Guidelines/ESPEN_practical_guideline_on_clinical_nutrition_in_hospitalized_patients_with_acute_or_chronic_kidney_disease-text.pdf",target="_blank",rel="noopener noreferrer")
        ui.p("This module focuses on hospitalized/critically ill adults. Stable outpatient CKD dietary management is outside the scope of this pocket guide.",class_="small-note")


with ui.panel_conditional("input.page === 'metabolic'"):
    ui.h2("Metabolic Calculations")
    with ui.card():
        ui.card_header("Nitrogen balance")
        with ui.layout_columns(col_widths=(4, 4, 4)):
            ui.input_numeric("nb_protein", "Protein intake (g/day)", 100, min=0.1, step=1)
            ui.input_numeric("uun", "UUN (g/day)", 12, min=0, step=0.1)
            ui.input_numeric("non_urinary", "Assumed non-urinary N losses (g/day)", 4, min=0, step=0.5)
        @render.ui
        def nb_result():
            r, err = safe_result(lambda: nitrogen_balance(input.nb_protein(), input.uun(), input.non_urinary()))
            if err:
                return ui.div(err, class_="error-box")
            return result_card("Estimated nitrogen balance", num(r.value, 1), r.unit, "The non-urinary loss assumption is shown and editable")

    with ui.card():
        ui.card_header("Non-protein calorie:nitrogen ratio")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("npc_total", "Total energy (kcal/day)", 2000, min=1, step=50)
            ui.input_numeric("npc_protein", "Protein (g/day)", 100, min=0.1, step=1)
        @render.ui
        def npcn_result():
            r, err = safe_result(lambda: npc_n_ratio(input.npc_total(), input.npc_protein()))
            if err:
                return ui.div(err, class_="error-box")
            return result_card("NPC:N", f"{num(r.value, 0)}:1", "", r.method)


with ui.panel_conditional("input.page === 'adequacy'"):
    ui.h2("Nutrition Adequacy")
    ui.p("Enter the prescribed target and the amount actually delivered. Adequacy is calculated as delivered ÷ prescribed × 100. Percentages are descriptive; no universal adequacy threshold is imposed.", class_="section-intro")
    with ui.card():
        ui.card_header("Energy")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("energy_prescribed", "Prescribed (kcal/day)", 1800, min=1, step=50)
            ui.input_numeric("energy_delivered", "Delivered (kcal/day)", 1420, min=0, step=50)
        @render.ui
        def energy_adequacy_result():
            r, err = safe_result(lambda: adequacy(input.energy_delivered(), input.energy_prescribed(), "kcal"))
            if err:
                return ui.div(err, class_="error-box")
            return ui.div(
                result_card("Energy adequacy", f"{num(r.value, 1)}%", "", "delivered ÷ prescribed × 100"),
                ui.p(f"{num(input.energy_delivered(),0)} kcal delivered ÷ {num(input.energy_prescribed(),0)} kcal prescribed", class_="small-note"),
            )

    with ui.card():
        ui.card_header("Protein")
        with ui.layout_columns(col_widths=(6, 6)):
            ui.input_numeric("protein_prescribed", "Prescribed (g/day)", 95, min=0.1, step=1)
            ui.input_numeric("protein_delivered", "Delivered (g/day)", 76, min=0, step=1)
        @render.ui
        def protein_adequacy_result():
            r, err = safe_result(lambda: adequacy(input.protein_delivered(), input.protein_prescribed(), "g"))
            if err:
                return ui.div(err, class_="error-box")
            return ui.div(
                result_card("Protein adequacy", f"{num(r.value, 1)}%", "", "delivered ÷ prescribed × 100"),
                ui.p(f"{num(input.protein_delivered(),1)} g delivered ÷ {num(input.protein_prescribed(),1)} g prescribed", class_="small-note"),
            )
