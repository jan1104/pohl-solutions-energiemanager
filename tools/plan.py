"""Local JSON planning runner. Does not connect to Home Assistant or devices."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "pohl_solutions_energiemanager"))

from core.models import BatteryConfig, ForecastSlot  # noqa: E402
from core.optimizer import optimize  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Pohl Solutions Energiemanager · lokale Planung")
    parser.add_argument("input", type=Path, help="JSON mit battery und slots")
    parser.add_argument("--output", type=Path, help="Plan als JSON speichern")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        config = BatteryConfig(**data.get("battery", {}))
        slots = [ForecastSlot(**{**row, "start": datetime.fromisoformat(row["start"])})
                 for row in data["slots"]]
        plan = optimize(slots, config)
    except (OSError, ValueError, TypeError, KeyError) as err:
        parser.exit(2, f"Planung nicht möglich: {err}\n")
    result = asdict(plan)
    for row in result["slots"]:
        row["start"] = row["start"].isoformat()
    result["planning_only"] = True
    result["data_origin"] = data.get("data_origin", "user_supplied_scenario")
    text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Plan gespeichert: {args.output.resolve()}")
        print(f"Szenariovorteil: {plan.savings_eur:.2f} EUR; {len(plan.slots)} Intervalle")
    else:
        print(text)


if __name__ == "__main__":
    main()
