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
    const replayKey = _activeKey;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Running&hellip;';
    renderPhases(false, 0);

    try {
      const result = await API.replay(replayKey);
      _state[replayKey] = {
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
  const run  = data.run;
  renderPhases(!!run, run ? run.breach_count : 0);
  renderDecisionHeadline(data);
  renderTimestamp(run);
  renderMetrics(data);
  renderFeed(data.candidates || [], run, data.comparison);
}

function renderPhases(complete, breachCount) {
  const desc = {
    sense:  'Monthly ride evidence',
    reason: 'OTA + volume + fleet context',
    act:    complete
      ? (breachCount > 0
          ? breachCount + ' evidence-backed alert' + (breachCount === 1 ? '' : 's')
          : 'No material deterioration detected')
      : '',
  };
  ['sense', 'reason', 'act'].forEach(p => {
    const el = document.getElementById('phase-' + p);
    if (!el) return;
    if (complete) {
      el.className = 'phase done';
      el.innerHTML =
        '<span class="phase-check">&#10003;</span>' +
        '<span class="phase-name">' + p.toUpperCase() + '</span>' +
        (desc[p] ? '<span class="phase-desc">' + desc[p] + '</span>' : '');
    } else {
      el.className = 'phase pending';
      el.innerHTML =
        '<span class="phase-name">' + p.toUpperCase() + '</span>' +
        (desc[p] ? '<span class="phase-desc">' + desc[p] + '</span>' : '');
    }
  });
}

function renderDecisionHeadline(data) {
  const el   = document.getElementById('decision-headline');
  if (!el) return;
  const run  = data.run;
  const comp = data.comparison;
  if (!run) {
    el.className = 'decision-headline neutral';
    el.innerHTML = '<span class="decision-text">Run the agent cycle to evaluate this analysis window.</span>';
    return;
  }
  const threshold    = comp ? comp.deterioration_threshold_pp : null;
  const thresholdStr = threshold !== null
    ? '&gt;' + threshold + ' percentage-point'
    : 'the configured';
  if (run.breach_count > 0) {
    el.className = 'decision-headline breach';
    el.innerHTML =
      '<span class="decision-flag">ATTENTION REQUIRED</span>' +
      '<span class="decision-text">' +
        run.breach_count + ' of ' + run.eligible_vendor_count +
        ' eligible vendors crossed the configured ' + thresholdStr +
        ' deterioration threshold.' +
      '</span>';
  } else {
    el.className = 'decision-headline clear';
    el.innerHTML =
      '<span class="decision-flag">NO MATERIAL DETERIORATION DETECTED</span>' +
      '<span class="decision-text">' +
        'No eligible vendor crossed the configured ' + thresholdStr +
        ' deterioration threshold.' +
      '</span>';
  }
}

function renderTimestamp(run) {
  const el = document.getElementById('run-timestamp');
  if (!el) return;
  if (!run || !run.completed_at) { el.textContent = ''; return; }
  try {
    const dt      = new Date(run.completed_at);
    const fmtDate = dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' });
    const fmtTime = dt.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' });
    el.textContent = 'Last agent run · ' + fmtDate + ', ' + fmtTime + ' UTC';
  } catch (_e) {
    el.textContent = '';
  }
}

function renderMetrics(data) {
  const run  = data.run;
  const comp = data.comparison;
  if (!run) {
    document.getElementById('run-metrics').innerHTML =
      '<span class="metric-loading">Run the agent cycle to evaluate OTA deterioration.</span>';
    return;
  }
  const priorStr   = comp ? comp.fleet_prior_ota_pct.toFixed(2) + '%' : '—';
  const currentStr = comp ? comp.fleet_current_ota_pct.toFixed(2) + '%' : '—';
  const deltaVal   = comp ? comp.fleet_ota_pp_change : null;
  const arrowChar  = deltaVal === null ? '' : deltaVal < 0 ? '↓ ' : deltaVal > 0 ? '↑ ' : '';
  const deltaStr   = deltaVal !== null
    ? arrowChar + Math.abs(deltaVal).toFixed(2) + ' pts'
    : '—';
  const deltaCls   = deltaVal === null ? '' : deltaVal < 0 ? ' neg' : deltaVal > 0 ? ' pos' : '';
  const alertCls   = run.breach_count > 0 ? ' alert' : ' ok';

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
      '<div class="kpi-sub' + deltaCls + '">' + deltaStr + '</div>' +
    '</div>' +
    '<div class="kpi-hint">pts = percentage-point change</div>';
}

function renderFeed(candidates, run, comparison) {
  const feed       = document.getElementById('alert-feed');
  const countEl    = document.getElementById('feed-count');
  const titleEl    = document.getElementById('feed-title');
  const subtitleEl = document.getElementById('feed-subtitle');

  // Update heading to reflect current run state
  if (!run) {
    if (titleEl)    titleEl.textContent    = 'Vendor Alert Feed';
    if (subtitleEl) subtitleEl.textContent = 'Run the agent cycle to evaluate this analysis window.';
    if (countEl)    countEl.style.display  = 'none';
    feed.innerHTML =
      '<div class="feed-loading">' +
        'Run the agent cycle to evaluate OTA deterioration.' +
      '</div>';
    return;
  }

  if (run.breach_count > 0) {
    if (titleEl)    titleEl.textContent    = 'Vendors Requiring Attention';
    if (subtitleEl) subtitleEl.textContent = 'Evidence-backed alerts that crossed the configured deterioration threshold.';
  } else {
    if (titleEl)    titleEl.textContent    = 'No Vendors Requiring Attention';
    if (subtitleEl) subtitleEl.textContent = 'No evidence-backed alerts were generated for this analysis window.';
  }

  if (countEl) {
    if (candidates.length > 0) {
      countEl.textContent = candidates.length + (candidates.length === 1 ? ' alert' : ' alerts');
      countEl.style.display = 'inline';
    } else {
      countEl.style.display = 'none';
    }
  }

  if (!candidates.length) {
    feed.innerHTML =
      '<div class="zero-alert-note">' +
        '<span class="zero-check" aria-hidden="true">&#10003;</span>' +
        '<span>No vendor alerts generated for this analysis window.</span>' +
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
  const ota_arrow  = c.ota_pp_change < 0 ? '↓ ' : c.ota_pp_change > 0 ? '↑ ' : '';
  const deltaStr   = ota_arrow + Math.abs(c.ota_pp_change).toFixed(2) + ' pts';
  const fleetArrow = c.fleet_ota_pp_change < 0 ? '↓ ' : c.fleet_ota_pp_change > 0 ? '↑ ' : '';
  const fleetStr   = 'Fleet ' + fleetArrow + Math.abs(c.fleet_ota_pp_change).toFixed(2) + ' pts';

  const tags = [
    c.current_total_count.toLocaleString() + ' trips',
    fleetStr,
  ];
  if (c.top_non_nodelay_reason) {
    tags.push('Top non-NODELAY: ' + esc(c.top_non_nodelay_reason));
  }

  const nodDelayBadge = c.nodelay_dominates
    ? '<span class="nodelay-badge">NODELAY most frequent label</span>'
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
      '<div class="card-cta-row">' +
        '<span class="card-cta">View evidence →</span>' +
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

  const changeArrow = d.ota_pp_change < 0 ? '↓ ' : d.ota_pp_change > 0 ? '↑ ' : '';
  const changeStr   = changeArrow + Math.abs(d.ota_pp_change).toFixed(2) + ' pts';
  const fleetArrow  = d.fleet_ota_pp_change < 0 ? '↓ ' : d.fleet_ota_pp_change > 0 ? '↑ ' : '';
  const fleetStr    = fleetArrow + Math.abs(d.fleet_ota_pp_change).toFixed(2) + ' pts';

  const nodDelayBadge = d.nodelay_dominates
    ? '<span class="amber-badge">Recorded-label pattern: NODELAY is the most frequent recorded reason</span>'
    : '';

  const toleranceMins = Math.round(d.T_seconds / 60);

  const briefCard = d.narrative
    ? '<div class="brief-card">' +
        '<div class="brief-header">' +
          '<h3>Claude Operational Brief</h3>' +
          '<span class="brief-label">AI-generated operational summary</span>' +
        '</div>' +
        '<p class="brief-provenance">Generated only from deterministic alert evidence</p>' +
        '<div class="brief-text">' + renderNarrative(d.narrative) + '</div>' +
        '<div class="brief-caution">Recorded delay context is observational and does not establish causality.</div>' +
      '</div>'
    : '';

  const rightCol = briefCard ? '<div class="modal-right">' + briefCard + '</div>' : '';

  return (
    '<div class="modal-head">' +
      '<div class="modal-vendor">' + esc(d.vendor_id) + '</div>' +
      '<div class="modal-subtitle">OTA Deterioration Alert &nbsp;&middot;&nbsp; ' +
        esc(d.prior_period) + ' → ' + esc(d.current_period) +
      '</div>' +
    '</div>' +

    '<div class="modal-columns">' +

      '<div class="modal-left">' +
        '<div class="det-label">DETERMINISTIC EVIDENCE</div>' +

        '<div class="evidence-section">' +
          '<h3 class="section-label">Vendor Evidence</h3>' +
          '<div class="tile-grid">' +
            tile('Prior OTA',     d.prior_ota_pct.toFixed(2) + '%') +
            tile('Current OTA',   d.current_ota_pct.toFixed(2) + '%') +
            tileNeg('OTA Change', changeStr) +
            tile('Current trips', d.current_total_count.toLocaleString()) +
          '</div>' +
        '</div>' +

        '<div class="evidence-section">' +
          '<h3 class="section-label">Fleet Context</h3>' +
          '<div class="tile-grid">' +
            tile('Fleet OTA',
              d.fleet_prior_ota_pct.toFixed(2) + '% → ' + d.fleet_current_ota_pct.toFixed(2) + '%') +
            tile('Fleet movement', fleetStr) +
            tile('Eligible vendors', String(d.eligible_vendor_count)) +
            tile('Threshold crossings',
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
            tile('NODELAY most frequent', d.nodelay_dominates ? 'Yes' : 'No') +
            tile('Top non-NODELAY',  esc(d.top_non_nodelay_reason || '—')) +
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

      '</div>' +

      rightCol +

    '</div>' +

    '<div class="policy-strip">' +
      '<div class="ps-row">' +
        '<span class="ps-item">' +
          '<span class="ps-label">OTA tolerance</span>' +
          '<span class="ps-val">' + toleranceMins + ' min</span>' +
        '</span>' +
        '<span class="ps-sep">&middot;</span>' +
        '<span class="ps-item">' +
          '<span class="ps-label">Minimum volume</span>' +
          '<span class="ps-val">' + d.vol_min.toLocaleString() + ' trips</span>' +
        '</span>' +
        '<span class="ps-sep">&middot;</span>' +
        '<span class="ps-item">' +
          '<span class="ps-label">Trigger</span>' +
          '<span class="ps-val">&gt;' + d.deterioration_threshold_pp + ' percentage points</span>' +
        '</span>' +
        '<span class="ps-sep">&middot;</span>' +
        '<span class="ps-item">' +
          '<span class="ps-label">Policy</span>' +
          '<span class="ps-val">' + esc(d.policy_version) + '</span>' +
        '</span>' +
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

function renderNarrative(text) {
  if (!text) return '';
  return text
    .split(/\n\n+/)
    .filter(p => p.trim())
    .map(para => {
      const lines = para.split('\n').map(line => {
        let s = line
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
        s = s.replace(/^#{1,6} (.+)$/, '<strong>$1</strong>');
        s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
        return s;
      });
      return '<p>' + lines.join('<br>') + '</p>';
    })
    .join('');
}

function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;');
}
