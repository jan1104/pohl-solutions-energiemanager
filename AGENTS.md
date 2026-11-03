# Pohl Solutions Energiemanager

- Product language is German. Brand: Pohl Solutions Energiemanager.
- Keep pure planning, costing, forecasting and hardware transport separate.
- Current development versions are planning-only until the user explicitly authorizes live device control. Never add live actuator writes as a side effect of setup, refresh, demo, tests, or a scheduled development run.
- Device control requires a documented adapter, explicit enablement, validated units/signs, fresh metering and a tested fallback. One writer per actuator and one Modbus RTU master per bus.
- Never infer register addresses or write permissions from product branding alone.
- All power in kW, energy in kWh, internal prices in EUR/kWh. AC battery power positive charging; grid power positive import. SOC is percent, efficiency is a fraction.
- Use timezone-aware timestamps. Handle 23/25-hour days and reject gaps/overlaps in input plans.
- Synthetic prices and generation must be visibly labeled as demonstration. Never silently substitute them for missing live data.
- Keep investment allocation separate from optional marginal cycle wear. Do not count losses or investment twice.
- Manufacturer cycle ratings need operating conditions and provenance. Battery chemistry alone is not a lifetime guarantee.
- Test physical energy balance, operating limits, invalid input, negative prices, reproducibility, and missing/stale data behavior.
- Do not commit private site documents, serial numbers, actual contracts, credentials or Home Assistant configuration. Put local private inputs in private/.
- Update CHANGELOG.md and docs when behavior changes. Commit small, reviewable changes; no release claims before relevant tests pass.
- Shared project UI lives in preview/. After editing its assets, run tools/sync_frontend.py and the archive/synchronization tests so HACS ships the same tested UI. frontend/pohl-panel.js is the HA-only wrapper.
