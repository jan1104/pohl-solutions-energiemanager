/* HA owns authentication. The editor receives approved project/status data only. */
(function () {
  'use strict';
  const REQUEST = 'pohl-energy-request', RESPONSE = 'pohl-energy-response';
  class PohlEnergyManagerPanel extends HTMLElement {
    constructor() { super(); this._hass = null; this._frame = null; this._header = null; this._narrow = false; this._revision = null; this._loaded = false; this._busy = false; this._systemBusy = false; this._seen = new Set(); this._receive = event => this._onMessage(event); }
    connectedCallback() { window.addEventListener('message', this._receive); this._ensureFrame(); }
    disconnectedCallback() { window.removeEventListener('message', this._receive); }
    set hass(value) { this._hass = value; this._ensureFrame(); this._sendTheme(); }
    get hass() { return this._hass; }
    set narrow(value) { this._narrow = Boolean(value); this._updateLayout(); }
    get narrow() { return this._narrow; }
    _updateLayout() {
      if (this._header) { this._header.hidden = !this._narrow; this._header.style.display = this._narrow ? 'flex' : 'none'; }
      if (this._frame) this._frame.style.height = this._narrow ? 'calc(100vh - 56px)' : '100vh';
    }
    _ensureFrame() {
      if (!this._hass || this._frame) return;
      this.style.display = 'block'; this.style.height = '100%'; this.style.minHeight = '100vh';
      const header = document.createElement('header'); header.style.height = '56px'; header.style.alignItems = 'center'; header.style.gap = '12px'; header.style.padding = '0 12px'; header.style.boxSizing = 'border-box'; header.style.borderBottom = '1px solid var(--divider-color, #dce5e3)'; header.style.background = 'var(--app-header-background-color, var(--primary-background-color, #fff))'; header.style.color = 'var(--app-header-text-color, var(--primary-text-color, #17363f))';
      const menu = document.createElement('button'); menu.type = 'button'; menu.textContent = '☰'; menu.setAttribute('aria-label', 'HA-Navigation öffnen'); menu.title = 'HA-Navigation öffnen'; menu.style.width = '40px'; menu.style.height = '40px'; menu.style.border = '0'; menu.style.background = 'transparent'; menu.style.color = 'inherit'; menu.style.fontSize = '24px'; menu.style.cursor = 'pointer';
      menu.addEventListener('click', () => this.dispatchEvent(new CustomEvent('hass-toggle-menu', {bubbles: true, composed: true})));
      const title = document.createElement('span'); title.textContent = 'Pohl Energiemanager'; title.style.font = '500 18px Roboto, sans-serif'; header.append(menu, title); this._header = header; this.append(header);
      const frame = document.createElement('iframe'); frame.title = 'Pohl Solutions Energiemanager'; frame.src = '/pohl-energy-assets/project.html?ha=1&v=0.5.1';
      frame.style.width = '100%'; frame.style.height = 'calc(100vh - 56px)'; frame.style.border = '0'; frame.style.display = 'block';
      frame.addEventListener('load', () => this._sendTheme()); this._frame = frame; this.append(frame); this._updateLayout();
    }
    _sendTheme() {
      if (!this._frame?.contentWindow) return;
      const style = getComputedStyle(this), names = ['primary-color', 'primary-background-color', 'secondary-background-color', 'card-background-color', 'primary-text-color', 'secondary-text-color', 'divider-color'];
      const colors = {}; names.forEach(name => { const value = style.getPropertyValue(`--${name}`).trim(); if (value) colors[name] = value; });
      this._frame.contentWindow.postMessage({type: 'pohl-energy-theme', colors}, window.location.origin);
    }
    _reply(id, ok, data) { this._frame?.contentWindow?.postMessage({type: RESPONSE, id, ok, ...(ok ? {data} : {error: data})}, window.location.origin); }
    _validateSystemResponse(data) {
      const text = (value, maximum = 200) => typeof value === 'string' && value.length > 0 && value.length <= maximum;
      if (!data || typeof data !== 'object' || data.planning_only !== true || !text(data.product_version, 64)) throw new Error('Unvollständige Antwort zum Systemstatus.');
      const db = data.database;
      if (!db || db.backend !== 'sqlite' || !Number.isSafeInteger(db.schema_version) || db.schema_version < 1 || typeof db.project_persisted !== 'boolean') throw new Error('Unvollständige Angaben zum Konfigurationsspeicher.');
      if (!Array.isArray(data.modules) || data.modules.length > 64) throw new Error('Unvollständige Modulliste.');
      const ids = new Set(), modules = data.modules.map(module => {
        if (!module || !text(module.id, 80) || !/^[a-z0-9_-]+$/.test(module.id) || ids.has(module.id) || !text(module.name) || !text(module.version, 64) || !['ready', 'blocked', 'disabled', 'failed'].includes(module.status) || !Array.isArray(module.reasons) || module.reasons.length > 50 || module.reasons.some(reason => !text(reason, 2000))) throw new Error('Ungültige Modulbeschreibung im Systemstatus.');
        ids.add(module.id); return {id: module.id, name: module.name, version: module.version, status: module.status, reasons: [...module.reasons]};
      });
      const database = {backend: db.backend, schema_version: db.schema_version, project_persisted: db.project_persisted};
      if (db.migration_status !== undefined) {
        if (!['not_needed', 'migrated_legacy', 'sqlite_existing'].includes(db.migration_status)) throw new Error('Ungültiger Übernahmestatus des Konfigurationsspeichers.');
        database.migration_status = db.migration_status;
      }
      if (db.legacy_retained !== undefined) { if (typeof db.legacy_retained !== 'boolean') throw new Error('Ungültiger Sicherungsstatus.'); database.legacy_retained = db.legacy_retained; }
      return {product_version: data.product_version, database, modules, planning_only: true};
    }
    async _onMessage(event) {
      if (event.origin !== window.location.origin || event.source !== this._frame?.contentWindow) return;
      const msg = event.data;
      if (!msg || typeof msg !== 'object' || msg.type !== REQUEST || typeof msg.id !== 'string' || !/^[a-zA-Z0-9_-]{1,100}$/.test(msg.id)) return;
      if (!['load', 'save', 'system', 'migration_preview', 'migrate'].includes(msg.operation)) { this._reply(msg.id, false, 'Nicht erlaubte Operation.'); return; }
      if (this._seen.has(msg.id)) { this._reply(msg.id, false, 'Anfrage wurde bereits bearbeitet.'); return; }
      this._seen.add(msg.id); if (this._seen.size > 1000) this._seen.delete(this._seen.values().next().value);
      const statusRead = msg.operation === 'system';
      const migrationPreview = msg.operation === 'migration_preview';
      const migration = migrationPreview || msg.operation === 'migrate';
      if (statusRead ? this._systemBusy : this._busy) { this._reply(msg.id, false, statusRead ? 'Eine Statusanfrage läuft bereits. Bitte kurz warten.' : 'Eine Projektanfrage läuft bereits. Bitte kurz warten.'); return; }
      if (!this._hass?.callWS) { this._reply(msg.id, false, 'Home Assistant ist noch nicht verbunden.'); return; }
      if (msg.operation === 'save' && (!this._loaded || typeof msg.expected_revision !== 'string' || !msg.expected_revision || msg.expected_revision.length > 128 || typeof msg.project_json !== 'string' || new TextEncoder().encode(msg.project_json).length > 2 * 1024 * 1024)) { this._reply(msg.id, false, 'Vor dem Speichern Projekt laden und gültige Projektdaten samt Ausgangsversion übergeben.'); return; }
      if (migration && (!this._loaded || typeof msg.expected_revision !== 'string' || !/^[a-f0-9]{64}$/.test(msg.expected_revision) || (!migrationPreview && (!Number.isSafeInteger(msg.source_revision) || msg.source_revision < 1)))) {
        this._reply(msg.id, false, 'Für die Umstellung ist ein geprüfter Projektstand erforderlich.');
        return;
      }
      if (statusRead) this._systemBusy = true; else this._busy = true; let timeout;
      try {
        let request;
        if (migration) {
          request = {type: `pohl_energy/project/${msg.operation}`, expected_revision: msg.expected_revision};
          if (!migrationPreview) request.source_revision = msg.source_revision;
        } else {
          request = statusRead ? {type: 'pohl_energy/system/get'} : msg.operation === 'load' ? {type: 'pohl_energy/project/get'} : {type: 'pohl_energy/project/set', project_json: msg.project_json, expected_revision: msg.expected_revision};
        }
        const data = await Promise.race([this._hass.callWS(request), new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error(statusRead ? 'Der Systemstatus konnte nicht rechtzeitig geladen werden. Bitte erneut versuchen.' : 'Zeitüberschreitung. Speicherstand vor erneutem Speichern laden; Entwurf bleibt erhalten.')), 15000); })]);
        if (statusRead) { this._reply(msg.id, true, this._validateSystemResponse(data)); return; }
        if (!data || typeof data.revision !== 'string' || !(data.project_json === null || typeof data.project_json === 'string')) throw new Error('Unvollständige Antwort von Home Assistant.');
        if (migration) {
          if (typeof data.project_json !== 'string' || new TextEncoder().encode(data.project_json).length > 2 * 1024 * 1024) throw new Error('Ungültiger Projektstand für die Umstellung.');
          if (migrationPreview) {
            if (data.revision !== msg.expected_revision || !Number.isSafeInteger(data.source_revision) || data.source_revision < 1) throw new Error('Ungültige Ausgangsversion der Umstellung.');
            this._reply(msg.id, true, {revision: data.revision, source_revision: data.source_revision, project_json: data.project_json});
            return;
          }
          if (!/^[a-f0-9]{64}$/.test(data.revision) || data.revision === msg.expected_revision) throw new Error('Die gespeicherte Umstellung konnte nicht bestätigt werden.');
        }
        this._revision = data.revision; this._loaded = true; this._reply(msg.id, true, data);
      } catch (err) {
        const conflict = err?.code === 'conflict';
        this._reply(msg.id, false, conflict ? 'Versionskonflikt: Der HA-Speicherstand wurde anderswo geändert. Ihr Entwurf bleibt erhalten. Bitte aktuellen Stand laden und vergleichen.' : String(err?.message || err?.code || 'Projektanfrage fehlgeschlagen.'));
      } finally { clearTimeout(timeout); if (statusRead) this._systemBusy = false; else this._busy = false; }
    }
  }
  if (!customElements.get('pohl-energy-manager-panel')) customElements.define('pohl-energy-manager-panel', PohlEnergyManagerPanel);
})();
