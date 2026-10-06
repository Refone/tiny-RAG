'use strict';

/*
 * Markdown Splitter · 纯静态查看器
 *
 * 不发任何网络请求, 也不执行 Python。数据完全来自你拖进来的 JSON 文件:
 *
 *   1) 命令行生成数据:
 *        python src/utils/markdown_splitter.py     # -> tmp/chunks.json
 *
 *   2) 打开本页面 (直接双击 index.html 即可, file:// 也能用),
 *      把 tmp/chunks.json 拖进窗口 —— 或者点右上角「打开 JSON」选择文件。
 *
 * 三种视图 (数据都来自这份 JSON):
 *   merge  — 按 level / title_stack 把 chunks 重新拼回完整文档
 *   split  — 每个 chunk 一张卡片 + 切分边界
 *   meta   — 原始 JSON, 每个元素一张代码卡片
 * 重新生成数据后再拖一次文件即可刷新。
 *
 * 左侧还有一条 chunk 长度条: 一根 bar 对应一个 chunk, 滚动时高亮当前 chunk,
 * 悬停显示大小, 点击跳到对应位置。
 */

/* ======================= DOM refs ======================= */
const $ = (sel) => document.querySelector(sel);

const modeSwitch = $('#modeSwitch');
const preview = $('#preview');
const chunkRail = $('#chunkRail');
const railTip = $('#railTip');
const srcPath = $('#srcPath');
const srcMeta = $('#srcMeta');
const openBtn = $('#openBtn');
const fileInput = $('#fileInput');
const dropOverlay = $('#dropOverlay');
const widthRange = $('#widthRange');
const widthValue = $('#widthValue');

/* 内容显示宽度: 相对窗口宽度的百分比 */
const WIDTH_KEY = 'markdown-splitter:content-width';
const WIDTH_MIN = 20;
const WIDTH_MAX = 100;
const WIDTH_DEFAULT = 50;

/* ======================= State ======================= */
const state = {
  mode: 'merge',      // 'merge' | 'split' | 'meta'
  chunks: null,       // Chunk[] | null
  file: null,         // {name, size} | null
  error: null,
  loadedAt: null,
  dragging: false,
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

function formatSize(bytes) {
  if (typeof bytes !== 'number' || Number.isNaN(bytes)) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// 字符串按 UTF-8 编码后的字节数 (中文一个字算 3 字节)
function byteLength(text) {
  try {
    return new Blob([text]).size;
  } catch {
    return text.length;
  }
}

function clockTime(date) {
  if (!date) return '';
  return date.toLocaleTimeString('zh-CN', { hour12: false });
}

// 没有 CDN (marked 未加载) 时退化成纯文本, 页面依然可用
function renderMarkdown(text) {
  if (window.marked && typeof window.marked.parse === 'function') {
    try {
      return marked.parse(text);
    } catch {
      /* fall through */
    }
  }
  return `<pre class="md-plain">${escapeHtml(text)}</pre>`;
}

/* ======================= 显示宽度 ======================= */
function applyWidth(pct, { persist = true } = {}) {
  const n = Number(pct);
  const value = Math.min(WIDTH_MAX, Math.max(WIDTH_MIN, Number.isFinite(n) ? Math.round(n) : WIDTH_DEFAULT));
  document.documentElement.style.setProperty('--content-width', `${value}%`);
  widthRange.value = String(value);
  widthValue.textContent = `${value}%`;
  if (persist) {
    try {
      localStorage.setItem(WIDTH_KEY, String(value));
    } catch {
      /* file:// 或隐私模式下可能不可用, 忽略 */
    }
  }
  return value;
}

function initialWidth() {
  try {
    const saved = localStorage.getItem(WIDTH_KEY);
    if (saved != null) return Number(saved);
  } catch {
    /* ignore */
  }
  return WIDTH_DEFAULT;
}

// 所有视图的输出都放进这个「按宽度居中」的列里
function setContent(html) {
  preview.innerHTML = `<div class="content-column">${html}</div>`;
}

/* ======================= 左侧 chunk 长度条 =======================
 * 每个 chunk 一根 bar, 从上到下按顺序排列, 左对齐、向右延长,
 * 长度 = chunk 字符数 / 最长 chunk。
 *   - 滚动: 视口顶部的那个 chunk 对应的 bar 高亮 (merge 视图按长度占比估算)
 *   - 悬停: 气泡显示 chunk size
 *   - 点击: 平滑滚动到该 chunk
 */
const RAIL_MIN_RATIO = 0.05;   // 空/极短的 chunk 也留一根看得见的 bar
const RAIL_TOP_PAD = 34;       // 自动滚动时给 sticky 标题让出的空间
const RAIL_BOTTOM_PAD = 12;

let railSizes = [];            // 每个 chunk 的字符数
let railTotal = 0;             // 字符数总和 (merge 视图估算用)
let railRegions = [];          // split / meta: 每个 chunk 的 DOM 区块
let activeBarIndex = -1;
let railFrame = 0;

function chunkCharCount(c) {
  return (c.content || '').length;
}

function isRailVisible() {
  return Array.isArray(state.chunks) && state.chunks.length > 0 && !state.error;
}

function renderRail() {
  hideTip();

  if (!isRailVisible()) {
    chunkRail.hidden = true;
    chunkRail.innerHTML = '';
    railSizes = [];
    railRegions = [];
    activeBarIndex = -1;
    return;
  }

  railSizes = state.chunks.map(chunkCharCount);
  railTotal = railSizes.reduce((a, b) => a + b, 0);
  const max = railSizes.reduce((m, n) => Math.max(m, n), 0) || 1;

  let html = `<div class="rail-caption">chunk size</div><div class="rail-bars">`;
  railSizes.forEach((n, i) => {
    const pct = Math.max(RAIL_MIN_RATIO, n / max) * 100;
    html += `<button class="rail-bar" type="button" data-index="${i}" aria-label="Chunk ${i + 1}, ${n} chars" style="width:${pct.toFixed(2)}%"></button>`;
  });
  html += `</div>`;
  chunkRail.innerHTML = html;
  chunkRail.hidden = false;

  // merge 视图没有逐 chunk 的 DOM 区块, 此时用长度占比估算
  railRegions = Array.from(preview.querySelectorAll('[data-chunk-index]'));

  activeBarIndex = -1;
  setActiveBar(activeIndexFromScroll());
}

function railBars() {
  return chunkRail.querySelectorAll('.rail-bar');
}

function setActiveBar(index) {
  if (!railSizes.length) return;
  const clamped = Number.isFinite(index) ? index : 0;
  const next = Math.min(railSizes.length - 1, Math.max(0, clamped));
  if (next === activeBarIndex) return;

  const bars = railBars();
  const prev = bars[activeBarIndex];
  if (prev) prev.classList.remove('active');

  const bar = bars[next];
  if (bar) {
    bar.classList.add('active');
    ensureBarVisible(bar);
  }
  activeBarIndex = next;
}

// 高亮的 bar 若滚出 rail 视野, 就把它带回来
function ensureBarVisible(bar) {
  const railRect = chunkRail.getBoundingClientRect();
  const r = bar.getBoundingClientRect();
  if (r.top < railRect.top + RAIL_TOP_PAD) {
    chunkRail.scrollTop -= railRect.top + RAIL_TOP_PAD - r.top;
  } else if (r.bottom > railRect.bottom - RAIL_BOTTOM_PAD) {
    chunkRail.scrollTop += r.bottom - (railRect.bottom - RAIL_BOTTOM_PAD);
  }
}

// 当前「阅读线」(视口顶部往下一点) 落在哪个 chunk 上
function activeIndexFromScroll() {
  if (!railSizes.length) return 0;

  if (state.mode === 'merge' || !railRegions.length) {
    // 拼接后的文档长度 ≈ 各 chunk 长度之和, 按比例换算
    const line = preview.scrollTop;
    const target = (line / Math.max(1, preview.scrollHeight)) * railTotal;
    let acc = 0;
    for (let i = 0; i < railSizes.length; i += 1) {
      acc += railSizes[i];
      if (target < acc) return i;
    }
    return railSizes.length - 1;
  }

  const containerTop = preview.getBoundingClientRect().top;
  let index = Number(railRegions[0].dataset.chunkIndex) || 0;
  for (const el of railRegions) {
    if (el.getBoundingClientRect().top <= containerTop + 8) {
      index = Number(el.dataset.chunkIndex) || 0;
    } else {
      break;
    }
  }
  return index;
}

function updateActiveBar() {
  if (!railSizes.length) return;
  setActiveBar(activeIndexFromScroll());
}

function onPreviewScroll() {
  hideTip();
  if (!railSizes.length || railFrame) return;
  railFrame = requestAnimationFrame(() => {
    railFrame = 0;
    updateActiveBar();
  });
}

function scrollToChunk(index) {
  if (!railSizes.length) return;
  hideTip();

  if (state.mode === 'merge' || !railRegions.length) {
    const before = railSizes.slice(0, index).reduce((a, b) => a + b, 0);
    const top = (before / Math.max(1, railTotal)) * preview.scrollHeight - 12;
    preview.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    return;
  }

  const el = preview.querySelector(`[data-chunk-index="${index}"]`);
  if (!el) return;
  const top = el.getBoundingClientRect().top - preview.getBoundingClientRect().top + preview.scrollTop - 12;
  preview.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
}

/* ---- 悬停气泡 ---- */
function showTip(bar) {
  const index = Number(bar.dataset.index);
  const n = railSizes[index] || 0;
  railTip.textContent = `Chunk ${index + 1} · ${n.toLocaleString('zh-CN')} chars`;
  railTip.hidden = false;

  const r = bar.getBoundingClientRect();
  const tip = railTip.getBoundingClientRect();
  let left = r.right + 10;
  if (left + tip.width > window.innerWidth - 8) {
    left = Math.max(8, r.left - tip.width - 10);
  }
  const half = tip.height / 2;
  const top = Math.min(Math.max(r.top + r.height / 2, half + 6), window.innerHeight - half - 6);
  railTip.style.left = `${left}px`;
  railTip.style.top = `${top}px`;
}

function hideTip() {
  railTip.hidden = true;
}

chunkRail.addEventListener('click', (e) => {
  const bar = e.target.closest('.rail-bar');
  if (bar) scrollToChunk(Number(bar.dataset.index));
});

chunkRail.addEventListener('mouseover', (e) => {
  const bar = e.target.closest('.rail-bar');
  if (bar) showTip(bar);
});

chunkRail.addEventListener('mouseleave', hideTip);
chunkRail.addEventListener('mouseout', (e) => {
  const to = e.relatedTarget;
  if (!to || typeof to.closest !== 'function' || !to.closest('.rail-bar')) hideTip();
});
chunkRail.addEventListener('scroll', hideTip, { passive: true });
chunkRail.addEventListener('focusin', (e) => {
  const bar = e.target.closest('.rail-bar');
  if (bar) showTip(bar);
});
chunkRail.addEventListener('focusout', hideTip);

preview.addEventListener('scroll', onPreviewScroll, { passive: true });
window.addEventListener('resize', hideTip);

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
  render();
});

/* ======================= marked (async 加载, 到了再重渲染) ======================= */
function onMarkedReady() {
  if (!window.marked || typeof window.marked.use !== 'function') return;
  marked.use({ gfm: true, breaks: true });
  render();   // 用真正的 Markdown 渲染重刷一次
}

// index.html 里 marked 是 async 的: 可能先于本文件执行完 (命中缓存), 也可能之后才到
if (window.marked) onMarkedReady();
window.__onMarkedReady = onMarkedReady;

/* ======================= 读取拖入 / 选中的文件 ======================= */
async function loadFile(file) {
  if (!file) return;
  state.file = { name: file.name, size: file.size };
  state.error = null;

  try {
    const text = await file.text();

    let data;
    try {
      data = JSON.parse(text);
    } catch (err) {
      throw new Error(`不是合法的 JSON (${err.message})`);
    }
    if (!Array.isArray(data)) {
      throw new Error('顶层结构应该是一个数组 (chunk list)');
    }

    state.chunks = data;
    state.loadedAt = new Date();
  } catch (err) {
    state.chunks = null;
    state.error = err;
  }

  render();
}

function loadFromFileList(fileList) {
  const files = Array.from(fileList || []);
  if (files.length === 0) return;
  // 优先挑 .json, 否则就用第一个
  loadFile(files.find((f) => /\.json$/i.test(f.name)) || files[0]);
}

/* ======================= Render ======================= */
function render() {
  // 顶栏信息
  srcPath.textContent = state.file ? state.file.name : '未载入';
  if (state.error) {
    srcMeta.textContent = '解析失败';
  } else if (state.chunks) {
    const parts = [`${state.chunks.length} chunks`];
    if (state.file) parts.push(formatSize(state.file.size));
    const t = clockTime(state.loadedAt);
    if (t) parts.push(t);
    srcMeta.textContent = parts.join(' · ');
  } else {
    srcMeta.textContent = '拖入 chunks.json';
  }

  document.body.classList.toggle('dragging', state.dragging);

  if (state.error) {
    renderRail();
    renderError();
    return;
  }

  if (!state.chunks) {
    renderRail();
    renderDropzone();
    return;
  }

  if (state.chunks.length === 0) {
    renderRail();
    setContent(`<div class="empty-state">这份 JSON 里没有任何 chunk。</div>`);
    return;
  }

  if (state.mode === 'meta') {
    renderMeta();
  } else if (state.mode === 'split') {
    renderSplit();
  } else {
    renderMerge();
  }

  // 正文渲染完再建左侧长度条, 这样能直接索引到每个 chunk 的 DOM 区块
  renderRail();
}

function renderSplit() {
  const chunks = state.chunks;

  let html = '';
  chunks.forEach((c, i) => {
    const title = (c.title_stack || []).join(' › ');
    const level = Number.isFinite(c.level) ? c.level : 0;

    html += `<div class="chunk-card" data-chunk-index="${i}">`;
    html += `<div class="chunk-card-head">`;
    html += `<span class="chunk-badge">Chunk ${i + 1}</span>`;
    if (title) html += `<span class="chunk-title-stack" title="${escapeHtml(title)}">${escapeHtml(title)}</span>`;
    html += `<span class="chunk-level">${level > 0 ? 'H' + level : 'top'}</span>`;
    html += `<span class="chunk-size-note">${(c.content || '').length} chars</span>`;
    html += `</div>`;
    html += `<div class="chunk-card-body markdown-body">${renderMarkdown(c.content || '')}</div>`;
    html += `</div>`;
    if (i < chunks.length - 1) {
      html += `<div class="split-marker"><span class="scissors">✂</span> split ${i + 1} → ${i + 2}</div>`;
    }
  });

  setContent(html);
}

// 只用 JSON 里的信息把原始文档拼回去: 标题取 title_stack 的最后一项
function buildDocument(chunks) {
  const parts = [];
  chunks.forEach((c) => {
    const level = Number.isFinite(c.level) ? c.level : 0;
    const stack = c.title_stack || [];
    const heading = stack.length ? stack[stack.length - 1] : '';
    if (level > 0 && heading) parts.push('#'.repeat(Math.min(level, 6)) + ' ' + heading);
    if (c.content) parts.push(c.content);
  });
  return parts.join('\n\n');
}

function renderMerge() {
  const md = buildDocument(state.chunks);
  setContent(`<div class="chunk-card"><div class="chunk-card-body markdown-body">${renderMarkdown(md)}</div></div>`);
}

// 复制文本并给按钮一个短暂的反馈; 没有 clipboard 权限时退化成 execCommand
async function copyText(text, btn, idleHtml, doneHtml, failHtml) {
  let ok = true;
  try {
    if (navigator.clipboard && window.isSecureContext !== false) {
      await navigator.clipboard.writeText(text);
    } else {
      ok = legacyCopy(text);
    }
  } catch {
    ok = legacyCopy(text);
  }
  btn.innerHTML = ok ? doneHtml : failHtml;
  setTimeout(() => {
    btn.innerHTML = idleHtml;
  }, 1400);
}

function legacyCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.position = 'fixed';
  ta.style.top = '-1000px';
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try {
    ok = document.execCommand('copy');
  } catch {
    ok = false;
  }
  document.body.removeChild(ta);
  return ok;
}

function renderMeta() {
  const json = JSON.stringify(state.chunks, null, 2);
  const label = state.file ? state.file.name : 'chunks.json';

  let html = '';
  html += `<div class="meta-bar">`;
  html += `<span class="meta-count">${state.chunks.length} chunks · ${escapeHtml(label)}</span>`;
  html += `<button id="copyJsonBtn" class="btn primary" type="button"><span class="btn-icon">⧉</span> Copy JSON</button>`;
  html += `</div>`;

  // 每个 chunk 一个代码卡片: 超出显示宽度时换行 (见 .meta-json 的 pre-wrap)
  state.chunks.forEach((c, i) => {
    const title = (c.title_stack || []).join(' › ');
    const itemJson = JSON.stringify(c, null, 2);
    const chars = (c.content || '').length;
    const bytes = byteLength(itemJson);
    html += `<div class="meta-card" data-chunk-index="${i}">`;
    html += `<div class="meta-card-head">`;
    html += `<span class="chunk-badge">Chunk ${i + 1}</span>`;
    if (title) html += `<span class="chunk-title-stack" title="${escapeHtml(title)}">${escapeHtml(title)}</span>`;
    html += `<span class="chunk-size-note" title="content ${chars} chars · JSON ${formatSize(bytes)}">${chars} chars · ${formatSize(bytes)}</span>`;
    html += `<button class="meta-copy" type="button" data-index="${i}" title="复制这个元素"><span class="btn-icon">⧉</span></button>`;
    html += `</div>`;
    html += `<pre class="meta-json">${escapeHtml(itemJson)}</pre>`;
    html += `</div>`;
  });

  setContent(html);

  const copyAllBtn = $('#copyJsonBtn');
  if (copyAllBtn) {
    const idle = '<span class="btn-icon">⧉</span> Copy JSON';
    copyAllBtn.addEventListener('click', () =>
      copyText(json, copyAllBtn, idle, '<span class="btn-icon">✓</span> Copied', '<span class="btn-icon">✗</span> Copy failed'));
  }

  preview.querySelectorAll('.meta-copy').forEach((btn) => {
    const idle = '<span class="btn-icon">⧉</span>';
    btn.addEventListener('click', () => {
      const item = state.chunks[Number(btn.dataset.index)];
      copyText(JSON.stringify(item, null, 2), btn, idle, '<span class="btn-icon">✓</span>', '<span class="btn-icon">✗</span>');
    });
  });
}

function renderDropzone() {
  setContent(`
    <button type="button" class="dropzone">
      <span class="dropzone-icon">⤓</span>
      <span class="dropzone-title">把 chunks.json 拖到这里</span>
      <span class="dropzone-sub">或点右上角「打开 JSON」选择文件</span>
      <span class="dropzone-hint">
        文件由 <code>python src/utils/markdown_splitter.py</code> 生成到 <code>tmp/chunks.json</code>
      </span>
    </button>`);
}

function renderError() {
  const name = state.file ? state.file.name : '文件';

  setContent(`
    <div class="empty-state">
      <strong>读取 <code>${escapeHtml(name)}</code> 失败:</strong>
      ${escapeHtml(state.error.message || state.error)}<br /><br />
      期望的格式是一个 chunk 数组:<br />
      <code>[{"content": "…", "level": 2, "title_stack": ["第一章", "习题"]}, …]</code><br /><br />
      可以用 <code>python src/utils/markdown_splitter.py</code> 生成,
      然后重新把文件拖进来。
    </div>`);
}

/* ======================= Events ======================= */
// 显示宽度: 拖动滑杆实时生效, 点百分比重置为默认值
widthRange.addEventListener('input', () => applyWidth(widthRange.value));
widthRange.addEventListener('change', () => applyWidth(widthRange.value));
widthValue.addEventListener('click', () => applyWidth(WIDTH_DEFAULT));

// 选择文件
openBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  loadFromFileList(fileInput.files);
  fileInput.value = '';   // 允许重复选择同一个文件
});

// 点击空白区的拖拽提示也能选文件
preview.addEventListener('click', (e) => {
  if (e.target.closest('.dropzone')) fileInput.click();
});

// 拖拽: 整窗口都是投放区
let dragDepth = 0;

function setDragging(on) {
  if (state.dragging === on) return;
  state.dragging = on;
  document.body.classList.toggle('dragging', on);
}

window.addEventListener('dragenter', (e) => {
  e.preventDefault();
  dragDepth += 1;
  setDragging(true);
});

window.addEventListener('dragover', (e) => {
  e.preventDefault();               // 必须阻止默认行为, 否则浏览器会直接打开文件
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
  setDragging(true);
});

window.addEventListener('dragleave', (e) => {
  e.preventDefault();
  dragDepth = Math.max(0, dragDepth - 1);
  // relatedTarget 为 null 表示真正离开了窗口
  if (dragDepth === 0 || e.relatedTarget === null) {
    dragDepth = 0;
    setDragging(false);
  }
});

window.addEventListener('drop', (e) => {
  e.preventDefault();
  dragDepth = 0;
  setDragging(false);
  if (e.dataTransfer && e.dataTransfer.files) {
    loadFromFileList(e.dataTransfer.files);
  }
});

/* ======================= Init ======================= */
applyWidth(initialWidth(), { persist: false });   // 默认 50% 窗口宽度
render();
