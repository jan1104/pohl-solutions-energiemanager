/* Offline project invariants. Run with node --test preview/test-project.cjs. */
const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('./project-model.js');
function fixture() {
  return {format: 'pohl-energy-project', schema_version: 1, id: 'example', name: 'Beispiel', mode: 'planning_only',
    grids: [{id: 'g', name: 'Netz'}], areas: [{id: 'a', name: 'Halle', grid_id: 'g'}, {id: 'b', name: 'Technik', grid_id: 'g'}],
    nodes: [{id: 'root', name: 'Netzanschluss', grid_id: 'g', parent_id: null}, {id: 'pv', name: 'PV-Zweig', grid_id: 'g', parent_id: 'root'}, {id: 'house', name: 'Haus', grid_id: 'g', parent_id: 'root'}],
    connections: [{id: 'lan', name: 'Netzwerk', kind: 'modbus_tcp_rtu_gateway', host: '192.0.2.1', port: 502}],
    devices: [{id: 'gateway', name: 'Gateway', kind: 'gateway', area_id: 'b', node_id: 'root', connection_id: 'lan', capabilities: []},
      {id: 'meter', name: 'Zähler', kind: 'meter', area_id: 'a', node_id: 'root', connection_id: 'lan', via_device_id: 'gateway', unit_id: 2, capabilities: ['measure']},
      {id: 'wr', name: 'WR', kind: 'hybrid_inverter', area_id: 'a', node_id: 'pv', capabilities: []},
      {id: 'battery', name: 'Batterie', kind: 'battery', area_id: 'a', node_id: 'pv', parent_id: 'wr', capacity_kwh: 10, capabilities: []}],
    channels: [{id: 'power', name: 'Netzleistung', device_id: 'meter', quantity: 'active_power', unit: 'kW', source: {kind: 'unconfigured'}}],
    measurements: [{id: 'main', name: 'Gesamtmessung', role: 'grid', node_id: 'root', channel_id: 'power', includes_device_ids: ['wr', 'battery']}], settings: {}};
}
test('validates independent electrical and communications paths without modifying input', () => {
  const input = fixture(), before = JSON.stringify(input), result = M.validateProject(input);
  assert.equal(JSON.stringify(input), before); result.devices[0].name = 'Geändert'; assert.equal(input.devices[0].name, 'Gateway');
  assert.deepEqual(M.sourceChain(input, 'power'), ['Netzleistung', 'Zähler', 'Gateway', 'Netzwerk']);
  assert.equal(M.projectSummary(input).counts.devices, 4);
});
test('export and import preserve all data including unknown settings', () => {
  const input = fixture(); input.settings = {future: {labels: ['öffentlich', 'PV'], flag: false}};
  assert.deepEqual(M.loadProjectJson(M.exportProjectJson(input)), input);
});
test('rejects duplicated JSON keys before they could overwrite a valid field', () => {
  const text = JSON.stringify(fixture()).replace('"mode":"planning_only"', '"mode":"live","mode":"planning_only"');
  assert.throws(() => M.loadProjectJson(text), /doppelter/);
  assert.throws(() => M.loadProjectJson(JSON.stringify(fixture()).replace('"settings":{}', '"settings":{"a":1,"\\u0061":2}')), /doppelter/);
});
test('rejects malformed JSON, excessive depth and oversized input', () => {
  for (const text of ['{} trailing', '{"x":}', '[1,]', '']) assert.throws(() => M.loadProjectJson(text));
  assert.throws(() => M.loadProjectJson('['.repeat(26) + '0' + ']'.repeat(26)), /tief/);
  assert.throws(() => M.loadProjectJson(' '.repeat(M.MAX_BYTES + 1)), /MiB/);
});
test('rejects hidden credentials and actuator flags recursively', () => {
  for (const key of ['password', 'TOKEN', 'credentials', 'enabled_control', 'actuator_enabled']) {
    const p = fixture(); p.settings.nested = {[key]: false}; assert.throws(() => M.validateProject(p), /nicht erlaubt/);
  }
});
test('rejects unsupported version, mode, fields, nonfinite values and duplicate IDs', () => {
  const mutations = [p => {p.schema_version = 2;}, p => {p.mode = 'live';}, p => {p.devices[0].surprise = true;}, p => {p.devices[3].capacity_kwh = NaN;}, p => {p.nodes.push({...p.nodes[0]});}];
  for (const mutate of mutations) { const p = fixture(); mutate(p); assert.throws(() => M.validateProject(p)); }
});
test('rejects electrical cycles, extra roots and cross-grid area assignment', () => {
  const mutations = [p => {p.nodes[0].parent_id = 'pv';}, p => {p.nodes[1].parent_id = null;}, p => {p.grids.push({id: 'other', name: 'Andere Halle'}); p.areas[0].grid_id = 'other';}];
  for (const mutate of mutations) { const p = fixture(); mutate(p); assert.throws(() => M.validateProject(p)); }
});
test('battery must belong to a storage-capable WR on the same grid', () => {
  const p = fixture(); p.devices[3].parent_id = 'meter'; assert.throws(() => M.validateProject(p), /WR/);
  p.devices[3].parent_id = 'wr'; p.devices[2].kind = 'pv_inverter'; assert.throws(() => M.validateProject(p), /WR/);
});
test('communication route may cross areas but not cycle or switch connections', () => {
  const p = fixture(); assert.doesNotThrow(() => M.validateProject(p));
  p.devices[0].via_device_id = 'gateway'; assert.throws(() => M.validateProject(p), /Kreis/); delete p.devices[0].via_device_id;
  p.connections.push({id: 'other', name: 'Andere Verbindung', kind: 'ha'}); p.devices[0].connection_id = 'other'; assert.throws(() => M.validateProject(p), /unterschiedliche/);
});
test('source mappings restrict Modbus to read functions and preserve fractional scaling', () => {
  const p = fixture(); p.channels[0].source = {kind: 'modbus', address: 0, function_code: 3, data_type: 'float32', scale: -0.001}; assert.doesNotThrow(() => M.validateProject(p));
  p.channels[0].source.function_code = 6; assert.throws(() => M.validateProject(p)); p.channels[0].source.function_code = 3;
  p.channels[0].source.scale = 0; assert.throws(() => M.validateProject(p));
});
test('prevents duplicate primary source and sibling-branch inclusion', () => {
  const p = fixture(); p.measurements.push({...p.measurements[0], id: 'double', role: 'branch'}); assert.throws(() => M.validateProject(p), /bereits/);
  p.measurements.pop(); p.channels.push({...p.channels[0], id: 'second'});
  p.measurements.push({id: 'branch', name: 'Hauszweig', role: 'branch', node_id: 'house', channel_id: 'second', includes_device_ids: ['wr']});
  assert.throws(() => M.validateProject(p), /nachgeordneten/);
});
test('a measurement source at a different grid is rejected', () => {
  const p = fixture(); p.grids.push({id: 'g2', name: 'Netz2'}); p.areas.push({id: 'a2', name: 'Halle2', grid_id: 'g2'}); p.nodes.push({id: 'n2', name: 'Netz2', grid_id: 'g2', parent_id: null});
  p.devices.push({id: 'm2', name: 'Zähler2', kind: 'meter', area_id: 'a2', node_id: 'n2'}); p.channels[0].device_id = 'm2';
  assert.throws(() => M.validateProject(p), /unterschiedlichen Netz/);
});
test('warnings identify draft connections and unconfigured channels', () => {
  const p = fixture(); delete p.connections[0].host; const warnings = M.projectSummary(p).warnings;
  assert.ok(warnings.some(w => w.includes('connections.lan.host'))); assert.ok(warnings.some(w => w.includes('Messquelle')));
});
module.exports.fixture = fixture;


test('staged v2 API does not activate legacy UI imports or share draft objects', () => {
  const original = fixture(), before = JSON.stringify(original);
  const migrated = M.migrateProjectV1ToV2(original);
  assert.equal(JSON.stringify(original), before);
  assert.throws(() => M.loadProjectJson(JSON.stringify(migrated)), /unbekanntes Feld/);
  assert.throws(() => M.exportProjectJson(migrated), /unbekanntes Feld/);
  migrated.measurements = [];
  assert.equal(M.validateProjectV2(migrated).measurements.length, 0);
  assert.deepEqual(M.configurationIssuesV2(migrated), [
    {code: 'plant_assignment_unconfirmed', plant_id: 'imported_plant'},
    {code: 'grid_measurement_missing', grid_id: 'g'}
  ]);
  const copy = M.validateProjectV2(migrated);
  copy.plants[0].grid_ids.length = 0;
  assert.deepEqual(migrated.plants[0].grid_ids, ['g']);
});
test('staged v2 API rejects non-JSON values and oversized objects before cloning', () => {
  for (const value of [NaN, Infinity, undefined, () => 1, new Date()]) {
    const p = M.migrateProjectV1ToV2(fixture());
    p.settings.invalid = value;
    assert.throws(() => M.validateProjectV2(p));
  }
  const oversized = M.migrateProjectV1ToV2(fixture());
  oversized.settings.padding = 'x'.repeat(M.MAX_BYTES);
  assert.throws(() => M.validateProjectV2(oversized), /MiB/);
});
