'use strict';

/* ======================= DOM refs ======================= */
const $ = (sel) => document.querySelector(sel);

const modeSwitch = $('#modeSwitch');
const markdownInput = $('#markdownInput');
const preview = $('#preview');
const previewHeader = $('#previewHeader');
const chunkSizeInput = $('#chunkSize');
const overlapInput = $('#overlap');
const runBtn = $('#runBtn');

const sampleMd = document.getElementById('sample-md').textContent.trim() + '\n';
const embeddedSource =
  document.getElementById('splitter-source').textContent.trim() + '\n';

/* ======================= State ======================= */
const state = {
  mode: 'origin',        // 'origin' | 'split' | 'meta'
  chunks: null,          // Chunk[] | null (null = not yet produced)
  lastError: null,
  running: false,
  sourceLabel: null,     // 'live' | 'fallback' | null
};

/* ======================= helpers ======================= */
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderMarkdown(text) {
  try {
    return marked.parse(text);
  } catch {
    return escapeHtml(text);
  }
}

/* ======================= Segmented switch ======================= */
function setupSegmented(container, onChange) {
  const thumb = container.querySelector('.seg-thumb');
  const btns = Array.from(container.querySelectorAll('.seg-btn'));

  function updateThumb() {
    const active = container.querySelector('.seg-btn.active');
    if (!active || !thumb) return;
    thumb.style.width = active.offsetWidth + 'px';
    thumb.style.transform = `translateX(${active.offsetLeft}px)`;
  }

  container.addEventListener('click', (e) => {
    const btn = e.target.closest('.seg-btn');
    if (!btn || btn.classList.contains('active')) return;
    btns.forEach((b) => b.classList.toggle('active', b === btn));
    updateThumb();
    onChange(btn.dataset.value);
  });

  requestAnimationFrame(updateThumb);
  window.addEventListener('resize', updateThumb);
  return { update: updateThumb };
}

setupSegmented(modeSwitch, (value) => {
  state.mode = value;
  renderPreview();
});

/* ======================= marked setup ======================= */
marked.use({ gfm: true, breaks: true });

/* ======================= Pyodide + splitter source ======================= */
const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/';
// Resolves to <project-root>/src/utils/markdown_splitter.py when the page is
// served from the project root. On file:// (or a wrong root) fetch() fails,
// so we fall back to the embedded copy.
const SPLITTER_URL = new URL('../../src/utils/markdown_splitter.py', location.href).href;

let pyodidePromise = null;
let sourceCode = null;   // stripMainBlock()-applied source, cached after first load
let sourceLabel = null;  // 'live' | 'fallback'

function getPyodide() {
  if (!pyodidePromise) {
    pyodidePromise = loadPyodide({ indexURL: PYODIDE_URL });
  }
  return pyodidePromise;
}

// The source file ends with an `if __name__ == "__main__":` demo block that
// imports `rich` and reads a local file. We only need the module definitions.
function stripMainBlock(src) {
  return src.replace(/\nif __name__\s*==\s*["']__main__["']\s*:[\s\S]*$/, '');
}

// Fetch the live file first; fall back to the embedded copy so the app also
// works when opened directly from disk (file://) with no server.
async function loadSource() {
  try {
    const resp = await fetch(SPLITTER_URL);
    if (resp.ok) {
      sourceLabel = 'live';
      return stripMainBlock(await resp.text());
    }
  } catch {
    // file:// or network failure → fall through to embedded copy
  }
  sourceLabel = 'fallback';
  return stripMainBlock(embeddedSource);
}

/* ======================= Run split_markdown ======================= */
async function runSplitter({ refreshSource = true } = {}) {
  if (state.running) return;
  state.running = true;
  setRunBtn(true);

  const md = markdownInput.value;
  const maxChunk = Math.max(1, parseInt(chunkSizeInput.value, 10) || 800);
  const overlap = Math.max(0, parseInt(overlapInput.value, 10) || 0);

  try {
    const py = await getPyodide();
    if (refreshSource || sourceCode == null) {
      sourceCode = await loadSource();
      py.runPython('import json');
      py.runPython(sourceCode);
    }

    // Pass the markdown through the globals dict to avoid any escaping issues.
    py.globals.set('__md', md);
    const json = py.runPython(
      `json.dumps(split_markdown(__md, ${maxChunk}, ${overlap}))`
    );
    state.chunks = JSON.parse(json);
    state.lastError = null;
    state.sourceLabel = sourceLabel;
  } catch (err) {
    state.lastError = err;
    state.chunks = null;
    state.sourceLabel = null;
  } finally {
    state.running = false;
    setRunBtn(false);
  }

  if (state.mode !== 'origin') renderPreview();
}

function setRunBtn(running) {
  runBtn.disabled = running;
  runBtn.innerHTML = running
    ? '<span class="btn-icon">◌</span> Running…'
    : '<span class="btn-icon">▶</span> Run';
}

/* ======================= Preview ======================= */
function renderPreview() {
  const md = markdownInput.value;

  if (state.mode === 'origin') {
    previewHeader.textContent = 'Rendered · origin';
    preview.innerHTML = `<div class="markdown-body">${renderMarkdown(md)}</div>`;
    return;
  }

  if (state.mode === 'meta') {
    renderMeta();
    return;
  }

  renderSplit();
}

function renderSplit() {
  if (!state.chunks || state.chunks.length === 0) {
    previewHeader.textContent = 'Split view';
    preview.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage())}</div>`;
    return;
  }

  previewHeader.textContent =
    `Split view · ${state.chunks.length} chunks` + sourceSuffix();
  let html = '';
  state.chunks.forEach((c, i) => {
    const title = (c.title_stack || []).join(' › ');
    const level = Number.isFinite(c.level) ? c.level : 0;

    html += `<div class="chunk-card">`;
    html += `<div class="chunk-card-head">`;
    html += `<span class="chunk-badge">Chunk ${i + 1}</span>`;
    if (title) html += `<span class="chunk-title-stack" title="${escapeHtml(title)}">${escapeHtml(title)}</span>`;
    html += `<span class="chunk-level">${level > 0 ? 'H' + level : 'top'}</span>`;
    html += `<span class="chunk-size-note">${(c.content || '').length} chars</span>`;
    html += `</div>`;
    html += `<div class="chunk-card-body markdown-body">${renderMarkdown(c.content || '')}</div>`;
    html += `</div>`;
    if (i < state.chunks.length - 1) {
      html += `<div class="split-marker"><span class="scissors">✂</span> split ${i + 1} → ${i + 2}</div>`;
    }
  });
  preview.innerHTML = html;
}

function renderMeta() {
  if (!state.chunks || state.chunks.length === 0) {
    previewHeader.textContent = 'Meta';
    preview.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage())}</div>`;
    return;
  }

  previewHeader.textContent =
    `Meta · ${state.chunks.length} chunks` + sourceSuffix();
  const json = JSON.stringify(state.chunks, null, 2);

  let html = '';
  html += `<div class="meta-bar">`;
  html += `<span class="meta-count">${state.chunks.length} chunks</span>`;
  html += `<button id="copyJsonBtn" class="btn primary" type="button"><span class="btn-icon">⧉</span> Copy JSON</button>`;
  html += `</div>`;
  html += `<pre class="meta-json">${escapeHtml(json)}</pre>`;
  preview.innerHTML = html;

  const copyBtn = $('#copyJsonBtn');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(json);
        copyBtn.innerHTML = '<span class="btn-icon">✓</span> Copied';
        setTimeout(() => {
          copyBtn.innerHTML = '<span class="btn-icon">⧉</span> Copy JSON';
        }, 1400);
      } catch {
        copyBtn.innerHTML = '<span class="btn-icon">✗</span> Copy failed';
      }
    });
  }
}

function sourceSuffix() {
  if (state.sourceLabel === 'fallback') return ' · embedded fallback';
  if (state.sourceLabel === 'live') return ' · live source';
  return '';
}

function emptyMessage() {
  if (state.lastError) {
    return `Splitter error: ${state.lastError.message || state.lastError}`;
  }
  if (state.running) {
    return 'Running split_markdown()…';
  }
  if (sourceCode == null) {
    return 'Press “Run” to fetch the splitter source and split the document.';
  }
  return 'No chunks produced.';
}

/* ======================= Events ======================= */
runBtn.addEventListener('click', () => runSplitter({ refreshSource: true }));

let debounceTimer = null;
function scheduleRun() {
  // Before the first successful Run there is nothing to re-run with, so wait.
  if (sourceCode == null) return;
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => runSplitter({ refreshSource: false }), 400);
}

markdownInput.addEventListener('input', () => {
  if (state.mode === 'origin') renderPreview();
  scheduleRun();
});
chunkSizeInput.addEventListener('change', scheduleRun);
chunkSizeInput.addEventListener('input', scheduleRun);
overlapInput.addEventListener('change', scheduleRun);
overlapInput.addEventListener('input', scheduleRun);

/* ======================= Init ======================= */
(function init() {
  markdownInput.value = sampleMd;
  renderPreview();
})();
