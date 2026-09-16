'use strict';

let _state = null;
let _activeKey = 'may-june';

const API = {
  state: () => fetch('/api/state').then(r => r.json()),
  alert: (id) => fetch('/api/alerts/' + id).then(r => {
    if (!r.ok) return r.json().then(e => Promise.reject(e));
    return r.json();
  }),
  replay: (key) => fetch('/api/replay/' + key, {method: 'POST'}).then(r => {
    if (!r.ok) return r.json().then(e => Promise.reject(e));
    return r.json();
  }),
};

// ── Init ─────────────────────────────────────────────────────────────────

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
  } catch (e) {
    document.getElementById('alert-feed').innerHTML =
      '<div class="feed-loading" style="color:#e53e3e">Failed to load state. Check server.</div>';
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
    btn.innerHTML = '<span class="spinner"></span> Running…';
    renderPhases(false);

    try {
      const result = await API.replay(_activeKey);
      _state[_activeKey] = {
        run: result.run,
        comparison: result.comparison,
        candidates: result.candidates,
      };
      renderView(_activeKey);
    } catch (e) {
      const msg = (e && e.detail) ? e.detail : 'Replay failed.';
      document.getElementById('run-metrics').innerHTML =
        '<span style="color:#e53e3e;font-size:.875rem">' + esc(msg) + '</span>';
    } finally {
      btn.disabled = false;
      btn.innerHTML = '► Run Agent Cycle';
    }
  });
}

// ── Render ────────────────────────────────────────────────────────────────

function renderView(key) {
  if (!_state || !_state[key]) return;
  const data = _state[key];
  renderPhases(!!data.run);
  renderMetrics(data);
  renderFeed(data.candidates || []);
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
  const run = data.run;
  const comp = data.comparison;
  if (!run) {
    document.getElementById('run-metrics').innerHTML =
      '<span class="metric-loading">No cycle run yet for this period.</span>';
    return;
  }
  const priorStr = comp ? comp.fleet_prior_ota_pct.toFixed(2) + '%' : '—';
  const currentStr = comp ? comp.fleet_current_ota_pct.toFixed(2) + '%' : '—';
  const deltaStr = comp
    ? (comp.fleet_ota_pp_change >= 0 ? '+' : '') + comp.fleet_ota_pp_change.toFixed(2) + ' pp'
    : '—';
  const breachClass = run.breach_count > 0 ? ' alert' : '';

  document.getElementById('run-metrics').innerHTML =
    '<div class="metric">' +
      '<div class="val">' + run.eligible_vendor_count + '</div>' +
      '<div class="lbl">eligible vendors</div>' +
    '</div>' +
    '<div class="metric' + breachClass + '">' +
      '<div class="val">' + run.breach_count + '</div>' +
      '<div class="lbl">deteriorations</div>' +
    '</div>' +
    '<div class="metric">' +
      '<div class="val">' + priorStr + ' → ' + currentStr + '</div>' +
      '<div class="lbl">fleet OTA (' + deltaStr + ')</div>' +
    '</div>';
}

function renderFeed(candidates) {
  const feed = document.getElementById('alert-feed');
  if (!candidates.length) {
    feed.innerHTML =
      '<div class="empty-state">' +
        '<div class="empty-icon">✅</div>' +
        '<h3>No Deterioration Detected</h3>' +
        '<p>All eligible vendors maintained OTA within the configured threshold.</p>' +
      '</div>';
    return;
  }
  feed.innerHTML = candidates.map(cardHTML).join('');
  feed.querySelectorAll('.alert-card').forEach(card => {
    card.addEventListener('click', () => openDetail(card.dataset.alertId));
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDetail(card.dataset.alertId); }
    });
  });
}

function cardHTML(c) {
  let tags = '<span class="card-tag">' + c.current_total_count.toLocaleString() + ' trips</span>';
  tags += '<span class="card-tag">Fleet ' +
    (c.fleet_ota_pp_change >= 0 ? '+' : '') + c.fleet_ota_pp_change.toFixed(2) + ' pp</span>';
  if (c.top_non_nodelay_reason) {
    tags += '<span class="card-tag">Recorded: ' + esc(c.top_non_nodelay_reason) + '</span>';
  }
  if (c.nodelay_dominates) {
    tags += '<span class="card-tag nodelay">NODELAY dominant</span>';
  }
  return '<div class="alert-card" role="listitem" tabindex="0" data-alert-id="' + c.alert_id + '">' +
    '<div class="card-vendor">' + esc(c.vendor_id) + '</div>' +
    '<div class="card-ota-row">' +
      '<span class="card-ota">' + c.prior_ota_pct.toFixed(1) + '%</span>' +
      '<span class="card-arrow">→</span>' +
      '<span class="card-ota">' + c.current_ota_pct.toFixed(1) + '%</span>' +
      '<span class="card-delta">' + c.ota_pp_change.toFixed(2) + ' pp</span>' +
    '</div>' +
    '<div class="card-meta">' + tags + '</div>' +
    '</div>';
}

// ── Modal ─────────────────────────────────────────────────────────────────

function setupModal() {
  document.querySelector('.modal-backdrop').addEventListener('click', closeModal);
  document.querySelector('.modal-close').addEventListener('click', closeModal);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
}

async function openDetail(alertId) {
  const modal = document.getElementById('modal');
  const body = document.getElementById('modal-body');
  body.innerHTML =
    '<div style="text-align:center;padding:3rem">' +
    '<span class="spinner" style="width:32px;height:32px;border-width:3px"></span></div>';
  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  try {
    const d = await API.alert(alertId);
    body.innerHTML = detailHTML(d);
  } catch (e) {
    body.innerHTML = '<p style="color:#e53e3e;padding:1rem">Failed to load alert detail.</p>';
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

  const narrative = d.narrative
    ? '<div class="narrative-section">' +
      '<h3>Operational Brief</h3>' +
      '<div class="narrative-text">' + esc(d.narrative) + '</div>' +
      '<div class="narrative-caution">Recorded delay context shows operational data only. ' +
      'Causality cannot be inferred from delay reason codes alone.</div>' +
      '</div>'
    : '';

  return '<div class="modal-vendor">' + esc(d.vendor_id) + '</div>' +
    '<div class="modal-period">' + esc(d.prior_period) + ' → ' + esc(d.current_period) +
    ' · OTA deterioration detected</div>' +

    '<div class="detail-grid">' +

    '<div class="detail-section"><h3>Vendor Evidence</h3>' +
    dr('Prior OTA', d.prior_ota_pct.toFixed(2) + '%') +
    dr('Current OTA', d.current_ota_pct.toFixed(2) + '%') +
    drNeg('OTA Change', d.ota_pp_change.toFixed(2) + ' pp') +
    dr('Prior trips', d.prior_total_count.toLocaleString()) +
    dr('Current trips', d.current_total_count.toLocaleString()) +
    '</div>' +

    '<div class="detail-section"><h3>Fleet Context</h3>' +
    dr('Fleet prior OTA', d.fleet_prior_ota_pct.toFixed(2) + '%') +
    dr('Fleet current OTA', d.fleet_current_ota_pct.toFixed(2) + '%') +
    dr('Fleet change', d.fleet_ota_pp_change.toFixed(2) + ' pp') +
    dr('Eligible vendors', String(d.eligible_vendor_count)) +
    dr('Breaches', d.breach_count + ' of ' + d.eligible_vendor_count +
      ' (' + d.breach_pct.toFixed(1) + '%)') +
    '</div>' +

    '<div class="detail-section"><h3>Recorded Delay Context</h3>' +
    dr('Total late trips', d.total_late_count.toLocaleString()) +
    dr('NODELAY', d.nodelay_count.toLocaleString() +
      ' (' + (d.nodelay_share * 100).toFixed(1) + '%)') +
    dr('NODELAY dominates', d.nodelay_dominates ? 'Yes' : 'No') +
    dr('Top non-NODELAY', esc(d.top_non_nodelay_reason || '—')) +
    (d.top_non_nodelay_reason
      ? dr('Top reason count', d.top_non_nodelay_count.toLocaleString() +
          ' (' + (d.top_non_nodelay_share * 100).toFixed(1) + '% of late)')
      : '') +
    '<table class="dist-table">' + distRows + '</table>' +
    '<div class="caution-note">Recorded delay context — not a causal determination.</div>' +
    '</div>' +

    '<div class="detail-section"><h3>Policy</h3>' +
    dr('T_SECONDS', d.T_seconds + 's (' + (d.T_seconds / 60) + ' min)') +
    dr('VOL_MIN', d.vol_min.toLocaleString()) +
    dr('Threshold', '&gt;' + d.deterioration_threshold_pp + ' pp') +
    dr('Policy version', esc(d.policy_version)) +
    '<div class="detail-row"><span class="dk">Alert ID</span>' +
    '<span class="dv" style="font-size:.68rem;word-break:break-all">' + d.alert_id + '</span></div>' +
    '</div>' +

    '</div>' + narrative;
}

function dr(key, val) {
  return '<div class="detail-row"><span class="dk">' + key +
    '</span><span class="dv">' + val + '</span></div>';
}
function drNeg(key, val) {
  return '<div class="detail-row"><span class="dk">' + key +
    '</span><span class="dv neg">' + val + '</span></div>';
}

function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
