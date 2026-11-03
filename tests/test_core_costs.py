from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "pohl_solutions_energiemanager"))
from core.costs import LifecycleInputs, calculate_lifecycle, delivered_energy_cost_eur_per_kwh


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.inputs = LifecycleInputs(purchase_cost_eur=40_000, capacity_kwh=200.704,
            min_soc_pct=10, max_soc_pct=100, cycle_life=6000, calendar_life_years=15,
            cycles_per_year=250, average_capacity_factor=.9, discharge_efficiency=.96)

    def test_calendar_limited_worked_example(self):
        result = calculate_lifecycle(self.inputs)
        self.assertEqual(result.expected_cycles, 3750)
        self.assertEqual(result.expected_years, 15)
        self.assertEqual(result.limiting_factor, "calendar")
        self.assertAlmostEqual(result.lifetime_output_kwh, 200.704 * .9 * 3750 * .9 * .96)
        self.assertAlmostEqual(result.cost_eur_per_output_kwh, .06834652443118298, places=5)

    def test_cycle_limit_shortens_operating_cost_period(self):
        result = calculate_lifecycle(replace(self.inputs, cycle_life=1000, annual_operating_cost_eur=100))
        self.assertEqual(result.expected_years, 4)
        self.assertEqual(result.expected_cycles, 1000)
        self.assertEqual(result.total_cost_eur, 40400)
        self.assertEqual(result.limiting_factor, "cycles")

    def test_soc_window_recalculates_usable_energy_not_cycle_life(self):
        wide = calculate_lifecycle(self.inputs)
        narrow = calculate_lifecycle(replace(self.inputs, min_soc_pct=20, max_soc_pct=90))
        self.assertAlmostEqual(narrow.usable_capacity_kwh, 200.704 * .7)
        self.assertEqual(narrow.expected_cycles, wide.expected_cycles)
        self.assertGreater(narrow.cost_eur_per_output_kwh, wide.cost_eur_per_output_kwh)

    def test_no_use_returns_unknown_unit_cost(self):
        result = calculate_lifecycle(replace(self.inputs, cycles_per_year=0))
        self.assertEqual(result.lifetime_output_kwh, 0)
        self.assertIsNone(result.cost_eur_per_output_kwh)

    def test_value_of_input_energy_accounts_for_both_losses(self):
        self.assertAlmostEqual(delivered_energy_cost_eur_per_kwh(.05, .95, .95, .06), .05 / .9025 + .06)
        self.assertLess(delivered_energy_cost_eur_per_kwh(-.1, .95, .95, 0), -.1)

    def test_invalid_cost_scenarios_rejected(self):
        for change in [{"capacity_kwh": 0}, {"cycle_life": 0}, {"min_soc_pct": 100},
                       {"residual_value_eur": 50000}, {"discharge_efficiency": 1.1},
                       {"average_capacity_factor": float("nan")}, {"cycles_per_year": -1}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                calculate_lifecycle(replace(self.inputs, **change))


if __name__ == "__main__":
    unittest.main()
