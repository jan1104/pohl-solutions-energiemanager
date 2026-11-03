"""Physical and economic regression tests; no Home Assistant runtime needed."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "pohl_solutions_energiemanager"))
from core.models import BatteryConfig, ForecastSlot
from core.optimizer import optimize


def slots(pv, load, imports=None, exports=None, duration=1.0):
    start = datetime(2026, 11, 3, tzinfo=timezone.utc)
    return [ForecastSlot(start + timedelta(hours=i * duration), duration, pv_kw, load_kw,
                         (imports or [0.3] * len(pv))[i], (exports or [0.05] * len(pv))[i])
            for i, (pv_kw, load_kw) in enumerate(zip(pv, load))]


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        self.cfg = BatteryConfig(capacity_kwh=10, min_soc_pct=0, max_soc_pct=100,
                                 initial_soc_pct=0, max_charge_kw=5, max_discharge_kw=5,
                                 charge_efficiency=1, discharge_efficiency=1,
                                 terminal_soc_pct=0, soc_step_kwh=1)

    def assert_balanced(self, plan, cfg):
        energy = cfg.capacity_kwh * cfg.initial_soc_pct / 100
        for slot in plan.slots:
            self.assertAlmostEqual(slot.grid_power_kw, slot.load_kw - slot.pv_kw + slot.battery_power_kw)
            ac = slot.battery_power_kw * slot.duration_hours
            energy += ac * cfg.charge_efficiency if ac >= 0 else ac / cfg.discharge_efficiency
            self.assertAlmostEqual(energy, slot.soc_pct * cfg.capacity_kwh / 100)
            self.assertGreaterEqual(slot.soc_pct + 1e-7, cfg.min_soc_pct)
            self.assertLessEqual(slot.soc_pct - 1e-7, cfg.max_soc_pct)
            self.assertLessEqual(slot.battery_power_kw, cfg.max_charge_kw + 1e-7)
            self.assertGreaterEqual(slot.battery_power_kw, -cfg.max_discharge_kw - 1e-7)

    def test_store_cheap_surplus_replace_expensive_consumption(self):
        plan = optimize(slots([5, 0], [0, 5]), self.cfg)
        self.assertAlmostEqual(plan.slots[0].battery_power_kw, 5)
        self.assertAlmostEqual(plan.slots[1].battery_power_kw, -5)
        self.assertAlmostEqual(plan.savings_eur, 1.25)
        self.assert_balanced(plan, self.cfg)

    def test_high_export_value_sells_instead_of_cycling(self):
        plan = optimize(slots([5, 0], [0, 5], exports=[0.5, 0.5]), self.cfg)
        self.assertTrue(all(abs(s.battery_power_kw) < 1e-7 for s in plan.slots))
        self.assertAlmostEqual(plan.savings_eur, 0)

    def test_negative_import_price_requires_explicit_grid_charge(self):
        forecast = slots([0, 0], [0, 5], imports=[-0.1, 0.3])
        blocked = optimize(forecast, self.cfg)
        self.assertEqual(blocked.slots[0].battery_power_kw, 0)
        permitted = optimize(forecast, replace(self.cfg, allow_grid_charge=True))
        self.assertEqual(permitted.slots[0].battery_power_kw, 5)
        self.assert_balanced(permitted, self.cfg)

    def test_no_battery_export_even_when_lucrative(self):
        cfg = replace(self.cfg, initial_soc_pct=100, terminal_soc_pct=0)
        blocked = optimize(slots([0], [1], exports=[2]), cfg)
        self.assertGreaterEqual(blocked.slots[0].grid_power_kw, -1e-7)
        self.assertEqual(blocked.slots[0].battery_power_kw, -1)
        permitted = optimize(slots([0], [1], exports=[2]), replace(cfg, allow_battery_export=True))
        self.assertLess(permitted.slots[0].grid_power_kw, 0)

    def test_battery_never_discharges_into_existing_pv_export(self):
        cfg = replace(self.cfg, initial_soc_pct=100, terminal_soc_pct=0)
        plan = optimize(slots([8], [1], exports=[2]), cfg)
        self.assertEqual(plan.slots[0].battery_power_kw, 0)

    def test_loss_and_quarterhour_power_limits_conserve_energy(self):
        cfg = replace(self.cfg, charge_efficiency=.9, discharge_efficiency=.8, soc_step_kwh=.1)
        plan = optimize(slots([5, 0], [0, 5], duration=.25), cfg)
        self.assert_balanced(plan, cfg)
        self.assertLessEqual(-plan.slots[1].battery_power_kw, plan.slots[0].battery_power_kw * .9 * .8 + 1e-7)

    def test_default_terminal_soc_preserves_starting_energy(self):
        cfg = replace(self.cfg, initial_soc_pct=50, terminal_soc_pct=None)
        plan = optimize(slots([0, 0], [5, 5]), cfg)
        self.assertEqual(plan.slots[-1].soc_pct, 50)
        self.assertEqual(plan.savings_eur, 0)

    def test_unreachable_terminal_target_raises(self):
        with self.assertRaisesRegex(ValueError, "cannot be reached"):
            optimize(slots([0], [0]), replace(self.cfg, terminal_soc_pct=100))

    def test_actual_soc_boundaries_not_rounded_away(self):
        cfg = replace(self.cfg, capacity_kwh=200.704, min_soc_pct=13, max_soc_pct=87,
                      initial_soc_pct=43.2, terminal_soc_pct=None, soc_step_kwh=2)
        plan = optimize(slots([3, 0], [0, 3]), cfg)
        self.assert_balanced(plan, cfg)
        self.assertGreaterEqual(plan.slots[-1].soc_pct + 1e-7, 43.2)

    def test_wear_discourages_unprofitable_cycle(self):
        cfg = replace(self.cfg, wear_cost_eur_per_kwh=.5)
        plan = optimize(slots([5, 0], [0, 5]), cfg)
        self.assertTrue(all(s.battery_power_kw == 0 for s in plan.slots))

    def test_zero_power_and_tied_prices_do_not_create_pointless_cycles(self):
        cfg = replace(self.cfg, initial_soc_pct=50, terminal_soc_pct=None, allow_grid_charge=True)
        plan = optimize(slots([0, 0], [0, 0], imports=[0, 0], exports=[0, 0]), cfg)
        self.assertTrue(all(s.battery_power_kw == 0 for s in plan.slots))
        zero = optimize(slots([5, 0], [0, 5]), replace(cfg, max_charge_kw=0, max_discharge_kw=0))
        self.assertTrue(all(s.battery_power_kw == 0 for s in zero.slots))

    def test_invalid_inputs_fail_explicitly(self):
        for cfg in [replace(self.cfg, capacity_kwh=-1), replace(self.cfg, initial_soc_pct=101),
                    replace(self.cfg, charge_efficiency=0), replace(self.cfg, max_charge_kw=math.nan),
                    replace(self.cfg, soc_step_kwh=.0001), replace(self.cfg, allow_grid_charge="false")]:
            with self.subTest(cfg=cfg), self.assertRaises(ValueError):
                optimize(slots([0], [0]), cfg)
        for forecast in [[], slots([-1], [0]), slots([0], [0], imports=[float("inf")]),
                         [replace(slots([0], [0])[0], start=datetime(2026, 1, 1))],
                         [slots([0], [0])[0], replace(slots([0], [0])[0], start=datetime(2026, 1, 5, tzinfo=timezone.utc))]]:
            with self.subTest(forecast=forecast), self.assertRaises(ValueError):
                optimize(forecast, self.cfg)

    def test_dst_repeat_compared_in_utc(self):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            zone = ZoneInfo("Europe/Berlin")
        except ZoneInfoNotFoundError:
            self.skipTest("Europe/Berlin timezone data is not installed")
        first = datetime(2026, 10, 25, 2, 0, tzinfo=zone, fold=0)
        second = datetime(2026, 10, 25, 2, 0, tzinfo=zone, fold=1)
        forecast = [ForecastSlot(first, 1, 0, 1, .3, .05), ForecastSlot(second, 1, 0, 1, .3, .05)]
        plan = optimize(forecast, self.cfg)
        self.assertEqual(len(plan.slots), 2)


if __name__ == "__main__":
    unittest.main()
