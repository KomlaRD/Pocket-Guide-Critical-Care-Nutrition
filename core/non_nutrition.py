from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EnergySource:
    name: str
    energy_kcal: float
    source_type: str  # NUTRITION or NON_NUTRITION


@dataclass(frozen=True)
class EnergyExposure:
    nutrition_kcal: float
    non_nutrition_kcal: float
    total_kcal: float
    sources: tuple[EnergySource, ...]


def iv_dextrose_energy(glucose_g: float, kcal_per_g: float = 3.4) -> float:
    glucose = float(glucose_g)
    density = float(kcal_per_g)
    if glucose < 0:
        raise ValueError("IV dextrose amount cannot be negative.")
    if density <= 0:
        raise ValueError("IV dextrose energy density must be greater than 0 kcal/g.")
    return glucose * density


def propofol_energy_from_volume(volume_ml: float, kcal_per_ml: float = 1.1) -> float:
    volume = float(volume_ml)
    density = float(kcal_per_ml)
    if volume < 0:
        raise ValueError("Propofol volume cannot be negative.")
    if density <= 0:
        raise ValueError("Propofol energy density must be greater than 0 kcal/mL.")
    return volume * density


def calculate_energy_exposure(sources: Iterable[EnergySource]) -> EnergyExposure:
    sources = tuple(sources)
    for source in sources:
        if source.energy_kcal < 0:
            raise ValueError(f"Energy for {source.name} cannot be negative.")
        if source.source_type not in {"NUTRITION", "NON_NUTRITION"}:
            raise ValueError(f"Unknown energy source type for {source.name}.")
    nutrition = sum(s.energy_kcal for s in sources if s.source_type == "NUTRITION")
    non_nutrition = sum(s.energy_kcal for s in sources if s.source_type == "NON_NUTRITION")
    return EnergyExposure(nutrition, non_nutrition, nutrition + non_nutrition, sources)
