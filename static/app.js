'use strict';

const state = {
  tone:          'dramatic',
  background:    'minecraft-parkour',
  subtitleStyle: 'bottom-strip',
  platforms:     [],
  generating:    false,
};

const STEPS = [
  { id: 'init',      label: 'Initialize' },
  { id: 'script',    label: 'Generate Script' },
  { id: 'tts',       label: 'Text-to-Speech' },
  { id: 'footage',   label: 'Background Footage' },
  { id: 'subtitles', label: 'Subtitles (Whisper)' },
  { id: 'render',    label: 'FFmpeg Render' },
  { id: 'post',      label: 'Post to Platforms' },
];

document.addEventListener('DOMContentLoaded', () => {
  initPills();
  initSliders();
  initPlatforms();
  initSchedule();
  initGenerate();
  initHistory();
  initScrollSpy();
  loadHistory();
});

// ── Pill groups (single-select) ───────────────────────────────────────────────

function initPills() {
  document.querySelectorAll('.pill[data-group]').forEach(pill => {
    pill.addEventListener('click', () => {
      const group = pill.dataset.group;
      document.querySelectorAll(`.pill[data-group="${group}"]`).forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state[group] = pill.dataset.value;
    });
  });
}

// ── Sliders ───────────────────────────────────────────────────────────────────

function initSliders() {
  document.querySelectorAll('input[type="range"]').forEach(slider => {
    const display = document.getElementById(slider.dataset.display);
    const unit    = slider.dataset.unit || '';
    const update  = () => { if (display) display.textContent = slider.value + unit; };
    slider.addEventListener('input', update);
    update();
  });
}

// ── Platform toggles (multi-select) ──────────────────────────────────────────

function initPlatforms() {
  document.querySelectorAll('.platform-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = btn.dataset.platform;
      btn.classList.toggle('active');
      if (btn.classList.contains('active')) {
        if (!state.platforms.includes(p)) state.platforms.push(p);
      } else {
        state.platforms = state.platforms.filter(x => x !== p);
      }
    });
  });
}

// ── Schedule picker ───────────────────────────────────────────────────────────

function initSchedule() {
  document.getElementById('scheduleType').addEventListener('change', function () {
    document.getElementById('scheduleTime').classList.toggle('hidden', this.value !== 'schedule');
  });
}

// ── Generate button ───────────────────────────────────────────────────────────

function initGenerate() {
  document.getElementById('generateBtn').addEventListener('click', kickGenerate);
}

// ── History clear button ──────────────────────────────────────────────────────

function initHistory() {
  document.getElementById('clearHistoryBtn').addEventListener('click', () => {
    if (!confirm('Clear all history?')) return;
    fetch('/api/history', { method: 'DELETE' }).then(() => loadHistory());
  });
}

// ── Scroll-spy nav tabs ───────────────────────────────────────────────────────

function initScrollSpy() {
  const sections = document.querySelectorAll('section[id]');
  const tabs     = document.querySelectorAll('.nav-tab');

  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        tabs.forEach(t => t.classList.toggle('active', t.getAttribute('href') === `#${e.target.id}`));
      }
    });
  }, { rootMargin: '-40% 0px -55%' });

  sections.forEach(s => obs.observe(s));
}

// ── Generate pipeline ─────────────────────────────────────────────────────────

function kickGenerate() {
  if (state.generating) return;
  state.generating = true;

  const btn = document.getElementById('generateBtn');
  btn.disabled = true;
  document.getElementById('generateLabel').textContent = 'Generating…';

  setLogStatus('running');
  resetLog();

  const config = {
    niche:         document.getElementById('niche').value,
    topic:         document.getElementById('topic').value.trim(),
    persona:       document.getElementById('persona').value.trim(),
    tone:          state.tone,
    voice:         document.getElementById('voiceModel').value,
    speed:         parseFloat(document.getElementById('speed').value),
    duration:      parseInt(document.getElementById('duration').value),
    language:      document.getElementById('language').value,
    background:    state.background,
    subtitleStyle: state.subtitleStyle,
    music:         document.getElementById('music').checked,
    platforms:     [...state.platforms],
    autoTitle:     document.getElementById('autoTitle').checked,
    autoHashtags:  document.getElementById('autoHashtags').checked,
  };

  fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
    .then(r => r.json())
    .then(({ job_id }) => connectStream(job_id))
    .catch(e => {
      addLogLine('error', '', `Request failed: ${e.message}`);
      doneGenerating('error');
    });

  document.getElementById('log').scrollIntoView({ behavior: 'smooth' });
}

function connectStream(jobId) {
  const es = new EventSource(`/api/stream/${jobId}`);

  es.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'heartbeat') return;
    handleMsg(msg);
    if (msg.type === 'done' || msg.type === 'error') {
      es.close();
      doneGenerating(msg.type);
      if (msg.type === 'done') loadHistory();
    }
  };

  es.onerror = () => {
    es.close();
    doneGenerating('error');
  };
}

function doneGenerating(type) {
  state.generating = false;
  const btn = document.getElementById('generateBtn');
  btn.disabled = false;
  document.getElementById('generateLabel').textContent = 'Generate Video';
  setLogStatus(type === 'done' ? 'done' : 'error');
}

// ── Pipeline log rendering ────────────────────────────────────────────────────

function setLogStatus(s) {
  const el = document.getElementById('logStatus');
  el.textContent = s;
  el.className = `log-status ${s}`;
}

function resetLog() {
  document.getElementById('pipelineSteps').innerHTML = STEPS.map((s, i) => `
    <div class="pipeline-step" id="step-${s.id}">
      <div class="step-num" id="num-${s.id}">${i + 1}</div>
      <span class="step-name" id="stepname-${s.id}">${s.label}</span>
      <span class="step-time" id="steptime-${s.id}"></span>
    </div>
  `).join('');
  document.getElementById('logOutput').innerHTML = '';
}

function handleMsg(msg) {
  if (msg.step) {
    const num  = document.getElementById(`num-${msg.step}`);
    const name = document.getElementById(`stepname-${msg.step}`);
    const time = document.getElementById(`steptime-${msg.step}`);
    if (num) {
      num.className  = `step-num ${msg.status}`;
      name.className = `step-name ${msg.status}`;
      if (msg.status === 'done')  num.textContent = '✓';
      if (msg.status === 'error') num.textContent = '✗';
      if (time && msg.time) time.textContent = msg.time;
    }
  }

  if (msg.message) {
    const cls = msg.type === 'error' ? 'error' : 'info';
    addLogLine(cls, msg.time || '', msg.message);
  }

  if (msg.type === 'done') {
    addLogLine('done', msg.time || '', `✓ Complete — ${msg.output || ''}`);
  }
}

function addLogLine(cls, time, text) {
  const out  = document.getElementById('logOutput');
  const line = document.createElement('div');
  line.className = `log-line ${cls}`;
  line.innerHTML = `<span class="log-time">${esc(time)}</span><span class="log-msg">${esc(text)}</span>`;
  out.appendChild(line);
  out.scrollTop = out.scrollHeight;
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── History ───────────────────────────────────────────────────────────────────

let _history = [];

function loadHistory() {
  fetch('/api/history')
    .then(r => r.json())
    .then(items => { _history = items; renderHistory(items); })
    .catch(() => {});
}

function renderHistory(items) {
  const el = document.getElementById('historyList');

  if (!items.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>No videos generated yet</p></div>';
    return;
  }

  el.innerHTML = items.map((item, i) => {
    const d       = new Date(item.date);
    const dateStr = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                  + ' · '
                  + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const platforms = (item.platforms || []).join(', ') || 'not posted';

    return `
      <div class="history-item">
        <div class="history-thumb">▶</div>
        <div class="history-meta">
          <h4>${esc(item.niche.replace(/-/g, ' '))} — ${esc(item.tone)}</h4>
          <div class="history-tags">
            <span class="tag">${item.duration}s</span>
            <span class="tag">${esc(platforms)}</span>
          </div>
          <div class="history-date">${esc(dateStr)}</div>
        </div>
        <div class="history-actions">
          <button class="btn-sm primary" data-rerun="${i}">Re-run</button>
          <button class="btn-sm" data-preview="${i}">Preview</button>
        </div>
      </div>
    `;
  }).join('');

  el.querySelectorAll('[data-rerun]').forEach(btn => {
    btn.addEventListener('click', () => rerun(parseInt(btn.dataset.rerun)));
  });
  el.querySelectorAll('[data-preview]').forEach(btn => {
    btn.addEventListener('click', () => previewItem(parseInt(btn.dataset.preview)));
  });
}

function rerun(i) {
  const item = _history[i];
  if (!item) return;
  const nicheEl = document.getElementById('niche');
  if (nicheEl) nicheEl.value = item.niche;
  if (item.tone) {
    document.querySelectorAll('.pill[data-group="tone"]').forEach(p => {
      p.classList.toggle('active', p.dataset.value === item.tone);
    });
    state.tone = item.tone;
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function previewItem(i) {
  const item = _history[i];
  if (!item || !item.output) { alert('No output file found.'); return; }
  alert(`Output file:\n${item.output}`);
}
