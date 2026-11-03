"""Explicit units and signs for deterministic energy planning.

Power is AC kW: battery positive means charging, grid positive means import.
SOC is internal stored energy as a percentage of current configured capacity.
Forecasts are scenario inputs, not claims about future production or consumption.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BatteryConfig:
    capacity_kwh: float = 200.704
    min_soc_pct: float = 10.0
    max_soc_pct: float = 90.0
    initial_soc_pct: float = 50.0
    max_charge_kw: float = 50.0
    max_discharge_kw: float = 50.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    wear_cost_eur_per_kwh: float = 0.0
    allow_grid_charge: bool = False
    allow_battery_export: bool = False
    terminal_soc_pct: float | None = None
    soc_step_kwh: float = 2.0


@dataclass(frozen=True, slots=True)
class ForecastSlot:
    start: datetime
    duration_hours: float
    pv_kw: float
    load_kw: float
    import_price_eur_kwh: float
    export_price_eur_kwh: float


@dataclass(frozen=True, slots=True)
class PlanSlot:
    start: datetime
    duration_hours: float
    pv_kw: float
    load_kw: float
    import_price_eur_kwh: float
    export_price_eur_kwh: float
    battery_power_kw: float
    soc_pct: float
    grid_power_kw: float
    cost_eur: float
    reason: str


@dataclass(frozen=True, slots=True)
class Plan:
    slots: list[PlanSlot]
    total_cost_eur: float
    baseline_cost_eur: float
    savings_eur: float
    assumptions: list[str] = field(default_factory=list)
