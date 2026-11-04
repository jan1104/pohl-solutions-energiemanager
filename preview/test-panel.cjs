const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync(require('node:path').join(__dirname, '../custom_components/pohl_solutions_energiemanager/frontend/pohl-panel.js'), 'utf8');
function setup(handler) {
  let Panel; const calls = [], sent = [], listeners = new Map();
  const frameWindow = {postMessage: (data, origin) => sent.push({data, origin})};
  const context = {HTMLElement: class {constructor() {this.style = {}; this.children = []; this.events = [];} append(child) {this.children.push(child);} dispatchEvent(event) {this.events.push(event);}},
    window: {location: {origin: 'https://ha.example'}, addEventListener: (type, fn) => listeners.set(type, fn), removeEventListener: type => listeners.delete(type)},
    customElements: {get: () => undefined, define: (_, cls) => {Panel = cls;}},
    document: {createElement: tag => ({tag, style: {}, contentWindow: frameWindow, children: [], handlers: {}, attributes: {}, append(...children) {this.children.push(...children);}, setAttribute(key, value) {this.attributes[key] = value;}, addEventListener(type, fn) {this.handlers[type] = fn;}})},
    CustomEvent: class {constructor(type, options) {this.type = type; Object.assign(this, options);}},
    getComputedStyle: () => ({getPropertyValue: key => key === '--primary-color' ? '#009688' : ''}), TextEncoder, setTimeout, clearTimeout};
  vm.runInNewContext(code, context); const panel = new Panel(); panel.connectedCallback();
  const hass = {auth: {accessToken: 'never-send-this'}, callWS: async request => {calls.push(request); return handler ? handler(request) : {project_json: null, revision: 'empty', has_project: false};}};
  panel.hass = hass;
  const request = (operation, extra = {}, id = 'request-1') => panel._onMessage({origin: 'https://ha.example', source: frameWindow, data: {type: 'pohl-energy-request', id, operation, ...extra}});
  return {panel, hass, calls, sent, request, frameWindow, listeners};
}
test('HA updates create one iframe and theme messages never contain authentication', () => {
  const t = setup(); t.panel.hass = t.hass; t.panel.hass = {...t.hass};
  assert.equal(t.panel.children.length, 2); assert.equal(t.panel._frame.src, '/pohl-energy-assets/project.html?ha=1&v=0.5.0');
  assert.equal(t.calls.length, 0); assert.ok(t.sent.length > 0); assert.ok(!JSON.stringify(t.sent).includes('never-send-this'));
  assert.ok(t.sent.every(s => s.origin === 'https://ha.example'));
  t.panel.disconnectedCallback(); assert.equal(t.listeners.size, 0);
});
test('narrow HA layout exposes a native navigation button and adapts iframe height', () => {
  const t = setup(); assert.equal(t.panel.narrow, false); assert.equal(t.panel._header.hidden, true); assert.equal(t.panel._frame.style.height, '100vh');
  t.panel.narrow = true; assert.equal(t.panel._header.hidden, false); assert.equal(t.panel._header.style.display, 'flex'); assert.equal(t.panel._frame.style.height, 'calc(100vh - 56px)');
  const menu = t.panel._header.children[0]; assert.equal(menu.attributes['aria-label'], 'HA-Navigation öffnen'); menu.handlers.click();
  assert.equal(t.panel.events.length, 1); assert.equal(t.panel.events[0].type, 'hass-toggle-menu'); assert.equal(t.panel.events[0].bubbles, true); assert.equal(t.panel.events[0].composed, true);
  assert.equal(t.calls.length, 0); t.panel.narrow = false; assert.equal(t.panel._header.hidden, true); assert.equal(t.panel._frame.style.height, '100vh');
});
test('ignores messages from another origin, window or protocol', async () => {
  const t = setup();
  for (const overrides of [{origin: 'https://evil.example'}, {source: {}}, {data: {type: 'other', id: 'x', operation: 'load'}}]) {
    await t.panel._onMessage({origin: 'https://ha.example', source: t.frameWindow, data: {type: 'pohl-energy-request', id: 'x', operation: 'load'}, ...overrides});
  }
  assert.equal(t.calls.length, 0);
});
test('whitelists approved operations only and prevents replay', async () => {
  const t = setup(); await t.request('device/write'); assert.equal(t.calls.length, 0);
  await t.request('load', {}, 'load-1'); await t.request('load', {}, 'load-1');
  assert.equal(t.calls.length, 1); assert.equal(t.calls[0].type, 'pohl_energy/project/get');
  assert.match(t.sent.at(-1).data.error, /bereits/);
});

function systemFixture() {
  return {product_version: '0.5.0', database: {backend: 'sqlite', schema_version: 1, project_persisted: true, migration_status: 'migrated_legacy', legacy_retained: true},
    modules: [{id: 'core', name: 'Grundmodul', version: '0.5.0', status: 'ready', reasons: []}, {id: 'storage', name: 'Konfigurationsspeicher', version: '0.5.0', status: 'ready', reasons: []}, {id: 'project', name: 'Projektverwaltung', version: '0.5.0', status: 'ready', reasons: []}], planning_only: true};
}

test('system read is whitelisted and does not load, replace or authorize a project revision', async () => {
  const t = setup(req => req.type === 'pohl_energy/system/get' ? {...systemFixture(), revision: 'must-not-adopt', secret: 'must-not-forward'} : {project_json: '{}', revision: 'project-r1'});
  await t.request('system', {project_json: '{"ignore":true}', expected_revision: 'ignore', actuator_enabled: true}, 'status-first');
  assert.deepEqual(JSON.parse(JSON.stringify(t.calls[0])), {type: 'pohl_energy/system/get'});
  assert.equal(t.panel._loaded, false); assert.equal(t.panel._revision, null);
  const status = t.sent.at(-1).data.data;
  assert.equal(status.product_version, '0.5.0'); assert.equal(status.database.migration_status, 'migrated_legacy');
  assert.equal(Object.hasOwn(status, 'revision'), false); assert.equal(Object.hasOwn(status, 'secret'), false);
  await t.request('save', {project_json: '{}', expected_revision: 'made-up'}, 'save-without-load'); assert.equal(t.calls.length, 1);
  await t.request('load', {}, 'project-load'); await t.request('system', {}, 'status-after-load');
  assert.equal(t.panel._revision, 'project-r1'); assert.equal(t.panel._loaded, true);
});

test('system responses reject malformed module/database payloads without altering loaded project state', async () => {
  const mutations = [s => {s.planning_only = false;}, s => {s.database.backend = 'unknown';}, s => {s.database.schema_version = 1.5;}, s => {s.database.project_persisted = 'yes';}, s => {s.database.migration_status = 'assumed';}, s => {s.database.legacy_retained = 1;}, s => {s.modules.push({...s.modules[0]});}, s => {s.modules[0].status = 'future-enabled';}, s => {s.modules[0].reasons = ['valid', null];}, s => {s.modules[0].version = null;}];
  for (const mutate of mutations) {
    const status = systemFixture(); mutate(status);
    const t = setup(req => req.type.endsWith('/system/get') ? status : {project_json: '{}', revision: 'keep'});
    await t.request('load', {}, 'load'); await t.request('system', {}, 'system');
    assert.equal(t.sent.at(-1).data.ok, false); assert.equal(t.panel._revision, 'keep'); assert.equal(t.panel._loaded, true);
  }
});

test('status requests can run during a project read but duplicate status reads are rejected', async () => {
  let resolveProject; const t = setup(req => req.type === 'pohl_energy/system/get' ? systemFixture() : new Promise(resolve => {resolveProject = resolve;}));
  const loading = t.request('load', {}, 'load'); await t.request('system', {}, 'status');
  assert.equal(t.calls.length, 2); assert.equal(t.panel._busy, true); assert.equal(t.panel._systemBusy, false);
  resolveProject({project_json: '{}', revision: 'r1'}); await loading; assert.equal(t.panel._revision, 'r1');
  let resolveStatus; t.panel.hass = {callWS: () => new Promise(resolve => {resolveStatus = resolve;})};
  const reading = t.request('system', {}, 'first-status'); await t.request('system', {}, 'second-status');
  assert.match(t.sent.at(-1).data.error, /Statusanfrage läuft bereits/);
  resolveStatus(systemFixture()); await reading; assert.equal(t.panel._revision, 'r1'); assert.equal(t.panel._systemBusy, false);
});

test('failed system read can be retried without changing the project revision', async () => {
  let fail = true; const t = setup(req => req.type !== 'pohl_energy/system/get' ? {project_json: '{}', revision: 'r1'} : fail ? Promise.reject(new Error('Datenbank nicht erreichbar')) : systemFixture());
  await t.request('load', {}, 'load'); await t.request('system', {}, 'failed-status'); assert.equal(t.sent.at(-1).data.ok, false);
  fail = false; await t.request('system', {}, 'retry-status'); assert.equal(t.sent.at(-1).data.ok, true); assert.equal(t.panel._revision, 'r1');
});
test('save requires loaded revision and forwards only permitted fields', async () => {
  let revision = 'r1'; const t = setup(req => ({project_json: req.project_json || null, revision, has_project: req.type.endsWith('/set')}));
  await t.request('save', {project_json: '{}'}, 'early'); assert.equal(t.calls.length, 0);
  await t.request('load', {}, 'get'); revision = 'r2';
  await t.request('save', {project_json: '{}', expected_revision: 'r1', device_write: true}, 'save');
  assert.equal(t.calls.length, 2);
  assert.deepEqual(JSON.parse(JSON.stringify(t.calls[1])), {type: 'pohl_energy/project/set', project_json: '{}', expected_revision: 'r1'});
  assert.equal(t.panel._revision, 'r2'); assert.equal(t.sent.at(-1).data.ok, true);
});
test('conflicts retain loaded revision and report draft preservation', async () => {
  const t = setup(req => {if (req.type.endsWith('/set')) return Promise.reject({code: 'conflict', message: 'changed'}); return {project_json: '{}', revision: 'r1'};});
  await t.request('load', {}, 'get'); await t.request('save', {project_json: '{}', expected_revision: 'r1'}, 'save');
  assert.equal(t.panel._revision, 'r1'); assert.equal(t.sent.at(-1).data.ok, false); assert.match(t.sent.at(-1).data.error, /Versionskonflikt.*Entwurf bleibt/);
});
test('rejects overlapping operations without issuing a second backend request', async () => {
  let resolve; const t = setup(() => new Promise(r => {resolve = r;})); const first = t.request('load', {}, 'first');
  await t.request('load', {}, 'second'); assert.equal(t.calls.length, 1); assert.match(t.sent.at(-1).data.error, /läuft bereits/);
  resolve({project_json: null, revision: 'empty'}); await first; assert.equal(t.panel._busy, false);
});
test('rejects oversized save data and incomplete server responses', async () => {
  const t = setup(() => ({project_json: null, revision: 'empty'})); await t.request('load', {}, 'get');
  await t.request('save', {project_json: 'x'.repeat(2 * 1024 * 1024 + 1), expected_revision: 'empty'}, 'huge'); assert.equal(t.calls.length, 1);
  t.panel.hass = {callWS: async () => ({revision: 123})}; await t.request('load', {}, 'bad-response'); assert.match(t.sent.at(-1).data.error, /Unvollständige/);
});
test('loading a newer revision does not silently change the revision attached to an older draft', async () => {
  let serverRevision = 'r1'; const t = setup(req => {
    if (req.type.endsWith('/set') && req.expected_revision !== serverRevision) return Promise.reject({code: 'conflict'});
    return {project_json: '{}', revision: serverRevision};
  });
  await t.request('load', {}, 'first'); serverRevision = 'r2'; await t.request('load', {}, 'preview');
  await t.request('save', {project_json: '{"name":"old draft"}', expected_revision: 'r1'}, 'save-old');
  assert.equal(t.calls.at(-1).expected_revision, 'r1'); assert.equal(t.sent.at(-1).data.ok, false); assert.match(t.sent.at(-1).data.error, /Versionskonflikt/);
});

// Exercise the actual iframe editor with a minimal DOM: revision ownership must
// follow explicit adoption, not a background read or a discarded preview.
function editorSetup() {
  class Element {
    constructor(tag = 'div') { this.tagName = tag; this.children = []; this.value = ''; this.dataset = {}; this.handlers = new Map(); this.style = {setProperty() {}}; this.classList = {add() {}}; }
    append(...items) { this.children.push(...items); if (this.tagName === 'select' && !this.value && this.children.length) this.value = this.children[0].value; }
    replaceChildren(...items) { this.children = []; if (this.tagName === 'select') this.value = ''; this.append(...items); }
    get options() { return this.children; }
    addEventListener(type, fn) { this.handlers.set(type, fn); }
    setAttribute() {} focus() {} remove() {}
  }
  const html = fs.readFileSync(require('node:path').join(__dirname, 'project.html'), 'utf8'), elements = new Map();
  for (const match of html.matchAll(/<([a-z]+)[^>]*\bid="([^"]+)"/g)) elements.set(match[2], new Element(match[1]));
  const tabs = ['electrical', 'communication', 'measurement'].map(id => { const e = elements.get(`tab-${id}`); e.dataset.view = id; return e; });
  elements.get('add-action').value = 'grid'; elements.get('add-device-kind').value = 'hybrid_inverter'; elements.get('add-connection-kind').value = 'modbus_tcp';
  const outgoing = [], listeners = new Map(), parent = {postMessage: data => outgoing.push(data)};
  const document = {getElementById: id => elements.get(id), createElement: tag => new Element(tag), body: new Element('body'), documentElement: new Element('html'), querySelectorAll: selector => selector === '[data-view]' ? tabs : selector === '[data-add]' ? [] : [...elements.values()].filter(e => ['button', 'input', 'select', 'textarea'].includes(e.tagName))};
  const win = {location: {search: '?ha=1', origin: 'https://ha.example'}, parent, addEventListener: (type, fn) => listeners.set(type, fn)};
  const context = vm.createContext({window: win, document, URLSearchParams, TextEncoder, Date, Map, Set, setTimeout, clearTimeout, Option: class extends Element {constructor(name, value) { super('option'); this.textContent = name; this.value = value; }}});
  vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, 'project-model.js'), 'utf8'), context);
  vm.runInContext('window.PohlProjectExamples = {simple: ' + fs.readFileSync(require('node:path').join(__dirname, '../examples/simple-project.json'), 'utf8') + '};', context);
  vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, 'project-ui.js'), 'utf8'), context);
  const reply = (request, data, ok = true) => listeners.get('message')({origin: 'https://ha.example', source: parent, data: {type: 'pohl-energy-response', id: request.id, ok, ...(ok ? {data} : {error: data})}});
  const click = id => elements.get(id).handlers.get('click')({preventDefault() {}});
  return {elements, outgoing, reply, click};
}
test('iframe reload/discard preserves old draft revision; explicit adoption changes it', async () => {
  const t = editorSetup(), fixture = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../examples/simple-project.json'), 'utf8'));
  assert.ok(t.outgoing.length, t.elements.get('project-error').textContent);
  t.reply(t.outgoing.at(-1), {project_json: JSON.stringify(fixture), revision: 'r1'}); await Promise.resolve(); await Promise.resolve();
  const newer = {...fixture, name: 'Anderswo geändert'};
  let loading = t.click('project-reload'); t.reply(t.outgoing.at(-1), {project_json: JSON.stringify(newer), revision: 'r2'}); await loading;
  t.click('project-discard');
  let saving = t.click('project-save'); assert.equal(t.outgoing.at(-1).expected_revision, 'r1');
  t.reply(t.outgoing.at(-1), 'Versionskonflikt: Entwurf bleibt erhalten.', false); await saving;
  assert.equal(t.elements.get('project-name').value, fixture.name);
  loading = t.click('project-reload'); t.reply(t.outgoing.at(-1), {project_json: JSON.stringify(newer), revision: 'r2'}); await loading;
  await t.click('project-apply'); assert.equal(t.elements.get('project-name').value, newer.name);
  saving = t.click('project-save'); assert.equal(t.outgoing.at(-1).expected_revision, 'r2');
  t.reply(t.outgoing.at(-1), {project_json: JSON.stringify(newer), revision: 'r3'}); await saving;
  assert.match(t.elements.get('project-message').textContent, /gespeichert/);
});

test('iframe basic-module status uses real backend fields, renders safely and preserves the project draft', async () => {
  const t = editorSetup(), fixture = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../examples/simple-project.json'), 'utf8'));
  t.reply(t.outgoing.at(-1), {project_json: JSON.stringify(fixture), revision: 'r1'}); await Promise.resolve(); await Promise.resolve();
  const draft = t.elements.get('project-json').value;
  const reading = t.click('section-tab-system'); assert.equal(t.outgoing.at(-1).operation, 'system');
  const status = systemFixture(); status.modules[0].name = '<img src=x onerror=alert(1)>'; status.modules[0].reasons = ['<script>bad()</script>'];
  t.reply(t.outgoing.at(-1), status); await reading;
  assert.equal(t.elements.get('project-panel').hidden, true); assert.equal(t.elements.get('system-panel').hidden, false);
  assert.equal(t.elements.get('system-version').textContent, '0.5.0'); assert.equal(t.elements.get('system-database').textContent, 'SQLite');
  assert.equal(t.elements.get('system-persisted').textContent, 'Gespeichert'); assert.match(t.elements.get('system-migration').textContent, /bisherige Projektdatei bleibt/);
  const module = t.elements.get('system-modules').children[0];
  assert.equal(module.children[0].children[0].textContent, '<img src=x onerror=alert(1)>'); assert.equal(module.children[0].children[0].children.length, 0);
  assert.equal(t.elements.get('project-json').value, draft);
  t.click('system-open-project'); assert.equal(t.elements.get('project-panel').hidden, false);
  const saving = t.click('project-save'); assert.equal(t.outgoing.at(-1).expected_revision, 'r1');
  t.reply(t.outgoing.at(-1), {project_json: JSON.stringify(fixture), revision: 'r2'}); await saving;
});

test('iframe basic-module errors support retry while keeping stale status explicitly marked', async () => {
  const t = editorSetup(), fixture = JSON.parse(fs.readFileSync(require('node:path').join(__dirname, '../examples/simple-project.json'), 'utf8'));
  t.reply(t.outgoing.at(-1), {project_json: JSON.stringify(fixture), revision: 'r1'}); await Promise.resolve(); await Promise.resolve();
  let reading = t.click('section-tab-system'); t.reply(t.outgoing.at(-1), 'Nicht erreichbar', false); await reading;
  assert.equal(t.elements.get('system-error').hidden, false); assert.equal(t.elements.get('system-refresh').disabled, false);
  assert.match(t.elements.get('system-message').textContent, /Noch kein bestätigter/);
  reading = t.click('system-refresh'); const status = systemFixture(); status.modules[1].status = 'failed'; status.modules[1].reasons = ['Speicher ist nicht erreichbar.']; t.reply(t.outgoing.at(-1), status); await reading;
  assert.equal(t.elements.get('system-error').hidden, true); assert.equal(t.elements.get('system-persisted').textContent, 'Derzeit nicht prüfbar');
  reading = t.click('system-refresh'); t.reply(t.outgoing.at(-1), 'Erneut nicht erreichbar', false); await reading;
  assert.match(t.elements.get('system-message').textContent, /letzten erfolgreichen Abruf/); assert.equal(t.elements.get('system-details').hidden, false);
});

test('basic-module navigation remains available when initial project loading fails', async () => {
  const t = editorSetup(); t.reply(t.outgoing.at(-1), 'Projekt kann nicht geladen werden', false); await Promise.resolve(); await Promise.resolve();
  assert.equal(t.elements.get('section-tab-system').disabled, false); assert.equal(t.elements.get('system-refresh').disabled, false);
  const reading = t.click('section-tab-system'); t.reply(t.outgoing.at(-1), systemFixture()); await reading;
  assert.equal(t.elements.get('system-version').textContent, '0.5.0');
});
