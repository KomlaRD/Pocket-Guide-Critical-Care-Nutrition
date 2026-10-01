from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    category: str
    basis_quantity: float
    basis_unit: str
    verification_status: str
    route: str = ""
    physical_form: str = ""
    use_class: str = ""
    volume_calculation_eligible: bool = False


@dataclass(frozen=True)
class NutritionSource:
    product_id: str
    amount_delivered: float
    amount_unit: str
    amount_prescribed: float | None = None


@dataclass(frozen=True)
class NutrientTotal:
    nutrient_id: str
    amount: float | None
    unit: str
    completeness: str  # COMPLETE, PARTIAL, UNAVAILABLE
    reporting_sources: int
    total_sources: int


class ProductDatabase:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.products: dict[str, Product] = {}
        self.nutrients: dict[str, dict[str, tuple[float, str, float, str]]] = {}
        self._load()

    def _load(self) -> None:
        prep_basis: dict[str, tuple[float, str]] = {}
        use_policy: dict[str, tuple[str, bool]] = {}
        policy_path = self.data_dir / "product_use_policy.csv"
        if policy_path.exists():
            with policy_path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    use_policy[row["product_id"]] = (
                        row["use_class"], row["volume_calculation_eligible"].strip().lower() == "true"
                    )
        with (self.data_dir / "product_preparations.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                prep_basis[row["product_id"]] = (float(row["basis_quantity"]), row["basis_unit"])
        with (self.data_dir / "products.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                basis_qty, basis_unit = prep_basis[row["product_id"]]
                use_class, volume_ok = use_policy.get(row["product_id"], ("", False))
                self.products[row["product_id"]] = Product(
                    row["product_id"], row["product_name"], row["category"],
                    basis_qty, basis_unit, row["verification_status"],
                    row.get("route", ""), row.get("physical_form", ""), use_class, volume_ok
                )
        with (self.data_dir / "product_nutrients.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.nutrients.setdefault(row["product_id"], {})[row["nutrient_id"]] = (
                    float(row["amount"]), row["unit"], float(row["basis_quantity"]), row["basis_unit"]
                )

    def choices(self) -> dict[str, str]:
        return {pid: p.name for pid, p in self.products.items()}

    def product(self, product_id: str) -> Product:
        try:
            return self.products[product_id]
        except KeyError as exc:
            raise ValueError(f"Unknown nutrition product: {product_id}.") from exc

    def nutrients_for(self, product_id: str) -> dict[str, tuple[float, str, float, str]]:
        self.product(product_id)
        return self.nutrients.get(product_id, {})


def calculate_delivery(db: ProductDatabase, sources: Iterable[NutritionSource], nutrient_units: dict[str, str]) -> dict[str, NutrientTotal]:
    sources = list(sources)
    if not sources:
        return {nid: NutrientTotal(nid, None, unit, "UNAVAILABLE", 0, 0) for nid, unit in nutrient_units.items()}

    for source in sources:
        if source.amount_delivered < 0:
            raise ValueError("Delivered amount cannot be negative.")
        product = db.product(source.product_id)
        if source.amount_unit != product.basis_unit:
            raise ValueError(
                f"{product.name} expects amounts in {product.basis_unit}, not {source.amount_unit}."
            )

    totals: dict[str, NutrientTotal] = {}
    for nutrient_id, canonical_unit in nutrient_units.items():
        known_total = 0.0
        reporting = 0
        for source in sources:
            record = db.nutrients_for(source.product_id).get(nutrient_id)
            if record is None:
                continue
            nutrient_amount, unit, basis_qty, basis_unit = record
            if unit != canonical_unit:
                raise ValueError(f"Unit conversion is required for {nutrient_id}: {unit} to {canonical_unit}.")
            if source.amount_unit != basis_unit:
                raise ValueError(f"Basis unit mismatch for {nutrient_id} in {source.product_id}.")
            known_total += source.amount_delivered / basis_qty * nutrient_amount
            reporting += 1
        completeness = "UNAVAILABLE" if reporting == 0 else ("COMPLETE" if reporting == len(sources) else "PARTIAL")
        totals[nutrient_id] = NutrientTotal(
            nutrient_id,
            None if reporting == 0 else known_total,
            canonical_unit,
            completeness,
            reporting,
            len(sources),
        )
    return totals


def volume_delivery_percent(delivered: float, prescribed: float) -> float:
    if prescribed <= 0:
        raise ValueError("Prescribed amount must be greater than 0.")
    if delivered < 0:
        raise ValueError("Delivered amount cannot be negative.")
    return delivered / prescribed * 100

@dataclass(frozen=True)
class CustomNutritionSource:
    name: str
    amount_delivered: float
    amount_unit: str
    basis_quantity: float
    basis_unit: str
    nutrients: dict[str, tuple[float, str]]


def calculate_custom_delivery(source: CustomNutritionSource, nutrient_units: dict[str, str]) -> dict[str, NutrientTotal]:
    if source.amount_delivered < 0:
        raise ValueError("Delivered amount cannot be negative.")
    if source.basis_quantity <= 0:
        raise ValueError("Custom product basis quantity must be greater than 0.")
    if source.amount_unit != source.basis_unit:
        raise ValueError("Delivered amount unit must match the custom product basis unit.")
    totals = {}
    for nutrient_id, canonical_unit in nutrient_units.items():
        record = source.nutrients.get(nutrient_id)
        if record is None:
            totals[nutrient_id] = NutrientTotal(nutrient_id, None, canonical_unit, "UNAVAILABLE", 0, 1)
            continue
        amount, unit = record
        if unit != canonical_unit:
            raise ValueError(f"Unit conversion is required for {nutrient_id}: {unit} to {canonical_unit}.")
        value = source.amount_delivered / source.basis_quantity * float(amount)
        totals[nutrient_id] = NutrientTotal(nutrient_id, value, canonical_unit, "COMPLETE", 1, 1)
    return totals


def combine_nutrient_totals(groups: Iterable[dict[str, NutrientTotal]], nutrient_units: dict[str, str]) -> dict[str, NutrientTotal]:
    groups = list(groups)
    if not groups:
        return {nid: NutrientTotal(nid, None, unit, "UNAVAILABLE", 0, 0) for nid, unit in nutrient_units.items()}
    out = {}
    for nutrient_id, unit in nutrient_units.items():
        values = [g[nutrient_id] for g in groups]
        known = [v.amount for v in values if v.amount is not None]
        reporting = sum(v.reporting_sources for v in values)
        total_sources = sum(v.total_sources for v in values)
        completeness = "UNAVAILABLE" if not known else ("COMPLETE" if reporting == total_sources else "PARTIAL")
        out[nutrient_id] = NutrientTotal(nutrient_id, None if not known else sum(known), unit, completeness, reporting, total_sources)
    return out

def amount_for_nutrient(db: ProductDatabase, product_id: str, nutrient_id: str, target_amount: float) -> tuple[float, str]:
    """Return product amount required to provide target nutrient amount."""
    if target_amount <= 0:
        raise ValueError("Target amount must be greater than 0.")
    product = db.product(product_id)
    record = db.nutrients_for(product_id).get(nutrient_id)
    if record is None:
        raise ValueError(f"{product.name} has no verified {nutrient_id.lower()} value in the catalogue.")
    nutrient_amount, _unit, basis_qty, basis_unit = record
    if nutrient_amount <= 0:
        raise ValueError(f"{product.name} cannot be used to calculate a positive {nutrient_id.lower()} target.")
    return target_amount / nutrient_amount * basis_qty, basis_unit


@dataclass(frozen=True)
class FormulaComparison:
    product_id: str
    name: str
    kcal_per_ml: float | None
    protein_g_per_1000_kcal: float | None
    water_ml_per_1000_kcal: float | None
    carbohydrate_g_per_1000_kcal: float | None
    sodium_mg_per_1000_kcal: float | None
    potassium_mg_per_1000_kcal: float | None
    phosphorus_mg_per_1000_kcal: float | None
    magnesium_mg_per_1000_kcal: float | None


def compare_liquid_formula(db: ProductDatabase, product_id: str) -> FormulaComparison:
    """Normalize a liquid formula for objective comparison without ranking products."""
    p = db.product(product_id)
    if not p.volume_calculation_eligible or p.basis_unit != "mL":
        raise ValueError(f"{p.name} is not eligible for liquid formula comparison.")
    n = db.nutrients_for(product_id)
    e = n.get("ENERGY")
    if e is None or e[0] <= 0:
        raise ValueError(f"{p.name} has no usable energy value.")
    kcal_per_ml = e[0] / e[2]
    def per_1000(nid):
        rec=n.get(nid)
        return None if rec is None else rec[0] / e[0] * 1000
    return FormulaComparison(
        p.product_id,p.name,kcal_per_ml,per_1000("PROTEIN"),per_1000("WATER"),
        per_1000("CARBOHYDRATE"),per_1000("SODIUM"),per_1000("POTASSIUM"),
        per_1000("PHOSPHORUS"),per_1000("MAGNESIUM")
    )


@dataclass(frozen=True)
class ContinuousFeedingPlan:
    product_id: str
    target_energy_kcal: float
    hours_per_day: float
    volume_ml_day: float
    rate_ml_hr: float
    protein_g_day: float | None
    water_ml_day: float | None
    protein_target_g: float | None
    protein_adequacy_percent: float | None


def continuous_feeding_from_energy(db: ProductDatabase, product_id: str, energy_kcal: float, hours_per_day: float, protein_target_g: float | None = None) -> ContinuousFeedingPlan:
    """Calculate liquid formula volume/rate from clinician-entered energy target."""
    if energy_kcal <= 0: raise ValueError("Energy target must be greater than 0.")
    if hours_per_day <= 0 or hours_per_day > 24: raise ValueError("Feeding hours must be greater than 0 and no more than 24.")
    p=db.product(product_id)
    if not p.volume_calculation_eligible or p.basis_unit!="mL":
        raise ValueError(f"{p.name} is not eligible for continuous liquid feeding calculations.")
    volume,unit=amount_for_nutrient(db,product_id,"ENERGY",energy_kcal)
    if unit!="mL": raise ValueError("Continuous feeding calculation requires a volume-based product.")
    n=db.nutrients_for(product_id)
    def delivered(nid):
        rec=n.get(nid)
        return None if rec is None else volume/rec[2]*rec[0]
    protein=delivered("PROTEIN"); water=delivered("WATER")
    adequacy=None
    if protein_target_g is not None:
        if protein_target_g <= 0: raise ValueError("Protein target must be greater than 0.")
        adequacy=None if protein is None else protein/protein_target_g*100
    return ContinuousFeedingPlan(product_id,energy_kcal,hours_per_day,volume,volume/hours_per_day,protein,water,protein_target_g,adequacy)


@dataclass(frozen=True)
class BolusFeedingPlan:
    product_id: str
    target_energy_kcal: float
    feeds_per_day: int
    volume_ml_day: float
    volume_ml_feed: float
    protein_g_day: float | None
    protein_g_feed: float | None
    water_ml_day: float | None
    water_ml_feed: float | None
    protein_target_g: float | None
    protein_adequacy_percent: float | None


def bolus_feeding_from_energy(db: ProductDatabase, product_id: str, energy_kcal: float, feeds_per_day: int, protein_target_g: float | None = None, delivery_site: str = "GASTRIC") -> BolusFeedingPlan:
    """Calculate a gastric bolus schedule from clinician-entered targets without prescribing a universal bolus limit."""
    if energy_kcal <= 0: raise ValueError("Energy target must be greater than 0.")
    if int(feeds_per_day) != feeds_per_day or feeds_per_day < 1:
        raise ValueError("Feeds per day must be a whole number of at least 1.")
    if delivery_site.upper() != "GASTRIC":
        raise ValueError("Bolus feeding is not appropriate for small-bowel delivery. Use a continuous/intermittent method consistent with the enteral access and local protocol.")
    prod=db.product(product_id)
    if not prod.volume_calculation_eligible or prod.basis_unit!="mL":
        raise ValueError(f"{prod.name} is not eligible for liquid bolus calculations.")
    volume,unit=amount_for_nutrient(db,product_id,"ENERGY",energy_kcal)
    if unit!="mL": raise ValueError("Bolus feeding calculation requires a volume-based product.")
    n=db.nutrients_for(product_id)
    def delivered(nid):
        rec=n.get(nid); return None if rec is None else volume/rec[2]*rec[0]
    protein=delivered("PROTEIN"); water=delivered("WATER")
    adequacy=None
    if protein_target_g is not None:
        if protein_target_g <= 0: raise ValueError("Protein target must be greater than 0.")
        adequacy=None if protein is None else protein/protein_target_g*100
    return BolusFeedingPlan(prod.product_id,energy_kcal,int(feeds_per_day),volume,volume/feeds_per_day,protein,None if protein is None else protein/feeds_per_day,water,None if water is None else water/feeds_per_day,protein_target_g,adequacy)
