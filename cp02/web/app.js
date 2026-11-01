'use strict';
(function () {
  const $ = (id) => document.getElementById(id);
  let backend = null;
  let state = null;
  const escapeHTML = (input) => String(input).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function parseMessage(raw) { try { return JSON.parse(raw); } catch (_err) { return { ok: false, error: 'HOLD_BAD_BRIDGE_JSON' }; } }
  function renderExtensions(snapshot) {
    state = snapshot;
    $('plugin-count').textContent = String(snapshot.extensions.length).padStart(2, '0');
    const root = $('extensions'); root.textContent = '';
    snapshot.extensions.forEach(ext => {
      const card = document.createElement('div'); card.className = 'module';
      const info = document.createElement('div');
      const title = document.createElement('h3'); title.textContent = ext.name;
      const desc = document.createElement('p'); desc.textContent = ext.description;
      const ver = document.createElement('div'); ver.className = 'version'; ver.textContent = `${ext.version} · ${ext.suffix}`;
      info.append(title, desc, ver);
      const toggle = document.createElement('button'); toggle.className = 'switch ' + (ext.enabled ? 'on' : '');
      toggle.textContent = ext.enabled ? 'ON' : 'OFF';
      toggle.addEventListener('click', () => {
        toggle.disabled = true;
        backend.setEnabled(ext.id, !ext.enabled, (raw) => {
          const msg = parseMessage(raw);
          if (msg.ok) renderExtensions(msg.snapshot);
          else { toggle.disabled = false; $('run-status').textContent = msg.error || 'HOLD'; }
        });
      });
      card.append(info, toggle); root.append(card);
    });
  }
  function renderReport(data) {
    const root = $('report'); root.textContent = '';
    if (!data.ok) { root.textContent = data.error || 'HOLD'; $('run-status').textContent = 'HOLD'; return; }
    const rep = data.report;
    $('run-status').textContent = rep.status;
    const h = document.createElement('h3'); h.textContent = `${rep.filename} · ${rep.status}`;
    const s = document.createElement('p'); s.textContent = `Tool: ${rep.tool} · Source: bundled synthetic fixture`;
    root.append(h, s);
    Object.entries(rep.summary).forEach(([k, v]) => {
      const span = document.createElement('span'); span.className = 'stat'; span.textContent = `${k}: ${v}`; root.append(span);
    });
    const label = document.createElement('p'); label.textContent = 'FINDINGS'; root.append(label);
    (rep.findings || []).forEach(f => {
      const p = document.createElement('p'); p.className = (f.severity || '').toLowerCase();
      p.textContent = `[${f.severity}] ${f.code}: ${f.message}`; root.append(p);
    });
    const details = document.createElement('details');
    const summary = document.createElement('summary'); summary.textContent = 'Structured JSON';
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(rep, null, 2);
    details.append(summary, pre); root.append(details);
  }
  function inspect(kind) {
    if (!backend) return;
    $('run-status').textContent = 'Inspecting…';
    backend.demo(kind, (raw) => renderReport(parseMessage(raw)));
  }
  function init() {
    if (!(window.qt && qt.webChannelTransport && window.QWebChannel)) {
      $('core-status').textContent = 'QT REQUIRED';
      $('run-status').textContent = 'HOLD: Qt WebChannel unavailable';
      return;
    }
    new QWebChannel(qt.webChannelTransport, (channel) => {
      backend = channel.objects.mmdLab;
      backend.getSnapshot((raw) => {
        const msg = parseMessage(raw);
        if (!msg.extensions) { $('core-status').textContent = 'HOLD'; return; }
        renderExtensions(msg);
        $('core-status').textContent = 'READY';
        $('run-status').textContent = 'Ready';
        $('demo-pmx').disabled = false;
        $('demo-vmd').disabled = false;
      });
    });
  }
  $('demo-pmx').addEventListener('click', () => inspect('pmx'));
  $('demo-vmd').addEventListener('click', () => inspect('vmd'));
  document.querySelectorAll('nav .nav').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('nav .nav').forEach(b => b.classList.toggle('active', b === btn));
    const title = {overview:'Your toolkit, one studio.', doctor:'MMD Doctor.', motion:'Motion diagnostics.', extensions:'Extension manager.'};
    $('page-title').textContent = title[btn.dataset.view] || title.overview;
    $('page-subtitle').textContent = 'CP02 synthetic-only diagnostics. No external model access or edits.';
  }));
  init();
}());
