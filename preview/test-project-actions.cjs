'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const model = require('./project-model.js');
const actions = require('./project-actions.js');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function empty() {
  return {format: 'pohl-energy-project', schema_version: 1, id: 'empty_project', name: 'Neues Projekt', mode: 'planning_only', grids: [], areas: [], nodes: [], connections: [], devices: [], channels: [], measurements: [], settings: {}};
}

function grid(project = empty(), name = 'Halle 1') { return actions.addGrid(project, {name}); }

test('user builds empty project, grid, area, connection, hybrid and battery without fake measurements', () => {
  const original = empty();
  let project = grid(original);
  assert.deepEqual(original, empty());
  assert.equal(project.grids.length, 1);
  assert.equal(project.nodes[0].parent_id, null);
  assert.equal(project.measurements[0].role, 'grid');
  assert.equal(project.channels[0].source.kind, 'unconfigured');
  assert.deepEqual(project.devices[0].capabilities, []);
  assert.ok(model.projectSummary(project).warnings.some(w => w.includes('Messquelle')));
  project = actions.addArea(project, {gridId: project.grids[0].id, name: 'Technik'});
  project = actions.addConnection(project, {name: 'Lokales Modbus', kind: 'modbus_tcp', host: '192.0.2.10', port: 502});
  const areaId = project.areas.at(-1).id, nodeId = project.nodes[0].id, connectionId = project.connections[0].id;
  project = actions.addDevice(project, {name: 'Speicher-WR', kind: 'hybrid_inverter', areaId, nodeId, connectionId, unitId: 1, phases: 3});
  const parentId = project.devices.at(-1).id;
  project = actions.addDevice(project, {name: 'Batterie', kind: 'battery', areaId, nodeId, parentId, capacityKwh: 15});
  assert.equal(project.devices.at(-1).parent_id, parentId);
  assert.equal(project.devices.at(-1).capacity_kwh, 15);
  assert.equal(project.channels.length, 1, 'no invented battery registers or SOC');
  assert.deepEqual(project, model.loadProjectJson(model.exportProjectJson(project)));
});

test('same named grids get stable distinct IDs and separate root balances', () => {
  const first = grid();
  const second = grid(first);
  assert.equal(first.grids.length, 1);
  assert.equal(second.grids.length, 2);
  assert.equal(second.measurements.length, 2);
  assert.equal(second.grids[0].id, first.grids[0].id);
  const ids = ['grids', 'areas', 'nodes', 'devices', 'channels', 'measurements'].flatMap(c => second[c].map(v => v.id));
  assert.equal(ids.length, new Set(ids).size);
  assert.ok(ids.every(id => /^[a-zA-Z0-9_-]{1,80}$/.test(id)));
});

test('failed edits never mutate project, including invalid names, credentials and cross-grid devices', () => {
  const project = grid(grid(), 'Halle 2');
  const before = JSON.stringify(project);
  const invalid = [
    () => actions.addGrid(project, {name: ''}),
    () => actions.addArea(project, {name: 'Ort', gridId: 'missing'}),
    () => actions.addConnection(project, {name: 'MQTT', kind: 'mqtt', password: 'never'}),
    () => actions.addConnection(project, {name: 'Modbus', kind: 'modbus_tcp', port: 70000}),
    () => actions.addDevice(project, {name: 'Falsch', kind: 'heater', areaId: project.areas[0].id, nodeId: project.nodes[1].id}),
    () => actions.addDevice(project, {name: 'Batterie', kind: 'battery', areaId: project.areas[0].id, nodeId: project.nodes[0].id}),
  ];
  for (const edit of invalid) {
    assert.throws(edit);
    assert.equal(JSON.stringify(project), before);
  }
});

test('battery requires supported WR at same electrical grid, not a PV-only WR or remote WR', () => {
  let project = grid(grid(), 'Halle 2');
  const areaId = project.areas[0].id, nodeId = project.nodes[0].id;
  project = actions.addDevice(project, {name: 'PV', kind: 'pv_inverter', areaId, nodeId});
  const pvId = project.devices.at(-1).id;
  assert.throws(() => actions.addDevice(project, {name: 'Batterie', kind: 'battery', areaId, nodeId, parentId: pvId}));
  project = actions.addDevice(project, {name: 'Speicher Halle 2', kind: 'storage_inverter', areaId: project.areas[1].id, nodeId: project.nodes[1].id});
  const remoteId = project.devices.at(-1).id;
  assert.throws(() => actions.addDevice(project, {name: 'Batterie', kind: 'battery', areaId, nodeId, parentId: remoteId}));
});

test('gateway route remains independent of electrical ownership but connection must agree', () => {
  let project = grid(grid(), 'Halle 2');
  project = actions.addConnection(project, {name: 'Gateway', kind: 'modbus_tcp_rtu_gateway'});
  project = actions.addConnection(project, {name: 'Andere Verbindung', kind: 'modbus_tcp'});
  const connectionId = project.connections[0].id;
  project = actions.addDevice(project, {name: 'Gateway', kind: 'gateway', areaId: project.areas[0].id, nodeId: project.nodes[0].id, connectionId});
  const viaDeviceId = project.devices.at(-1).id;
  const child = {name: 'Zähler Halle 2', kind: 'meter', areaId: project.areas[1].id, nodeId: project.nodes[1].id, viaDeviceId, connectionId, unitId: 3};
  const added = actions.addDevice(project, child);
  assert.equal(added.devices.at(-1).via_device_id, viaDeviceId);
  assert.throws(() => actions.addDevice(project, {...child, connectionId: project.connections[1].id}));
});

test('existing invalid cycles cannot be laundered through an otherwise valid action', () => {
  const project = grid();
  project.nodes[0].parent_id = project.nodes[0].id;
  const snapshot = JSON.stringify(project);
  assert.throws(() => actions.addConnection(project, {name: 'HA', kind: 'ha'}));
  assert.equal(JSON.stringify(project), snapshot);
});

test('serial values and optional nulls map without coercion or connection attempts', () => {
  const project = actions.addConnection(empty(), {name: 'Bus', kind: 'modbus_rtu_usb', serialPort: '/dev/serial/by-id/example', baudrate: 9600, parity: 'N', stopbits: 2});
  assert.equal(project.connections[0].serial_port, '/dev/serial/by-id/example');
  assert.equal(project.connections[0].baudrate, 9600);
  assert.throws(() => actions.addConnection(project, {name: 'Falsch', kind: 'modbus_tcp', port: '502'}));
  const withNull = actions.addConnection(project, {name: 'Entwurf', kind: 'mqtt', host: null});
  assert.equal(withNull.connections.at(-1).host, null);
});

test('browser API works on local HTTP with secure random bytes and no Node dependencies', () => {
  let sequence = 0;
  const context = vm.createContext({window: {}, TextEncoder, crypto: {getRandomValues: bytes => {
    bytes.fill(++sequence); return bytes;
  }}});
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'project-model.js'), 'utf8'), context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'project-actions.js'), 'utf8'), context);
  const serialized = vm.runInContext(`JSON.stringify(window.PohlProjectActions.addGrid(${JSON.stringify(empty())}, {name: 'Lokale HA-Instanz'}))`, context);
  const project = JSON.parse(serialized);
  assert.equal(model.validateProject(project).grids.length, 1);
  assert.equal(project.channels[0].source.kind, 'unconfigured');
});

function emptyV2() {
  return model.migrateProjectV1ToV2(empty());
}

test('v2 plant can be saved before a grid or device exists', () => {
  const original = emptyV2();
  const plantDetails = {name: 'Anlage A', location: 'Gebäude A', description: 'Testanlage'};
  const project = actions.addPlant(original, plantDetails);
  assert.deepEqual(original, emptyV2());
  const [plant] = project.plants;
  assert.deepEqual(plant, {id: plant.id, ...plantDetails, grid_ids: []});
  assert.deepEqual(project.grids, []);
  assert.deepEqual(project.devices, []);
  assert.throws(() => actions.addPlant(empty(), plantDetails));
});

test('v2 grid creates a root and plant link without inventing metering', () => {
  const plantOnly = actions.addPlant(emptyV2(), {name: 'Anlage A'});
  const plantId = plantOnly.plants[0].id;
  const project = actions.addGrid(plantOnly, {
    plantId, name: 'HAK', location: 'Technikraum', description: 'Hauptanschluss', fuseA: 63, phases: 3,
  });
  const [grid] = project.grids;
  const [node] = project.nodes;
  assert.deepEqual(plantOnly.plants[0].grid_ids, []);
  assert.deepEqual(project.plants[0].grid_ids, [grid.id]);
  assert.equal(grid.name, 'HAK');
  assert.deepEqual(node, {
    id: node.id, name: 'HAK', grid_id: grid.id, parent_id: null,
    location: 'Technikraum', description: 'Hauptanschluss', fuse_a: 63, phases: 3,
  });
  for (const key of ['areas', 'devices', 'channels', 'measurements']) assert.deepEqual(project[key], []);
  assert.deepEqual(model.configurationIssuesV2(project), [{code: 'grid_measurement_missing', grid_id: grid.id}]);
});

test('v2 area and device edits retain plant and electrical boundaries', () => {
  let project = actions.addPlant(actions.addPlant(emptyV2(), {name: 'Anlage A'}), {name: 'Anlage B'});
  const [plantA, plantB] = project.plants.map(plant => plant.id);
  project = actions.addGrid(project, {plantId: plantA, name: 'HAK A'});
  project = actions.addGrid(project, {plantId: plantB, name: 'HAK B'});
  const gridId = project.grids[0].id;
  const before = JSON.stringify(project);
  assert.throws(() => actions.addArea(project, {plantId: plantB, gridId, name: 'Fehlzuordnung'}), /nicht zugeordnet/);
  assert.equal(JSON.stringify(project), before);
  project = actions.addArea(project, {plantId: plantA, gridId, name: 'Technikraum'});
  const [area] = project.areas;
  assert.equal(area.plant_id, plantA);
  assert.equal(area.grid_id, gridId);
  project = actions.addConnection(project, {name: 'Gateway', kind: 'modbus_tcp_rtu_gateway'});
  const connectionId = project.connections[0].id;
  project = actions.addDevice(project, {name: 'Zähler', kind: 'meter', areaId: area.id,
    nodeId: project.nodes[0].id, connectionId, unitId: 2});
  assert.equal(project.devices[0].connection_id, connectionId);
  assert.deepEqual(project.measurements, []);
  assert.throws(() => actions.addDevice(project, {name: 'Zähler am falschen Anschluss', kind: 'meter',
    areaId: area.id, nodeId: project.nodes[1].id}));
  assert.deepEqual(model.validateProjectV2(project), project);
});

test('v2 invalid grid or plant metadata cannot mutate a valid draft', () => {
  const project = actions.addPlant(emptyV2(), {name: 'Anlage A'});
  const plantId = project.plants[0].id;
  const before = JSON.stringify(project);
  const invalid = [
    () => actions.addGrid(project, {name: 'HAK'}),
    () => actions.addGrid(project, {plantId: 'missing', name: 'HAK'}),
    () => actions.addGrid(project, {plantId, name: 'HAK', phases: 2}),
    () => actions.addGrid(project, {plantId, name: 'HAK', fuseA: '63'}),
    () => actions.addPlant(project, {name: 'Anlage B', location: 17}),
  ];
  for (const edit of invalid) {
    assert.throws(edit);
    assert.equal(JSON.stringify(project), before);
  }
});


function netMeterProject() {
  const power = (id, deviceId, phase = 'total') => ({
    id, name: id, device_id: deviceId, quantity: 'active_power', unit: 'W', phase,
    source: {kind: 'ha', entity_id: `sensor.${id}`},
  });
  const unspecified = power('unspecified', 'meter_a');
  delete unspecified.phase;
  return {
    ...emptyV2(),
    plants: [{id: 'plant', name: 'Anlage', grid_ids: ['grid_a', 'grid_b']}],
    grids: [{id: 'grid_a', name: 'Netz A'}, {id: 'grid_b', name: 'Netz B'}],
    areas: [
      {id: 'area_a', name: 'Bereich A', grid_id: 'grid_a', plant_id: 'plant'},
      {id: 'area_b', name: 'Bereich B', grid_id: 'grid_b', plant_id: 'plant'},
    ],
    nodes: [
      {id: 'root_a', name: 'HAK A', grid_id: 'grid_a', parent_id: null},
      {id: 'root_b', name: 'HAK B', grid_id: 'grid_b', parent_id: null},
      {id: 'branch', name: 'Abgang A', grid_id: 'grid_a', parent_id: 'root_a'},
    ],
    devices: [
      {id: 'meter_a', name: 'Zähler A', kind: 'meter', area_id: 'area_a', node_id: 'root_a'},
      {id: 'meter_b', name: 'Zähler B', kind: 'meter', area_id: 'area_b', node_id: 'root_b'},
      {id: 'meter_empty', name: 'Neuer Zähler', kind: 'meter', area_id: 'area_a', node_id: 'root_a'},
      {id: 'pv', name: 'PV A', kind: 'pv_inverter', area_id: 'area_a', node_id: 'root_a'},
    ],
    channels: [
      power('total', 'meter_a'), power('phase_one', 'meter_a', 'L1'), unspecified,
      power('used', 'meter_a'), power('remote', 'meter_b'), power('pv_power', 'pv'),
      {...power('voltage', 'meter_a'), quantity: 'voltage', unit: 'V'},
    ],
    measurements: [{id: 'branch_measurement', name: 'Abgang A', role: 'branch',
      node_id: 'branch', channel_id: 'used', includes_device_ids: []}],
  };
}

test('v2 grid meter choices expose only unused total power channels of local meters', () => {
  const project = netMeterProject();
  assert.deepEqual(actions.gridMeterChoices(project, 'grid_a'), [
    {id: 'meter_a', name: 'Zähler A', channels: [{id: 'total', name: 'total', unit: 'W'}]},
    {id: 'meter_empty', name: 'Neuer Zähler', channels: []},
  ]);
  assert.deepEqual(actions.gridMeterChoices(project, 'grid_b').map(meter => meter.id), ['meter_b']);
  assert.throws(() => actions.gridMeterChoices(project, 'missing'));
  assert.throws(() => actions.gridMeterChoices(empty(), 'grid_a'));
});

test('v2 grid measurement links an existing configured channel without changing its source', () => {
  const project = netMeterProject();
  const snapshot = JSON.stringify(project);
  const updated = actions.addGridMeasurement(project, {gridId: 'grid_a', meterId: 'meter_a', channelId: 'total'});
  assert.equal(JSON.stringify(project), snapshot);
  assert.deepEqual(updated.channels, project.channels);
  const measurement = updated.measurements.at(-1);
  assert.deepEqual(measurement, {id: measurement.id, name: 'Netzbilanz', role: 'grid',
    node_id: 'root_a', channel_id: 'total', includes_device_ids: []});
  assert.deepEqual(model.configurationIssuesV2(updated), [{code: 'grid_measurement_missing', grid_id: 'grid_b'}]);
  assert.throws(() => actions.addGridMeasurement(updated, {
    gridId: 'grid_a', meterId: 'meter_empty', channelName: 'Ersatzkanal', unit: 'kW',
  }), /bereits eine Netzmessung/);
});

test('v2 new net channel is explicit and reports its missing source', () => {
  const project = netMeterProject();
  const updated = actions.addGridMeasurement(project, {
    gridId: 'grid_a', meterId: 'meter_empty', channelName: 'Summenleistung', unit: 'kW',
  });
  const channel = updated.channels.at(-1);
  const measurement = updated.measurements.at(-1);
  assert.deepEqual(channel, {id: channel.id, name: 'Summenleistung', device_id: 'meter_empty',
    quantity: 'active_power', phase: 'total', unit: 'kW', source: {kind: 'unconfigured'}});
  assert.equal(measurement.channel_id, channel.id);
  assert.deepEqual(updated.devices, project.devices);
  assert.deepEqual(model.configurationIssuesV2(updated), [
    {code: 'grid_measurement_missing', grid_id: 'grid_b'},
    {code: 'measurement_source_unconfigured', measurement_id: measurement.id, channel_id: channel.id},
  ]);
});

test('v2 rejects ambiguous, used, cross-grid or non-total channel assignments without mutating the draft', () => {
  const project = netMeterProject();
  const snapshot = JSON.stringify(project);
  const base = {gridId: 'grid_a', meterId: 'meter_a'};
  const invalid = [
    ...['phase_one', 'unspecified', 'used', 'voltage', 'remote', 'missing'].map(channelId => ({...base, channelId})),
    {...base, meterId: 'meter_b', channelId: 'remote'},
    {...base, meterId: 'pv', channelId: 'pv_power'},
    {...base, meterId: 'meter_empty', channelId: 'total'},
    {...base, channelId: 'total', channelName: 'Zusatz', unit: 'kW'},
    {...base, channelName: 'Summenleistung', unit: 'Wh'},
    {...base, unit: 'kW'},
  ];
  for (const values of invalid) {
    assert.throws(() => actions.addGridMeasurement(project, values));
    assert.equal(JSON.stringify(project), snapshot);
  }
  assert.throws(() => actions.addGridMeasurement(empty(), {...base, channelId: 'total'}));
});


test('v2 source replacement preserves channel identity, unit and measurement assignment', () => {
  const original = actions.addGridMeasurement(netMeterProject(), {
    gridId: 'grid_a', meterId: 'meter_a', channelId: 'total',
  });
  const snapshot = JSON.stringify(original);
  const sources = [
    {kind: 'modbus', address: 0, function_code: 4, data_type: 's32', scale: 0.1},
    {kind: 'mqtt', topic: 'test/meter/power', json_path: 'data.power'},
    {kind: 'ha', entity_id: 'sensor.test_power'},
    {kind: 'unconfigured'},
  ];
  let project = original;
  for (const source of sources) {
    project = actions.setChannelSource(project, {channelId: 'total', source});
    const expected = JSON.parse(snapshot);
    expected.channels.find(channel => channel.id === 'total').source = source;
    assert.deepEqual(project, expected);
    assert.notEqual(project.channels.find(channel => channel.id === 'total').source, source);
    assert.equal(JSON.stringify(original), snapshot);
  }
  assert.ok(model.configurationIssuesV2(project).some(issue =>
    issue.code === 'measurement_source_unconfigured' && issue.channel_id === 'total'));
});

test('v2 source edits reject malformed, mixed, or unsupported configurations', () => {
  const project = netMeterProject();
  const snapshot = JSON.stringify(project);
  const modbus = {kind: 'modbus', address: 100, function_code: 3, data_type: 'u32'};
  const invalidSources = [
    null,
    {kind: 'unconfigured', address: null},
    {kind: 'unsupported'},
    {kind: 'modbus', address: 100},
    {...modbus, function_code: 6},
    {...modbus, address: '100'},
    {...modbus, address: 65536},
    {...modbus, scale: 0},
    {...modbus, topic: null},
    {kind: 'mqtt', topic: ''},
    {kind: 'mqtt', topic: 'test/meter', token: 'synthetic'},
    {kind: 'ha', entity_id: ''},
  ];
  for (const source of invalidSources) {
    assert.throws(() => actions.setChannelSource(project, {channelId: 'total', source}));
    assert.equal(JSON.stringify(project), snapshot);
  }
  assert.throws(() => actions.setChannelSource(project, {channelId: 'missing', source: modbus}));
  assert.throws(() => actions.setChannelSource(project, {channelId: 'total', source: modbus, unit: 'kW'}));
  const v1 = grid();
  assert.throws(() => actions.setChannelSource(v1, {channelId: v1.channels[0].id, source: modbus}));
});
