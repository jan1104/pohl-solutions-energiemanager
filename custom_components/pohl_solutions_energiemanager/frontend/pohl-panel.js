/* HA owns authentication. The embedded editor receives project data only. */
(function () {
  'use strict';
  const REQUEST = 'pohl-energy-request', RESPONSE = 'pohl-energy-response';
  class PohlEnergyManagerPanel extends HTMLElement {
    constructor() { super(); this._hass = null; this._frame = null; this._header = null; this._narrow = false; this._revision = null; this._loaded = false; this._busy = false; this._seen = new Set(); this._receive = event => this._onMessage(event); }
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
      const frame = document.createElement('iframe'); frame.title = 'Pohl Solutions Energiemanager'; frame.src = '/pohl-energy-assets/project.html?ha=1&v=0.4.0';
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
    async _onMessage(event) {
      if (event.origin !== window.location.origin || event.source !== this._frame?.contentWindow) return;
      const msg = event.data;
      if (!msg || typeof msg !== 'object' || msg.type !== REQUEST || typeof msg.id !== 'string' || !/^[a-zA-Z0-9_-]{1,100}$/.test(msg.id)) return;
      if (!['load', 'save'].includes(msg.operation)) { this._reply(msg.id, false, 'Nicht erlaubte Projektoperation.'); return; }
      if (this._seen.has(msg.id)) { this._reply(msg.id, false, 'Anfrage wurde bereits bearbeitet.'); return; }
      this._seen.add(msg.id); if (this._seen.size > 1000) this._seen.delete(this._seen.values().next().value);
      if (this._busy) { this._reply(msg.id, false, 'Eine Projektanfrage läuft bereits. Bitte kurz warten.'); return; }
      if (!this._hass?.callWS) { this._reply(msg.id, false, 'Home Assistant ist noch nicht verbunden.'); return; }
      if (msg.operation === 'save' && (!this._loaded || typeof msg.expected_revision !== 'string' || !msg.expected_revision || msg.expected_revision.length > 128 || typeof msg.project_json !== 'string' || new TextEncoder().encode(msg.project_json).length > 2 * 1024 * 1024)) { this._reply(msg.id, false, 'Vor dem Speichern Projekt laden und gültige Projektdaten samt Ausgangsversion übergeben.'); return; }
      this._busy = true; let timeout;
      try {
        const request = msg.operation === 'load' ? {type: 'pohl_energy/project/get'} : {type: 'pohl_energy/project/set', project_json: msg.project_json, expected_revision: msg.expected_revision};
        const data = await Promise.race([this._hass.callWS(request), new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error('Zeitüberschreitung. Speicherstand vor erneutem Speichern laden; Entwurf bleibt erhalten.')), 15000); })]);
        if (!data || typeof data.revision !== 'string' || !(data.project_json === null || typeof data.project_json === 'string')) throw new Error('Unvollständige Antwort von Home Assistant.');
        this._revision = data.revision; this._loaded = true; this._reply(msg.id, true, data);
      } catch (err) {
        const conflict = err?.code === 'conflict';
        this._reply(msg.id, false, conflict ? 'Versionskonflikt: Der HA-Speicherstand wurde anderswo geändert. Ihr Entwurf bleibt erhalten. Bitte aktuellen Stand laden und vergleichen.' : String(err?.message || err?.code || 'Projektanfrage fehlgeschlagen.'));
      } finally { clearTimeout(timeout); this._busy = false; }
    }
  }
  if (!customElements.get('pohl-energy-manager-panel')) customElements.define('pohl-energy-manager-panel', PohlEnergyManagerPanel);
})();
