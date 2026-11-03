/* Pohl Solutions Energiemanager: local planning preview, no device connections. */
"use strict";

const PohlPreview = (() => {
  const DEFAULTS = Object.freeze({ chemistry: "lfp", purchase: 40000, residual: 0, capacity: 200.704,
    minSoc: 10, maxSoc: 90, cycles: 6000, years: 15, cyclesPerYear: 250,
    averageCapacity: 90, chargeEfficiency: 95, dischargeEfficiency: 96, marginalWear: 0 });
  const number = (value, digits = 1) => new Intl.NumberFormat("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
  const time = (value) => new Intl.DateTimeFormat("de-DE", { timeZone: "Europe/Berlin", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
  const date = (value) => new Intl.DateTimeFormat("de-DE", { timeZone: "Europe/Berlin", day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(value));
  const euro = (value) => new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(value);
  const PRICE_MODES = Object.freeze({ forecast: "Im Prognosedatensatz enthalten", entity: "Home-Assistant-Entität", url: "JSON-API-URL", fixed: "Fester Tarif", smard: "SMARD · Deutschland/Luxemburg" });
  const PRICE_UNITS = Object.freeze({ eur_kwh: "EUR/kWh", ct_kwh: "ct/kWh", eur_mwh: "EUR/MWh" });
  const PRICE_DEFAULTS = Object.freeze(Object.fromEntries(["import", "export"].flatMap((p) => [
    [`${p}_price_mode`, "forecast"], [`${p}_price_entity`, ""], [`${p}_price_url`, ""], [`${p}_price_unit`, "eur_kwh"],
    [`${p}_fixed_price`, 0], [`${p}_price_multiplier`, 1], [`${p}_price_adder_eur_kwh`, 0]
  ])));

  function validatePriceConfig(input) {
    if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("Ungültige Preisquellen-Konfiguration.");
    const result = {};
    for (const prefix of ["import", "export"]) {
      const label = prefix === "import" ? "Bezug" : "Einspeisung";
      const key = (name) => `${prefix}_${name}`;
      const mode = input[key("price_mode")];
      if (!Object.hasOwn(PRICE_MODES, mode)) throw new Error(`${label}: Bitte eine gültige Preisquelle wählen.`);
      const rawUnit = input[key("price_unit")];
      if (!Object.hasOwn(PRICE_UNITS, rawUnit)) throw new Error(`${label}: Bitte eine gültige Quellen-Einheit wählen.`);
      result[key("price_mode")] = mode;
      result[key("price_unit")] = mode === "smard" ? "eur_mwh" : mode === "forecast" ? "eur_kwh" : rawUnit;
      const entity = typeof input[key("price_entity")] === "string" ? input[key("price_entity")].trim() : "";
      const url = typeof input[key("price_url")] === "string" ? input[key("price_url")].trim() : "";
      if (mode === "entity" && !/^[a-z_][a-z0-9_]*\.[a-z0-9_]+$/.test(entity)) throw new Error(`${label}: Eine gültige HA-Entität angeben, zum Beispiel sensor.strompreis_prognose.`);
      if (mode === "url") {
        let parsed;
        try { parsed = new URL(url); } catch { throw new Error(`${label}: Eine vollständige JSON-API-URL mit http:// oder https:// angeben.`); }
        if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname || parsed.username || parsed.password) throw new Error(`${label}: Erlaubt sind HTTP-/HTTPS-URLs ohne eingebettete Zugangsdaten.`);
      }
      result[key("price_entity")] = mode === "entity" ? entity : "";
      result[key("price_url")] = mode === "url" ? url : "";
      for (const suffix of ["fixed_price", "price_multiplier", "price_adder_eur_kwh"]) {
        const raw = input[key(suffix)];
        if (raw === "" || typeof raw === "string" && raw.trim() === "" || raw === null || typeof raw === "boolean" || !["string", "number"].includes(typeof raw) || !Number.isFinite(Number(raw))) throw new Error(`${label}: Tarif, Faktor und Zuschlag müssen endliche Zahlen sein.`);
        result[key(suffix)] = Number(raw);
      }
      if (result[key("price_multiplier")] < 0) throw new Error(`${label}: Der Preisfaktor darf nicht negativ sein.`);
      if (mode === "fixed") transformPrice(result[key("fixed_price")], result[key("price_unit")], result[key("price_multiplier")], result[key("price_adder_eur_kwh")]);
    }
    return result;
  }

  function transformPrice(value, unit, multiplier = 1, adderEurKwh = 0) {
    if (![value, multiplier, adderEurKwh].every((v) => typeof v === "number" && Number.isFinite(v)) || !Object.hasOwn(PRICE_UNITS, unit) || multiplier < 0) throw new Error("Ungültige Preisumrechnung.");
    const factors = { eur_kwh: 1, ct_kwh: 0.01, eur_mwh: 0.001 };
    const price = value * factors[unit] * multiplier + adderEurKwh;
    if (!Number.isFinite(price)) throw new Error("Preisumrechnung außerhalb des gültigen Zahlenbereichs.");
    return price;
  }

  function lifecycleCost(raw) {
    const p = {};
    for (const key of Object.keys(DEFAULTS).filter((key) => key !== "chemistry")) {
      if (raw[key] === "" || raw[key] == null) throw new Error("Bitte alle Zahlenfelder ausfüllen.");
      p[key] = Number(raw[key]);
      if (!Number.isFinite(p[key])) throw new Error("Alle Eingaben müssen endliche Zahlen sein.");
    }
    if (p.purchase < 0 || p.residual < 0 || p.residual > p.purchase) throw new Error("Der Restwert muss zwischen 0 und dem Kaufpreis liegen.");
    if (p.capacity <= 0 || p.cycles <= 0 || p.years <= 0 || p.cyclesPerYear <= 0) throw new Error("Kapazität, Lebensdauer und Nutzung müssen größer als 0 sein.");
    if (p.minSoc < 0 || p.maxSoc > 100 || p.minSoc >= p.maxSoc) throw new Error("Der minimale Ladezustand muss unter dem maximalen liegen (0–100 %).");
    if ([p.averageCapacity, p.chargeEfficiency, p.dischargeEfficiency].some((v) => v <= 0 || v > 100)) throw new Error("Kapazitätsfaktor und Wirkungsgrade müssen größer als 0 und höchstens 100 % sein.");
    if (p.marginalWear < 0) throw new Error("Der zusätzliche Verschleiß darf nicht negativ sein.");
    const window = (p.maxSoc - p.minSoc) / 100;
    const usableKwh = p.capacity * window;
    const calendarCycles = p.cyclesPerYear * p.years;
    const lifetimeCycles = Math.min(p.cycles, calendarCycles);
    const lifetimeOutputKwh = usableKwh * lifetimeCycles * p.averageCapacity / 100 * p.dischargeEfficiency / 100;
    const fullCostCtKwh = (p.purchase - p.residual) / lifetimeOutputKwh * 100;
    return { window, usableKwh, lifetimeCycles, lifetimeOutputKwh, fullCostCtKwh,
      roundTripEfficiency: p.chargeEfficiency / 100 * p.dischargeEfficiency / 100,
      limitingFactor: p.cycles < calendarCycles ? "Zyklenlebensdauer" : p.cycles > calendarCycles ? "Kalenderlebensdauer" : "Beide Grenzen", marginalWearCtKwh: p.marginalWear };
  }

  function validatePlan(input) {
    if (!input || typeof input !== "object" || !Array.isArray(input.slots) || !input.slots.length) throw new Error("Die Datei muss einen Plan mit einer nicht leeren Liste „slots“ enthalten.");
    if (input.slots.length > 768) throw new Error("Diese Vorschau unterstützt höchstens 768 Zeitintervalle.");
    const required = ["duration_hours", "pv_kw", "load_kw", "import_price_eur_kwh", "export_price_eur_kwh", "battery_power_kw", "soc_pct", "grid_power_kw", "cost_eur"];
    let previousEnd = null;
    const slots = input.slots.map((s, i) => {
      if (!s || typeof s !== "object") throw new Error(`Intervall ${i + 1}: ungültiger Datensatz.`);
      if (typeof s.start !== "string" || !/(Z|[+-]\d{2}:\d{2})$/i.test(s.start) || !Number.isFinite(Date.parse(s.start))) throw new Error(`Intervall ${i + 1}: „start“ braucht einen gültigen ISO-Zeitstempel mit Zeitzone.`);
      for (const key of required) if (typeof s[key] !== "number" || !Number.isFinite(s[key])) throw new Error(`Intervall ${i + 1}: „${key}“ muss eine endliche Zahl sein.`);
      if (s.duration_hours <= 0 || s.duration_hours > 24) throw new Error(`Intervall ${i + 1}: ungültige Dauer.`);
      if (s.soc_pct < -1e-6 || s.soc_pct > 100.000001 || s.pv_kw < 0 || s.load_kw < 0) throw new Error(`Intervall ${i + 1}: ungültige Erzeugung, Last oder SOC.`);
      const startMs = Date.parse(s.start);
      if (previousEnd !== null && Math.abs(startMs - previousEnd) > 1000) throw new Error(`Intervall ${i + 1}: Der Plan muss zeitlich lückenlos und sortiert sein.`);
      previousEnd = startMs + s.duration_hours * 3600000;
      if (Math.abs(s.grid_power_kw - (s.load_kw + s.battery_power_kw - s.pv_kw)) > 0.02) throw new Error(`Intervall ${i + 1}: Die AC-Leistungsbilanz ist nicht plausibel.`);
      return { ...s, reason: typeof s.reason === "string" ? s.reason : "Keine Begründung übermittelt" };
    });
    for (const key of ["total_cost_eur", "baseline_cost_eur", "savings_eur"]) if (typeof input[key] !== "number" || !Number.isFinite(input[key])) throw new Error(`Der Planwert „${key}“ fehlt oder ist ungültig.`);
    if (Math.abs(input.baseline_cost_eur - input.total_cost_eur - input.savings_eur) > 0.02) throw new Error("Die Einsparung stimmt nicht mit Plan- und Vergleichskosten überein.");
    const sum = slots.reduce((total, slot) => total + slot.cost_eur, 0);
    if (Math.abs(sum - input.total_cost_eur) > 0.02) throw new Error("Die Intervallkosten stimmen nicht mit den Gesamtkosten überein.");
    return { ...input, slots, assumptions: Array.isArray(input.assumptions) ? input.assumptions.filter((s) => typeof s === "string") : [] };
  }

  function createDemo() {
    const slots = [];
    const capacity = 200.704, lower = capacity * 0.1, upper = capacity * 0.9;
    let stored = capacity * 0.5;
    // Fixed illustrative date avoids the false appearance of live price data.
    const base = Date.parse("2026-11-03T00:00:00+01:00");
    for (let i = 0; i < 96; i++) {
      const h = i / 4;
      const pv = h > 7 && h < 17 ? 145 * Math.pow(Math.sin((h - 7) / 10 * Math.PI), 1.8) : 0;
      const load = 13 + 7 * Math.exp(-Math.pow((h - 8) / 1.6, 2)) + 17 * Math.exp(-Math.pow((h - 19) / 2, 2));
      const importPrice = 0.22 + 0.08 * Math.exp(-Math.pow((h - 19) / 2.8, 2)) - 0.11 * Math.exp(-Math.pow((h - 12.5) / 2.6, 2));
      const exportPrice = importPrice - 0.13;
      let battery = 0;
      if (pv > load && h >= 10) battery = Math.min(50, pv - load, (upper - stored) / 0.95 / 0.25);
      else if (h >= 17 || h < 7) battery = -Math.min(35, Math.max(0, load - pv), (stored - lower) * 0.96 / 0.25);
      stored += battery > 0 ? battery * 0.25 * 0.95 : battery * 0.25 / 0.96;
      const grid = load + battery - pv;
      slots.push({ start: new Date(base + i * 900000).toISOString(), duration_hours: 0.25, pv_kw: pv, load_kw: load,
        import_price_eur_kwh: importPrice, export_price_eur_kwh: exportPrice, battery_power_kw: battery,
        soc_pct: stored / capacity * 100, grid_power_kw: grid, cost_eur: grid * 0.25 * (grid >= 0 ? importPrice : exportPrice),
        reason: battery > 0.01 ? "Illustration: PV-Überschuss aufnehmen" : battery < -0.01 ? "Illustration: Hausverbrauch decken" : "Illustration: Batterie in Bereitschaft" });
    }
    return { slots, assumptions: ["Alle Werte einschließlich der Preise sind synthetische Beispieldaten.", "Die Beispielkurve folgt einer einfachen festen Regel, nicht dem wirtschaftlichen Optimierer.", "Lade-/Entladewirkungsgrade und SOC-Grenzen sind Annahmen. Keine Verbindung zur echten Anlage."] };
  }

  function chartSvg(slots) {
    const w = 900, h = 330, left = 48, right = 54, top = 25, bottom = 37;
    const plotW = w - left - right, plotH = h - top - bottom;
    const minPower = Math.min(-10, ...slots.map((s) => s.battery_power_kw));
    const maxPower = Math.max(50, ...slots.map((s) => Math.max(s.pv_kw, s.load_kw, s.battery_power_kw)));
    const powerStep = Math.max(10, Math.ceil((maxPower - minPower) / 5 / 10) * 10);
    const pMin = Math.floor(minPower / powerStep) * powerStep, pMax = Math.ceil(maxPower / powerStep) * powerStep;
    const prices = slots.map((s) => s.import_price_eur_kwh * 100);
    const cMin = Math.floor(Math.min(...prices, 0) / 5) * 5, cMax = Math.max(cMin + 5, Math.ceil(Math.max(...prices) / 5) * 5);
    const start = Date.parse(slots[0].start), end = Date.parse(slots.at(-1).start) + slots.at(-1).duration_hours * 3600000;
    const x = (s) => left + (Date.parse(s.start) - start) / (end - start) * plotW;
    const y = (v) => top + (pMax - v) / (pMax - pMin) * plotH;
    const cy = (v) => top + (cMax - v) / (cMax - cMin) * plotH;
    const line = (key, ys = y, multiplier = 1) => slots.map((s, i) => `${i ? "L" : "M"}${x(s).toFixed(2)},${ys(s[key] * multiplier).toFixed(2)}`).join(" ");
    let markup = `<svg viewBox="0 0 ${w} ${h}" role="img" aria-labelledby="chart-title chart-description"><title id="chart-title">Energieverlauf des angezeigten Plans</title><desc id="chart-description">PV, Verbrauch und Batterieleistung in Kilowatt sowie Bezugspreis in Cent pro Kilowattstunde. Die vollständigen Werte stehen im Energieplan.</desc><defs><linearGradient id="pv-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#72bea0" stop-opacity=".23"/><stop offset="1" stop-color="#72bea0" stop-opacity=".015"/></linearGradient></defs>`;
    for (let v = pMin; v <= pMax + 0.1; v += powerStep) markup += `<line x1="${left}" y1="${y(v)}" x2="${w - right}" y2="${y(v)}" stroke="${v === 0 ? "#cadbd2" : "#edf1ee"}" ${v === 0 ? "" : 'stroke-dasharray="3 5"'}/><text x="${left - 10}" y="${y(v) + 3}" text-anchor="end" fill="#96a69e" font-size="10">${v}</text>`;
    for (let i = 0; i <= 4; i++) { const v = cMin + (cMax - cMin) * i / 4; markup += `<text x="${w - right + 12}" y="${cy(v) + 3}" fill="#bb9d74" font-size="10">${number(v, 0)}</text>`; }
    for (let i = 0; i < 7; i++) { const t = start + (end - start) * i / 6; markup += `<text x="${left + plotW * i / 6}" y="${h - 12}" fill="#93a49b" font-size="10" text-anchor="middle">${time(t)}</text>`; }
    markup += `<text x="${left}" y="13" fill="#92a69b" font-size="9">kW</text><text x="${w - right}" y="13" fill="#bb9d74" font-size="9" text-anchor="end">ct/kWh</text>`;
    markup += `<path d="${line("pv_kw")} L${x(slots.at(-1))},${y(0)} L${x(slots[0])},${y(0)} Z" fill="url(#pv-fill)"/>`;
    for (const [key, color, ys, mult, dash] of [["pv_kw", "#43a88a", y, 1, ""], ["load_kw", "#385b69", y, 1, ""], ["battery_power_kw", "#7b9bd5", y, 1, ""], ["import_price_eur_kwh", "#d8a253", cy, 100, "5 4"]]) markup += `<path d="${line(key, ys, mult)}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" ${dash ? `stroke-dasharray="${dash}"` : ""}/>`;
    return markup + "</svg>";
  }

  function init() {
    const $ = (id) => document.getElementById(id);
    let plan = createDemo(), imported = false;
    const titleMap = { overview: "Übersicht", plan: "Energieplan", devices: "Geräte & Messung", costs: "Kostenmodell", prices: "Preisquellen", settings: "Einstellungen" };
    const showError = (message) => { $("global-error").textContent = message; $("global-error").hidden = !message; };
    const set = (id, content) => { $(id).textContent = content; };
    function navigate() {
      const requested = location.hash.slice(1), page = Object.hasOwn(titleMap, requested) ? requested : "overview";
      for (const key of Object.keys(titleMap)) $("page-" + key).hidden = key !== page;
      document.querySelectorAll("nav [data-page]").forEach((a) => { a.classList.toggle("active", a.dataset.page === page); if (a.dataset.page === page) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
      set("breadcrumb-page", titleMap[page]);
      document.title = `${titleMap[page]} · Pohl Solutions Energiemanager`;
    }
    function renderPlan() {
      const now = Date.now();
      const current = imported ? plan.slots.find((s) => Date.parse(s.start) <= now && Date.parse(s.start) + s.duration_hours * 3600000 > now) || plan.slots[0] : plan.slots[48];
      set("stat-pv", number(current.pv_kw)); set("stat-soc", number(current.soc_pct, 0)); set("stat-grid", number(Math.abs(current.grid_power_kw)));
      $("soc-fill").style.width = Math.min(100, Math.max(0, current.soc_pct)) + "%";
      set("stat-grid-direction", `${imported ? "Plan" : "Demo"}: ${current.grid_power_kw >= 0 ? "Netzbezug" : "Einspeisung"} · ${time(current.start)}`);
      set("stat-savings", imported ? number(plan.savings_eur, 2) : "—");
      set("savings-caption", imported ? "Gegen den im Plan definierten Vergleich" : "Erst nach Import eines berechneten Plans");
      set("source-badge", imported ? "IMPORTIERTER PLAN" : "DEMODATEN"); $("source-badge").classList.toggle("imported", imported);
      set("chart-date", date(plan.slots[0].start));
      set("data-notice", imported ? `Importierter Fahrplan vom ${date(plan.slots[0].start)}. Die Anzeige enthält Planwerte, keine Live-Messungen. Es werden keine Geräte gesteuert.` : "Ansicht mit Beispieldaten. Die Kurven veranschaulichen die Bedienung; sie sind keine Preisprognose und kein optimierter Fahrplan.");
      set("plan-notice", imported ? `${plan.slots.length} Intervalle importiert · Plankosten ${euro(plan.total_cost_eur)} · Vergleichskosten ${euro(plan.baseline_cost_eur)}. Angaben und Annahmen des Planers beachten.` : "Der Beispielverlauf ist nicht optimiert. Importieren Sie eine JSON-Datei aus dem Python-Planer für einen berechneten Fahrplan.");
      set("decision-tag", imported ? `PLANINTERVALL ${time(current.start)}` : "ILLUSTRATION");
      set("decision-title", imported ? current.battery_power_kw > 0.01 ? "Batterie laden" : current.battery_power_kw < -0.01 ? "Batterie entladen" : "Energie zurückhalten" : "Überschuss gezielt speichern");
      set("decision-text", imported ? current.reason : "Der spätere Planer wägt Einspeiseerlös, vermiedenen Netzbezug, Verluste und Verschleiß gegeneinander ab.");
      set("decision-source", imported ? "JSON-Fahrplan" : "Beispielverlauf");
      $("energy-chart").innerHTML = chartSvg(plan.slots);
      $("plan-assumptions").replaceChildren(...(plan.assumptions.length ? plan.assumptions : ["Keine Annahmen übermittelt. Für die Bewertung die Quelle des Plans prüfen."]).map((text) => { const li = document.createElement("li"); li.textContent = text; return li; }));
      $("plan-table").replaceChildren(...plan.slots.map((s) => {
        const row = document.createElement("tr");
        const values = [time(s.start), `${number(s.pv_kw)} kW`, `${number(s.load_kw)} kW`, `${s.battery_power_kw > 0 ? "+" : ""}${number(s.battery_power_kw)} kW`, `${number(s.soc_pct)} %`, `${number(s.grid_power_kw)} kW`, `${number(s.import_price_eur_kwh * 100, 2)} / ${number(s.export_price_eur_kwh * 100, 2)} ct`, s.reason];
        values.forEach((v, i) => { const cell = document.createElement("td"); cell.textContent = v; if (i === 3) cell.className = s.battery_power_kw > 0 ? "charge-text" : "discharge-text"; row.appendChild(cell); }); return row;
      }));
    }
    function renderDevices() {
      const devices = [
        ["☀", "PV-Wechselrichter", "Sungrow SG125CX-P2", "125 kW AC-Nennleistung", "Vorgesehen: RS485 → Plexlog"],
        ["☀", "PV-Wechselrichter", "Sungrow SG50CX(-P2)", "50 kW · genaue Variante offen", "Vorgesehen: RS485 → Plexlog"],
        ["☀", "Hybrid ohne Batterie", "Sungrow SH20T / SH25T", "20 + 25 kW · derzeit PV-Erzeugung", "Vorgesehen: WiNet-S2 / Modbus TCP"],
        ["▥", "Batteriespeicher", "Solis / Bluesun BSE", "50 kW · 2 × 100,352 kWh nominal", "Vorgesehen: eigener Kommunikationsanschluss"],
        ["⇄", "Gesamtnetzmessung", "Eastron", "Vor den gemeinsamen Abgängen", "Vorgesehen: RS485 → Solis METER"],
        ["▤", "Kontrollmessung & Logger", "Janitza / Plexlog PL500+", "Netz, Haus und PV-/Technikabgang", "Messgrenzen und Bus-Master prüfen"]
      ];
      $("device-list").replaceChildren(...devices.map(([icon, kind, name, description, meta]) => { const article = document.createElement("article"); article.className = "panel device-card"; for (const [tag, text, cls] of [["span", icon, "stat-icon teal"], ["p", kind, "device-kind"], ["h2", name, ""], ["p", description, ""], ["span", "Nicht verbunden", "not-connected"], ["div", meta, "device-meta"]]) { const el = document.createElement(tag); el.textContent = text; el.className = cls; article.appendChild(el); } return article; }));
    }
    function setupPriceSources() {
      const container = $("price-source-cards"), priceForm = $("price-form");
      const fieldNames = ["price_mode", "price_entity", "price_url", "price_unit", "fixed_price", "price_multiplier", "price_adder_eur_kwh"];
      for (const prefix of ["import", "export"]) {
        const card = document.createElement("article"); card.className = "panel form-panel price-source-card";
        const title = prefix === "import" ? "Strombezug" : "Einspeiseerlös";
        // Only fixed application strings are inserted as HTML; imported/user data uses values or textContent.
        card.innerHTML = `<div class="price-card-title"><span class="stat-icon ${prefix === "import" ? "blue" : "teal"}">${prefix === "import" ? "↙" : "↗"}</span><div><p class="eyebrow">${prefix === "import" ? "IMPORT" : "EXPORT"}</p><h2>${title}</h2></div></div><div class="form-grid">
          <label class="full-width">Preisquelle<select name="${prefix}_price_mode">${Object.entries(PRICE_MODES).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}</select></label>
          <label class="full-width" data-field="entity" hidden>HA-Entität mit Preiszeitreihe<input name="${prefix}_price_entity" type="text" placeholder="sensor.strompreis_prognose" autocomplete="off" spellcheck="false"><small>Entitäts-ID aus Ihrer Home-Assistant-Instanz. Hier findet keine Verbindung statt.</small></label>
          <label class="full-width" data-field="url" hidden>JSON-API-URL (kein Webseitenlink)<input name="${prefix}_price_url" type="url" placeholder="https://anbieter.example/api/preise" autocomplete="off" spellcheck="false"><small>Die HA-Integration benötigt maschinenlesbare Zeitintervalle; eine normale Tarif-Webseite genügt nicht. Diese Vorschau lädt die URL nicht.</small></label>
          <label data-field="fixed" hidden>Fester Quellenpreis<input name="${prefix}_fixed_price" type="number" step="any" value="0"><small>In der gewählten Quellen-Einheit.</small></label>
          <label>Quellen-Einheit<select name="${prefix}_price_unit">${Object.entries(PRICE_UNITS).map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}</select></label>
          <label>Vertragsfaktor<input name="${prefix}_price_multiplier" type="number" min="0" step="any" value="1"><small>1 = unverändert · 1,19 = × 1,19</small></label>
          <label>Zuschlag / Abschlag (€/kWh)<input name="${prefix}_price_adder_eur_kwh" type="number" step="any" value="0"><small>Zum Beispiel 0,02 = +2 ct/kWh.</small></label>
        </div><p class="price-source-help"></p><div class="price-source-summary"></div>`;
        container.appendChild(card);
      }
      const control = (prefix, suffix) => priceForm.elements.namedItem(`${prefix}_${suffix}`);
      function collect() { return Object.fromEntries(["import", "export"].flatMap((p) => fieldNames.map((s) => [`${p}_${s}`, control(p, s).value]))); }
      function showModes() {
        for (const [i, prefix] of ["import", "export"].entries()) {
          const card = container.children[i], mode = control(prefix, "price_mode").value;
          for (const field of ["url", "entity", "fixed"]) {
            card.querySelector(`[data-field="${field}"]`).hidden = mode !== field;
            const input = control(prefix, field === "fixed" ? "fixed_price" : `price_${field}`);
            input.required = mode === field;
          }
          const unit = control(prefix, "price_unit");
          if (mode === "smard") unit.value = "eur_mwh";
          if (mode === "forecast") unit.value = "eur_kwh";
          unit.disabled = mode === "smard" || mode === "forecast";
          const explanations = { forecast: "Die Preiswerte kommen aus den bereits vorhandenen Prognoseintervallen in €/kWh. Vertragsfaktor und Zuschlag können zusätzlich angewendet werden.", entity: "Die HA-Integration liest eine passende Preiszeitreihe aus der gewählten Entität. Ein einzelner aktueller Preis ersetzt keine vollständige Tagesprognose.", url: "Die HA-Integration ruft die JSON-API ab und verarbeitet deren Preiszeitreihe. Die Quellen-Einheit muss zu den tatsächlich gelieferten Werten passen.", fixed: "Ein konstanter Tarif wird für die vorhandenen Planungsintervalle verwendet. Auch negative Preise sind als ausdrückliche Annahme möglich.", smard: "SMARD liefert Viertelstunden-Großhandelspreise für Deutschland/Luxemburg in €/MWh. Die HA-Integration übernimmt den Abruf; Aufschläge und Vermarktungskonditionen ergänzen Sie hier." };
          card.querySelector(".price-source-help").textContent = explanations[mode] || "Bitte eine Quelle wählen.";
          let summary = "Konfiguration prüfen.";
          try {
            const source = Number(control(prefix, "fixed_price").value), multiplier = Number(control(prefix, "price_multiplier").value), adder = Number(control(prefix, "price_adder_eur_kwh").value);
            if (mode === "fixed") summary = `Resultierender Tarif: ${number(transformPrice(source, unit.value, multiplier, adder) * 100, 3)} ct/kWh.`;
            else if (Number.isFinite(multiplier) && Number.isFinite(adder)) summary = `Nach Einheitenumrechnung: Quellenpreis × ${number(multiplier, 3)} ${adder < 0 ? "−" : "+"} ${number(Math.abs(adder) * 100, 3)} ct/kWh.`;
          } catch { /* Keep neutral summary until validation. */ }
          card.querySelector(".price-source-summary").textContent = summary;
        }
      }
      function showPriceError(message) { $("price-error").textContent = message; $("price-error").hidden = !message; }
      function changed() { showModes(); set("price-status", "Änderungen noch nicht gespeichert. Ein importierter Plan bleibt unverändert."); }
      let initial = { ...PRICE_DEFAULTS };
      try { const saved = JSON.parse(localStorage.getItem("pohl-energy-preview-prices-v1") || "null"); if (saved) { initial = validatePriceConfig(saved); set("price-status", "Lokale Quellenkonfiguration geladen. Keine Preise abgerufen."); } } catch { showPriceError("Gespeicherte Preisquellen waren ungültig. Die Standardauswahl wird angezeigt."); }
      for (const [key, value] of Object.entries(initial)) priceForm.elements.namedItem(key).value = value;
      showModes();
      priceForm.addEventListener("change", changed); priceForm.addEventListener("input", changed);
      priceForm.addEventListener("submit", (event) => {
        event.preventDefault();
        try { const config = validatePriceConfig(collect()); localStorage.setItem("pohl-energy-preview-prices-v1", JSON.stringify(config)); showPriceError(""); set("price-status", "Lokal gespeichert. Keine HA-Verbindung, kein Preisabruf und keine Planänderung."); }
        catch (error) { showPriceError(error.message); }
      });
      $("export-prices").addEventListener("click", () => {
        try {
          const config = validatePriceConfig(collect());
          const url = URL.createObjectURL(new Blob([JSON.stringify(config, null, 2) + "\n"], { type: "application/json" }));
          const a = document.createElement("a"); a.href = url; a.download = "pohl-preisquellen-ha-einstellungen.json"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
          showPriceError(""); set("price-status", "HA-Einstellungswerte exportiert. Übernahme in HA separat vornehmen; bestehender Plan unverändert.");
        } catch (error) { showPriceError(error.message); }
      });
    }
    const form = $("cost-form");
    function applySettings(settings) { for (const [key, value] of Object.entries(settings)) if (form.elements.namedItem(key)) form.elements.namedItem(key).value = value; }
    function updateCosts() {
      const raw = Object.fromEntries(new FormData(form).entries());
      try {
        const c = lifecycleCost(raw);
        $("cost-error").hidden = true;
        set("cost-unit", number(c.fullCostCtKwh, 2)); set("cost-window", number(c.window * 100, 0) + " %");
        set("cost-usable", number(c.usableKwh) + " kWh"); set("cost-cycles", number(c.lifetimeCycles, 0));
        set("cost-throughput", number(c.lifetimeOutputKwh, 0) + " kWh"); set("cost-limit", c.limitingFactor);
        set("cost-efficiency", number(c.roundTripEfficiency * 100) + " %");
        set("wear-result", c.marginalWearCtKwh > 0 ? `Separater Verschleißansatz: ${number(c.marginalWearCtKwh, 2)} ct/kWh AC-Ausgabe. Dieser Wert wird nicht zu den Investitionsvollkosten addiert.` : "Zusätzlicher Verschleiß aktuell nicht bewertet (0 ct/kWh). Das bedeutet nicht, dass real kein Verschleiß entsteht.");
        try { localStorage.setItem("pohl-energy-preview-costs-v1", JSON.stringify(raw)); } catch { /* Storage may be unavailable for local files. */ }
      } catch (error) {
        $("cost-error").textContent = error.message; $("cost-error").hidden = false;
        for (const id of ["cost-unit", "cost-window", "cost-usable", "cost-cycles", "cost-throughput", "cost-limit", "cost-efficiency"]) set(id, "—");
        set("wear-result", "Bitte die Eingaben korrigieren.");
      }
    }
    let settings = { ...DEFAULTS };
    try { const saved = JSON.parse(localStorage.getItem("pohl-energy-preview-costs-v1") || "null"); if (saved && typeof saved === "object") settings = { ...settings, ...saved }; } catch { /* Keep transparent defaults. */ }
    applySettings(settings); updateCosts();
    form.addEventListener("input", updateCosts); form.addEventListener("change", updateCosts); form.addEventListener("submit", (event) => event.preventDefault());
    $("reset-settings").addEventListener("click", () => { applySettings(DEFAULTS); updateCosts(); });
    document.querySelectorAll('[data-action="import"]').forEach((button) => button.addEventListener("click", () => $("plan-file").click()));
    document.querySelectorAll('[data-action="demo"]').forEach((button) => button.addEventListener("click", () => { plan = createDemo(); imported = false; showError(""); renderPlan(); }));
    $("plan-file").addEventListener("change", async (event) => {
      const file = event.target.files[0]; if (!file) return;
      try { if (file.size > 3000000) throw new Error("Die JSON-Datei ist größer als 3 MB."); const nextPlan = validatePlan(JSON.parse(await file.text())); plan = nextPlan; imported = true; showError(""); renderPlan(); }
      catch (error) { showError(`Plan nicht geladen: ${error.message}`); }
      finally { event.target.value = ""; }
    });
    $("export-csv").addEventListener("click", () => {
      const header = ["Start ISO", "Dauer h", "PV kW", "Last kW", "Batterie kW (+Laden)", "SOC Ende %", "Netz kW (+Bezug)", "Bezug EUR/kWh", "Einspeisung EUR/kWh", "Kosten EUR", "Begründung"];
      const safeCell = (v) => { let text = String(v); if (/^[=+@\-]/.test(text) && typeof v !== "number") text = "'" + text; return '"' + text.replaceAll('"', '""') + '"'; };
      const rows = [header, ...plan.slots.map((s) => [s.start, s.duration_hours, s.pv_kw, s.load_kw, s.battery_power_kw, s.soc_pct, s.grid_power_kw, s.import_price_eur_kwh, s.export_price_eur_kwh, s.cost_eur, s.reason])];
      const url = URL.createObjectURL(new Blob(["\uFEFF" + rows.map((row) => row.map(safeCell).join(";")).join("\r\n")], { type: "text/csv;charset=utf-8" }));
      const a = document.createElement("a"); a.href = url; a.download = imported ? "pohl-energieplan.csv" : "pohl-demodaten-nicht-optimiert.csv"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    window.addEventListener("hashchange", navigate);
    renderPlan(); renderDevices(); setupPriceSources(); navigate();
  }
  return { DEFAULTS, PRICE_DEFAULTS, PRICE_MODES, PRICE_UNITS, lifecycleCost, validatePlan, validatePriceConfig, transformPrice, createDemo, chartSvg, init };
})();

if (typeof module !== "undefined" && module.exports) module.exports = PohlPreview;
if (typeof document !== "undefined") PohlPreview.init();
