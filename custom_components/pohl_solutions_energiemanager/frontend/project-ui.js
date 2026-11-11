/* Standalone offline project editor. Rendering uses textContent exclusively. */
(function () {
  'use strict';
  const M = window.PohlProjectModel, examples = window.PohlProjectExamples;
  const embedded = new URLSearchParams(window.location.search).get('ha') === '1' && window.parent !== window;
  const $ = id => document.getElementById(id), storageKey = 'pohl-energy-project-v1';
  let project, candidate = null, candidateRevision, baseRevision, savedText, migrationPreview, view = 'electrical';
  let measurementGrid, sourceChannel, simulationMeasurement, meterChoices = [];
  let initialLoadPending = false, systemBusy = false, systemLoaded = false, addPanelOpen = false;
  function initialControls(disabled) {
    document.querySelectorAll('button,input,select,textarea').forEach(control => { control.disabled = disabled; });
    // Backend diagnostics remain reachable even if loading the project fails.
    ['section-tab-project', 'section-tab-system', 'system-open-project'].forEach(id => { $(id).disabled = false; });
    $('system-refresh').disabled = !embedded || systemBusy;
    if (!disabled) $('project-object-rename').disabled = !$('project-object').value;
  }
  let requestCounter = 0; const pending = new Map();
  function haRequest(operation, fields = {}) {
    return new Promise((resolve, reject) => {
      const id = `project-${Date.now()}-${++requestCounter}`;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(operation === 'system' ? 'Home Assistant antwortet nicht auf die Statusanfrage. Bitte erneut versuchen.' : 'Home Assistant antwortet nicht. Ihr Entwurf bleibt erhalten.')); }, 18000);
      pending.set(id, {resolve, reject, timer});
      window.parent.postMessage({type: 'pohl-energy-request', id, operation, ...fields}, window.location.origin);
    });
  }
  if (embedded) window.addEventListener('message', event => {
    if (event.origin !== window.location.origin || event.source !== window.parent || !event.data || typeof event.data !== 'object') return;
    const msg = event.data;
    if (msg.type === 'pohl-energy-theme' && msg.colors && typeof msg.colors === 'object') {
      const mapping = {'primary-color': '--teal', 'primary-background-color': '--bg', 'card-background-color': '--white', 'primary-text-color': '--ink', 'secondary-text-color': '--muted', 'divider-color': '--line'};
      for (const [key, value] of Object.entries(msg.colors)) if (mapping[key] && typeof value === 'string' && value.length < 150 && !/[;{}]|url\(/i.test(value)) document.documentElement.style.setProperty(mapping[key], value);
      return;
    }
    if (msg.type !== 'pohl-energy-response' || typeof msg.id !== 'string' || !pending.has(msg.id)) return;
    const task = pending.get(msg.id); pending.delete(msg.id); clearTimeout(task.timer);
    if (msg.ok === true) task.resolve(msg.data); else task.reject(new Error(typeof msg.error === 'string' ? msg.error : 'Projektanfrage fehlgeschlagen.'));
  });
  const labels = {gateway: 'Gateway', meter: 'Messgerät', pv_inverter: 'PV-Wechselrichter', hybrid_inverter: 'Hybrid-Wechselrichter', storage_inverter: 'Speicher-Wechselrichter', battery: 'Batterie', ev_charger: 'Ladestation', heater: 'Heizstab', grid: 'Netzanschluss', branch: 'Zweig', pv_generation: 'PV-Erzeugung', battery_power: 'Batterieleistung', consumer: 'Einzelverbraucher', load: 'Verbrauch'};
  const groups = ['plants', 'grids', 'areas', 'nodes', 'connections', 'devices', 'channels', 'measurements'];
  const groupLabels = {plants: 'Anlage', grids: 'Netzanschluss', areas: 'Bereich', nodes: 'Anschlussknoten', connections: 'Verbindung', devices: 'Gerät', channels: 'Messkanal', measurements: 'Messstelle'};
  function el(tag, text, cls) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; }
  function renderSystem(data) {
    // The HA wrapper validates and limits this read-only response before forwarding it.
    if (!data || data.planning_only !== true || typeof data.product_version !== 'string' || !data.database || data.database.backend !== 'sqlite' || !Array.isArray(data.modules)) throw new Error('Der Systemstatus ist unvollständig. Bitte die Integration aktualisieren und erneut versuchen.');
    $('system-version').textContent = data.product_version;
    $('system-database').textContent = 'SQLite';
    $('system-schema').textContent = `Speicherformat ${data.database.schema_version}`;
    const storage = data.modules.find(module => module.id === 'storage');
    $('system-persisted').textContent = storage && storage.status !== 'ready' ? 'Derzeit nicht prüfbar' : data.database.project_persisted ? 'Gespeichert' : 'Noch kein Projekt gespeichert';
    const migrations = {not_needed: 'Keine Übernahme älterer Projektdaten erforderlich.', migrated_legacy: 'Vorhandene Projektdaten wurden in die SQLite-Projektablage übernommen.', sqlite_existing: 'Die vorhandene SQLite-Projektablage wird weiterverwendet.'};
    const migration = migrations[data.database.migration_status];
    $('system-migration').hidden = !migration;
    $('system-migration').textContent = migration ? migration + (data.database.legacy_retained ? ' Die bisherige Projektdatei bleibt erhalten.' : '') : '';
    const target = $('system-modules'); target.replaceChildren();
    const statuses = {ready: 'Verfügbar', blocked: 'Voraussetzung fehlt', disabled: 'Deaktiviert', failed: 'Fehler'};
    if (!data.modules.length) target.append(el('p', 'Das Backend meldet derzeit keine Module.', 'project-muted'));
    data.modules.forEach(module => {
      const row = el('article', undefined, 'system-module-row'), title = el('div', undefined, 'system-module-title');
      title.append(el('h3', module.name), el('span', statuses[module.status] || 'Unbekannter Status', `system-module-badge system-module-${module.status}`));
      row.append(title, el('p', `Version ${module.version}`, 'project-muted'));
      if (module.reasons.length) { const list = el('ul'); module.reasons.forEach(reason => list.append(el('li', reason))); row.append(list); }
      target.append(row);
    });
    $('system-planning-note').textContent = 'Konfiguration und Planung. Es werden keine Geräteschaltbefehle gesendet.';
    $('system-details').hidden = false; systemLoaded = true;
  }
  async function refreshSystem() {
    if (!embedded) { $('system-message').textContent = 'Der echte Systemstatus ist nur innerhalb von Home Assistant verfügbar. Es wird kein Datenbank- oder Modulstatus simuliert.'; return; }
    if (systemBusy) return;
    systemBusy = true; $('system-refresh').disabled = true; $('system-error').hidden = true; $('system-message').textContent = 'Systemstatus wird aus Home Assistant geladen …';
    try {
      renderSystem(await haRequest('system'));
      $('system-message').textContent = `Status aktualisiert um ${new Date().toLocaleTimeString('de-DE', {hour: '2-digit', minute: '2-digit'})}.`;
    } catch (err) {
      $('system-error').textContent = `Systemstatus nicht aktualisiert: ${err.message}`; $('system-error').hidden = false;
      $('system-message').textContent = systemLoaded ? 'Die angezeigten Angaben stammen vom letzten erfolgreichen Abruf. Bitte erneut versuchen.' : 'Noch kein bestätigter Systemstatus verfügbar. Bitte erneut versuchen.';
    } finally { systemBusy = false; $('system-refresh').disabled = false; }
  }
  function openSection(section, loadStatus = true) {
    const system = section === 'system';
    $('project-panel').hidden = system; $('system-panel').hidden = !system;
    for (const key of ['project', 'system']) { const button = $(`section-tab-${key}`); const active = key === section; button.setAttribute('aria-selected', String(active)); button.tabIndex = active ? 0 : -1; }
    if (system && loadStatus && !systemLoaded) return refreshSystem();
  }
  ['project', 'system'].forEach((key, index) => {
    const button = $(`section-tab-${key}`);
    button.addEventListener('click', () => openSection(key));
    button.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); const next = event.key === 'Home' ? 'project' : event.key === 'End' ? 'system' : index === 0 ? 'system' : 'project';
      openSection(next); $(`section-tab-${next}`).focus();
    });
  });
  $('system-open-project').addEventListener('click', () => { openSection('project'); $('section-tab-project').focus(); });
  $('system-refresh').addEventListener('click', refreshSystem);
  $('system-refresh').disabled = !embedded;
  if (embedded) $('system-mode-note').textContent = 'Status Ihrer Home-Assistant-Installation.';
  function message(text) { $('project-message').textContent = text; $('project-error').hidden = true; }
  function guard(fn) { return async function (...args) { try { await fn(...args); } catch (err) { $('project-error').textContent = `Nicht übernommen: ${err.message}`; $('project-error').hidden = false; $('project-message').textContent = ''; } }; }
  function warningList(target, warnings) {
    target.replaceChildren(); if (!warnings.length) { target.append(el('p', 'Keine zusätzlichen Hinweise aus der Strukturprüfung.', 'project-muted')); return; }
    const list = el('ul'); warnings.forEach(w => list.append(el('li', w))); target.append(list);
  }
  const isV2 = value => value?.schema_version === 2;
  const validate = value => isV2(value) ? M.validateProjectV2(value) : M.validateProject(value);
  const exportDraft = value => isV2(value) ? JSON.stringify(M.validateProjectV2(value)) : M.exportProjectJson(value);
  function ensureGuidedEditorClosed() {
    if (addPanelOpen || measurementGrid || sourceChannel) {
      throw new Error('Bitte die offene Bearbeitung zuerst übernehmen oder schließen.');
    }
  }
  function stage(value, origin, revision, migration) {
    ensureGuidedEditorClosed();
    if (embedded && !migration && revision === undefined && value.schema_version !== project.schema_version) {
      throw new Error('Das Importformat muss zum gespeicherten Projekt passen.');
    }
    const checked = validate(value), summary = M.projectSummary(checked);
    candidate = checked;
    candidateRevision = revision;
    migrationPreview = migration;
    $('project-candidate').hidden = false;
    $('candidate-heading').textContent = migration ? 'Anlagenstruktur übernehmen?' : 'Änderungen übernehmen?';
    $('candidate-migration-note').hidden = !migration;
    $('project-apply').textContent = migration ? 'Umstellen und speichern' : 'Übernehmen';
    $('candidate-summary').textContent = `${origin}: „${checked.name}“ · ${isV2(checked) ? `${summary.counts.plants} Anlagen · ` : ''}${summary.counts.grids} Netzanschlüsse · ${summary.counts.devices} Geräte · ${summary.counts.measurements} Bilanzmessungen. Noch nicht übernommen.`;
    warningList($('candidate-warnings'), summary.warnings); $('project-json').value = exportDraft(checked);
    message('Vorschau geprüft. Bitte prüfen und ausdrücklich übernehmen.');
    $('project-apply').focus();
  }
  function clearCandidate() {
    candidate = null;
    candidateRevision = migrationPreview = undefined;
    $('project-candidate').hidden = true;
  }
  function accept(value, note, revision) {
    project = validate(value);
    addPanelOpen = false;
    measurementGrid = sourceChannel = simulationMeasurement = undefined;
    if (revision !== undefined) {
      baseRevision = revision;
      savedText = exportDraft(project);
    }
    clearCandidate();
    render(); message(note);
  }
  async function exclusiveProjectRequest(operation, fields) {
    initialControls(true);
    try {
      return await haRequest(operation, fields);
    } finally {
      initialControls(false);
      renderAddForm();
    }
  }
  $('project-migration-preview').addEventListener('click', guard(async () => {
    if (!embedded || isV2(project) || !savedText) throw new Error('Kein gespeichertes Projekt zur Umstellung vorhanden.');
    if (candidate || addPanelOpen || measurementGrid || sourceChannel || simulationMeasurement || exportDraft(project) !== savedText || $('project-json').value !== savedText || $('project-name').value !== project.name) {
      throw new Error('Bitte offene Bearbeitungen zuerst abschließen und den Projektentwurf speichern.');
    }
    const data = await exclusiveProjectRequest('migration_preview', {expected_revision: baseRevision});
    const draft = M.loadProjectDocument(data.project_json);
    if (!isV2(draft) || data.revision !== baseRevision || !Number.isSafeInteger(data.source_revision) || data.source_revision < 1) {
      throw new Error('Die Umstellungsvorschau ist unvollständig. Bitte den gespeicherten Stand neu laden.');
    }
    stage(draft, 'Geplante Anlagenstruktur', undefined, data);
  }));
  function currentArea() { return $('project-area').value; }
  function devicesForArea() { return project.devices.filter(d => !currentArea() || d.area_id === currentArea()); }
  function chip(text) { return el('span', text, 'project-chip'); }
  function byId(group, id) { return (project[group] || []).find(v => v.id === id); }
  function path(container, parts) { const p = el('div', undefined, 'project-path'); parts.forEach(s => p.append(el('span', s))); container.append(p); }
  function gridMeasurement(gridId) {
    return project.measurements.find(m => m.role === 'grid' && byId('nodes', m.node_id).grid_id === gridId);
  }
  function measurementButton(grid) {
    const button = el('button', 'Netzmessung zuordnen', 'button secondary');
    button.type = 'button';
    button.setAttribute('aria-label', `Netzmessung für ${grid.name} zuordnen`);
    button.addEventListener('click', guard(() => openMeasurement(grid.id)));
    return button;
  }
  function renderElectrical(target) {
    const area = byId('areas', currentArea()); const grids = project.grids.filter(g => !area || g.id === area.grid_id);
    function renderNode(node) {
      const item = el('li'); item.append(el('span', node.name, 'project-node-title'));
      const devices = devicesForArea().filter(d => d.node_id === node.id && d.kind !== 'battery');
      for (const d of devices) {
        const row = el('div', undefined, 'project-row'); row.append(el('strong', d.name), el('br'), chip(labels[d.kind]), chip(byId('areas', d.area_id).name));
        if (d.phases) row.append(chip(`${d.phases}-phasig`));
        const batteries = project.devices.filter(b => b.kind === 'battery' && b.parent_id === d.id);
        batteries.forEach(b => row.append(el('p', `↳ ${b.name}${b.capacity_kwh != null ? ` · ${b.capacity_kwh} kWh` : ' · Kapazität offen'}${currentArea() && b.area_id !== currentArea() ? ` · ${byId('areas', b.area_id).name}` : ''}`)));
        item.append(row);
      }
      // A filtered area may contain batteries whose WR belongs to another area.
      devicesForArea().filter(d => d.node_id === node.id && d.kind === 'battery' && currentArea() && byId('devices', d.parent_id).area_id !== currentArea()).forEach(b => item.append(el('p', `${b.name} → zugehöriger WR: ${byId('devices', b.parent_id).name}`, 'project-muted')));
      const children = project.nodes.filter(n => n.parent_id === node.id); if (children.length) { const list = el('ul', undefined, 'project-tree'); children.forEach(n => list.append(renderNode(n))); item.append(list); }
      return item;
    }
    if (isV2(project) && !area) {
      for (const plant of project.plants.filter(p => !p.grid_ids.length)) {
        const row = el('article', undefined, 'project-row');
        row.append(el('strong', plant.name), chip('Netzanschluss offen'));
        target.append(row);
      }
    }
    grids.forEach(g => {
      target.append(el('h2', g.name));
      const root = project.nodes.find(n => n.grid_id === g.id && n.parent_id === null);
      if (isV2(project)) {
        const owners = project.plants.filter(p => p.grid_ids.includes(g.id));
        target.append(el('p', owners.map(p => p.name).join(' · '), 'project-muted'));
        const details = [root.location, root.fuse_a && `${root.fuse_a} A`, root.phases && `${root.phases} ${root.phases === 1 ? 'Phase' : 'Phasen'}`].filter(Boolean);
        if (details.length) target.append(el('p', details.join(' · '), 'project-muted'));
        if (root.description) target.append(el('p', root.description, 'project-muted'));
        const measurement = gridMeasurement(g.id);
        if (!measurement) {
          const actions = el('div', undefined, 'project-toolbar');
          actions.append(measurementButton(g));
          target.append(actions);
        } else if (byId('channels', measurement.channel_id).source.kind === 'unconfigured') {
          target.append(chip('Messquelle offen'));
        }
      }
      const tree = el('ul', undefined, 'project-tree');
      tree.append(renderNode(root)); target.append(tree);
    });
    if (!grids.length) target.append(el('p', 'Noch kein Netzanschluss angelegt.'));
  }
  function renderCommunication(target) {
    target.append(el('h2', 'Verbindung und Herkunft'), el('p', 'Pfeile zeigen vom Gerät über mögliche Gateways zur Verbindung. Dies ist kein elektrischer Energiefluss.', 'project-muted'));
    devicesForArea().forEach(d => {
      const row = el('article', undefined, 'project-row'); row.append(el('strong', d.name), chip(labels[d.kind]));
      const parts = []; const seen = new Set(); let at = d, connection;
      while (at && !seen.has(at.id)) { seen.add(at.id); parts.push(`${at.name}${at.unit_id != null ? ` (Unit-ID ${at.unit_id})` : ''}`); if (at.connection_id) connection = byId('connections', at.connection_id); at = byId('devices', at.via_device_id); }
      parts.push(connection ? `${connection.name} · ${connection.kind}` : 'Verbindung noch offen'); path(row, parts);
      if (connection) row.append(el('p', connection.host ? `${connection.host}${connection.port ? `:${connection.port}` : ''}` : connection.serial_port || 'Endpunkt noch nicht angegeben'));
      row.append(el('p', `Fähigkeiten: ${d.capabilities?.length ? d.capabilities.map(c => ({measure: 'Messen', switch: 'Ein/Aus', set_power: 'Leistungsvorgabe'}[c])).join(', ') : 'noch nicht bestätigt'}`));
      if (d.kind === 'battery') row.append(el('p', `Elektrisch zugehöriger WR: ${byId('devices', d.parent_id).name}`)); target.append(row);
    });
  }
  function renderMeasurements(target) {
    target.append(el('h2', 'Messort und Datenquelle'), el('p', 'Bei Bereichsauswahl werden Messstellen des zugehörigen Netzanschlusses angezeigt. Die Quelle kann in einem anderen Bereich liegen. Enthaltene Geräte werden nicht zusätzlich zur Zweigmessung summiert.', 'project-muted'));
    const area = byId('areas', currentArea());
    if (isV2(project)) {
      for (const grid of project.grids.filter(g => (!area || g.id === area.grid_id) && !gridMeasurement(g.id))) {
        const row = el('article', undefined, 'project-row');
        row.append(el('strong', grid.name), el('p', 'Netzmessung offen'), measurementButton(grid));
        target.append(row);
      }
    }
    // Measurements belong to electrical nodes, not necessarily to the source device area.
    const measurements = project.measurements.filter(m => !area || byId('nodes', m.node_id).grid_id === area.grid_id);
    measurements.forEach(m => {
      const row = el('article', undefined, 'project-row'), channel = byId('channels', m.channel_id), node = byId('nodes', m.node_id);
      row.append(el('strong', m.name), chip(labels[m.role]), chip(channel.unit), el('p', `Messort: ${node.name} · ${byId('grids', node.grid_id).name}`));
      path(row, M.sourceChain(project, channel.id));
      const s = channel.source;
      row.append(el('p', s.kind === 'unconfigured' ? 'Quelle noch nicht konfiguriert · kein Livewert' : s.kind === 'modbus' ? `Lesezuordnung: FC ${s.function_code} · Adresse ${s.address} · ${s.data_type}${s.scale != null ? ` · Faktor ${s.scale}` : ''}` : s.kind === 'mqtt' ? `MQTT: ${s.topic}${s.json_path ? ` · ${s.json_path}` : ''}` : `HA-Entität: ${s.entity_id}`));
      row.append(el('p', `Enthaltene Geräte: ${m.includes_device_ids.length ? m.includes_device_ids.map(id => byId('devices', id).name).join(', ') : 'keine ausdrücklich zugeordnet'}`));
      if (isV2(project)) {
        const actions = el('div', undefined, 'project-toolbar');
        const button = el('button', s.kind === 'unconfigured' ? 'Quelle einrichten' : 'Quelle bearbeiten', 'button secondary');
        button.type = 'button';
        button.addEventListener('click', guard(() => openSource(channel.id)));
        actions.append(button);
        if (embedded && s.kind !== 'unconfigured') {
          const simulate = el('button', 'Mit Testwert prüfen', 'button secondary');
          simulate.type = 'button';
          simulate.addEventListener('click', guard(() => openSimulation(m.id)));
          actions.append(simulate);
        }
        row.append(actions);
      }
      target.append(row);
    });
    if (!measurements.length) target.append(el('p', 'Keine zugeordnete Bilanzmessung in diesem Bereich.'));
  }
  function renderView() {
    const target = $('project-view'); target.replaceChildren(); target.setAttribute('aria-labelledby', `tab-${view}`);
    document.querySelectorAll('[data-view]').forEach(b => { b.setAttribute('aria-selected', String(b.dataset.view === view)); b.tabIndex = b.dataset.view === view ? 0 : -1; });
    ({electrical: renderElectrical, communication: renderCommunication, measurement: renderMeasurements})[view](target);
  }
  function selectedObject() { const [group, id] = $('project-object').value.split(':'); return {group, value: byId(group, id)}; }
  function render() {
    const previousArea = currentArea(); $('project-name').value = project.name; $('project-heading').textContent = project.name;
    $('project-area').replaceChildren(new Option('Alle Bereiche', ''));
    project.areas.forEach(a => $('project-area').append(new Option(`${a.name} · ${byId('grids', a.grid_id).name}`, a.id)));
    $('project-area').value = project.areas.some(a => a.id === previousArea) ? previousArea : '';
    const summary = M.projectSummary(project), counts = $('project-counts'); counts.replaceChildren();
    for (const [key, singular, plural] of [['plants', 'Anlage', 'Anlagen'], ['grids', 'Netzanschluss', 'Netzanschlüsse'], ['areas', 'Bereich', 'Bereiche'], ['devices', 'Gerät', 'Geräte'], ['measurements', 'Messstelle', 'Messstellen']]) { if (!summary.counts[key]) continue; const card = el('article'); card.append(el('strong', summary.counts[key]), el('span', summary.counts[key] === 1 ? singular : plural)); counts.append(card); }
    warningList($('project-warnings'), summary.warnings); $('project-json').value = exportDraft(project);
    $('project-warnings-section').hidden = !summary.warnings.length;
    $('project-warnings-count').textContent = summary.warnings.length ? `(${summary.warnings.length})` : '';
    $('project-object').replaceChildren(); groups.forEach(g => (project[g] || []).forEach(o => $('project-object').append(new Option(`${o.name} (${groupLabels[g]})`, `${g}:${o.id}`))));
    $('project-object-name').value = selectedObject().value?.name || ''; $('project-object-rename').disabled = !$('project-object').value;
    $('project-object-options').hidden = !$('project-object').value;
    $('project-area-filter').hidden = project.areas.length < 2;
    renderProjectLayout();
    renderAddForm(); renderView();
  }
  function firstAction() {
    if (isV2(project) && !project.plants.length) return 'plant';
    return project.grids.length ? null : 'grid';
  }
  function renderProjectLayout() {
    const first = firstAction();
    $('project-empty').hidden = !first || addPanelOpen;
    $('project-overview').hidden = Boolean(first);
    $('project-add-panel').hidden = !addPanelOpen;
    $('project-measure-panel').hidden = !measurementGrid;
    $('project-source-panel').hidden = !sourceChannel;
    $('project-simulation-panel').hidden = !simulationMeasurement;
    $('project-migration-option').hidden = !embedded || isV2(project) || !savedText;
    $('project-start-add').textContent = first === 'plant' ? 'Anlage hinzufügen' : 'Netzanschluss hinzufügen';
    $('empty-heading').textContent = first === 'plant' ? 'Erste Anlage einrichten' : 'Netzanschluss einrichten';
    const onlyPlant = project.plants?.length === 1 ? project.plants[0] : null;
    $('project-empty-copy').textContent = first === 'plant' ? 'Geben Sie Ihrer Anlage einen Namen.'
      : onlyPlant ? `Legen Sie den Netzanschluss für „${onlyPlant.name}“ an.`
      : 'Legen Sie einen Anschluss an. Danach können Sie Geräte und Messstellen ergänzen.';
  }
  function openAdd() {
    ensureGuidedEditorClosed();
    if (candidate) throw new Error('Offene Vorschau zuerst übernehmen oder verwerfen.');
    addPanelOpen = true;
    measurementGrid = sourceChannel = simulationMeasurement = undefined;
    $('add-action').value = firstAction() || (project.areas.length ? 'device' : 'area');
    $('add-details').open = false;
    renderProjectLayout(); renderAddForm(); $('add-name').focus();
  }
  $('project-start-add').addEventListener('click', guard(openAdd));
  $('project-open-add').addEventListener('click', guard(openAdd));
  $('project-add-cancel').addEventListener('click', () => { addPanelOpen = false; renderProjectLayout(); $(firstAction() ? 'project-start-add' : 'project-open-add').focus(); });
  function renderAddForm() {
    const fill = (id, rows, empty) => { const prior = $(id).value; $(id).replaceChildren(); if (empty) $(id).append(new Option(empty, '')); rows.forEach(row => $(id).append(new Option(row.name, row.id))); if ([...$(id).options].some(o => o.value === prior)) $(id).value = prior; };
    const action = $('add-action').value, v2 = isV2(project);
    fill('add-plant', (project.plants || []).filter(p => action !== 'area' || p.grid_ids.length));
    const plant = byId('plants', $('add-plant').value);
    fill('add-grid', v2 ? project.grids.filter(g => plant?.grid_ids.includes(g.id)) : project.grids);
    fill('add-area', project.areas); fill('add-device-connection', project.connections, 'Noch nicht zuordnen');
    const area = byId('areas', $('add-area').value), grid = area?.grid_id;
    fill('add-node', project.nodes.filter(n => n.grid_id === grid));
    fill('add-parent', project.devices.filter(d => ['hybrid_inverter', 'storage_inverter'].includes(d.kind) && byId('nodes', d.node_id).grid_id === grid));
    document.querySelectorAll('[data-add]').forEach(field => { field.hidden = field.dataset.add !== action; });
    $('add-action-field').hidden = Boolean(firstAction());
    $('add-plant-option').hidden = !v2;
    $('add-plant-option').disabled = !v2;
    $('add-plant-field').hidden = !v2 || !['area', 'grid'].includes(action);
    $('add-details').hidden = !v2 || !['plant', 'grid'].includes(action);
    $('add-fuse-field').hidden = $('add-phases-field').hidden = !v2 || action !== 'grid';
    $('add-fuse').disabled = !v2 || action !== 'grid';
    $('add-name').placeholder = action === 'plant' ? 'Zum Beispiel Werkstatt' : action === 'grid' ? 'Zum Beispiel HAK' : '';

    $('project-add-heading').textContent = ({plant: 'Anlage hinzufügen', grid: 'Netzanschluss hinzufügen', area: 'Bereich hinzufügen', connection: 'Verbindung hinzufügen', device: 'Gerät hinzufügen'})[action] || 'Projekt ergänzen';
    $('add-parent-field').hidden = action !== 'device' || $('add-device-kind').value !== 'battery';
  }
  function renderChannelChoices() {
    const meter = meterChoices.find(choice => choice.id === $('measure-meter').value);
    const select = $('measure-channel');
    select.replaceChildren(new Option('Bitte wählen', ''));
    if (meter) {
      for (const channel of meter.channels) {
        select.append(new Option(`${channel.name} · ${channel.unit}`, channel.id));
      }
      select.append(new Option('Neuen Messkanal anlegen', ':new'));
      if (!meter.channels.length) select.value = ':new';
    }
    select.disabled = !meter;
    renderNewChannelFields();
  }
  function renderNewChannelFields() {
    const create = $('measure-channel').value === ':new';
    $('measure-name-field').hidden = $('measure-unit-field').hidden = $('measure-source-note').hidden = !create;
    $('measure-name').required = $('measure-unit').required = create;
  }
  function openMeasurement(gridId) {
    ensureGuidedEditorClosed();
    if (candidate) throw new Error('Offene Vorschau zuerst übernehmen oder verwerfen.');
    meterChoices = window.PohlProjectActions.gridMeterChoices(project, gridId);
    measurementGrid = gridId;
    sourceChannel = simulationMeasurement = undefined;
    addPanelOpen = false;
    const grid = byId('grids', gridId);
    const area = project.areas.find(a => a.grid_id === gridId);
    $('project-measure-grid').textContent = grid.name;
    $('project-measure-empty').hidden = Boolean(meterChoices.length);
    $('project-measure-form').hidden = !meterChoices.length;
    $('project-measure-add-meter').textContent = area ? 'Messgerät hinzufügen' : 'Bereich hinzufügen';
    const meter = $('measure-meter');
    meter.replaceChildren(new Option('Bitte wählen', ''));
    for (const choice of meterChoices) meter.append(new Option(choice.name, choice.id));
    if (meterChoices.length === 1) meter.value = meterChoices[0].id;
    $('measure-name').value = '';
    $('measure-unit').value = '';
    renderChannelChoices();
    renderProjectLayout();
    $(meterChoices.length ? 'measure-meter' : 'project-measure-add-meter').focus();
  }
  $('measure-meter').addEventListener('change', renderChannelChoices);
  $('measure-channel').addEventListener('change', renderNewChannelFields);
  $('project-measure-cancel').addEventListener('click', () => {
    measurementGrid = undefined;
    renderProjectLayout();
    $('project-open-add').focus();
  });
  $('project-measure-add-meter').addEventListener('click', guard(() => {
    const gridId = measurementGrid;
    if (!gridId) return;
    const area = project.areas.find(a => a.grid_id === gridId);
    measurementGrid = undefined;
    openAdd();
    if (area) {
      $('add-action').value = 'device';
      $('add-area').value = area.id;
      $('add-device-kind').value = 'meter';
      renderAddForm();
      $('add-node').value = project.nodes.find(n => n.grid_id === gridId && n.parent_id === null).id;
    } else {
      $('add-action').value = 'area';
      $('add-plant').value = project.plants.find(p => p.grid_ids.includes(gridId)).id;
      renderAddForm();
      $('add-grid').value = gridId;
    }
  }));
  $('project-measure-form').addEventListener('submit', guard(event => {
    event.preventDefault();
    if (candidate || !measurementGrid) throw new Error('Bitte zuerst die aktuelle Vorschau abschließen.');
    const channelId = $('measure-channel').value;
    const choice = channelId === ':new'
      ? {channelName: $('measure-name').value.trim(), unit: $('measure-unit').value}
      : {channelId};
    const next = window.PohlProjectActions.addGridMeasurement(project, {
      gridId: measurementGrid, meterId: $('measure-meter').value, ...choice,
    });
    view = 'measurement';
    accept(next, 'Netzmessung zugeordnet. Änderungen noch nicht gespeichert.');
    $('tab-measurement').focus();
  }));
  function renderSourceFields() {
    const selected = $('source-kind').value;
    for (const kind of ['modbus', 'mqtt', 'ha']) {
      const group = $(`source-${kind}`);
      group.hidden = group.disabled = selected !== kind;
    }
  }
  function openSource(channelId) {
    ensureGuidedEditorClosed();
    if (candidate) throw new Error('Offene Vorschau zuerst übernehmen oder verwerfen.');
    const channel = byId('channels', channelId);
    if (!channel || !isV2(project)) throw new Error('Messkanal nicht gefunden.');
    sourceChannel = channelId;
    measurementGrid = simulationMeasurement = undefined;
    addPanelOpen = false;
    $('project-source-channel').textContent = `${channel.name} · ${channel.unit} · ${byId('devices', channel.device_id).name}`;
    const source = channel.source;
    const fields = {'source-kind': 'kind', 'source-address': 'address', 'source-function': 'function_code',
      'source-type': 'data_type', 'source-scale': 'scale', 'source-topic': 'topic', 'source-path': 'json_path',
      'source-entity': 'entity_id'};
    for (const [id, key] of Object.entries(fields)) $(id).value = String(source[key] ?? '');
    renderSourceFields();
    renderProjectLayout();
    $('source-kind').focus();
  }
  $('source-kind').addEventListener('change', renderSourceFields);
  $('project-source-cancel').addEventListener('click', () => {
    sourceChannel = undefined;
    renderProjectLayout();
    $('tab-measurement').focus();
  });
  $('project-source-form').addEventListener('submit', guard(event => {
    event.preventDefault();
    if (candidate || !sourceChannel) throw new Error('Bitte zuerst die aktuelle Vorschau abschließen.');
    const kind = $('source-kind').value;
    const source = {kind};
    if (kind === 'modbus') {
      const address = $('source-address').value;
      source.address = address === '' ? NaN : Number(address);
      source.function_code = Number($('source-function').value);
      source.data_type = $('source-type').value;
      if ($('source-scale').value !== '') source.scale = Number($('source-scale').value);
    } else if (kind === 'mqtt') {
      source.topic = $('source-topic').value;
      const path = $('source-path').value;
      if (path) source.json_path = path;
    } else if (kind === 'ha') {
      source.entity_id = $('source-entity').value.trim();
    }
    const next = window.PohlProjectActions.setChannelSource(project, {channelId: sourceChannel, source});
    accept(next, 'Messquelle geändert. Änderungen noch nicht gespeichert.');
    $('tab-measurement').focus();
  }));
  function ensureSimulationSource() {
    if (candidate || addPanelOpen || measurementGrid || sourceChannel) {
      throw new Error('Bitte offene Bearbeitungen zuerst abschließen.');
    }
    if (!savedText || exportDraft(project) !== savedText || $('project-json').value !== savedText) {
      throw new Error('Bitte das Projekt vor dem Test speichern.');
    }
  }
  function openSimulation(measurementId) {
    ensureSimulationSource();
    const measurement = byId('measurements', measurementId);
    const channel = byId('channels', measurement.channel_id);
    simulationMeasurement = measurementId;
    $('project-simulation-channel').textContent = `${measurement.name} · ${channel.name}`;
    $('simulation-raw-label').textContent = `Testwert (${channel.unit})`;
    $('simulation-raw').value = '';
    $('simulation-polarity').value = '';
    $('simulation-result').hidden = true;
    renderProjectLayout();
    $('simulation-raw').focus();
  }
  $('project-simulation-cancel').addEventListener('click', () => {
    simulationMeasurement = undefined;
    renderProjectLayout();
    $('tab-measurement').focus();
  });
  $('simulation-raw').addEventListener('input', () => { $('simulation-result').hidden = true; });
  $('simulation-polarity').addEventListener('change', () => { $('simulation-result').hidden = true; });
  const formatSimulation = number => number.toLocaleString('de-DE', {
    maximumSignificantDigits: 12,
    notation: Math.abs(number) >= 1e9 || (number !== 0 && Math.abs(number) < 1e-6) ? 'scientific' : 'standard',
  });
  $('project-simulation-form').addEventListener('submit', guard(async event => {
    event.preventDefault();
    ensureSimulationSource();
    if (!simulationMeasurement) return;
    const measurement = byId('measurements', simulationMeasurement);
    const channel = byId('channels', measurement.channel_id);
    const text = $('simulation-raw').value;
    const raw = text === '' ? NaN : Number(text);
    const polarity = Number($('simulation-polarity').value);
    if (!Number.isFinite(raw) || ![-1, 1].includes(polarity)) throw new Error('Testwert und Ausrichtung angeben.');
    $('simulation-result').hidden = true;
    const data = await exclusiveProjectRequest('simulate_measurement', {
      expected_revision: baseRevision, measurement_id: measurement.id, raw_value: raw, polarity,
    });
    if (data.simulated !== true || data.measurement_id !== measurement.id || data.channel_id !== channel.id ||
        data.raw_unit !== channel.unit || data.polarity !== polarity || !Number.isFinite(data.kw) || !Number.isFinite(data.scale)) {
      throw new Error('Testergebnis passt nicht zur gewählten Messung.');
    }
    $('simulation-kw').textContent = `Simuliert: ${formatSimulation(data.kw)} kW`;
    $('simulation-calculation').textContent = `Testwert ${formatSimulation(raw)} ${data.raw_unit} · Faktor ${formatSimulation(data.scale)} · Ausrichtung ${polarity === 1 ? '+1' : '−1'}`;
    $('simulation-direction').textContent = measurement.role === 'grid'
      ? (data.kw > 0 ? 'Netzbezug' : data.kw < 0 ? 'Einspeisung' : 'Keine Nettoleistung') : '';
    $('simulation-direction').hidden = !$('simulation-direction').textContent;
    $('simulation-result').hidden = false;
    message('');
  }));
  const template = value => isV2(project) ? M.migrateProjectV1ToV2(value) : value;
  $('project-new').addEventListener('click', guard(() => stage(template(examples.simple), 'Neue einfache Vorlage')));
  $('project-reference').addEventListener('click', guard(() => stage(template(examples.reference), 'Anonymisiertes Referenzbeispiel')));
  $('project-validate').addEventListener('click', guard(() => stage(M.loadProjectDocument($('project-json').value), 'JSON-Änderungen')));
  $('project-json').addEventListener('input', () => { if (candidate) { clearCandidate(); message('Editor geändert. Vor der Übernahme bitte erneut prüfen.'); } });
  $('project-apply').addEventListener('click', guard(async () => {
    if (!candidate) throw new Error('Keine geprüfte Vorschau vorhanden.');
    if (migrationPreview) {
      const {revision, source_revision} = migrationPreview;
      try {
        const data = await exclusiveProjectRequest('migrate', {expected_revision: revision, source_revision});
        const stored = M.loadProjectDocument(data.project_json);
        if (!isV2(stored)) throw new Error('Der neue Speicherstand konnte nicht bestätigt werden.');
        accept(stored, 'Anlagenstruktur in Home Assistant gespeichert. Der bisherige Stand ist gesichert.', data.revision);
      } catch (err) {
        clearCandidate();
        $('project-json').value = exportDraft(project);
        throw err;
      }
      return;
    }
    accept(candidate, candidateRevision !== undefined ? 'Gespeicherten Stand geladen.' : embedded ? 'Projektentwurf übernommen. Noch nicht in Home Assistant gespeichert.' : 'Projekt übernommen. Noch nicht lokal gespeichert.', candidateRevision);
  }));
  $('project-discard').addEventListener('click', () => { clearCandidate(); $('project-json').value = exportDraft(project); message('Vorschau verworfen. Projekt unverändert.'); });
  $('project-reset-editor').addEventListener('click', () => { clearCandidate(); $('project-json').value = exportDraft(project); message('Editor zurückgesetzt.'); });
  $('project-area').addEventListener('change', renderView);
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => { view = b.dataset.view; renderView(); }));
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault(); const buttons = [...document.querySelectorAll('[data-view]')], index = buttons.indexOf(b);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
    view = buttons[next].dataset.view; renderView(); buttons[next].focus();
  }));
  $('project-rename').addEventListener('click', guard(() => { ensureGuidedEditorClosed(); const next = validate(project); next.name = $('project-name').value; accept(next, embedded ? 'Projektname geändert. Noch nicht in Home Assistant gespeichert.' : 'Projektname geändert. Noch nicht lokal gespeichert.'); }));
  $('project-object').addEventListener('change', () => { $('project-object-name').value = selectedObject().value?.name || ''; });
  $('project-object-rename').addEventListener('click', guard(() => { ensureGuidedEditorClosed(); const {group, value} = selectedObject(); if (!value) throw new Error('Objekt auswählen.'); const next = validate(project); next[group].find(v => v.id === value.id).name = $('project-object-name').value; accept(next, embedded ? 'Objektname geändert. Noch nicht in Home Assistant gespeichert.' : 'Objektname geändert. Noch nicht lokal gespeichert.'); }));
  $('project-import').addEventListener('click', () => $('project-file').click());
  $('project-file').addEventListener('change', guard(async event => { const file = event.target.files[0]; event.target.value = ''; if (!file) return; if (file.size > M.MAX_BYTES) throw new Error('Datei überschreitet 2 MiB.'); stage(M.loadProjectDocument(await file.text()), `Import ${file.name}`); }));
  $('project-export').addEventListener('click', guard(() => { const blob = new Blob([exportDraft(project)], {type: 'application/json'}), url = URL.createObjectURL(blob), a = el('a'); a.href = url; a.download = `${project.id}.json`; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); message('Übernommenes Projekt exportiert; eine offene Vorschau wird nicht exportiert.'); }));
  $('project-save').addEventListener('click', guard(async () => {
    if (candidate) throw new Error('Offene Vorschau zuerst übernehmen oder verwerfen.');
    if (addPanelOpen || measurementGrid || sourceChannel) {
      throw new Error('Bitte die offene Bearbeitung zuerst übernehmen oder schließen.');
    }
    if ($('project-name').value !== project.name || $('project-json').value !== exportDraft(project)) {
      throw new Error('Bitte die Änderungen in den Projektoptionen zuerst prüfen und übernehmen.');
    }
    const text = exportDraft(project);
    if (embedded) { $('project-save').disabled = true; try { const data = await haRequest('save', {project_json: text, expected_revision: baseRevision}); baseRevision = data.revision; savedText = text; renderProjectLayout(); message(exportDraft(project) === text ? 'Projekt in Home Assistant gespeichert. Keine Gerätesteuerung aktiviert.' : 'Vorherigen Entwurf gespeichert. Neuere Änderungen in dieser Ansicht sind noch nicht gespeichert.'); } finally { $('project-save').disabled = false; } }
    else { window.localStorage.setItem(storageKey, text); message('Übernommenes Projekt in diesem Browser gespeichert.'); }
  }));
  $('project-reload').addEventListener('click', guard(async () => {
    if (embedded) { const data = await haRequest('load'); if (initialLoadPending) { initialLoadPending = false; baseRevision = data.revision; initialControls(false); } if (!data.project_json) { message('In Home Assistant ist noch kein Projekt gespeichert. Ihr Entwurf bleibt erhalten.'); return; } stage(M.loadProjectDocument(data.project_json), 'Aktueller Home-Assistant-Speicherstand', data.revision); }
    else { const raw = window.localStorage.getItem(storageKey); if (!raw) throw new Error('Kein lokaler Stand vorhanden.'); stage(M.loadProjectDocument(raw), 'Lokaler Speicherstand'); }
  }));
  ['add-action', 'add-plant', 'add-area', 'add-device-kind'].forEach(id => $(id).addEventListener('change', renderAddForm));
  $('project-add-form').addEventListener('submit', guard(event => {
    event.preventDefault(); if (candidate) throw new Error('Offene Vorschau zuerst übernehmen oder verwerfen.');
    const A = window.PohlProjectActions; if (!A) throw new Error('Projektfunktionen sind noch nicht verfügbar.');
    const name = $('add-name').value, action = $('add-action').value; let next;
    const v2 = isV2(project), plantId = $('add-plant').value;
    const optional = {};
    for (const key of ['location', 'description']) {
      const value = $(`add-${key}`).value.trim();
      if (value) optional[key] = value;
    }
    if (action === 'plant') next = A.addPlant(project, {name, ...optional});
    if (action === 'grid') {
      const values = v2 ? {name, plantId, ...optional} : {name};
      if (v2 && $('add-fuse').value) values.fuseA = Number($('add-fuse').value);
      if (v2 && $('add-phases').value) values.phases = Number($('add-phases').value);
      next = A.addGrid(project, values);
    }
    if (action === 'area') next = A.addArea(project, {name, gridId: $('add-grid').value, ...(v2 ? {plantId} : {})});
    if (action === 'connection') {
      const values = {name, kind: $('add-connection-kind').value};
      if ($('add-host').value.trim()) values.host = $('add-host').value.trim(); if ($('add-port').value) values.port = Number($('add-port').value); if ($('add-serial').value.trim()) values.serialPort = $('add-serial').value.trim();
      next = A.addConnection(project, values);
    }
    if (action === 'device') {
      const values = {name, areaId: $('add-area').value, nodeId: $('add-node').value, kind: $('add-device-kind').value};
      if ($('add-device-connection').value) values.connectionId = $('add-device-connection').value;
      if (values.kind === 'battery') values.parentId = $('add-parent').value;
      next = A.addDevice(project, values);
    }
    addPanelOpen = false;
    accept(next, 'Hinzugefügt. Änderungen noch nicht gespeichert.');
    for (const id of ['add-name', 'add-location', 'add-description', 'add-fuse', 'add-phases']) $(id).value = '';
    $(firstAction() ? 'project-start-add' : 'project-open-add').focus();
  }));
  try {
    if (!M || !examples?.simple) throw new Error('Lokale Projektdateien fehlen. Bitte Projektdateien vollständig bereitstellen.');
    const empty = {format: 'pohl-energy-project', schema_version: 1, id: 'energy-project', name: 'Mein Energieprojekt', mode: 'planning_only', grids: [], areas: [], nodes: [], connections: [], devices: [], channels: [], measurements: [], settings: {}};
    if (embedded) {
      document.body.classList.add('ha-embedded'); $('project-save').textContent = 'Speichern'; $('project-reload').textContent = 'Gespeicherten Stand laden';
      $('project-storage-note').textContent = 'Ihr Projekt wird in Home Assistant gespeichert. Änderungen werden erst mit Speichern dauerhaft übernommen.';
      $('project-mode-note').textContent = 'Einrichtung';
      accept(empty, 'Projekt wird aus Home Assistant geladen …'); initialLoadPending = true; initialControls(true);
      haRequest('load').then(data => { if (data.project_json) accept(M.loadProjectDocument(data.project_json), '', data.revision); else { baseRevision = data.revision; message(''); } initialLoadPending = false; initialControls(false); }).catch(err => { $('project-error').hidden = false; $('project-error').textContent = err.message; $('project-reload').disabled = false; });
    } else accept(M.migrateProjectV1ToV2(empty), '');
  }
  catch (err) { $('project-error').hidden = false; $('project-error').textContent = err.message; document.querySelectorAll('button').forEach(b => { b.disabled = true; }); }
})();
