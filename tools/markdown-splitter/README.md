# Markdown Splitter

A small single-page app that visualises how `src/utils/markdown_splitter.py`
splits a Markdown document. It executes the splitter's `split_markdown()` in the
browser via **Pyodide** — there is no separate JavaScript reimplementation and
no in-browser code editing.

## How it works

- Click **Run** (top-right) to fetch the splitter source and execute
  `split_markdown()`.
- The Run button first tries to fetch the **live** file
  `../../src/utils/markdown_splitter.py` (i.e.
  `<project-root>/src/utils/markdown_splitter.py`). When the page is opened
  directly via `file://` — or the file isn't reachable — it falls back to an
  **embedded copy** of the module bundled in `index.html`, so the page works
  without a server.
- The fetched source is evaluated in Pyodide (the `if __name__ == "__main__":`
  demo block is stripped first), then called with the current document:

  ```python
  split_markdown(md_content, max_chunk_size, overlap_size) -> list[Chunk]
  ```

  where each `Chunk` is a dict with `content`, `level` and `title_stack`.
- After the first successful Run, editing the Markdown or the `max chunk` /
  `overlap` inputs re-runs the splitter automatically (reusing the loaded
  source). Clicking Run again re-fetches the source.

## Features

- **Run button** (top-right) — fetches the source and produces the split.
- **Three display modes**
  - `origin` — render the whole document as one piece.
  - `split` — draw each `Chunk` as a rounded card with its title breadcrumb,
    heading level and character count, plus a `✂ split` marker at every
    boundary.
  - `meta` — show every `Chunk` as pretty-printed JSON (`content` / `level` /
    `title_stack`), with a copy-to-clipboard button.
- **Parameters** — `max chunk` and `overlap` are passed straight through to
  `split_markdown`.
- Editable Markdown source on the left, live preview on the right.
- A suffix in the preview header shows whether the result came from the
  **live source** or the **embedded fallback**.

## Run

### Option A — open the file directly (no server)

Double-click `tools/markdown-splitter/index.html` (open it in a browser) and
press **Run**. Pyodide and marked are loaded from a CDN, and the splitter source
comes from the embedded fallback.

> Note: this needs an internet connection for the CDN. If your browser blocks
> the WASM/CDN load from a `file://` page, use Option B instead.

### Option B — serve from the project root (recommended, uses the live source)

```bash
cd /Users/refone/Coding/shop-assistant
python3 -m http.server 5180
```

Then open <http://127.0.0.1:5180/tools/markdown-splitter/> and press **Run**.

## Files

- `index.html` — structure, top bar, Run button, display-mode switch, default
  Markdown, and the embedded fallback copy of the splitter.
- `styles.css` — styling for the switch, chunk cards and JSON view.
- `app.js` — Run handling, fetching + Pyodide execution of
  `src/utils/markdown_splitter.py`, and chunk rendering.
- `../../src/utils/markdown_splitter.py` — the actual splitter implementation.
  If you change it, keep the embedded copy in `index.html` in sync (it is only
  used when the live file cannot be fetched).
