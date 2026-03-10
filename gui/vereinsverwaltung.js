// ─────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────
const API = 'http://localhost:8000';

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────
let kontenList = [];
let mitgliederList = [];
let editKontoId = null;
let statuswechselId = null;
let editBuchungId = null;
let stornoBuchungId = null;
let _editOriginal = null;
let _editSubMode  = 'simple';
let buchungenGruppiert = false;
let tkGruppiert = false;

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────
const $ = id => document.getElementById(id);

async function api(path, opts = {}) {
  try {
    const res = await fetch(API + path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts
    });
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    return data;
  } catch (e) {
    throw e;
  }
}

function toast(msg, type = 'ok') {
  const el = $('toast');
  el.textContent = msg;
  el.className = `show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.className = '', 3000);
}

function fmt(val) {
  return Number(val).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function openModal(id) { $(id).classList.add('open'); }
function closeModal(id) { $(id).classList.remove('open'); }

// Close on backdrop click
document.querySelectorAll('.modal-overlay').forEach(el => {
  el.addEventListener('click', e => { if (e.target === el) el.classList.remove('open'); });
});

// ─────────────────────────────────────────────
// Navigation
// ─────────────────────────────────────────────
function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  $(`view-${name}`).classList.add('active');
  event.target.classList.add('active');
  if (name === 'dashboard')  loadDashboard();
  if (name === 'mitglieder') loadMitglieder();
  if (name === 'konten')     loadKonten();
  if (name === 'buchungen')  { loadKontenSelect(); loadBuchungen(); }
  if (name === 'tkonten')    { initTKonten(); }
}

// ─────────────────────────────────────────────
// API Health Check
// ─────────────────────────────────────────────
async function checkHealth() {
  try {
    await api('/');
    $('statusDot').className = 'status-dot ok';
    $('statusText').textContent = API;
  } catch {
    $('statusDot').className = 'status-dot err';
    $('statusText').textContent = 'API nicht erreichbar';
  }
  updateSyncStatus();
}

async function updateSyncStatus() {
  try {
    const s = await api('/sync/status');
    const el = $('syncText');
    if (s.error) {
      el.style.color = 'var(--red)';
      el.textContent = '↑ FTP Fehler';
      el.title = s.error;
    } else if (s.last_sync) {
      const t = new Date(s.last_sync);
      const hm = t.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
      el.style.color = 'var(--text-dim)';
      el.textContent = `↑ FTP ${hm}`;
      el.title = `Letzter Sync: ${t.toLocaleString('de-DE')}\nIntervall: ${s.interval_seconds}s\nKlicken für manuellen Sync`;
    } else {
      el.style.color = 'var(--text-dim)';
      el.textContent = '↑ FTP ausstehend';
    }
  } catch {
    $('syncText').textContent = '↑ FTP n/a';
  }
}

async function manualSync() {
  const el = $('syncText');
  el.textContent = '↑ syncing…';
  el.style.color = 'var(--yellow)';
  try {
    const res = await api('/sync/now', { method: 'POST' });
    if (res.ok) {
      toast(`Sync erfolgreich (${(res.bytes / 1024).toFixed(1)} KB)`, 'ok');
    } else {
      toast('Sync fehlgeschlagen: ' + res.error, 'err');
    }
  } catch(e) {
    toast('Sync fehlgeschlagen: ' + e.message, 'err');
  }
  updateSyncStatus();
}

// Sync-Status alle 60s aktualisieren
setInterval(updateSyncStatus, 60_000);

// ─────────────────────────────────────────────
// Dashboard
// ─────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [mAll, mAktiv, konten, buchungen] = await Promise.all([
      api('/members/?nur_aktuell=false'),
      api('/members/?nur_aktuell=true&mitglied_status=aktiv'),
      api('/konten/'),
      api('/buchungen/'),
    ]);
    $('stat-gesamt').textContent   = mAll.length;
    $('stat-aktiv').textContent    = mAktiv.length;
    $('stat-konten').textContent   = konten.length;
    $('stat-buchungen').textContent = buchungen.length;

    const recent = buchungen.slice(0, 8);
    const tbody = $('dash-buchungen');
    tbody.innerHTML = recent.length ? recent.map(b => `
      <tr>
        <td>${b.buchungstext || '<span style="color:var(--text-dim)">—</span>'}</td>
        <td class="mono">${b.sollkonto.kontonummer} ${b.sollkonto.kontoname}</td>
        <td class="mono">${b.habenkonto.kontonummer} ${b.habenkonto.kontoname}</td>
        <td class="mono" style="color:var(--accent)">${fmt(b.betrag)} €</td>
        <td class="mono">${b.buchungsdatum}</td>
      </tr>`) .join('') : '<tr class="empty-row"><td colspan="5">Keine Buchungen vorhanden</td></tr>';
  } catch(e) { toast('Dashboard-Fehler: ' + e.message, 'err'); }
}

// ─────────────────────────────────────────────
// Mitglieder
// ─────────────────────────────────────────────
async function loadMitglieder() {
  try {
    const alle = $('filter-alle').checked;
    const st   = $('filter-status').value;
    let url = `/members/?nur_aktuell=${!alle}`;
    if (st) url += `&mitglied_status=${st}`;
    const data = await api(url);
    mitgliederList = data;
    $('count-mitglieder').textContent = data.length;
    const tbody = $('tbl-mitglieder');
    tbody.innerHTML = data.length ? data.map(m => `
      <tr>
        <td class="mono" style="color:var(--text-dim)">#${m.id}</td>
        <td style="font-weight:500">${m.name}</td>
        <td><span class="badge badge-${m.status}">${m.status}</span></td>
        <td class="mono">${m.gueltig_von}</td>
        <td class="mono">${m.gueltig_bis || '<span style="color:var(--accent)">aktuell</span>'}</td>
        <td style="text-align:right;white-space:nowrap">
          ${!m.gueltig_bis ? `<button class="btn btn-ghost btn-sm" onclick="openStatuswechsel(${m.id},'${m.name}','${m.status}')">Status ⇄</button>` : ''}
          <button class="btn btn-danger btn-sm" onclick="deleteMitglied(${m.id})">✕</button>
        </td>
      </tr>`).join('') : '<tr class="empty-row"><td colspan="6">Keine Mitglieder gefunden</td></tr>';
  } catch(e) { toast('Fehler: ' + e.message, 'err'); }
}

async function saveMitglied() {
  const name = $('m-name').value.trim();
  const von  = $('m-von').value;
  if (!name || !von) { toast('Name und Gültig-von sind Pflichtfelder', 'err'); return; }
  try {
    await api('/members/', {
      method: 'POST',
      body: JSON.stringify({ name, status: $('m-status').value, gueltig_von: von })
    });
    closeModal('modal-mitglied');
    $('m-name').value = '';
    toast('Mitglied angelegt');
    loadMitglieder();
  } catch(e) { toast(e.message, 'err'); }
}

function openStatuswechsel(id, name, status) {
  statuswechselId = id;
  $('sw-info').textContent = `${name}  ·  aktuell: ${status}`;
  $('sw-ab').value = today();
  openModal('modal-statuswechsel');
}

async function saveStatuswechsel() {
  const ab = $('sw-ab').value;
  if (!ab) { toast('Datum ist Pflicht', 'err'); return; }
  try {
    await api(`/members/${statuswechselId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ neuer_status: $('sw-status').value, gueltig_ab: ab })
    });
    closeModal('modal-statuswechsel');
    toast('Statuswechsel gespeichert');
    loadMitglieder();
  } catch(e) { toast(e.message, 'err'); }
}

async function deleteMitglied(id) {
  if (!confirm('Eintrag löschen?')) return;
  try {
    await api(`/members/${id}`, { method: 'DELETE' });
    toast('Eintrag gelöscht');
    loadMitglieder();
  } catch(e) { toast(e.message, 'err'); }
}

// ─────────────────────────────────────────────
// Konten
// ─────────────────────────────────────────────
async function loadKonten() {
  try {
    const data = await api('/konten/');
    kontenList = data;
    $('count-konten').textContent = data.length;
    const tbody = $('tbl-konten');
    tbody.innerHTML = data.length ? data.map(k => `
      <tr>
        <td class="mono" style="color:var(--text-dim)">#${k.id}</td>
        <td class="mono" style="color:var(--accent)">${k.kontonummer}</td>
        <td>${k.kontoname}</td>
        <td style="text-align:right;white-space:nowrap">
          <button class="btn btn-ghost btn-sm" onclick="editKonto(${k.id},'${k.kontonummer}','${k.kontoname}')">Bearbeiten</button>
          <button class="btn btn-danger btn-sm" onclick="deleteKonto(${k.id})">✕</button>
        </td>
      </tr>`).join('') : '<tr class="empty-row"><td colspan="4">Keine Konten vorhanden</td></tr>';
  } catch(e) { toast('Fehler: ' + e.message, 'err'); }
}

function editKonto(id, nr, name) {
  editKontoId = id;
  $('k-nr').value = nr;
  $('k-name').value = name;
  $('modal-konto-title').textContent = 'Konto bearbeiten';
  openModal('modal-konto');
}

async function saveKonto() {
  const nr   = $('k-nr').value.trim();
  const name = $('k-name').value.trim();
  if (!nr || !name) { toast('Alle Felder ausfüllen', 'err'); return; }
  try {
    if (editKontoId) {
      await api(`/konten/${editKontoId}`, { method: 'PUT', body: JSON.stringify({ kontonummer: nr, kontoname: name }) });
      toast('Konto aktualisiert');
    } else {
      await api('/konten/', { method: 'POST', body: JSON.stringify({ kontonummer: nr, kontoname: name }) });
      toast('Konto angelegt');
    }
    closeModal('modal-konto');
    editKontoId = null;
    $('k-nr').value = '';
    $('k-name').value = '';
    $('modal-konto-title').textContent = 'Konto anlegen';
    loadKonten();
  } catch(e) { toast(e.message, 'err'); }
}

async function deleteKonto(id) {
  if (!confirm('Konto löschen?')) return;
  try {
    await api(`/konten/${id}`, { method: 'DELETE' });
    toast('Konto gelöscht');
    loadKonten();
  } catch(e) { toast(e.message, 'err'); }
}

// ─────────────────────────────────────────────
// Buchungen
// ─────────────────────────────────────────────
async function loadKontenSelect() {
  if (!kontenList.length) kontenList = await api('/konten/');
  const mitglieder = await api('/members/?nur_aktuell=true');

  ['b-soll','b-haben'].forEach(id => {
    $(id).innerHTML = kontenList.map(k =>
      `<option value="${k.id}">${k.kontonummer} – ${k.kontoname}</option>`
    ).join('');
  });

  $('b-mitglied').innerHTML = '<option value="">— kein Mitglied —</option>' +
    mitglieder.map(m => `<option value="${m.id}">${m.name}</option>`).join('');

  // Filter dropdowns
  $('filter-konto').innerHTML = '<option value="">Alle Konten</option>' +
    kontenList.map(k => `<option value="${k.id}">${k.kontonummer} – ${k.kontoname}</option>`).join('');

  $('filter-mitglied').innerHTML = '<option value="">Alle Mitglieder</option>' +
    mitglieder.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
}

function _setLocked(locked) {
  ['b-soll', 'b-haben', 'b-betrag'].forEach(id => {
    $(id).disabled      = locked;
    $(id).style.opacity = locked ? '0.45' : '';
    $(id).style.cursor  = locked ? 'not-allowed' : '';
  });
}

function setBuchungEditMode(subMode) {
  _editSubMode = subMode;
  $('b-tab-simple').classList.toggle('b-tab-active', subMode === 'simple');
  $('b-tab-storno').classList.toggle('b-tab-active', subMode === 'storno');

  if (subMode === 'simple') {
    _setLocked(true);
    $('b-simple-hint').style.display = '';
    $('b-storno-hint').style.display = 'none';
    $('b-save-btn').textContent = 'Speichern';
    // Felder auf Originalwerte zurücksetzen
    if (_editOriginal) {
      $('b-soll').value     = _editOriginal.sollkonto?.id  ?? '';
      $('b-haben').value    = _editOriginal.habenkonto?.id ?? '';
      $('b-betrag').value   = _editOriginal.betrag;
    }
  } else {
    _setLocked(false);
    $('b-simple-hint').style.display = 'none';
    $('b-storno-hint').style.display = '';
    $('b-save-btn').textContent = 'Stornieren & neu buchen';
  }
}

function _fillBuchungModal(b, mode) {
  // mode: 'edit' | 'copy' | 'new'
  _editOriginal   = mode === 'edit' ? b : null;
  stornoBuchungId = null;
  editBuchungId   = mode === 'edit' ? b.id : null;

  $('b-modal-title').textContent = {
    edit: `Buchung #${b.id} bearbeiten`,
    copy: `Buchung #${b.id} kopieren`,
    new:  'Buchung erfassen'
  }[mode];

  $('b-soll').value     = b.sollkonto?.id  ?? b.sollkonto_id  ?? '';
  $('b-haben').value    = b.habenkonto?.id ?? b.habenkonto_id ?? '';
  $('b-betrag').value   = b.betrag;
  $('b-datum').value    = mode === 'copy' ? today() : b.buchungsdatum;
  $('b-text').value     = b.buchungstext || '';
  $('b-mitglied').value = b.mitglied?.id  ?? b.mitglied_id   ?? '';

  const isEdit = mode === 'edit';
  $('b-edit-tabs').style.display    = isEdit ? 'flex' : 'none';
  $('b-simple-hint').style.display  = 'none';
  $('b-storno-hint').style.display  = 'none';

  if (isEdit) {
    // Standard: einfacher Modus mit gesperrten Feldern
    setBuchungEditMode('simple');
  } else {
    _setLocked(false);
    $('b-save-btn').textContent = mode === 'copy' ? 'Als Kopie buchen' : 'Buchen';
  }

  openModal('modal-buchung');
}

function openBuchungModal() {
  editBuchungId   = null;
  stornoBuchungId = null;
  _editOriginal   = null;
  $('b-modal-title').textContent  = 'Buchung erfassen';
  $('b-save-btn').textContent     = 'Buchen';
  $('b-edit-tabs').style.display  = 'none';
  $('b-simple-hint').style.display = 'none';
  $('b-storno-hint').style.display = 'none';
  $('b-datum').value   = today();
  $('b-betrag').value  = '';
  $('b-text').value    = '';
  $('b-mitglied').value = '';
  _setLocked(false);
  openModal('modal-buchung');
}

async function editBuchung(id) {
  try {
    const b = await api(`/buchungen/${id}`);
    _fillBuchungModal(b, 'edit');
  } catch(e) { toast(e.message, 'err'); }
}

async function copyBuchung(id) {
  try {
    const b = await api(`/buchungen/${id}`);
    _fillBuchungModal(b, 'copy');
  } catch(e) { toast(e.message, 'err'); }
}

async function saveBuchung() {
  const datum    = $('b-datum').value;
  const text     = $('b-text').value.trim() || null;
  const mitglied = $('b-mitglied').value ? parseInt($('b-mitglied').value) : null;

  if (!datum) { toast('Buchungsdatum ist Pflicht', 'err'); return; }

  try {
    if (editBuchungId && _editSubMode === 'simple') {
      // ── Nur nicht-buchhalterische Felder per PUT ─────────────
      await api(`/buchungen/${editBuchungId}`, {
        method: 'PUT',
        body: JSON.stringify({ buchungsdatum: datum, buchungstext: text, mitglied_id: mitglied })
      });
      toast('Buchung aktualisiert');

    } else if (editBuchungId && _editSubMode === 'storno') {
      // ── Storno + Neubuchung ──────────────────────────────────
      const soll   = parseInt($('b-soll').value);
      const haben  = parseInt($('b-haben').value);
      const betrag = parseFloat($('b-betrag').value);
      if (soll === haben) { toast('Soll- und Habenkonto dürfen nicht identisch sein', 'err'); return; }
      if (!betrag || betrag <= 0) { toast('Betrag muss größer 0 sein', 'err'); return; }

      const orig = _editOriginal ?? await api(`/buchungen/${editBuchungId}`);
      // 1. Stornobuchung
      await api('/buchungen/', {
        method: 'POST',
        body: JSON.stringify({
          sollkonto_id:  orig.habenkonto.id,
          habenkonto_id: orig.sollkonto.id,
          betrag:        orig.betrag,
          buchungsdatum: today(),
          buchungstext:  `Storno #${editBuchungId}${orig.buchungstext ? ' – ' + orig.buchungstext : ''}`,
          mitglied_id:   orig.mitglied?.id ?? null
        })
      });
      // 2. Korrekturbuchung
      await api('/buchungen/', {
        method: 'POST',
        body: JSON.stringify({
          sollkonto_id: soll, habenkonto_id: haben,
          betrag: betrag.toFixed(2), buchungsdatum: datum,
          buchungstext: text, mitglied_id: mitglied
        })
      });
      toast(`Buchung #${editBuchungId} storniert und neu erfasst`);

    } else {
      // ── Neue Buchung / Kopie ─────────────────────────────────
      const soll   = parseInt($('b-soll').value);
      const haben  = parseInt($('b-haben').value);
      const betrag = parseFloat($('b-betrag').value);
      if (soll === haben) { toast('Soll- und Habenkonto dürfen nicht identisch sein', 'err'); return; }
      if (!betrag || betrag <= 0) { toast('Betrag muss größer 0 sein', 'err'); return; }
      await api('/buchungen/', {
        method: 'POST',
        body: JSON.stringify({
          sollkonto_id: soll, habenkonto_id: haben,
          betrag: betrag.toFixed(2), buchungsdatum: datum,
          buchungstext: text, mitglied_id: mitglied
        })
      });
      toast('Buchung erfasst');
    }
    closeModal('modal-buchung');
    await loadBuchungen();
  } catch(e) { toast(e.message, 'err'); }
}

function toggleGruppierung() {
  buchungenGruppiert = !buchungenGruppiert;
  const btn = $('btn-gruppieren');
  btn.textContent = buchungenGruppiert ? '⊞ Einzeln' : '⊟ Gruppieren';
  btn.classList.toggle('btn-gruppieren-active', buchungenGruppiert);
  $('th-id').textContent = buchungenGruppiert ? 'Anz.' : 'ID';
  loadBuchungen();
}

function _gruppierungsKey(b) {
  // Gleiche Buchungen = selbe Konten, Datum und Text
  return `${b.sollkonto_id}|${b.habenkonto_id}|${b.buchungsdatum}|${b.buchungstext || ''}`;
}

function _renderGruppiert(data) {
  // Gruppen bilden
  const gruppen = new Map();
  for (const b of data) {
    const key = _gruppierungsKey(b);
    if (!gruppen.has(key)) gruppen.set(key, []);
    gruppen.get(key).push(b);
  }

  const rows = [];
  let gIdx = 0;
  for (const [key, buchungen] of gruppen) {
    const rep        = buchungen[0];
    const hatMitglieder = buchungen.some(b => b.mitglied);
    const totalBetrag   = buchungen.reduce((s, b) => s + Number(b.betrag), 0);
    const mehrere       = buchungen.length > 1;
    const gid           = `grp-${gIdx++}`;

    if (mehrere && hatMitglieder) {
      // ── Gruppenzeile (klickbar) ──
      rows.push(`
        <tr class="group-header" id="${gid}" onclick="toggleGroup('${gid}')">
          <td class="mono" style="color:var(--accent)">
            <span class="group-toggle">▾</span>
            <span class="group-count">${buchungen.length}</span>
          </td>
          <td class="mono">${rep.buchungsdatum}</td>
          <td class="mono"><span style="color:var(--accent)">${rep.sollkonto.kontonummer}</span> ${rep.sollkonto.kontoname}</td>
          <td class="mono"><span style="color:var(--blue)">${rep.habenkonto.kontonummer}</span> ${rep.habenkonto.kontoname}</td>
          <td class="mono" style="color:var(--accent);font-weight:600">${fmt(totalBetrag)} €</td>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
            ${rep.buchungstext || '<span style="color:var(--text-dim)">—</span>'}
          </td>
          <td style="color:var(--text-dim);font-size:12px;font-style:italic">${buchungen.length} Mitglieder</td>
          <td></td>
        </tr>`);

      // ── Mitglieder-Unterzeilen ──
      for (const b of buchungen) {
        rows.push(`
          <tr class="group-member-row" data-group="${gid}">
            <td class="mono" style="color:var(--text-dim)">#${b.id}</td>
            <td class="mono">${b.buchungsdatum}</td>
            <td></td>
            <td></td>
            <td class="mono" style="color:var(--accent)">${fmt(b.betrag)} €</td>
            <td></td>
            <td>${b.mitglied ? b.mitglied.name : '<span style="color:var(--text-dim)">—</span>'}</td>
            <td style="text-align:right;white-space:nowrap">
              <button class="btn btn-ghost btn-sm" onclick="editBuchung(${b.id})" title="Bearbeiten">✎</button>
              <button class="btn btn-ghost btn-sm" onclick="copyBuchung(${b.id})" title="Kopieren">⎘</button>
              <button class="btn btn-danger btn-sm" onclick="deleteBuchung(${b.id})" title="Löschen">✕</button>
            </td>
          </tr>`);
      }
    } else {
      // ── Einzelzeile (keine sinnvolle Gruppe) ──
      rows.push(_renderEinzelzeile(rep));
    }
  }
  return rows.join('');
}

function _renderEinzelzeile(b) {
  return `
    <tr>
      <td class="mono" style="color:var(--text-dim)">#${b.id}</td>
      <td class="mono">${b.buchungsdatum}</td>
      <td class="mono"><span style="color:var(--accent)">${b.sollkonto.kontonummer}</span> ${b.sollkonto.kontoname}</td>
      <td class="mono"><span style="color:var(--blue)">${b.habenkonto.kontonummer}</span> ${b.habenkonto.kontoname}</td>
      <td class="mono" style="color:var(--accent);font-weight:600">${fmt(b.betrag)} €</td>
      <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
        ${b.buchungstext || '<span style="color:var(--text-dim)">—</span>'}
      </td>
      <td>${b.mitglied ? b.mitglied.name : '<span style="color:var(--text-dim)">—</span>'}</td>
      <td style="text-align:right;white-space:nowrap">
        <button class="btn btn-ghost btn-sm" onclick="editBuchung(${b.id})" title="Bearbeiten">✎</button>
        <button class="btn btn-ghost btn-sm" onclick="copyBuchung(${b.id})" title="Kopieren">⎘</button>
        <button class="btn btn-danger btn-sm" onclick="deleteBuchung(${b.id})" title="Löschen">✕</button>
      </td>
    </tr>`;
}

function toggleGroup(gid) {
  const header = $(gid);
  const collapsed = header.classList.toggle('collapsed');
  document.querySelectorAll(`[data-group="${gid}"]`).forEach(row => {
    row.classList.toggle('hidden', collapsed);
  });
}

async function loadBuchungen() {
  try {
    let url = '/buchungen/?';
    const von      = $('filter-von').value;
    const bis      = $('filter-bis').value;
    const konto    = $('filter-konto').value;
    const mitglied = $('filter-mitglied').value;
    if (von)      url += `von=${von}&`;
    if (bis)      url += `bis=${bis}&`;
    if (konto)    url += `konto_id=${konto}&`;
    if (mitglied) url += `mitglied_id=${mitglied}&`;
    const data = await api(url);
    $('count-buchungen').textContent = data.length;
    const tbody = $('tbl-buchungen');
    if (!data.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="8">Keine Buchungen gefunden</td></tr>';
      return;
    }
    tbody.innerHTML = buchungenGruppiert
      ? _renderGruppiert(data)
      : data.map(_renderEinzelzeile).join('');
  } catch(e) { toast('Fehler: ' + e.message, 'err'); }
}


async function deleteBuchung(id) {
  if (!confirm('Buchung löschen?')) return;
  try {
    await api(`/buchungen/${id}`, { method: 'DELETE' });
    toast('Buchung gelöscht');
    loadBuchungen();
  } catch(e) { toast(e.message, 'err'); }
}

function clearBuchungFilter() {
  $('filter-von').value = '';
  $('filter-bis').value = '';
  $('filter-konto').value = '';
  $('filter-mitglied').value = '';
  loadBuchungen();
}

function jumpToBuchung(id) {
  // Nav-Button für Buchungen finden und aktivieren
  const navBtns = document.querySelectorAll('nav button');
  navBtns.forEach(b => b.classList.remove('active'));
  navBtns[3].classList.add('active');   // 4. Button = Buchungen

  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  $('view-buchungen').classList.add('active');

  // Filter leeren, dann Buchungen laden – danach Zeile hervorheben
  $('filter-von').value   = '';
  $('filter-bis').value   = '';
  $('filter-konto').value = '';
  if (buchungenGruppiert) toggleGruppierung();   // Gruppierung aus, damit ID-Zeile sichtbar

  loadBuchungen().then(() => {
    // Zeile mit der gesuchten ID finden und hervorheben
    const rows = $('tbl-buchungen').querySelectorAll('tr');
    for (const row of rows) {
      const idCell = row.querySelector('td.mono');
      if (idCell && idCell.textContent.trim() === `#${id}`) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.style.transition = 'background 0s';
        row.style.background = 'rgba(0,201,122,0.15)';
        setTimeout(() => {
          row.style.transition = 'background 1.4s ease';
          row.style.background = '';
        }, 80);
        break;
      }
    }
  });
}

// ─────────────────────────────────────────────
// T-Konto Auswertung
// ─────────────────────────────────────────────

function toggleTKGruppierung() {
  tkGruppiert = !tkGruppiert;
  const btn = $('btn-tk-gruppieren');
  btn.textContent = tkGruppiert ? '⊞ Einzeln' : '⊟ Gruppieren';
  btn.classList.toggle('btn-gruppieren-active', tkGruppiert);
  loadTKonten();
}

function toggleTKGroup(gid) {
  const header   = $(gid);
  const children = $(`${gid}-ch`);
  const collapsed = header.classList.toggle('collapsed');
  children.classList.toggle('hidden', collapsed);
}

async function initTKonten() {
  // Konten-Filter-Dropdown befüllen
  if (!kontenList.length) kontenList = await api('/konten/');
  $('tk-konto-filter').innerHTML =
    '<option value="">Alle Konten anzeigen</option>' +
    kontenList.map(k => `<option value="${k.id}">${k.kontonummer} – ${k.kontoname}</option>`).join('');
  loadTKonten();
}

function clearTKFilter() {
  $('tk-von').value = '';
  $('tk-bis').value = '';
  $('tk-konto-filter').value = '';
  loadTKonten();
}

async function loadTKonten() {
  try {
    if (!kontenList.length) kontenList = await api('/konten/');

    // Buchungen laden (mit optionalem Datumsfilter)
    let url = '/buchungen/?';
    const von = $('tk-von').value;
    const bis = $('tk-bis').value;
    const filterKontoId = $('tk-konto-filter').value ? parseInt($('tk-konto-filter').value) : null;
    if (von) url += `von=${von}&`;
    if (bis) url += `bis=${bis}&`;
    const alleBuchungen = await api(url);

    // Welche Konten sollen dargestellt werden?
    const zeigeKonten = filterKontoId
      ? kontenList.filter(k => k.id === filterKontoId)
      : kontenList;

    // Pro Konto: Soll- und Haben-Buchungen sammeln
    const kontoMap = {};
    for (const k of kontenList) {
      kontoMap[k.id] = { konto: k, soll: [], haben: [] };
    }
    for (const b of alleBuchungen) {
      if (kontoMap[b.sollkonto_id])  kontoMap[b.sollkonto_id].soll.push(b);
      if (kontoMap[b.habenkonto_id]) kontoMap[b.habenkonto_id].haben.push(b);
    }

    // T-Konto-Karten rendern
    const grid = $('tkonto-grid');
    grid.innerHTML = zeigeKonten.map(k => {
      const data = kontoMap[k.id];
      if (!data) return '';
      const sollSum  = data.soll.reduce((s, b)  => s + Number(b.betrag), 0);
      const habenSum = data.haben.reduce((s, b) => s + Number(b.betrag), 0);
      const saldo    = sollSum - habenSum;
      const hasBuchungen = data.soll.length > 0 || data.haben.length > 0;

      // Wenn "Alle Konten" und Konto hat keine Buchungen → trotzdem zeigen (ausgegraut)
      const saldoClass = saldo > 0 ? 'saldo-soll' : saldo < 0 ? 'saldo-haben' : 'saldo-zero';
      const saldoText  = saldo === 0
        ? 'Saldo 0,00 €'
        : saldo > 0
          ? `S ${fmt(Math.abs(saldo))} €`
          : `H ${fmt(Math.abs(saldo))} €`;

      const maxRows = Math.max(data.soll.length, data.haben.length, 1);

      const renderEntries = (list, emptyMsg, side) => {
        if (!list.length) return `<div class="tkonto-empty">${emptyMsg}</div>`;

        if (!tkGruppiert) {
          return list.map(b => `
            <div class="tkonto-entry" onclick="jumpToBuchung(${b.id})" title="Zur Buchung #${b.id} springen">
              <span class="entry-date">${b.buchungsdatum}</span>
              <span class="entry-text" title="${b.buchungstext || ''}">${b.buchungstext || '—'}</span>
              <span class="entry-amount">${fmt(b.betrag)}</span>
            </div>`).join('');
        }

        // Gruppieren nach Buchungstext + Datum
        const gruppen = new Map();
        for (const b of list) {
          const key = `${b.buchungsdatum}|${b.buchungstext || ''}`;
          if (!gruppen.has(key)) gruppen.set(key, []);
          gruppen.get(key).push(b);
        }

        return [...gruppen.entries()].map(([key, buchungen], gi) => {
          const gid      = `tkg-${k.id}-${side}-${gi}`;
          const summe    = buchungen.reduce((s, b) => s + Number(b.betrag), 0);
          const rep      = buchungen[0];
          const mehrere  = buchungen.length > 1;

          if (!mehrere) {
            // Einzelner Eintrag – normal anzeigen
            return `
              <div class="tkonto-entry" onclick="jumpToBuchung(${rep.id})" title="Zur Buchung #${rep.id} springen">
                <span class="entry-date">${rep.buchungsdatum}</span>
                <span class="entry-text" title="${rep.buchungstext || ''}">${rep.buchungstext || '—'}</span>
                <span class="entry-amount">${fmt(rep.betrag)}</span>
              </div>`;
          }

          // Gruppenheader + eingeklappte Einzeleinträge
          return `
            <div class="tkonto-group-header" id="${gid}" onclick="toggleTKGroup('${gid}')">
              <span class="tkonto-group-toggle">▾</span>
              <span class="tkonto-group-label" title="${rep.buchungstext || ''}">${rep.buchungstext || '—'}</span>
              <span class="tkonto-group-meta">${rep.buchungsdatum} · ${buchungen.length}×</span>
              <span class="tkonto-group-sum">${fmt(summe)}</span>
            </div>
            <div class="tkonto-group-children" id="${gid}-ch">
              ${buchungen.map(b => `
                <div class="tkonto-entry" onclick="jumpToBuchung(${b.id})" title="Zur Buchung #${b.id} springen">
                  <span class="entry-date">${b.buchungsdatum}</span>
                  <span class="entry-text">${b.mitglied ? b.mitglied.name : (b.buchungstext || '—')}</span>
                  <span class="entry-amount">${fmt(b.betrag)}</span>
                </div>`).join('')}
            </div>`;
        }).join('');
      };

      return `
        <div class="tkonto-card">
          <div class="tkonto-card-header">
            <div>
              <span class="tkonto-nr">${k.kontonummer}</span>
              <span class="tkonto-name">${k.kontoname}</span>
            </div>
            <span class="tkonto-saldo ${saldoClass}">${saldoText}</span>
          </div>
          <div class="tkonto-body">
            <div class="tkonto-col">
              <div class="tkonto-col-header">
                <span>Soll</span>
                <span class="col-sum">${fmt(sollSum)} €</span>
              </div>
              ${renderEntries(data.soll,  'keine Sollbuchungen',  'soll')}
            </div>
            <div class="tkonto-col">
              <div class="tkonto-col-header">
                <span>Haben</span>
                <span class="col-sum">${fmt(habenSum)} €</span>
              </div>
              ${renderEntries(data.haben, 'keine Habenbuchungen', 'haben')}
            </div>
          </div>
        </div>`;
    }).join('');

    if (!grid.innerHTML.trim()) {
      grid.innerHTML = '<div style="color:var(--text-dim);font-family:var(--mono);font-size:12px;padding:20px 0">Keine Konten vorhanden</div>';
    }

    // Saldenliste rendern
    const tbody = $('tbl-saldenliste');
    const saldoRows = kontenList.map(k => {
      const data = kontoMap[k.id] || { soll: [], haben: [] };
      const sollSum  = data.soll.reduce((s, b)  => s + Number(b.betrag), 0);
      const habenSum = data.haben.reduce((s, b) => s + Number(b.betrag), 0);
      const saldo    = sollSum - habenSum;
      return { k, sollSum, habenSum, saldo };
    });

    tbody.innerHTML = saldoRows.map(({ k, sollSum, habenSum, saldo }) => {
      const richtung = saldo > 0
        ? `<span class="badge" style="background:rgba(0,201,122,0.1);color:var(--accent);border:1px solid rgba(0,201,122,0.2)">Soll</span>`
        : saldo < 0
          ? `<span class="badge" style="background:rgba(74,158,255,0.1);color:var(--blue);border:1px solid rgba(74,158,255,0.2)">Haben</span>`
          : `<span style="color:var(--text-dim);font-family:var(--mono);font-size:11px">ausgeglichen</span>`;
      return `
        <tr>
          <td class="mono" style="color:var(--accent)">${k.kontonummer}</td>
          <td>${k.kontoname}</td>
          <td class="mono" style="text-align:right;color:var(--accent)">${fmt(sollSum)} €</td>
          <td class="mono" style="text-align:right;color:var(--blue)">${fmt(habenSum)} €</td>
          <td class="mono" style="text-align:right;font-weight:600;color:${saldo === 0 ? 'var(--text-dim)' : saldo > 0 ? 'var(--accent)' : 'var(--blue)'}">${fmt(Math.abs(saldo))} €</td>
          <td>${richtung}</td>
        </tr>`;
    }).join('');

    if (!saldoRows.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Keine Konten vorhanden</td></tr>';
    }

  } catch(e) { toast('T-Konto-Fehler: ' + e.message, 'err'); }
}

// ─────────────────────────────────────────────
// Sammelbuchung
// ─────────────────────────────────────────────
let sbStep = 1;
let sbMitglieder = [];   // alle aktuellen Mitglieder
let sbSelected = new Set();  // gewählte Mitglied-IDs

async function openSammelbuchungModal() {
  // Daten laden
  if (!kontenList.length) kontenList = await api('/konten/');
  sbMitglieder = await api('/members/?nur_aktuell=true');

  // Konten-Selects befüllen
  const kontoOpts = kontenList.map(k =>
    `<option value="${k.id}">${k.kontonummer} – ${k.kontoname}</option>`).join('');
  $('sb-soll').innerHTML  = kontoOpts;
  $('sb-haben').innerHTML = kontoOpts;

  // Datum vorbelegen
  $('sb-datum').value = today();
  $('sb-betrag-alle').value = '';
  $('sb-text').value = '';

  // Mitglieder-Grid rendern
  sbSelected.clear();
  sbRenderMemberGrid();

  // Auf Schritt 1 zurücksetzen
  sbGoTo(1);
  openModal('modal-sammelbuchung');
}

function sbRenderMemberGrid() {
  $('sb-member-grid').innerHTML = sbMitglieder.map(m => `
    <label class="member-chip ${sbSelected.has(m.id) ? 'selected' : ''}" onclick="sbToggle(${m.id}, this)">
      <input type="checkbox" ${sbSelected.has(m.id) ? 'checked' : ''}
             onclick="event.stopPropagation();sbToggle(${m.id},this.closest('.member-chip'))">
      <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${m.name}</span>
      <span class="badge badge-${m.status}" style="font-size:9px;padding:1px 5px">${m.status}</span>
    </label>`).join('');
  sbUpdateCount();
}

function sbToggle(id, chip) {
  if (sbSelected.has(id)) {
    sbSelected.delete(id);
    chip.classList.remove('selected');
    chip.querySelector('input').checked = false;
  } else {
    sbSelected.add(id);
    chip.classList.add('selected');
    chip.querySelector('input').checked = true;
  }
  sbUpdateCount();
}

function sbSelectAll()  { sbMitglieder.forEach(m => sbSelected.add(m.id));    sbRenderMemberGrid(); }
function sbSelectNone() { sbSelected.clear(); sbRenderMemberGrid(); }
function sbUpdateCount() { $('sb-selected-count').textContent = sbSelected.size; }

function sbFillAll() {
  const val = $('sb-betrag-alle').value;
  document.querySelectorAll('.betrag-input').forEach(inp => { inp.value = val; });
}

function sbRenderBetragTable() {
  const selected = sbMitglieder.filter(m => sbSelected.has(m.id));
  $('sb-betrag-tbody').innerHTML = selected.map(m => `
    <tr>
      <td style="font-weight:500">${m.name}</td>
      <td><span class="badge badge-${m.status}">${m.status}</span></td>
      <td style="text-align:right">
        <input type="number" class="betrag-input" data-mid="${m.id}"
               step="0.01" min="0.01" placeholder="0.00">
      </td>
    </tr>`).join('');
}

function sbRenderPreview() {
  const soll  = kontenList.find(k => k.id === parseInt($('sb-soll').value));
  const haben = kontenList.find(k => k.id === parseInt($('sb-haben').value));
  const datum = $('sb-datum').value;
  const text  = $('sb-text').value.trim();

  // Mitglieder-Map für schnellen Zugriff per ID
  const memberMap = Object.fromEntries(sbMitglieder.map(m => [m.id, m]));

  const rows = [];
  document.querySelectorAll('#sb-betrag-tbody .betrag-input').forEach(inp => {
    const mid    = parseInt(inp.dataset.mid);
    const betrag = parseFloat(inp.value);
    const m      = memberMap[mid];
    if (!m || !betrag || betrag <= 0) return;
    rows.push({ m, betrag, soll, haben, datum, text });
  });

  $('sb-preview-count').textContent = rows.length;
  const total = rows.reduce((s, r) => s + r.betrag, 0);
  $('sb-preview-total').textContent = fmt(total) + ' €';

  $('sb-preview-list').innerHTML = `
    <div class="sb-preview-row header">
      <span>Mitglied</span>
      <span>Soll</span>
      <span>Haben</span>
      <span style="text-align:right">Betrag</span>
    </div>` +
    (rows.length ? rows.map(r => `
      <div class="sb-preview-row">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.m.name}</span>
        <span class="mono" style="color:var(--accent);font-size:11px">${r.soll?.kontonummer || '?'}</span>
        <span class="mono" style="color:var(--blue);font-size:11px">${r.haben?.kontonummer || '?'}</span>
        <span class="mono" style="text-align:right;font-weight:600">${fmt(r.betrag)} €</span>
      </div>`).join('')
    : '<div style="padding:20px;text-align:center;color:var(--text-dim);font-family:var(--mono);font-size:12px">Keine gültigen Beträge eingegeben</div>');

  return rows;
}

function sbGoTo(step) {
  sbStep = step;
  [1,2,3].forEach(i => {
    $(`sbstep-${i}`).className  = 'sb-step' + (i === step ? ' active' : i < step ? ' done' : '');
    $(`sbpanel-${i}`).className = 'modal-body sb-panel' + (i === step ? ' active' : '');
  });
  $('sb-btn-back').style.display = step > 1 ? '' : 'none';
  $('sb-btn-next').textContent   = step === 3 ? '✓ Buchen' : 'Weiter →';
}

function sbBack() { sbGoTo(sbStep - 1); }

async function sbNext() {
  if (sbStep === 1) {
    if (sbSelected.size === 0) { toast('Bitte mindestens ein Mitglied wählen', 'err'); return; }
    sbRenderBetragTable();
    sbGoTo(2);

  } else if (sbStep === 2) {
    const soll  = parseInt($('sb-soll').value);
    const haben = parseInt($('sb-haben').value);
    if (soll === haben) { toast('Soll- und Habenkonto dürfen nicht identisch sein', 'err'); return; }
    if (!$('sb-datum').value) { toast('Buchungsdatum ist Pflicht', 'err'); return; }

    // Mindestens ein Betrag > 0?
    const inputs = [...document.querySelectorAll('.betrag-input')];
    const valid  = inputs.filter(i => parseFloat(i.value) > 0);
    if (!valid.length) { toast('Bitte mindestens einen Betrag eingeben', 'err'); return; }

    sbRenderPreview();
    $('sb-progress-wrap').style.display = 'none';
    sbGoTo(3);

  } else if (sbStep === 3) {
    await sbSaveAll();
  }
}

async function sbSaveAll() {
  const soll  = parseInt($('sb-soll').value);
  const haben = parseInt($('sb-haben').value);
  const datum = $('sb-datum').value;
  const text  = $('sb-text').value.trim() || null;

  // Zeilen aus der Betrag-Tabelle sammeln
  const buchungen = [];
  document.querySelectorAll('#sb-betrag-tbody .betrag-input').forEach(inp => {
    const betrag = parseFloat(inp.value);
    if (!betrag || betrag <= 0) return;
    buchungen.push({ sollkonto_id: soll, habenkonto_id: haben,
      betrag: betrag.toFixed(2), buchungsdatum: datum,
      buchungstext: text, mitglied_id: parseInt(inp.dataset.mid) });
  });

  if (!buchungen.length) { toast('Keine buchbaren Zeilen', 'err'); return; }

  // UI blockieren, Fortschritt anzeigen
  $('sb-btn-next').disabled = true;
  $('sb-btn-next').textContent = 'Buche…';
  $('sb-progress-wrap').style.display = '';
  const bar = $('sb-progress-bar');

  let done = 0, errors = 0;
  for (const payload of buchungen) {
    try {
      await api('/buchungen/', { method: 'POST', body: JSON.stringify(payload) });
    } catch(e) {
      errors++;
    }
    done++;
    bar.style.width = Math.round((done / buchungen.length) * 100) + '%';
  }

  $('sb-btn-next').disabled = false;
  closeModal('modal-sammelbuchung');

  if (errors === 0) {
    toast(`${done} Buchung${done !== 1 ? 'en' : ''} erfolgreich angelegt`);
  } else {
    toast(`${done - errors} von ${done} Buchungen angelegt (${errors} Fehler)`, 'err');
  }
  loadBuchungen();
}

// ─────────────────────────────────────────────
// ─────────────────────────────────────────────
$('m-von').value  = today();
$('sw-ab').value  = today();
$('b-datum').value = today();

checkHealth();
loadDashboard();
