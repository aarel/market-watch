# Inventory Report Usage

This guide explains how to view the interactive inventory report at:

- `reports/inventory/index.html`

without relying on double-click file opening.

## Why Use HTTP (Not Double-Click)

Opening `index.html` directly as `file://...` can cause inconsistent browser behavior for local `fetch("data.json")` and other script features.

Serving the report over local HTTP is more reliable for:

- loading `data.json`
- running filters/search/charts
- matching expected browser security model

## Quick Start (Python Built-In Server)

From repository root:

```bash
cd reports/inventory
python3 -m http.server 8765
```

Open in browser:

- `http://127.0.0.1:8765/index.html`

Expected server output example:

```text
Serving HTTP on 0.0.0.0 port 8765 (http://0.0.0.0:8765/) ...
```

Stop server with:

- `Ctrl+C`

## Alternative Port

If `8765` is already in use:

```bash
cd reports/inventory
python3 -m http.server 8080
```

Then open:

- `http://127.0.0.1:8080/index.html`

## Verify Interactivity

After loading the page:

1. Confirm summary chips show file/dir/size totals.
2. Use search input with a known path fragment (example: `commscribe`).
3. Change category filter and verify tables/charts refresh.
4. Click sortable table headers and verify row ordering changes.
5. Click top-level directory buttons in left panel and verify tree filter applies.

If these actions respond, interactive behavior is working.

## Regenerate Then Serve

From repository root:

```bash
python3 reports/inventory/generate_inventory_report.py
cd reports/inventory
python3 -m http.server 8765
```

Open:

- `http://127.0.0.1:8765/index.html`

## Optional Static Serving (Node, if available)

If you prefer Node tooling:

```bash
npx serve reports/inventory -l 8765
```

Open:

- `http://127.0.0.1:8765/index.html`

## OS / Browser Notes

- Windows/macOS/Linux: commands are identical when using `python3`.
- Some systems use `python` instead of `python3`.
- Modern Chromium/Firefox/Safari should work over HTTP local serving.

## Troubleshooting

- Blank page or missing data:
  - confirm you opened `http://...`, not `file://...`
  - confirm `reports/inventory/data.json` exists
  - check browser devtools console/network for missing files
- Port in use:
  - use another port (`8080`, `9000`, etc.)
