"""Compare finite candidate models on synthetic data; not a Pi benchmark."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter
import tracemalloc
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "pohl_solutions_energiemanager"))
from core.models import BatteryConfig, ForecastSlot
from core.optimizer import optimize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10:
        parser.error("repeats must be between 1 and 10")
    start = datetime(2026, 11, 4, tzinfo=timezone.utc)
    report = {"synthetic_only": True, "platform": platform.platform(),
              "python": platform.python_version(), "repeats": args.repeats, "cases": []}
    for name, count, terminal in (("small_load_4h", 16, 10), ("mixed_day_24h", 96, 50)):
        cfg = BatteryConfig(terminal_soc_pct=terminal)
        forecast = [ForecastSlot(start + timedelta(minutes=15 * i), .25,
                                 0 if count == 16 or not 28 <= i < 64 else 40,
                                 1 if count == 16 else 5 + i % 7,
                                 .4 if count == 16 else (.1 if i < 28 else .35), .05)
                    for i in range(count)]
        for enhanced in (False, True):
            context = nullcontext() if enhanced else patch("core.optimizer._self_consumption_states", return_value=set())
            with context:
                elapsed = []
                for _ in range(args.repeats):
                    before = perf_counter()
                    plan = optimize(forecast, cfg)
                    elapsed.append(perf_counter() - before)
                # Peak allocation is a separate run so tracing doesn't distort
                # the reported uninstrumented timing. Not total process RSS.
                tracemalloc.start()
                try:
                    optimize(forecast, cfg)
                    _, peak = tracemalloc.get_traced_memory()
                finally:
                    tracemalloc.stop()
            report["cases"].append({"case": name, "slots": count,
                                    "candidate_path": enhanced,
                                    "median_seconds": round(median(elapsed), 6),
                                    "peak_traced_kib": round(peak / 1024, 1),
                                    "scenario_cost_eur": round(plan.total_cost_eur, 8),
                                    "state_note": next(a for a in plan.assumptions if "Eigenverbrauchspfad" in a)})
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
