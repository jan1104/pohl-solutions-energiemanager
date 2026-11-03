"""Transparent scenario economics, separate from marginal dispatch wear costs.

Cycle-life inputs must refer to the selected SOC window. This module does not
invent chemistry-specific lifetimes or extrapolate a manufacturer's DoD curve.
"""

from dataclasses import dataclass, field
from math import isfinite


@dataclass(frozen=True, slots=True)
class LifecycleInputs:
    purchase_cost_eur: float
    capacity_kwh: float
    min_soc_pct: float
    max_soc_pct: float
    cycle_life: float
    calendar_life_years: float
    cycles_per_year: float
    average_capacity_factor: float = 0.90
    discharge_efficiency: float = 0.96
    annual_operating_cost_eur: float = 0.0
    residual_value_eur: float = 0.0


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    usable_capacity_kwh: float
    expected_years: float
    expected_cycles: float
    lifetime_output_kwh: float
    total_cost_eur: float
    cost_eur_per_output_kwh: float | None
    limiting_factor: str
    assumptions: list[str] = field(default_factory=list)


def calculate_lifecycle(inputs: LifecycleInputs) -> LifecycleResult:
    """Calculate indicative levelized storage cost, excluding input energy cost.

    No discounting, price escalation or lifetime prediction is performed. Average
    capacity factor explicitly approximates fade; it is not another conversion
    efficiency. Purchase includes whichever system components the user chooses.
    """
    for name in inputs.__dataclass_fields__:
        value = getattr(inputs, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    if inputs.capacity_kwh <= 0 or inputs.cycle_life <= 0 or inputs.calendar_life_years <= 0:
        raise ValueError("Capacity, cycle life and calendar life must be positive")
    if not 0 <= inputs.min_soc_pct < inputs.max_soc_pct <= 100:
        raise ValueError("SOC limits must satisfy 0 <= minimum < maximum <= 100")
    if min(inputs.purchase_cost_eur, inputs.annual_operating_cost_eur, inputs.residual_value_eur, inputs.cycles_per_year) < 0:
        raise ValueError("Costs, residual value and annual cycles must not be negative")
    if inputs.residual_value_eur > inputs.purchase_cost_eur:
        raise ValueError("Residual value must not exceed the selected purchase cost")
    if not 0 < inputs.average_capacity_factor <= 1 or not 0 < inputs.discharge_efficiency <= 1:
        raise ValueError("Capacity factor and discharge efficiency must be fractions in (0, 1]")
    years_to_cycles = inputs.cycle_life / inputs.cycles_per_year if inputs.cycles_per_year else float("inf")
    years = min(inputs.calendar_life_years, years_to_cycles)
    cycles = years * inputs.cycles_per_year
    usable = inputs.capacity_kwh * (inputs.max_soc_pct - inputs.min_soc_pct) / 100
    output = usable * cycles * inputs.average_capacity_factor * inputs.discharge_efficiency
    total_cost = inputs.purchase_cost_eur - inputs.residual_value_eur + inputs.annual_operating_cost_eur * years
    limiting = "calendar" if inputs.calendar_life_years <= years_to_cycles else "cycles"
    assumptions = [
        "Szenariorechnung, keine garantierte Batterie-Lebensdauer; keine Abzinsung oder Preissteigerung.",
        "Zyklenlebensdauer und Jahreszyklen beziehen sich auf vollständige Durchläufe des gewählten SOC-Fensters, nicht automatisch auf 0–100-%-Vollzyklen.",
        "Ein Batterietyp allein liefert keine belastbare Zyklenzahl; passende Herstellerdaten oder eigene ausgewiesene Annahmen verwenden.",
        "Durchschnittlicher Kapazitätsfaktor bildet Alterung vereinfacht ab; Entladewirkungsgrad bildet separate Umwandlungsverluste ab.",
        "Kosten je abgegebener AC-kWh ohne Wert der geladenen Energie; nicht zusätzlich zu demselben bereits angesetzten Investitionsverschleiß addieren.",
        "Bestehende PV-Investitionen sind für die kurzfristige Ladeentscheidung keine zusätzlichen Grenzkosten.",
    ]
    if output == 0:
        assumptions.append("Ohne Jahreszyklen entsteht keine abgegebene Energie und kein definierter kWh-Kostenwert.")
    return LifecycleResult(usable, years, cycles, output, total_cost,
                           total_cost / output if output else None, limiting, assumptions)


def delivered_energy_cost_eur_per_kwh(
    source_cost_eur_kwh: float,
    charge_efficiency: float,
    discharge_efficiency: float,
    storage_cost_eur_per_output_kwh: float,
) -> float:
    """Input energy value divided by AC round-trip efficiency plus storage cost.

    For PV the source value is foregone export revenue. The storage cost should be
    either marginal wear OR the chosen levelized figure, never their duplicate sum.
    Negative source prices are legitimate. No tariff or tax assumptions are added.
    """
    values = (source_cost_eur_kwh, charge_efficiency, discharge_efficiency, storage_cost_eur_per_output_kwh)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in values):
        raise ValueError("Energy cost inputs must be finite numbers")
    if not 0 < charge_efficiency <= 1 or not 0 < discharge_efficiency <= 1:
        raise ValueError("Efficiencies must be fractions in (0, 1]")
    if storage_cost_eur_per_output_kwh < 0:
        raise ValueError("Storage cost must not be negative")
    return source_cost_eur_kwh / (charge_efficiency * discharge_efficiency) + storage_cost_eur_per_output_kwh
