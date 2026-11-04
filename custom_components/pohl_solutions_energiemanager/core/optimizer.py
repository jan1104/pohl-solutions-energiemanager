"""SOC-discretized dynamic programming over a supplied forecast scenario.

This solves the finite state model, not an exact continuous or stochastic model.
The grid of stored-energy states includes exact initial, boundary and target SOC.
PV is never curtailed by this module. Import/export are net site power; all prices
must be the user's actual marginal tariffs. No commands are sent to any device.
"""

from bisect import bisect_left, bisect_right
from datetime import timedelta, timezone
from math import isfinite

from .models import BatteryConfig, ForecastSlot, Plan, PlanSlot

EPS = 1e-8


def _finite(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")


def _validate(slots: list[ForecastSlot], cfg: BatteryConfig) -> float:
    for name in (
        "capacity_kwh", "min_soc_pct", "max_soc_pct", "initial_soc_pct",
        "max_charge_kw", "max_discharge_kw", "charge_efficiency",
        "discharge_efficiency", "wear_cost_eur_per_kwh", "soc_step_kwh",
    ):
        _finite(name, getattr(cfg, name))
    if cfg.capacity_kwh <= 0 or cfg.soc_step_kwh <= 0:
        raise ValueError("Capacity and SOC step must be positive")
    if not 0 <= cfg.min_soc_pct < cfg.max_soc_pct <= 100:
        raise ValueError("SOC limits must satisfy 0 <= minimum < maximum <= 100")
    if not cfg.min_soc_pct <= cfg.initial_soc_pct <= cfg.max_soc_pct:
        raise ValueError("Initial SOC must be inside the allowed range")
    if min(cfg.max_charge_kw, cfg.max_discharge_kw, cfg.wear_cost_eur_per_kwh) < 0:
        raise ValueError("Power limits and wear cost must not be negative")
    if not 0 < cfg.charge_efficiency <= 1 or not 0 < cfg.discharge_efficiency <= 1:
        raise ValueError("Efficiencies must be fractions greater than 0 and at most 1")
    if not isinstance(cfg.allow_grid_charge, bool) or not isinstance(cfg.allow_battery_export, bool):
        raise ValueError("Grid charging and battery export permissions must be boolean")
    target = cfg.initial_soc_pct if cfg.terminal_soc_pct is None else cfg.terminal_soc_pct
    _finite("terminal_soc_pct", target)
    if not cfg.min_soc_pct <= target <= cfg.max_soc_pct:
        raise ValueError("Terminal SOC must be inside the allowed range")
    if not slots or len(slots) > 384:
        raise ValueError("Provide between 1 and 384 contiguous forecast slots")
    previous_end = None
    for index, slot in enumerate(slots):
        for name in ("duration_hours", "pv_kw", "load_kw", "import_price_eur_kwh", "export_price_eur_kwh"):
            _finite(f"slots[{index}].{name}", getattr(slot, name))
        if not 0 < slot.duration_hours <= 24:
            raise ValueError("Each slot duration must be positive and at most 24 hours")
        if min(slot.pv_kw, slot.load_kw) < 0:
            raise ValueError("PV and load forecasts must not be negative")
        if slot.start.tzinfo is None or slot.start.utcoffset() is None:
            raise ValueError("Slot start timestamps must include a timezone")
        instant = slot.start.astimezone(timezone.utc)
        if previous_end is not None and abs((instant - previous_end).total_seconds()) > 0.001:
            raise ValueError("Forecast slots must be chronological and contiguous in UTC")
        previous_end = instant + timedelta(hours=slot.duration_hours)
    return target


def _grid_cost(power_kw: float, duration: float, slot: ForecastSlot) -> float:
    return power_kw * duration * (slot.import_price_eur_kwh if power_kw >= 0 else slot.export_price_eur_kwh)


def _self_consumption_states(slots, config, low, high, initial):
    """Exact candidate path following net demand, not a forced dispatch policy.

    Small quarter-hour powers can move less energy than one regular SOC step.
    Retain every endpoint of one physically bounded self-consumption path so
    the finite optimizer can choose that path instead of being forced to idle.
    Its prices/terminal target are deliberately left to the optimizer to judge.
    """
    energy = initial
    result = {round(energy, 10)}
    for slot in slots:
        net = slot.load_kw - slot.pv_kw
        if net < 0:
            energy = min(high, energy + min(-net, config.max_charge_kw)
                         * slot.duration_hours * config.charge_efficiency)
        else:
            energy = max(low, energy - min(net, config.max_discharge_kw)
                         * slot.duration_hours / config.discharge_efficiency)
        result.add(round(energy, 10))
    return result


def optimize(slots: list[ForecastSlot], config: BatteryConfig) -> Plan:
    """Return an economically minimal plan on a discrete stored-energy grid.

    Wear cost is per AC kWh discharged, separate from the cost of energy losses.
    End SOC is at least terminal_soc_pct (defaults to initial SOC). Baseline is
    an idle battery; if target differs from initial, savings aren't SOC-equivalent.
    Current BMS limits should be supplied through the configuration; forecasted
    fixed limits cannot substitute for real-time actuator enforcement.
    """
    slots = list(slots)
    target_pct = _validate(slots, config)
    low = config.capacity_kwh * config.min_soc_pct / 100
    high = config.capacity_kwh * config.max_soc_pct / 100
    initial = config.capacity_kwh * config.initial_soc_pct / 100
    target = config.capacity_kwh * target_pct / 100
    steps = int((high - low) / config.soc_step_kwh)
    if steps > 997:
        raise ValueError("SOC resolution is too fine: choose a step with at most 1001 energy states")
    states = sorted({round(low + i * config.soc_step_kwh, 10) for i in range(steps + 1)} | {
        round(low, 10), round(high, 10), round(initial, 10), round(target, 10),
    })
    augmented = sorted(set(states) | _self_consumption_states(slots, config, low, high, initial))
    path_included = len(augmented) <= 1001
    added_states = len(augmented) - len(states) if path_included else 0
    if path_included:
        states = augmented
    initial_index = min(range(len(states)), key=lambda j: abs(states[j] - initial))
    # Value pairs use AC throughput as a tie-breaker to avoid pointless cycling.
    current: dict[int, tuple[float, float]] = {initial_index: (0.0, 0.0)}
    history: list[dict[int, int]] = []
    for slot in slots:
        duration = slot.duration_hours
        net = slot.load_kw - slot.pv_kw
        charge_kw = config.max_charge_kw
        discharge_kw = config.max_discharge_kw
        if not config.allow_grid_charge:
            charge_kw = min(charge_kw, max(0.0, -net))
        if not config.allow_battery_export:
            discharge_kw = min(discharge_kw, max(0.0, net))
        next_values: dict[int, tuple[float, float]] = {}
        predecessors: dict[int, int] = {}
        for source, (cost_so_far, throughput) in current.items():
            source_energy = states[source]
            bottom = source_energy - discharge_kw * duration / config.discharge_efficiency
            top = source_energy + charge_kw * duration * config.charge_efficiency
            for dest in range(bisect_left(states, bottom - EPS), bisect_right(states, top + EPS)):
                delta = states[dest] - source_energy
                ac_energy = delta / config.charge_efficiency if delta >= 0 else delta * config.discharge_efficiency
                battery_kw = ac_energy / duration
                grid_kw = net + battery_kw
                cost = cost_so_far + _grid_cost(grid_kw, duration, slot) + max(0.0, -ac_energy) * config.wear_cost_eur_per_kwh
                travel = throughput + abs(ac_energy)
                previous = next_values.get(dest)
                if previous is None or cost < previous[0] - 1e-10 or (abs(cost - previous[0]) <= 1e-10 and travel < previous[1] - EPS):
                    next_values[dest] = (cost, travel)
                    predecessors[dest] = source
        if not next_values:
            raise ValueError("No physically feasible battery path exists for the forecast")
        current = next_values
        history.append(predecessors)
    candidates = [index for index in current if states[index] >= target - EPS]
    if not candidates:
        raise ValueError("Terminal SOC target cannot be reached under the supplied forecasts and limits")
    final_index = min(candidates, key=lambda j: current[j])
    route = [final_index]
    for predecessors in reversed(history):
        route.append(predecessors[route[-1]])
    route.reverse()
    planned: list[PlanSlot] = []
    for i, slot in enumerate(slots):
        delta = states[route[i + 1]] - states[route[i]]
        ac_energy = delta / config.charge_efficiency if delta >= 0 else delta * config.discharge_efficiency
        power = ac_energy / slot.duration_hours
        grid = slot.load_kw - slot.pv_kw + power
        cost = _grid_cost(grid, slot.duration_hours, slot) + max(0.0, -ac_energy) * config.wear_cost_eur_per_kwh
        if power > EPS:
            reason = "Laden: im berechneten Preis- und Prognoseszenario wirtschaftlich; Ladezustandsziel berücksichtigt."
        elif power < -EPS:
            reason = "Entladen: prognostizierten Netzbezug ersetzen" if not config.allow_battery_export else "Entladen: wirtschaftliche Nutzung im berechneten Szenario."
        else:
            reason = "Bereitschaft: Energie oder freien Speicherplatz für spätere Zeitfenster erhalten."
        planned.append(PlanSlot(slot.start, slot.duration_hours, slot.pv_kw, slot.load_kw,
                                slot.import_price_eur_kwh, slot.export_price_eur_kwh,
                                power, states[route[i + 1]] / config.capacity_kwh * 100, grid, cost, reason))
    total = sum(slot.cost_eur for slot in planned)
    baseline = sum(_grid_cost(slot.load_kw - slot.pv_kw, slot.duration_hours, slot) for slot in slots)
    assumptions = [
        f"Deterministische Näherung mit {config.soc_step_kwh:g} kWh Zustandsraster; keine Garantie eines kontinuierlichen Optimums.",
        "PV- und Lastprognosen sowie Preise werden als gegeben behandelt; keine garantierten Einsparungen.",
        "Keine PV-Abregelung; Lade- und Entladegrenzen bleiben im gesamten Horizont konstant.",
        "Kosten enthalten Netzbezug minus Einspeiseerlös plus Verschleiß je abgegebener AC-kWh; Investition wird nicht zusätzlich verrechnet.",
        f"Endladezustand mindestens {target_pct:g} %. Vergleich: Batterie bleibt ungenutzt auf dem Anfangsladezustand.",
    ]
    if path_included:
        assumptions.append(f"Eigenverbrauchspfad ergänzt {added_states} Energiezustände; insgesamt {len(states)}. Er ist eine wählbare Alternative, keine erzwungene Strategie.")
    else:
        assumptions.append("Eigenverbrauchspfad wegen Grenze von 1001 Energiezuständen nicht ergänzt; kleine Leistungen können weiterhin vom Raster begrenzt sein.")
    if abs(target_pct - config.initial_soc_pct) > EPS:
        assumptions.append("Endziel und Anfangsladezustand unterscheiden sich: Baseline-Vergleich ist nicht energiegleich.")
    return Plan(planned, total, baseline, baseline - total, assumptions)
