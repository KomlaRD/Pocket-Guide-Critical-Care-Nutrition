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
        with (self.data_dir / "product_preparations.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                prep_basis[row["product_id"]] = (float(row["basis_quantity"]), row["basis_unit"])
        with (self.data_dir / "products.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                basis_qty, basis_unit = prep_basis[row["product_id"]]
                self.products[row["product_id"]] = Product(
                    row["product_id"], row["product_name"], row["category"],
                    basis_qty, basis_unit, row["verification_status"]
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
