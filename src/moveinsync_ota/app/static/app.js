'use strict';

let _state = null;
let _activeKey = 'may-june';

// ── API ───────────────────────────────────────────────────────────────────

const API = {
  state: () => fetch('/api/state').then(r => r.json()),
  alert: id => fetch('/api/alerts/' + id).then(r => {
    if (!r.ok) return r.json().then(e => Promise.reject(e));
    return r.json();
  }),
  replay: key => fetch('/api/replay/' + key, { method: 'POST' }).then(r => {
    if (!r.ok) return r.json().then(e => Promise.reject(e));
    return r.json();
  }),
};

// ── Init ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupReplayButton();
  setupModal();
  loadAndRender();
});

async function loadAndRender() {
  try {
    _state = await API.state();
    renderView(_activeKey);
  } catch (_e) {
    document.getElementById('alert-feed').innerHTML =
      '<div class="feed-loading" style="color:var(--red)">Failed to load state. Check server.</div>';
  }
}

// ── Tabs ──────────────────────────────────────────────────────────────────

function setupTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      _activeKey = tab.dataset.key;
      document.querySelectorAll('.tab').forEach(t => {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      renderView(_activeKey);
    });
  });
}

// ── Replay ────────────────────────────────────────────────────────────────

function setupReplayButton() {
  document.getElementById('run-replay').addEventListener('click', async () => {
    const btn = document.getElementById('run-replay');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running&hellip;';
    renderPhases(false);

    try {
      const result = await API.replay(_activeKey);
      _state[_activeKey] = {
        run:        result.run,
        comparison: result.comparison,
        candidates: result.candidates,
      };
      renderView(_activeKey);
    } catch (e) {
      const msg = (e && e.detail) ? e.detail : 'Replay failed.';
      document.getElementById('run-metrics').innerHTML =
        '<span style="color:var(--red);font-size:.875rem">' + esc(msg) + '</span>';
    } finally {
      btn.disabled = false;
      btn.innerHTML = '&#9654; Run Agent Cycle';
    }
  });
}

// ── Render ────────────────────────────────────────────────────────────────

function renderView(key) {
  if (!_state || !_state[key]) return;
  const data = _state[key];
  renderPhases(!!data.run);
  renderMetrics(data);
  renderFeed(data.candidates || [], data.run);
}

function renderPhases(complete) {
  ['sense', 'reason', 'act'].forEach(p => {
    const el = document.getElementById('phase-' + p);
    if (!el) return;
    if (complete) {
      el.className = 'phase done';
      el.textContent = p.toUpperCase() + ' ✓';
    } else {
      el.className = 'phase pending';
      el.textContent = p.toUpperCase();
    }
  });
}

function renderMetrics(data) {
  const run  = data.run;
  const comp = data.comparison;
  if (!run) {
    document.getElementById('run-metrics').innerHTML =
      '<span class="metric-loading">No cycle run yet for this period.</span>';
    return;
  }
  const priorStr   = comp ? comp.fleet_prior_ota_pct.toFixed(2) + '%' : '—';
  const currentStr = comp ? comp.fleet_current_ota_pct.toFixed(2) + '%' : '—';
  const deltaVal   = comp ? comp.fleet_ota_pp_change : null;
  const deltaStr   = deltaVal !== null
    ? (deltaVal >= 0 ? '+' : '') + deltaVal.toFixed(2) + ' pp'
    : '—';
  const alertCls = run.breach_count > 0 ? ' alert' : ' ok';

  document.getElementById('run-metrics').innerHTML =
    '<div class="kpi-block">' +
      '<div class="kpi-value">' + run.eligible_vendor_count + '</div>' +
      '<div class="kpi-label">Eligible Vendors</div>' +
    '</div>' +
    '<div class="kpi-block' + alertCls + '">' +
      '<div class="kpi-value">' + run.breach_count + '</div>' +
      '<div class="kpi-label">Deterioration Alerts</div>' +
    '</div>' +
    '<div class="kpi-block">' +
      '<div class="kpi-value">' + priorStr + ' → ' + currentStr + '</div>' +
      '<div class="kpi-label">Fleet OTA</div>' +
      '<div class="kpi-sub">' + deltaStr + '</div>' +
    '</div>';
}

function renderFeed(candidates, run) {
  const feed    = document.getElementById('alert-feed');
  const countEl = document.getElementById('feed-count');
  if (countEl) {
    if (candidates.length > 0) {
      countEl.textContent = candidates.length + (candidates.length === 1 ? ' alert' : ' alerts');
      countEl.style.display = 'inline';
    } else {
      countEl.style.display = 'none';
    }
  }
  if (!candidates.length) {
    const eligibleText = run ? run.eligible_vendor_count + ' vendors' : 'All vendors';
    feed.innerHTML =
      '<div class="empty-state">' +
        '<div class="empty-icon" aria-hidden="true">✓</div>' +
        '<h3>No material OTA deterioration detected</h3>' +
        '<p>' + esc(eligibleText) + ' met the volume threshold.</p>' +
        '<p>No vendor exceeded the configured &gt;5&nbsp;pp deterioration trigger.</p>' +
        '<p>Demo policy defaults applied.</p>' +
      '</div>';
    return;
  }
  feed.innerHTML = candidates.map(cardHTML).join('');
  feed.querySelectorAll('.alert-card').forEach(card => {
    card.addEventListener('click', () => openDetail(card.dataset.alertId));
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openDetail(card.dataset.alertId);
      }
    });
  });
}

function cardHTML(c) {
  const deltaStr = c.ota_pp_change.toFixed(2) + ' pp';
  const tags = [
    c.current_total_count.toLocaleString() + ' trips',
    'Fleet ' + (c.fleet_ota_pp_change >= 0 ? '+' : '') + c.fleet_ota_pp_change.toFixed(2) + ' pp',
  ];
  if (c.top_non_nodelay_reason) {
    tags.push('Recorded: ' + esc(c.top_non_nodelay_reason));
  }
  const nodDelayBadge = c.nodelay_dominates
    ? '<span class="nodelay-badge">NODELAY-dominant data</span>'
    : '';
  return (
    '<div class="alert-card" role="listitem" tabindex="0" data-alert-id="' + c.alert_id + '">' +
      '<div class="card-vendor">' + esc(c.vendor_id) + '</div>' +
      '<div class="card-ota-row">' +
        '<span class="card-ota">' + c.prior_ota_pct.toFixed(1) + '%</span>' +
        '<span class="card-arrow">→</span>' +
        '<span class="card-ota">' + c.current_ota_pct.toFixed(1) + '%</span>' +
        '<span class="card-delta-pill">' + deltaStr + '</span>' +
      '</div>' +
      '<div class="card-meta">' +
        tags.map(t => '<span class="card-tag">' + t + '</span>').join('') +
        nodDelayBadge +
      '</div>' +
    '</div>'
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────

function setupModal() {
  document.querySelector('.modal-backdrop').addEventListener('click', closeModal);
  document.querySelector('.modal-close').addEventListener('click', closeModal);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
}

async function openDetail(alertId) {
  const modal = document.getElementById('modal');
  const body  = document.getElementById('modal-body');
  body.innerHTML =
    '<div style="text-align:center;padding:4rem">' +
    '<span class="spinner" style="width:28px;height:28px;border-width:3px"></span></div>';
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  try {
    const d = await API.alert(alertId);
    body.innerHTML = detailHTML(d);
  } catch (_e) {
    body.innerHTML = '<p style="color:var(--red);padding:1.5rem">Failed to load alert detail.</p>';
  }
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  document.body.style.overflow = '';
}

function detailHTML(d) {
  const distRows = Object.entries(d.full_distribution || {})
    .sort((a, b) => b[1] - a[1])
    .map(e => '<tr><td>' + esc(e[0]) + '</td><td>' + e[1].toLocaleString() + '</td></tr>')
    .join('');

  const nodDelayBadge = d.nodelay_dominates
    ? '<span class="amber-badge">Data-quality signal: NODELAY dominates recorded reasons</span>'
    : '';

  const narrative = d.narrative
    ? '<div class="brief-card">' +
        '<div class="brief-header">' +
          '<h3>Claude Operational Brief</h3>' +
          '<span class="brief-label">Generated from deterministic alert evidence</span>' +
        '</div>' +
        '<div class="brief-text">' + esc(d.narrative) + '</div>' +
        '<div class="brief-caution">Recorded delay context shows operational data only. ' +
          'Causality cannot be inferred from delay reason codes alone.</div>' +
      '</div>'
    : '';

  return (
    '<div class="modal-head">' +
      '<div class="modal-vendor">' + esc(d.vendor_id) + '</div>' +
      '<div class="modal-subtitle">OTA Deterioration Alert &nbsp;&middot;&nbsp; ' +
        esc(d.prior_period) + ' → ' + esc(d.current_period) +
      '</div>' +
    '</div>' +

    '<div class="evidence-section">' +
      '<h3 class="section-label">Vendor Evidence</h3>' +
      '<div class="tile-grid">' +
        tile('Prior OTA',     d.prior_ota_pct.toFixed(2) + '%') +
        tile('Current OTA',   d.current_ota_pct.toFixed(2) + '%') +
        tileNeg('OTA Change', d.ota_pp_change.toFixed(2) + ' pp') +
        tile('Current trips', d.current_total_count.toLocaleString()) +
      '</div>' +
    '</div>' +

    '<div class="evidence-section">' +
      '<h3 class="section-label">Fleet Context</h3>' +
      '<div class="tile-grid">' +
        tile('Fleet OTA',
          d.fleet_prior_ota_pct.toFixed(2) + '% → ' + d.fleet_current_ota_pct.toFixed(2) + '%') +
        tile('Fleet change',     d.fleet_ota_pp_change.toFixed(2) + ' pp') +
        tile('Eligible vendors', String(d.eligible_vendor_count)) +
        tile('Breaches',
          d.breach_count + ' of ' + d.eligible_vendor_count +
          ' (' + d.breach_pct.toFixed(1) + '%)') +
      '</div>' +
    '</div>' +

    '<div class="evidence-section">' +
      '<h3 class="section-label">Recorded Delay Context</h3>' +
      '<p class="section-note">Contextual evidence only — not a causal determination.</p>' +
      '<div class="tile-grid">' +
        tile('Total late trips', d.total_late_count.toLocaleString()) +
        tile('NODELAY',
          d.nodelay_count.toLocaleString() + ' (' + (d.nodelay_share * 100).toFixed(1) + '%)') +
        tile('NODELAY dominates', d.nodelay_dominates ? 'Yes' : 'No') +
        tile('Top non-NODELAY',   esc(d.top_non_nodelay_reason || '—')) +
      '</div>' +
      nodDelayBadge +
      '<table class="dist-table">' +
        '<thead><tr>' +
          '<th>Reason</th>' +
          '<th style="text-align:right">Trips</th>' +
        '</tr></thead>' +
        '<tbody>' + distRows + '</tbody>' +
      '</table>' +
    '</div>' +

    narrative +

    '<div class="evidence-section policy-section">' +
      '<h3 class="section-label">Demo Policy</h3>' +
      '<div class="tile-grid">' +
        tile('T_SECONDS',      d.T_seconds + 's (5 min)') +
        tile('Vol min',        d.vol_min.toLocaleString()) +
        tile('Threshold',      '>' + d.deterioration_threshold_pp + ' pp') +
        tile('Policy version', esc(d.policy_version)) +
      '</div>' +
      '<div class="alert-id-row">Alert ID: <span class="alert-id">' + d.alert_id + '</span></div>' +
    '</div>'
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────

function tile(key, val) {
  return (
    '<div class="tile">' +
      '<div class="tile-lbl">' + key + '</div>' +
      '<div class="tile-val">' + val + '</div>' +
    '</div>'
  );
}

function tileNeg(key, val) {
  return (
    '<div class="tile">' +
      '<div class="tile-lbl">' + key + '</div>' +
      '<div class="tile-val neg">' + val + '</div>' +
    '</div>'
  );
}

function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;');
}
