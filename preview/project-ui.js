/* Standalone offline project editor. Rendering uses textContent exclusively. */
(function () {
  'use strict';
  const M = window.PohlProjectModel, examples = window.PohlProjectExamples;
  const $ = id => document.getElementById(id), storageKey = 'pohl-energy-project-v1';
  let project, candidate = null, view = 'electrical';
  const labels = {gateway: 'Gateway', meter: 'Messgerät', pv_inverter: 'PV-Wechselrichter', hybrid_inverter: 'Hybrid-Wechselrichter', storage_inverter: 'Speicher-Wechselrichter', battery: 'Batterie', ev_charger: 'Ladestation', heater: 'Heizstab', grid: 'Netzanschluss', branch: 'Zweig', pv_generation: 'PV-Erzeugung', battery_power: 'Batterieleistung', consumer: 'Einzelverbraucher', load: 'Verbrauch'};
  const groups = ['grids', 'areas', 'nodes', 'connections', 'devices', 'channels', 'measurements'];
  function el(tag, text, cls) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; }
  function message(text) { $('project-message').textContent = text; $('project-error').hidden = true; }
  function guard(fn) { return async function (...args) { try { await fn(...args); } catch (err) { $('project-error').textContent = `Nicht übernommen: ${err.message}`; $('project-error').hidden = false; $('project-message').textContent = ''; } }; }
  function warningList(target, warnings) {
    target.replaceChildren(); if (!warnings.length) { target.append(el('p', 'Keine zusätzlichen Hinweise aus der Strukturprüfung.', 'project-muted')); return; }
    const list = el('ul'); warnings.forEach(w => list.append(el('li', w))); target.append(list);
  }
  function stage(value, origin) {
    const checked = M.validateProject(value), summary = M.projectSummary(checked);
    candidate = checked; $('project-candidate').hidden = false;
    $('candidate-summary').textContent = `${origin}: „${checked.name}“ · ${summary.counts.grids} Netzanschlüsse · ${summary.counts.devices} Geräte · ${summary.counts.measurements} Bilanzmessungen. Noch nicht übernommen.`;
    warningList($('candidate-warnings'), summary.warnings); $('project-json').value = M.exportProjectJson(checked);
    message('Vorschau geprüft. Bitte prüfen und ausdrücklich übernehmen.');
  }
  function accept(value, note) { project = M.validateProject(value); candidate = null; $('project-candidate').hidden = true; render(); message(note); }
  function currentArea() { return $('project-area').value; }
  function devicesForArea() { return project.devices.filter(d => !currentArea() || d.area_id === currentArea()); }
  function chip(text) { return el('span', text, 'project-chip'); }
  function byId(group, id) { return project[group].find(v => v.id === id); }
  function path(container, parts) { const p = el('div', undefined, 'project-path'); parts.forEach(s => p.append(el('span', s))); container.append(p); }
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
    grids.forEach(g => { target.append(el('h2', g.name)); const tree = el('ul', undefined, 'project-tree'); tree.append(renderNode(project.nodes.find(n => n.grid_id === g.id && n.parent_id === null))); target.append(tree); });
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
    // Measurements belong to electrical nodes, not necessarily to the source device area.
    const measurements = project.measurements.filter(m => !area || byId('nodes', m.node_id).grid_id === area.grid_id);
    measurements.forEach(m => {
      const row = el('article', undefined, 'project-row'), channel = byId('channels', m.channel_id), node = byId('nodes', m.node_id);
      row.append(el('strong', m.name), chip(labels[m.role]), chip(channel.unit), el('p', `Messort: ${node.name} · ${byId('grids', node.grid_id).name}`));
      path(row, M.sourceChain(project, channel.id));
      const s = channel.source;
      row.append(el('p', s.kind === 'unconfigured' ? 'Quelle noch nicht konfiguriert · kein Livewert' : s.kind === 'modbus' ? `Lesezuordnung: FC ${s.function_code} · Adresse ${s.address} · ${s.data_type}${s.scale != null ? ` · Faktor ${s.scale}` : ''}` : s.kind === 'mqtt' ? `MQTT: ${s.topic}${s.json_path ? ` · ${s.json_path}` : ''}` : `HA-Entität: ${s.entity_id}`));
      row.append(el('p', `Enthaltene Geräte: ${m.includes_device_ids.length ? m.includes_device_ids.map(id => byId('devices', id).name).join(', ') : 'keine ausdrücklich zugeordnet'}`)); target.append(row);
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
    const previousArea = currentArea(); $('project-name').value = project.name;
    $('project-area').replaceChildren(new Option('Alle Bereiche', ''));
    project.areas.forEach(a => $('project-area').append(new Option(`${a.name} · ${byId('grids', a.grid_id).name}`, a.id)));
    $('project-area').value = project.areas.some(a => a.id === previousArea) ? previousArea : '';
    const summary = M.projectSummary(project), counts = $('project-counts'); counts.replaceChildren();
    for (const [key, name] of [['grids', 'Netzanschlüsse'], ['areas', 'Bereiche'], ['devices', 'Geräte'], ['measurements', 'Bilanzmessungen']]) { const card = el('article'); card.append(el('strong', summary.counts[key]), el('span', name)); counts.append(card); }
    warningList($('project-warnings'), summary.warnings); $('project-json').value = M.exportProjectJson(project);
    $('project-object').replaceChildren(); groups.forEach(g => project[g].forEach(o => $('project-object').append(new Option(`${o.name} (${g})`, `${g}:${o.id}`))));
    $('project-object-name').value = selectedObject().value?.name || ''; $('project-object-rename').disabled = !$('project-object').value;
    renderView();
  }
  $('project-new').addEventListener('click', guard(() => stage(examples.simple, 'Neue einfache Vorlage')));
  $('project-reference').addEventListener('click', guard(() => stage(examples.reference, 'Anonymisiertes Referenzbeispiel')));
  $('project-validate').addEventListener('click', guard(() => stage(M.loadProjectJson($('project-json').value), 'JSON-Änderungen')));
  $('project-json').addEventListener('input', () => { if (candidate) { candidate = null; $('project-candidate').hidden = true; message('Editor geändert. Vor der Übernahme bitte erneut prüfen.'); } });
  $('project-apply').addEventListener('click', guard(() => { if (!candidate) throw new Error('Keine geprüfte Vorschau vorhanden.'); accept(candidate, 'Projekt übernommen. Noch nicht lokal gespeichert.'); }));
  $('project-discard').addEventListener('click', () => { candidate = null; $('project-candidate').hidden = true; $('project-json').value = M.exportProjectJson(project); message('Vorschau verworfen. Projekt unverändert.'); });
  $('project-reset-editor').addEventListener('click', () => { candidate = null; $('project-candidate').hidden = true; $('project-json').value = M.exportProjectJson(project); message('Editor zurückgesetzt.'); });
  $('project-area').addEventListener('change', renderView);
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => { view = b.dataset.view; renderView(); }));
  document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault(); const buttons = [...document.querySelectorAll('[data-view]')], index = buttons.indexOf(b);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
    view = buttons[next].dataset.view; renderView(); buttons[next].focus();
  }));
  $('project-rename').addEventListener('click', guard(() => { const next = M.validateProject(project); next.name = $('project-name').value; accept(next, 'Projektname geändert. Noch nicht lokal gespeichert.'); }));
  $('project-object').addEventListener('change', () => { $('project-object-name').value = selectedObject().value?.name || ''; });
  $('project-object-rename').addEventListener('click', guard(() => { const {group, value} = selectedObject(); if (!value) throw new Error('Objekt auswählen.'); const next = M.validateProject(project); next[group].find(v => v.id === value.id).name = $('project-object-name').value; accept(next, 'Objektname geändert. Noch nicht lokal gespeichert.'); }));
  $('project-import').addEventListener('click', () => $('project-file').click());
  $('project-file').addEventListener('change', guard(async event => { const file = event.target.files[0]; event.target.value = ''; if (!file) return; if (file.size > M.MAX_BYTES) throw new Error('Datei überschreitet 2 MiB.'); stage(M.loadProjectJson(await file.text()), `Import ${file.name}`); }));
  $('project-export').addEventListener('click', guard(() => { const blob = new Blob([M.exportProjectJson(project)], {type: 'application/json'}), url = URL.createObjectURL(blob), a = el('a'); a.href = url; a.download = `${project.id}.json`; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); message('Übernommenes Projekt exportiert; eine offene Vorschau wird nicht exportiert.'); }));
  $('project-save').addEventListener('click', guard(() => { window.localStorage.setItem(storageKey, M.exportProjectJson(project)); message('Übernommenes Projekt in diesem Browser gespeichert.'); }));
  $('project-reload').addEventListener('click', guard(() => { const raw = window.localStorage.getItem(storageKey); if (!raw) throw new Error('Kein lokaler Stand vorhanden.'); stage(M.loadProjectJson(raw), 'Lokaler Speicherstand'); }));
  try { if (!M || !examples?.simple) throw new Error('Lokale Projektdateien fehlen. Bitte project-examples.js und project-model.js neben dieser Seite bereitstellen.'); accept(examples.simple, 'Einfache Beispielvorlage geladen. Keine Live-Verbindung.'); }
  catch (err) { $('project-error').hidden = false; $('project-error').textContent = err.message; document.querySelectorAll('button').forEach(b => { b.disabled = true; }); }
})();
