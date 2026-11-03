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
