/* Offline project format 1. No network, device commands or optimization. */
(function (root) {
  'use strict';
  const LIMIT = 2 * 1024 * 1024;
  const collections = ['grids', 'areas', 'nodes', 'connections', 'devices', 'channels', 'measurements'];
  const forbidden = new Set(['password', 'passwd', 'token', 'access_token', 'refresh_token', 'api_key', 'secret', 'credentials', 'enabled_control', 'actuator_enabled']);
  const idPattern = /^[a-zA-Z0-9_-]{1,80}$/;
  const kinds = ['gateway', 'meter', 'pv_inverter', 'hybrid_inverter', 'storage_inverter', 'battery', 'ev_charger', 'heater'];
  const connectionKinds = ['modbus_tcp', 'modbus_rtu_usb', 'modbus_tcp_rtu_gateway', 'rtu_over_tcp', 'mqtt', 'solarman', 'ha'];
  const units = {active_power: ['W', 'kW'], soc: ['%'], voltage: ['V'], current: ['A'], energy: ['Wh', 'kWh'], temperature: ['°C'], state: ['bool']};
  const fail = (path, message) => { throw new Error(`${path}: ${message}`); };
  const object = (v, p) => { if (!v || typeof v !== 'object' || Array.isArray(v)) fail(p, 'Objekt erwartet'); };
  const text = (v, p, max = 160) => { if (typeof v !== 'string' || !v.trim() || [...v].length > max) fail(p, `nichtleerer Text bis ${max} Zeichen erwartet`); };
  const number = (v, p, min, max) => { if (typeof v !== 'number' || !Number.isFinite(v) || v < min || v > max) fail(p, 'Zahl außerhalb des erlaubten Bereichs'); };
  function shape(v, p, required, optional = []) {
    object(v, p);
    for (const k of required) if (!Object.hasOwn(v, k)) fail(`${p}.${k}`, 'Pflichtfeld fehlt');
    for (const k of Object.keys(v)) if (![...required, ...optional].includes(k)) fail(`${p}.${k}`, 'unbekanntes Feld');
  }
  function choose(v, p, values) { if (!values.includes(v)) fail(p, `erlaubt: ${values.join(', ')}`); }
  function safeWalk(v, p = '$', depth = 0) {
    if (depth > 24) fail(p, 'JSON zu tief verschachtelt');
    if (typeof v === 'number' && !Number.isFinite(v)) fail(p, 'endliche Zahl erwartet');
    if (v === null || ['string', 'boolean', 'number'].includes(typeof v)) return;
    if (typeof v !== 'object') fail(p, 'nur JSON-Werte erlaubt');
    if (!Array.isArray(v) && ![Object.prototype, null].includes(Object.getPrototypeOf(v))) fail(p, 'einfaches JSON-Objekt erwartet');
    for (const k of Object.keys(v)) {
      if (forbidden.has(k.toLowerCase())) fail(`${p}.${k}`, 'Zugangsdaten und Steuerfreigaben sind nicht erlaubt');
      safeWalk(v[k], `${p}.${k}`, depth + 1);
    }
  }
  function validateProject(data) { return validateProjectV1(data); }
  function validateProjectV1(data, requireGridMeasurement = true) {
    safeWalk(data);
    if (new TextEncoder().encode(JSON.stringify(data)).length > LIMIT) fail('$', 'Projekt darf höchstens 2 MiB groß sein');
    shape(data, '$', ['format', 'schema_version', 'id', 'name', 'mode', ...collections, 'settings']);
    if (data.format !== 'pohl-energy-project' || data.schema_version !== 1 || data.mode !== 'planning_only') fail('$', 'unbekanntes Format, Version oder Modus');
    if (!idPattern.test(data.id) || typeof data.id !== 'string') fail('$.id', 'ungültige Kennung');
    text(data.name, '$.name'); object(data.settings, '$.settings');
    const maps = {}; let total = 0;
    for (const c of collections) {
      if (!Array.isArray(data[c]) || data[c].length > 500) fail(`$.${c}`, 'Liste mit höchstens 500 Einträgen erwartet');
      total += data[c].length; maps[c] = new Map();
      data[c].forEach((v, i) => {
        const p = `$.${c}[${i}]`; object(v, p);
        if (typeof v.id !== 'string' || !idPattern.test(v.id)) fail(`${p}.id`, 'ungültige Kennung');
        if (maps[c].has(v.id)) fail(`${p}.id`, 'doppelte Kennung');
        text(v.name, `${p}.name`); maps[c].set(v.id, v);
      });
    }
    if (total > 2000) fail('$', 'höchstens 2000 Objekte erlaubt');
    const ref = (c, id, p) => { if (typeof id !== 'string' || !maps[c].has(id)) fail(p, `unbekannter Verweis auf ${c}`); return maps[c].get(id); };
    const rows = (c, fn) => data[c].forEach((v, i) => fn(v, `$.${c}[${i}]`));
    rows('grids', (v, p) => shape(v, p, ['id', 'name']));
    rows('areas', (v, p) => { shape(v, p, ['id', 'name', 'grid_id']); ref('grids', v.grid_id, `${p}.grid_id`); });
    rows('nodes', (v, p) => {
      shape(v, p, ['id', 'name', 'grid_id', 'parent_id']); ref('grids', v.grid_id, `${p}.grid_id`);
      if (v.parent_id !== null && ref('nodes', v.parent_id, `${p}.parent_id`).grid_id !== v.grid_id) fail(p, 'Elternknoten liegt an anderem Netzanschluss');
      let at = v; const seen = new Set();
      while (at) { if (seen.has(at.id)) fail(p, 'Kreis im elektrischen Baum'); seen.add(at.id); at = at.parent_id === null ? null : ref('nodes', at.parent_id, p); }
    });
    for (const grid of data.grids) if (data.nodes.filter(n => n.grid_id === grid.id && n.parent_id === null).length !== 1) fail('$.nodes', `Netz ${grid.id} benötigt genau eine Wurzel`);
    rows('connections', (v, p) => {
      shape(v, p, ['id', 'name', 'kind'], ['host', 'port', 'serial_port', 'baudrate', 'parity', 'stopbits']); choose(v.kind, `${p}.kind`, connectionKinds);
      for (const k of ['host', 'serial_port']) if (v[k] != null) text(v[k], `${p}.${k}`, 512);
      for (const [k, low, high] of [['port', 1, 65535], ['baudrate', 1, Number.MAX_VALUE]]) if (v[k] != null) { number(v[k], `${p}.${k}`, low, high); if (!Number.isInteger(v[k])) fail(p, 'Ganzzahl erwartet'); }
      if (v.parity != null) choose(v.parity, `${p}.parity`, ['N', 'E', 'O']);
      if (v.stopbits != null) choose(v.stopbits, `${p}.stopbits`, [1, 2]);
    });
    rows('devices', (v, p) => {
      shape(v, p, ['id', 'name', 'kind', 'area_id', 'node_id'], ['connection_id', 'via_device_id', 'unit_id', 'parent_id', 'model', 'phases', 'capacity_kwh', 'max_power_kw', 'capabilities']);
      choose(v.kind, `${p}.kind`, kinds); const area = ref('areas', v.area_id, `${p}.area_id`), node = ref('nodes', v.node_id, `${p}.node_id`);
      if (area.grid_id !== node.grid_id) fail(p, 'Bereich und Knoten gehören zu unterschiedlichen Netzanschlüssen');
      if (v.connection_id != null) ref('connections', v.connection_id, `${p}.connection_id`);
      if (v.model != null) text(v.model, `${p}.model`);
      if (v.phases != null) choose(v.phases, `${p}.phases`, [1, 3]);
      if (v.unit_id != null) { number(v.unit_id, `${p}.unit_id`, 1, 247); if (!Number.isInteger(v.unit_id)) fail(p, 'Unit-ID muss ganzzahlig sein'); }
      for (const k of ['capacity_kwh', 'max_power_kw']) if (v[k] != null) { number(v[k], `${p}.${k}`, Number.MIN_VALUE, Number.MAX_VALUE); }
      if (v.capabilities != null) {
        if (!Array.isArray(v.capabilities) || new Set(v.capabilities).size !== v.capabilities.length) fail(`${p}.capabilities`, 'Liste eindeutiger Fähigkeiten erwartet');
        v.capabilities.forEach(c => choose(c, `${p}.capabilities`, ['measure', 'switch', 'set_power']));
      }
      if (v.kind === 'battery') {
        const parent = ref('devices', v.parent_id, `${p}.parent_id`);
        if (!['hybrid_inverter', 'storage_inverter'].includes(parent.kind) || ref('nodes', parent.node_id, p).grid_id !== node.grid_id) fail(p, 'Batterie benötigt zugehörigen Speicher-/Hybrid-WR am selben Netz');
      } else if (v.parent_id != null) fail(`${p}.parent_id`, 'Elternbeziehung nur für Batterien erlaubt');
      let at = v; const seen = new Set();
      while (at) {
        if (seen.has(at.id)) fail(p, 'Kreis im Kommunikationsweg'); seen.add(at.id);
        if (at.via_device_id == null) break;
        const via = ref('devices', at.via_device_id, `${p}.via_device_id`);
        if (!['gateway', 'pv_inverter', 'hybrid_inverter', 'storage_inverter'].includes(via.kind)) fail(p, 'Kommunikationsweg benötigt Gateway oder WR');
        if (at.connection_id != null && via.connection_id != null && at.connection_id !== via.connection_id) fail(p, 'Gateway und Gerät verwenden unterschiedliche Verbindungen');
        at = via;
      }
    });
    rows('channels', (v, p) => {
      shape(v, p, ['id', 'name', 'device_id', 'quantity', 'unit', 'source'], ['phase']); ref('devices', v.device_id, `${p}.device_id`);
      if (!Object.hasOwn(units, v.quantity)) fail(`${p}.quantity`, 'unbekannte Messgröße'); choose(v.unit, `${p}.unit`, units[v.quantity]);
      if (v.phase != null) choose(v.phase, `${p}.phase`, ['L1', 'L2', 'L3', 'total']);
      const s = v.source; shape(s, `${p}.source`, ['kind'], ['address', 'function_code', 'data_type', 'scale', 'topic', 'json_path', 'entity_id']);
      choose(s.kind, `${p}.source.kind`, ['unconfigured', 'modbus', 'mqtt', 'ha']);
      const allowed = {unconfigured: [], modbus: ['address', 'function_code', 'data_type', 'scale'], mqtt: ['topic', 'json_path'], ha: ['entity_id']}[s.kind];
      for (const k of Object.keys(s)) if (k !== 'kind' && s[k] != null && !allowed.includes(k)) fail(`${p}.source.${k}`, 'Feld passt nicht zur Quellenart');
      if (s.kind === 'modbus') {
        number(s.address, `${p}.source.address`, 0, 65535); if (!Number.isInteger(s.address)) fail(p, 'Registeradresse muss ganzzahlig sein');
        choose(s.function_code, `${p}.source.function_code`, [3, 4]); choose(s.data_type, `${p}.source.data_type`, ['u16', 's16', 'u32', 's32', 'float32']);
        if (s.scale != null) { number(s.scale, `${p}.source.scale`, -Number.MAX_VALUE, Number.MAX_VALUE); if (s.scale === 0) fail(p, 'Skalierung darf nicht null sein'); }
      }
      if (s.kind === 'mqtt') { text(s.topic, `${p}.source.topic`, 512); if (s.json_path != null) text(s.json_path, `${p}.source.json_path`, 512); }
      if (s.kind === 'ha') text(s.entity_id, `${p}.source.entity_id`, 512);
    });
    const usedChannels = new Set(), usedRoles = new Set();
    rows('measurements', (v, p) => {
      shape(v, p, ['id', 'name', 'role', 'node_id', 'channel_id', 'includes_device_ids']);
      choose(v.role, `${p}.role`, ['grid', 'branch', 'pv_generation', 'battery_power', 'consumer', 'load']);
      const node = ref('nodes', v.node_id, `${p}.node_id`), channel = ref('channels', v.channel_id, `${p}.channel_id`);
      if (channel.quantity !== 'active_power') fail(p, 'Bilanzmessung benötigt Wirkleistung');
      if (ref('nodes', ref('devices', channel.device_id, p).node_id, p).grid_id !== node.grid_id) fail(p, 'Messgerät und Messort gehören zu unterschiedlichen Netzanschlüssen');
      if (usedChannels.has(v.channel_id)) fail(p, 'Kanal bereits als primäre Messung verwendet'); usedChannels.add(v.channel_id);
      const key = `${v.node_id}/${v.role}`; if (usedRoles.has(key)) fail(p, 'Messrolle an diesem Knoten bereits vergeben'); usedRoles.add(key);
      if (v.role === 'grid' && node.parent_id !== null) fail(p, 'Netzmessung muss an der Wurzel liegen');
      if (!Array.isArray(v.includes_device_ids) || new Set(v.includes_device_ids).size !== v.includes_device_ids.length) fail(p, 'Liste eindeutiger enthaltener Geräte erwartet');
      for (const id of v.includes_device_ids) {
        let at = ref('nodes', ref('devices', id, p).node_id, p);
        while (at && at.id !== node.id) at = at.parent_id === null ? null : ref('nodes', at.parent_id, p);
        if (!at) fail(p, 'Enthaltenes Gerät liegt nicht am Messknoten oder einem nachgeordneten Zweig');
      }
    });
    for (const grid of data.grids) if (requireGridMeasurement && data.measurements.filter(m => m.role === 'grid' && maps.nodes.get(m.node_id).grid_id === grid.id).length !== 1) fail('$.measurements', `Netz ${grid.id} benötigt genau eine primäre Netzmessung`);
    return JSON.parse(JSON.stringify(data));
  }
  // Development API only: the deployed UI and import/export remain strict v1.
  function validateProjectV2(data) {
    safeWalk(data);
    if (new TextEncoder().encode(JSON.stringify(data)).length > LIMIT) fail('$', 'Projekt darf höchstens 2 MiB groß sein');
    shape(data, '$', ['format', 'schema_version', 'id', 'name', 'mode', 'plants', ...collections, 'settings']);
    if (data.schema_version !== 2) fail('$', 'Projektformat 2 erwartet');
    if (!Array.isArray(data.plants) || data.plants.length > 500) fail('$.plants', 'höchstens 500 Anlagen erlaubt');
    for (const c of collections) if (!Array.isArray(data[c])) fail(`$.${c}`, 'Liste erwartet');
    if (collections.reduce((sum, c) => sum + data[c].length, data.plants.length) > 2500) fail('$', 'höchstens 2500 Objekte erlaubt');
    const clone = v => JSON.parse(JSON.stringify(v));
    const base = clone(data), plants = new Map();
    delete base.plants; base.schema_version = 1;
    const optionalText = (row, key, limit, path) => {
      if (row[key] != null && (typeof row[key] !== 'string' || [...row[key]].length > limit)) fail(`${path}.${key}`, `Text bis ${limit} Zeichen erwartet`);
    };
    data.plants.forEach((plant, i) => {
      const p = `$.plants[${i}]`;
      shape(plant, p, ['id', 'name', 'grid_ids'], ['description', 'location', 'assignment_confirmed']);
      if (typeof plant.id !== 'string' || !idPattern.test(plant.id) || plants.has(plant.id)) fail(p, 'ungültige oder doppelte Anlagenkennung');
      text(plant.name, `${p}.name`);
      optionalText(plant, 'description', 2048, p); optionalText(plant, 'location', 512, p);
      if (Object.hasOwn(plant, 'assignment_confirmed') && typeof plant.assignment_confirmed !== 'boolean') fail(p, 'Anlagenbestätigung muss boolesch sein');
      plants.set(plant.id, plant);
    });
    base.areas.forEach((area, i) => {
      const p = `$.areas[${i}]`;
      shape(area, p, ['id', 'name', 'grid_id', 'plant_id']);
      if (typeof area.plant_id !== 'string' || !plants.has(area.plant_id)) fail(p, 'unbekannte Anlage');
      delete area.plant_id;
    });
    base.nodes.forEach((node, i) => {
      const p = `$.nodes[${i}]`;
      shape(node, p, ['id', 'name', 'grid_id', 'parent_id'], ['description', 'location', 'fuse_a', 'phases']);
      optionalText(node, 'description', 2048, p); optionalText(node, 'location', 512, p);
      if (node.fuse_a != null) { number(node.fuse_a, `${p}.fuse_a`, 0, Number.MAX_VALUE); if (node.fuse_a === 0) fail(p, 'Absicherung muss positiv sein'); }
      if (node.phases != null) choose(node.phases, `${p}.phases`, [1, 3]);
      for (const key of ['description', 'location', 'fuse_a', 'phases']) delete node[key];
    });
    validateProjectV1(base, false);
    const grids = new Set(data.grids.map(g => g.id)), linked = new Set();
    for (const plant of plants.values()) {
      if (!Array.isArray(plant.grid_ids)) fail('$.plants.grid_ids', 'Liste erwartet');
      const seen = new Set();
      for (const id of plant.grid_ids) {
        if (typeof id !== 'string' || !grids.has(id) || seen.has(id)) fail('$.plants.grid_ids', 'unbekannter oder doppelter Netzanschluss');
        seen.add(id); linked.add(id);
      }
    }
    if (linked.size !== grids.size) fail('$.plants', 'Jeder Netzanschluss benötigt eine Anlage');
    for (const area of data.areas) if (!plants.get(area.plant_id).grid_ids.includes(area.grid_id)) fail('$.areas', 'Bereich und Anlage müssen den Netzanschluss gemeinsam referenzieren');
    return clone(data);
  }
  function migrateProjectV1ToV2(data) {
    const result = validateProject(data);
    result.schema_version = 2; result.plants = [];
    if (collections.some(c => result[c].length)) {
      result.plants = [{id: 'imported_plant', name: 'Importierte Anlage', grid_ids: result.grids.map(g => g.id), assignment_confirmed: false,
        description: 'Organisatorische Zuordnung nach Import bitte prüfen.'}];
      result.areas.forEach(area => { area.plant_id = 'imported_plant'; });
    }
    return validateProjectV2(result);
  }
  function configurationIssuesV2(data) {
    const project = validateProjectV2(data), issues = [];
    for (const plant of project.plants) if (plant.assignment_confirmed === false) issues.push({code: 'plant_assignment_unconfirmed', plant_id: plant.id});
    const nodes = new Map(project.nodes.map(n => [n.id, n]));
    const measured = new Set(project.measurements.filter(m => m.role === 'grid').map(m => nodes.get(m.node_id).grid_id));
    for (const grid of project.grids) if (!measured.has(grid.id)) issues.push({code: 'grid_measurement_missing', grid_id: grid.id});
    const channels = new Map(project.channels.map(c => [c.id, c]));
    for (const m of project.measurements) if (channels.get(m.channel_id).source.kind === 'unconfigured') issues.push({code: 'measurement_source_unconfigured', measurement_id: m.id, channel_id: m.channel_id});
    return issues;
  }
  function loadProjectJson(input) {
    if (typeof input !== 'string' || new TextEncoder().encode(input).length > LIMIT) fail('$', 'JSON-Datei darf höchstens 2 MiB groß sein');
    // Parse independently to reject duplicate keys before JSON.parse could overwrite them.
    let pos = 0; const whitespace = () => { while (/\s/.test(input[pos] || '') && pos < input.length) pos++; };
    function string() {
      const start = pos++; while (pos < input.length) { const ch = input[pos++]; if (ch === '\\') pos++; else if (ch === '"') return JSON.parse(input.slice(start, pos)); }
      fail('$', 'unvollständiger JSON-Text');
    }
    function value(depth) {
      if (depth > 24) fail('$', 'JSON zu tief verschachtelt'); whitespace();
      if (input[pos] === '{') {
        pos++; whitespace(); const keys = new Set(); if (input[pos] === '}') { pos++; return; }
        while (true) {
          whitespace(); if (input[pos] !== '"') fail('$', 'JSON-Schlüssel erwartet'); const key = string();
          if (keys.has(key)) fail('$', `doppelter JSON-Schlüssel: ${key}`); keys.add(key); whitespace(); if (input[pos++] !== ':') fail('$', 'Doppelpunkt erwartet'); value(depth + 1); whitespace();
          const end = input[pos++]; if (end === '}') return; if (end !== ',') fail('$', 'ungültiges JSON-Objekt');
        }
      }
      if (input[pos] === '[') {
        pos++; whitespace(); if (input[pos] === ']') { pos++; return; }
        while (true) { value(depth + 1); whitespace(); const end = input[pos++]; if (end === ']') return; if (end !== ',') fail('$', 'ungültige JSON-Liste'); }
      }
      if (input[pos] === '"') { string(); return; }
      const match = input.slice(pos).match(/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/); if (!match) fail('$', 'ungültiger JSON-Wert'); pos += match[0].length;
    }
    value(0); whitespace(); if (pos !== input.length) fail('$', 'Zeichen nach dem JSON-Dokument');
    return validateProject(JSON.parse(input));
  }
  function exportProjectJson(data) { return JSON.stringify(validateProject(data), null, 2); }
  function sourceChain(data, channelId) {
    const ch = data.channels.find(c => c.id === channelId); if (!ch) return [];
    const result = [ch.name]; let d = data.devices.find(v => v.id === ch.device_id); const seen = new Set();
    while (d && !seen.has(d.id)) { seen.add(d.id); result.push(d.name); if (!d.via_device_id) { const conn = data.connections.find(c => c.id === d.connection_id); if (conn) result.push(conn.name); break; } d = data.devices.find(v => v.id === d.via_device_id); }
    return result;
  }
  function projectSummary(input) {
    const data = validateProject(input); const warnings = [];
    data.connections.forEach(c => {
      const endpoint = c.kind === 'modbus_rtu_usb' ? 'serial_port' : 'host';
      if (c.kind !== 'ha' && !c[endpoint]) warnings.push(`connections.${c.id}.${endpoint}: Verbindung noch nicht eingerichtet`);
    });
    data.channels.filter(c => c.source.kind === 'unconfigured').forEach(c => warnings.push(`channels.${c.id}.source: Messquelle noch nicht eingerichtet`));
    return {id: data.id, name: data.name, mode: data.mode, counts: Object.fromEntries(collections.map(c => [c, data[c].length])), warnings};
  }
  const api = {validateProjectV2, migrateProjectV1ToV2, configurationIssuesV2, validateProject, loadProjectJson, exportProjectJson, projectSummary, sourceChain, MAX_BYTES: LIMIT};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.PohlProjectModel = api;
})(typeof window !== 'undefined' ? window : null);
