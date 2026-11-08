/* Pure project edits. No discovery, device commands, credentials or network access. */
(function (root) {
  'use strict';
  const model = typeof module !== 'undefined' && module.exports
    ? require('./project-model.js') : root.PohlProjectModel;
  const collections = ['grids', 'areas', 'nodes', 'connections', 'devices', 'channels', 'measurements'];

  function options(value, required, optional = []) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Angaben: Objekt erwartet');
    for (const key of required) if (!Object.hasOwn(value, key)) throw new Error(`Angaben.${key}: Pflichtfeld fehlt`);
    for (const key of Object.keys(value)) if (![...required, ...optional].includes(key)) throw new Error(`Angaben.${key}: unbekanntes Feld`);
  }

  function validate(input) {
    return input?.schema_version === 2 ? model.validateProjectV2(input) : model.validateProject(input);
  }

  function find(project, collection, id, path) {
    if (typeof id !== 'string') throw new Error(`${path}: Kennung erwartet`);
    const result = project[collection].find(row => row.id === id);
    if (!result) throw new Error(`${path}: unbekanntes Objekt`);
    return result;
  }

  function newId(project, prefix) {
    const crypto = typeof globalThis !== 'undefined' && globalThis.crypto
      ? globalThis.crypto : typeof require === 'function' ? require('node:crypto') : null;
    if (!crypto || (typeof crypto.randomUUID !== 'function' && typeof crypto.getRandomValues !== 'function')) throw new Error('Sichere ID-Erzeugung ist nicht verfügbar');
    const uuid = () => {
      if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
      // Local HTTP HA pages may expose getRandomValues without randomUUID.
      const bytes = crypto.getRandomValues(new Uint8Array(16));
      bytes[6] = (bytes[6] & 15) | 64;
      bytes[8] = (bytes[8] & 63) | 128;
      return Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
    };
    const usedCollections = project.schema_version === 2 ? ['plants', ...collections] : collections;
    const existing = new Set(usedCollections.flatMap(key => project[key].map(row => row.id)));
    for (let attempt = 0; attempt < 20; attempt++) {
      const id = `${prefix}_${uuid()}`;
      if (/^[a-zA-Z0-9_-]{1,80}$/.test(id) && !existing.has(id)) return id;
    }
    throw new Error('Keine eindeutige neue Kennung erzeugbar');
  }

  function addPlant(input, values) {
    options(values, ['name'], ['location', 'description']);
    const project = model.validateProjectV2(input);
    const plant = {id: newId(project, 'plant'), name: values.name, grid_ids: []};
    for (const key of ['location', 'description']) {
      if (Object.hasOwn(values, key)) plant[key] = values[key];
    }
    project.plants.push(plant);
    return model.validateProjectV2(project);
  }

  function addGridV2(input, values) {
    const mapping = {location: 'location', description: 'description', fuseA: 'fuse_a', phases: 'phases'};
    options(values, ['plantId', 'name'], Object.keys(mapping));
    const project = model.validateProjectV2(input);
    const plant = find(project, 'plants', values.plantId, 'Anlage');
    const gridId = newId(project, 'grid');
    project.grids.push({id: gridId, name: values.name});
    const node = {id: newId(project, 'node'), name: values.name, grid_id: gridId, parent_id: null};
    for (const [option, field] of Object.entries(mapping)) {
      if (Object.hasOwn(values, option)) node[field] = values[option];
    }
    project.nodes.push(node);
    plant.grid_ids.push(gridId);
    return model.validateProjectV2(project);
  }

  function addGrid(input, values) {
    if (input?.schema_version === 2) return addGridV2(input, values);
    options(values, ['name'], ['areaName']);
    const project = model.validateProject(input);
    const gridId = newId(project, 'grid');
    project.grids.push({id: gridId, name: values.name});
    const areaId = newId(project, 'area');
    project.areas.push({id: areaId, name: values.areaName ?? 'Allgemein', grid_id: gridId});
    const nodeId = newId(project, 'node');
    project.nodes.push({id: nodeId, name: 'Netzanschluss', grid_id: gridId, parent_id: null});
    const deviceId = newId(project, 'meter');
    project.devices.push({id: deviceId, name: 'Netzmessgerät – noch zuzuordnen', kind: 'meter', area_id: areaId, node_id: nodeId, capabilities: []});
    const channelId = newId(project, 'channel');
    project.channels.push({id: channelId, name: 'Netzleistung', device_id: deviceId, quantity: 'active_power', unit: 'kW', phase: 'total', source: {kind: 'unconfigured'}});
    project.measurements.push({id: newId(project, 'measurement'), name: 'Netzbilanz', role: 'grid', node_id: nodeId, channel_id: channelId, includes_device_ids: []});
    return model.validateProject(project);
  }

  function addArea(input, values) {
    const isV2 = input?.schema_version === 2;
    options(values, isV2 ? ['plantId', 'gridId', 'name'] : ['gridId', 'name']);
    const project = validate(input);
    find(project, 'grids', values.gridId, 'gridId');
    const area = {id: newId(project, 'area'), name: values.name, grid_id: values.gridId};
    if (isV2) {
      const plant = find(project, 'plants', values.plantId, 'Anlage');
      if (!plant.grid_ids.includes(values.gridId)) throw new Error('Der Netzanschluss ist dieser Anlage nicht zugeordnet');
      area.plant_id = plant.id;
    }
    project.areas.push(area);
    return validate(project);
  }

  function addConnection(input, values) {
    const mapping = {host: 'host', port: 'port', serialPort: 'serial_port', baudrate: 'baudrate', parity: 'parity', stopbits: 'stopbits'};
    options(values, ['name', 'kind'], Object.keys(mapping));
    const project = validate(input);
    const connection = {id: newId(project, 'connection'), name: values.name, kind: values.kind};
    for (const [option, field] of Object.entries(mapping)) if (Object.hasOwn(values, option)) connection[field] = values[option];
    project.connections.push(connection);
    return validate(project);
  }

  function addDevice(input, values) {
    const mapping = {parentId: 'parent_id', connectionId: 'connection_id', viaDeviceId: 'via_device_id', unitId: 'unit_id', phases: 'phases', capacityKwh: 'capacity_kwh', maxPowerKw: 'max_power_kw', model: 'model'};
    options(values, ['areaId', 'nodeId', 'name', 'kind'], Object.keys(mapping));
    const project = validate(input);
    find(project, 'areas', values.areaId, 'areaId');
    find(project, 'nodes', values.nodeId, 'nodeId');
    const device = {id: newId(project, 'device'), name: values.name, kind: values.kind, area_id: values.areaId, node_id: values.nodeId, capabilities: []};
    for (const [option, field] of Object.entries(mapping)) if (Object.hasOwn(values, option)) device[field] = values[option];
    project.devices.push(device);
    return validate(project);
  }

  const api = {addPlant, addGrid, addArea, addDevice, addConnection};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.PohlProjectActions = api;
})(typeof window !== 'undefined' ? window : null);
