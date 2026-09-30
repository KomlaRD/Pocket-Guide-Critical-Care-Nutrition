from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class CalcResult:
    value: float
    unit: str
    method: str
    inputs: dict[str, Any]
    warnings: tuple[str, ...] = field(default_factory=tuple)

def _positive(name: str, value: float) -> float:
    value = float(value)
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0.")
    return value

def bmi(weight_kg: float, height_cm: float) -> CalcResult:
    w, h = _positive("Weight", weight_kg), _positive("Height", height_cm) / 100
    return CalcResult(w / h**2, "kg/m²", "BMI = weight / height²", {"weight_kg": w, "height_cm": height_cm})

def percent_weight_loss(usual_weight_kg: float, current_weight_kg: float) -> CalcResult:
    usual, current = _positive("Usual weight", usual_weight_kg), _positive("Current weight", current_weight_kg)
    value=(usual-current)/usual*100
    warnings=("Current weight exceeds usual weight; the negative result represents weight gain, not weight loss.",) if value < 0 else ()
    return CalcResult(value, "%", "% change = (usual-current)/usual × 100", {"usual_weight_kg": usual, "current_weight_kg": current}, warnings)

def weight_based_range(weight_kg: float, minimum: float, maximum: float, unit_per_kg: str, output_unit: str) -> tuple[CalcResult, CalcResult]:
    w, lo, hi = _positive("Dosing weight", weight_kg), _positive("Minimum dose", minimum), _positive("Maximum dose", maximum)
    if lo > hi: raise ValueError("Minimum dose cannot exceed maximum dose.")
    return (CalcResult(w*lo, output_unit, f"{lo:g} {unit_per_kg}", {"weight_kg":w}), CalcResult(w*hi, output_unit, f"{hi:g} {unit_per_kg}", {"weight_kg":w}))

def weir_energy(vo2_ml_min: float, vco2_ml_min: float) -> CalcResult:
    vo2, vco2 = _positive("VO2", vo2_ml_min), _positive("VCO2", vco2_ml_min)
    value = (3.941*vo2 + 1.106*vco2)*1.44
    return CalcResult(value, "kcal/day", "Weir equation", {"VO2_ml_min":vo2, "VCO2_ml_min":vco2})

def en_rate(energy_target_kcal: float, density_kcal_ml: float, feeding_hours: float=24) -> CalcResult:
    e, d, h = _positive("Energy target", energy_target_kcal), _positive("Energy density", density_kcal_ml), _positive("Feeding duration", feeding_hours)
    if h > 24: raise ValueError("Feeding duration cannot exceed 24 hours/day.")
    return CalcResult(e/(d*h), "mL/hour", "Energy target / (energy density × feeding hours)", {"energy_target_kcal":e,"density_kcal_ml":d,"feeding_hours":h})

def gir(glucose_g_day: float, weight_kg: float) -> CalcResult:
    g, w = _positive("Glucose", glucose_g_day), _positive("Dosing weight", weight_kg)
    return CalcResult(g*1000/(w*1440), "mg/kg/min", "GIR = glucose mg/day / (kg × 1440 min)", {"glucose_g_day":g,"weight_kg":w})

def propofol_energy(rate_ml_hr: float, hours: float, energy_density_kcal_ml: float=1.1) -> CalcResult:
    r, h, d = _positive("Propofol rate", rate_ml_hr), _positive("Duration", hours), _positive("Energy density", energy_density_kcal_ml)
    if h > 24: raise ValueError("Duration cannot exceed 24 hours/day for this daily energy calculation.")
    return CalcResult(r*h*d, "kcal", "rate × duration × product energy density", {"rate_ml_hr":r,"hours":h,"energy_density_kcal_ml":d})

def nitrogen_balance(protein_g_day: float, uun_g_day: float, non_urinary_loss_g: float=4.0) -> CalcResult:
    p, u = _positive("Protein intake", protein_g_day), float(uun_g_day)
    loss = float(non_urinary_loss_g)
    if u < 0 or loss < 0: raise ValueError("Nitrogen losses cannot be negative.")
    return CalcResult(p/6.25-(u+loss), "g N/day", "protein/6.25 − (UUN + non-urinary losses)", {"protein_g_day":p,"uun_g_day":u,"non_urinary_loss_g":loss})

def npc_n_ratio(total_kcal: float, protein_g: float) -> CalcResult:
    kcal, p = _positive("Total energy", total_kcal), _positive("Protein", protein_g)
    protein_kcal = p*4
    if protein_kcal >= kcal: raise ValueError("Protein-derived energy must be less than total energy for NPC:N calculation.")
    nitrogen = p/6.25
    return CalcResult((kcal-protein_kcal)/nitrogen, "kcal:g N", "(total kcal − protein kcal) / nitrogen", {"total_kcal":kcal,"protein_g":p})

def adequacy(delivered: float, prescribed: float, unit: str) -> CalcResult:
    p = _positive("Prescribed amount", prescribed)
    d = float(delivered)
    if d < 0: raise ValueError("Delivered amount cannot be negative.")
    return CalcResult(d/p*100, "%", "delivered / prescribed × 100", {"delivered":d,"prescribed":p,"quantity_unit":unit})

def ideal_body_weight_devine(height_cm: float, sex: str) -> CalcResult:
    h = _positive("Height", height_cm)
    s = str(sex).strip().lower()
    if s not in {"male", "female"}:
        raise ValueError("Sex must be 'male' or 'female' for the Devine equation.")
    inches = h / 2.54
    base = 50.0 if s == "male" else 45.5
    value = base + 2.3 * (inches - 60.0)
    warnings = () if inches >= 60 else ("Devine IBW is commonly expressed from 5 ft; use clinical judgment below this height.",)
    return CalcResult(value, "kg", "Devine ideal body weight", {"height_cm": h, "sex": s}, warnings)


def adjusted_body_weight(actual_weight_kg: float, ideal_weight_kg: float, correction_factor: float = 0.4) -> CalcResult:
    actual = _positive("Actual weight", actual_weight_kg)
    ideal = _positive("Ideal body weight", ideal_weight_kg)
    factor = float(correction_factor)
    if factor < 0 or factor > 1:
        raise ValueError("Correction factor must be between 0 and 1.")
    value = ideal + factor * (actual - ideal)
    return CalcResult(value, "kg", "AdjBW = IBW + factor × (actual − IBW)", {"actual_weight_kg": actual, "ideal_weight_kg": ideal, "correction_factor": factor})


def fluid_balance(total_input_ml: float, total_output_ml: float) -> CalcResult:
    inp, out = float(total_input_ml), float(total_output_ml)
    if inp < 0 or out < 0:
        raise ValueError("Fluid input and output cannot be negative.")
    return CalcResult(inp - out, "mL", "Fluid balance = total input − total output", {"input_ml": inp, "output_ml": out})


def formula_free_water(volume_ml: float, water_ml_per_100ml: float) -> CalcResult:
    volume = float(volume_ml)
    water = float(water_ml_per_100ml)
    if volume < 0:
        raise ValueError("Formula volume cannot be negative.")
    if water < 0 or water > 100:
        raise ValueError("Water content must be between 0 and 100 mL per 100 mL.")
    return CalcResult(volume * water / 100.0, "mL", "volume × water content / 100", {"volume_ml": volume, "water_ml_per_100ml": water})


def pn_macronutrient_energy(dextrose_g: float, amino_acid_g: float, lipid_g: float, dextrose_kcal_g: float = 3.4, amino_acid_kcal_g: float = 4.0, lipid_kcal_g: float = 10.0) -> CalcResult:
    vals = [float(dextrose_g), float(amino_acid_g), float(lipid_g)]
    if any(v < 0 for v in vals):
        raise ValueError("PN macronutrient amounts cannot be negative.")
    densities = [float(dextrose_kcal_g), float(amino_acid_kcal_g), float(lipid_kcal_g)]
    if any(v <= 0 for v in densities):
        raise ValueError("Energy densities must be greater than 0.")
    value = vals[0]*densities[0] + vals[1]*densities[1] + vals[2]*densities[2]
    return CalcResult(value, "kcal", "dextrose × density + amino acids × density + lipid × density", {"dextrose_g":vals[0],"amino_acid_g":vals[1],"lipid_g":vals[2],"dextrose_kcal_g":densities[0],"amino_acid_kcal_g":densities[1],"lipid_kcal_g":densities[2]}, ("Confirm product-specific energy densities, especially lipid emulsions.",))


def respiratory_quotient(vo2_ml_min: float, vco2_ml_min: float) -> CalcResult:
    vo2, vco2 = _positive("VO2", vo2_ml_min), _positive("VCO2", vco2_ml_min)
    return CalcResult(vco2 / vo2, "", "RQ = VCO2 / VO2", {"VO2_ml_min":vo2,"VCO2_ml_min":vco2})


def convert_units(value: float, from_unit: str, to_unit: str) -> CalcResult:
    v = float(value)
    f, t = str(from_unit), str(to_unit)
    factors = {
        ("kg", "lb"): 2.2046226218, ("lb", "kg"): 1/2.2046226218,
        ("cm", "in"): 1/2.54, ("in", "cm"): 2.54,
        ("L", "mL"): 1000.0, ("mL", "L"): 0.001,
        ("kcal", "kJ"): 4.184, ("kJ", "kcal"): 1/4.184,
    }
    if f == t:
        factor = 1.0
    elif (f, t) in factors:
        factor = factors[(f, t)]
    else:
        raise ValueError(f"Unsupported conversion: {f} to {t}.")
    return CalcResult(v*factor, t, f"{f} → {t}", {"value":v,"from_unit":f,"to_unit":t})


def electrolyte_mmol_mEq(amount: float, valence: int, direction: str = "mmol_to_mEq") -> CalcResult:
    a = float(amount)
    z = int(valence)
    if a < 0:
        raise ValueError("Electrolyte amount cannot be negative.")
    if z <= 0:
        raise ValueError("Absolute ionic valence must be greater than 0.")
    if direction == "mmol_to_mEq":
        return CalcResult(a*z, "mEq", "mEq = mmol × |valence|", {"amount_mmol":a,"valence":z})
    if direction == "mEq_to_mmol":
        return CalcResult(a/z, "mmol", "mmol = mEq / |valence|", {"amount_mEq":a,"valence":z})
    raise ValueError("Direction must be 'mmol_to_mEq' or 'mEq_to_mmol'.")
