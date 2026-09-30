from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Ion:
    name: str
    stoichiometry: float
    valence: int

@dataclass(frozen=True)
class Formulation:
    formulation_id: str
    name: str
    molecular_weight_g_mol: float
    ions: tuple[Ion, ...]
    note: str = ""

# Chemical forms only. Commercial injection concentrations vary and must be entered from the label.
FORMULATIONS: dict[str, Formulation] = {
    "nacl": Formulation("nacl", "Sodium chloride (NaCl)", 58.44, (Ion("sodium",1,1), Ion("chloride",1,1))),
    "kcl": Formulation("kcl", "Potassium chloride (KCl)", 74.5513, (Ion("potassium",1,1), Ion("chloride",1,1))),
    "mgso4_anhydrous": Formulation("mgso4_anhydrous", "Magnesium sulfate, anhydrous (MgSO4)", 120.366, (Ion("magnesium",1,2), Ion("sulfate",1,2)), "Do not use this molecular weight for hydrated magnesium sulfate products."),
    "mgso4_7h2o": Formulation("mgso4_7h2o", "Magnesium sulfate heptahydrate (MgSO4·7H2O)", 246.47, (Ion("magnesium",1,2), Ion("sulfate",1,2))),
    "kh2po4": Formulation("kh2po4", "Potassium dihydrogen phosphate (KH2PO4)", 136.086, (Ion("potassium",1,1), Ion("phosphate",1,1)), "Phosphate acid-base species vary with pH; use product labeling for clinical electrolyte content."),
    "na2hpo4": Formulation("na2hpo4", "Disodium hydrogen phosphate, anhydrous (Na2HPO4)", 141.958, (Ion("sodium",2,1), Ion("phosphate",1,2)), "Hydration state changes molecular weight; confirm the actual formulation."),
}

def get_formulation(formulation_id: str) -> Formulation:
    try: return FORMULATIONS[str(formulation_id)]
    except KeyError: raise ValueError("Unsupported formulation. Select the exact chemical formulation; do not infer it from the electrolyte name.")

def mass_mg_to_compound_mmol(mass_mg: float, formulation_id: str) -> float:
    mass=float(mass_mg)
    if mass < 0: raise ValueError("Mass cannot be negative.")
    f=get_formulation(formulation_id)
    return mass / f.molecular_weight_g_mol  # mg / (mg/mmol)

def compound_mmol_to_mass_mg(mmol: float, formulation_id: str) -> float:
    n=float(mmol)
    if n < 0: raise ValueError("Amount cannot be negative.")
    return n * get_formulation(formulation_id).molecular_weight_g_mol

def ion_amounts(compound_mmol: float, formulation_id: str) -> dict[str, dict[str,float]]:
    n=float(compound_mmol)
    if n < 0: raise ValueError("Amount cannot be negative.")
    f=get_formulation(formulation_id)
    return {ion.name:{"mmol":n*ion.stoichiometry,"mEq":n*ion.stoichiometry*abs(ion.valence)} for ion in f.ions}

def dextrose_concentration_percent(dextrose_g: float, final_volume_ml: float) -> float:
    g=float(dextrose_g); v=float(final_volume_ml)
    if g < 0: raise ValueError("Dextrose amount cannot be negative.")
    if v <= 0: raise ValueError("Final volume must be greater than 0.")
    return g / v * 100.0

def infusion_rate_ml_hr(volume_ml: float, hours: float) -> float:
    v=float(volume_ml); h=float(hours)
    if v < 0: raise ValueError("Volume cannot be negative.")
    if h <= 0: raise ValueError("Infusion duration must be greater than 0.")
    return v/h

def pn_distribution(dextrose_g: float, amino_acid_g: float, lipid_g: float, *, dextrose_kcal_g: float=3.4, amino_acid_kcal_g: float=4.0, lipid_kcal_g: float=10.0) -> dict[str,float]:
    amounts=[float(dextrose_g),float(amino_acid_g),float(lipid_g)]; dens=[float(dextrose_kcal_g),float(amino_acid_kcal_g),float(lipid_kcal_g)]
    if any(x<0 for x in amounts): raise ValueError("PN macronutrient amounts cannot be negative.")
    if any(x<=0 for x in dens): raise ValueError("Energy densities must be greater than 0.")
    kcal=[a*d for a,d in zip(amounts,dens)]; total=sum(kcal)
    if total <= 0: raise ValueError("At least one PN macronutrient amount must be greater than 0.")
    return {"dextrose_kcal":kcal[0],"amino_acid_kcal":kcal[1],"lipid_kcal":kcal[2],"total_kcal":total,"dextrose_percent":kcal[0]/total*100,"amino_acid_percent":kcal[1]/total*100,"lipid_percent":kcal[2]/total*100}
