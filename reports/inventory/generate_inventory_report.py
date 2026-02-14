#!/usr/bin/env python3
"""Generate an offline structural inventory report for the repository.

Writes only:
- reports/inventory/data.json
- reports/inventory/index.html
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "inventory"
DATA_PATH = OUT_DIR / "data.json"
HTML_PATH = OUT_DIR / "index.html"

CATEGORIES = [
    "Runtime Core",
    "Product Logic",
    "Infrastructure / CI",
    "Tests (code)",
    "Test Artifacts (generated outputs)",
    "Audit / Compliance Artifacts (DRA, verification, phase docs)",
    "Development Docs (handoffs, notes, session logs)",
    "Operational Artifacts (logs, metrics dumps, generated operational reports)",
    "Archive Candidates (duplicates, superseded, stale, experiments)",
]

SKIP_DIRS = {
    ".git",
    ".venv",
    ".venv-wsl",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_archive_candidate(path: str) -> bool:
    name = Path(path).name.lower()
    p = path.lower()
    patterns = (
        "/archive/",
        "/legacy/",
        "session_handoff",
        "latest_update",
        "reality_check",
        "priority_",
        "phase_",
        "old",
        "backup",
        ".bak",
        "copy",
    )
    return any(x in p for x in patterns) or name.startswith("tmp")


def classify(path: str) -> str:
    p = path.lower()
    if is_archive_candidate(path):
        return CATEGORIES[8]
    if p.startswith("commscribe/scripts/") or p.startswith("commscribe/communicate") or p.startswith("commscribe/failure_log") or p.endswith("codex_communicate_instructions.md"):
        return CATEGORIES[0]
    if p.startswith("alerts/") or p.startswith("analytics/") or p.startswith("backtest/") or p.startswith("strategies/") or p.startswith("risk/") or p.startswith("server/") or p.startswith("static/") or p.startswith("monitoring/"):
        return CATEGORIES[1]
    if p.startswith(".github/") or p.startswith("deploy/") or p.endswith("requirements.txt") or p.endswith("requirements.lock") or p.endswith("pytest.ini") or p.endswith(".coveragerc") or p.endswith(".ruff.toml"):
        return CATEGORIES[2]
    if p.startswith("tests/") or p.startswith("commscribe/tests/") or p.endswith("conftest.py") or p == "run_tests":
        return CATEGORIES[3]
    if p.startswith("test_results/") or p.endswith("coverage.json") or p == ".coverage":
        return CATEGORIES[4]
    if p.startswith("commscribe/docs/") or "audit" in p or "compliance" in p or "verification" in p:
        return CATEGORIES[5]
    if p.startswith("development_docs/") or p.endswith("handoff.md") or "session_handoff" in p or p.endswith("readme.md"):
        return CATEGORIES[6]
    if p.startswith("logs/") or p.startswith("data/live/") or p.startswith("data/paper/") or p.startswith("data/simulation/"):
        return CATEGORIES[7]
    return CATEGORIES[1]


def ownership(path: str) -> str:
    p = path.lower()
    if p.startswith("logs/") or p.startswith("test_results/") or p.endswith("coverage.json") or p == ".coverage":
        return "derived"
    if p.startswith("commscribe/communicate.md") or p.startswith("commscribe/communicate.json") or p.startswith("commscribe/failure_log.json"):
        return "authoritative"
    if p.startswith("data/live/") or p.startswith("data/paper/") or p.startswith("data/simulation/"):
        return "derived"
    if p.startswith("commscribe/docs/") or "audit" in p:
        return "derived"
    return "authoritative"


def normalize_dup_key(path: str) -> str:
    stem = Path(path).stem.lower()
    stem = re.sub(r"\d{4}[-_]?\d{2}[-_]?\d{2}", "", stem)
    stem = re.sub(r"\d{8}", "", stem)
    stem = re.sub(r"(copy|final|latest|v\d+)", "", stem)
    stem = re.sub(r"[_\-\s]+", "_", stem).strip("_")
    return stem or Path(path).name.lower()


def scan() -> dict:
    files = []
    dir_sizes: Counter[str] = Counter()
    dir_counts: Counter[str] = Counter()
    category_sizes: Counter[str] = Counter()
    category_files: Counter[str] = Counter()
    category_dirs: defaultdict[str, set[str]] = defaultdict(set)
    ext_counts: Counter[str] = Counter()
    modified_buckets: Counter[str] = Counter()
    dup_groups: defaultdict[str, list[dict]] = defaultdict(list)

    for cur, dirs, names in os.walk(ROOT):
        rel_cur = Path(cur).relative_to(ROOT).as_posix()
        if rel_cur == ".":
            rel_cur = ""
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        dirs[:] = [d for d in dirs if not (Path(rel_cur) / d).as_posix().startswith("reports/inventory")]
        for name in names:
            p = Path(cur) / name
            r = relpath(p)
            if r.startswith("reports/inventory/"):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            size = st.st_size
            mtime = datetime.fromtimestamp(st.st_mtime, UTC)
            category = classify(r)
            own = ownership(r)
            ext = p.suffix.lower() or "(none)"

            files.append(
                {
                    "path": r,
                    "size": size,
                    "mtime": mtime.isoformat(),
                    "mtime_bucket": mtime.strftime("%Y-%m"),
                    "ext": ext,
                    "category": category,
                    "ownership": own,
                    "dir": Path(r).parent.as_posix() if Path(r).parent.as_posix() != "." else "",
                }
            )

            category_sizes[category] += size
            category_files[category] += 1
            category_dirs[category].add(Path(r).parent.as_posix())
            ext_counts[ext] += 1
            modified_buckets[mtime.strftime("%Y-%m")] += 1

            parts = Path(r).parts
            for i in range(1, len(parts)):
                d = "/".join(parts[:i])
                dir_sizes[d] += size
                dir_counts[d] += 1

            dup_groups[normalize_dup_key(r)].append({"path": r, "size": size})

    top_dirs_size = [
        {"path": p, "size": s, "count": dir_counts[p]}
        for p, s in dir_sizes.most_common(30)
    ]
    top_dirs_count = [
        {"path": p, "count": c, "size": dir_sizes[p]}
        for p, c in dir_counts.most_common(30)
    ]
    largest_files = sorted(files, key=lambda x: x["size"], reverse=True)[:50]
    dup_candidates = []
    for key, group in dup_groups.items():
        if len(group) >= 2 and key:
            dup_candidates.append(
                {
                    "key": key,
                    "count": len(group),
                    "total_size": sum(g["size"] for g in group),
                    "paths": sorted(g["path"] for g in group)[:10],
                }
            )
    dup_candidates.sort(key=lambda x: (x["count"], x["total_size"]), reverse=True)

    root_md = [f for f in files if "/" not in f["path"] and f["path"].lower().endswith(".md")]
    status_like = [f for f in root_md if any(k in f["path"].lower() for k in ("status", "update", "handoff", "phase", "audit", "verification"))]
    findings = []
    if len(status_like) >= 4:
        findings.append(
            {
                "title": "Root-level status/audit document sprawl",
                "severity": "High",
                "detail": f"{len(status_like)} root markdown files match status/update/handoff/audit patterns.",
            }
        )
    artifacts_count = sum(1 for f in files if f["path"].startswith("logs/") or f["path"].startswith("test_results/"))
    if artifacts_count >= 100:
        findings.append(
            {
                "title": "Large generated artifact footprint",
                "severity": "Medium",
                "detail": f"{artifacts_count} files in logs/test_results indicate high derived-artifact accumulation.",
            }
        )
    if dup_candidates:
        findings.append(
            {
                "title": "Duplicate/near-duplicate naming patterns",
                "severity": "Medium",
                "detail": f"{len(dup_candidates)} duplication candidates detected by normalized filename heuristic.",
            }
        )

    categories = []
    for c in CATEGORIES:
        c_files = [f for f in files if f["category"] == c]
        risk = "Low"
        priority = "Low"
        if len(c_files) > 200 or category_sizes[c] > 100 * 1024 * 1024:
            risk = "High"
            priority = "High"
        elif len(c_files) > 50 or category_sizes[c] > 20 * 1024 * 1024:
            risk = "Medium"
            priority = "Medium"
        top_sub = Counter((f["dir"].split("/")[0] if f["dir"] else "(root)") for f in c_files).most_common(5)
        categories.append(
            {
                "name": c,
                "file_count": category_files[c],
                "dir_count": len(category_dirs[c]),
                "size_bytes": category_sizes[c],
                "top_subtrees": [{"path": p, "count": n} for p, n in top_sub],
                "naming_signals": "date-stamped/repeated naming detected" if any("-20" in f["path"] or "latest" in f["path"].lower() for f in c_files) else "mostly stable",
                "ownership_clarity": "mixed" if any(f["ownership"] == "derived" for f in c_files) and any(f["ownership"] == "authoritative" for f in c_files) else ("derived" if c_files and c_files[0]["ownership"] == "derived" else "authoritative"),
                "redundancy_risk": risk,
                "cleanup_priority": priority,
            }
        )

    top_level = Counter((f["path"].split("/")[0] if "/" in f["path"] else "(root)") for f in files)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(ROOT),
        "summary": {
            "file_count": len(files),
            "dir_count": len({f["dir"] for f in files}),
            "total_size_bytes": sum(f["size"] for f in files),
        },
        "categories": categories,
        "files": files,
        "tables": {
            "largest_files": largest_files,
            "largest_dirs": top_dirs_size,
            "dense_dirs": top_dirs_count,
            "dup_candidates": dup_candidates[:50],
        },
        "charts": {
            "count_by_category": {c["name"]: c["file_count"] for c in categories},
            "size_by_category": {c["name"]: c["size_bytes"] for c in categories},
            "mtime_buckets": dict(sorted(modified_buckets.items())),
            "top_level_tree": dict(top_level),
        },
        "filter_values": {
            "categories": CATEGORIES,
            "extensions": [k for k, _ in ext_counts.most_common(60)],
            "mtime_buckets": sorted(modified_buckets.keys()),
            "ownership": ["authoritative", "derived"],
        },
        "findings": findings,
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Repository Structural Inventory</title>
  <style>
    :root {
      --bg: #f5f7fa;
      --panel: #ffffff;
      --ink: #1e2630;
      --muted: #5f6f82;
      --line: #d7dde5;
      --accent: #0b7285;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #eef3f8, var(--bg));
    }
    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 1rem;
      max-width: 1400px;
      margin: 1rem auto;
      padding: 0 1rem 1rem;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 0.8rem;
    }
    h1, h2, h3 { margin: 0.2rem 0 0.6rem; }
    .muted { color: var(--muted); font-size: 0.9rem; }
    input, select {
      width: 100%;
      margin-bottom: 0.5rem;
      padding: 0.45rem 0.55rem;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .chips { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.5rem; }
    .chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 0.2rem 0.55rem;
      font-size: 0.82rem;
      background: #f7fafc;
    }
    .grid2 {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.8rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.86rem;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 0.35rem 0.45rem;
      vertical-align: top;
    }
    th { cursor: pointer; background: #f8fafc; position: sticky; top: 0; }
    .table-wrap { max-height: 280px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; }
    canvas {
      width: 100%;
      height: 180px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .tree button {
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      border-radius: 8px;
      margin-bottom: 0.3rem;
      padding: 0.3rem 0.45rem;
      background: #fff;
      cursor: pointer;
    }
    @media (max-width: 1000px) {
      .layout { grid-template-columns: 1fr; }
      .grid2 { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="layout">
    <aside class="panel">
      <h2>Inventory Controls</h2>
      <p class="muted" id="generatedAt"></p>
      <input id="search" placeholder="Search path substring" />
      <select id="category"></select>
      <select id="extension"></select>
      <select id="sizeRange">
        <option value="">All sizes</option>
        <option value="lt1m">< 1 MB</option>
        <option value="1to10m">1-10 MB</option>
        <option value="gt10m">> 10 MB</option>
      </select>
      <select id="mtime"></select>
      <select id="ownership"></select>
      <h3>Directory Tree (top level)</h3>
      <div id="tree" class="tree"></div>
      <button id="clearPrefix">Clear Tree Filter</button>
    </aside>
    <main>
      <section class="panel">
        <h1>Repository Structural Inventory</h1>
        <div id="summary" class="chips"></div>
        <h3>Findings</h3>
        <div id="findings"></div>
      </section>
      <section class="grid2">
        <div class="panel"><h3>Counts by Category</h3><canvas id="countChart" width="640" height="220"></canvas></div>
        <div class="panel"><h3>Size by Category</h3><canvas id="sizeChart" width="640" height="220"></canvas></div>
        <div class="panel"><h3>Modified-Time Histogram</h3><canvas id="timeChart" width="640" height="220"></canvas></div>
        <div class="panel"><h3>Category Detail</h3><div id="categoryCards"></div></div>
      </section>
      <section class="grid2">
        <div class="panel"><h3>Largest Files</h3><div id="largestFiles" class="table-wrap"></div></div>
        <div class="panel"><h3>Largest Directories</h3><div id="largestDirs" class="table-wrap"></div></div>
        <div class="panel"><h3>Most Dense Directories</h3><div id="denseDirs" class="table-wrap"></div></div>
        <div class="panel"><h3>Duplication Candidates</h3><div id="dups" class="table-wrap"></div></div>
      </section>
    </main>
  </div>
  <script>
    let data = null;
    let pathPrefix = "";
    async function loadData() {
      const res = await fetch("data.json");
      data = await res.json();
      renderControls();
      renderAll();
    }
    function fmtBytes(v) {
      if (v < 1024) return v + " B";
      if (v < 1024*1024) return (v/1024).toFixed(1) + " KB";
      if (v < 1024*1024*1024) return (v/1024/1024).toFixed(1) + " MB";
      return (v/1024/1024/1024).toFixed(2) + " GB";
    }
    function renderControls() {
      document.getElementById("generatedAt").textContent = "Generated: " + data.generated_at;
      const category = document.getElementById("category");
      category.innerHTML = '<option value="">All categories</option>' + data.filter_values.categories.map(v => `<option>${v}</option>`).join("");
      const ext = document.getElementById("extension");
      ext.innerHTML = '<option value="">All extensions</option>' + data.filter_values.extensions.map(v => `<option>${v}</option>`).join("");
      const mtime = document.getElementById("mtime");
      mtime.innerHTML = '<option value="">All modified buckets</option>' + data.filter_values.mtime_buckets.map(v => `<option>${v}</option>`).join("");
      const own = document.getElementById("ownership");
      own.innerHTML = '<option value="">All ownership tags</option>' + data.filter_values.ownership.map(v => `<option>${v}</option>`).join("");
      for (const id of ["search","category","extension","sizeRange","mtime","ownership"]) {
        document.getElementById(id).addEventListener("input", renderAll);
      }
      const tree = document.getElementById("tree");
      const entries = Object.entries(data.charts.top_level_tree).sort((a,b)=>b[1]-a[1]);
      tree.innerHTML = entries.map(([k,v]) => `<button data-prefix="${k === "(root)" ? "" : k + "/"}">${k} (${v})</button>`).join("");
      tree.querySelectorAll("button").forEach(btn => {
        btn.addEventListener("click", () => {
          pathPrefix = btn.dataset.prefix || "";
          renderAll();
        });
      });
      document.getElementById("clearPrefix").addEventListener("click", () => {
        pathPrefix = "";
        renderAll();
      });
    }
    function filteredFiles() {
      const q = document.getElementById("search").value.toLowerCase().trim();
      const c = document.getElementById("category").value;
      const e = document.getElementById("extension").value;
      const s = document.getElementById("sizeRange").value;
      const m = document.getElementById("mtime").value;
      const o = document.getElementById("ownership").value;
      return data.files.filter(f => {
        if (pathPrefix && !f.path.startsWith(pathPrefix)) return false;
        if (q && !f.path.toLowerCase().includes(q)) return false;
        if (c && f.category !== c) return false;
        if (e && f.ext !== e) return false;
        if (m && f.mtime_bucket !== m) return false;
        if (o && f.ownership !== o) return false;
        if (s === "lt1m" && f.size >= 1024*1024) return false;
        if (s === "1to10m" && (f.size < 1024*1024 || f.size > 10*1024*1024)) return false;
        if (s === "gt10m" && f.size <= 10*1024*1024) return false;
        return true;
      });
    }
    function renderSummary(files) {
      const total = files.reduce((a,b)=>a+b.size,0);
      const dirs = new Set(files.map(f=>f.dir)).size;
      document.getElementById("summary").innerHTML =
        `<span class="chip">Files: ${files.length}</span>` +
        `<span class="chip">Dirs: ${dirs}</span>` +
        `<span class="chip">Size: ${fmtBytes(total)}</span>` +
        `<span class="chip">Tree Filter: ${pathPrefix || "(none)"}</span>`;
    }
    function renderFindings() {
      const el = document.getElementById("findings");
      if (!data.findings.length) {
        el.innerHTML = '<p class="muted">No major entropy hotspots detected by current heuristics.</p>';
        return;
      }
      el.innerHTML = data.findings.map(f => `<p><strong>${f.severity}:</strong> ${f.title} — ${f.detail}</p>`).join("");
    }
    function drawBarChart(canvasId, labels, values, color) {
      const c = document.getElementById(canvasId);
      const ctx = c.getContext("2d");
      ctx.clearRect(0,0,c.width,c.height);
      const max = Math.max(1, ...values);
      const pad = 40;
      const w = (c.width - pad*2) / Math.max(1, labels.length);
      ctx.font = "11px sans-serif";
      labels.forEach((label, i) => {
        const h = ((c.height - pad*2) * values[i]) / max;
        const x = pad + i*w + 4;
        const y = c.height - pad - h;
        ctx.fillStyle = color;
        ctx.fillRect(x, y, Math.max(8, w-8), h);
        ctx.fillStyle = "#334";
        ctx.fillText(String(values[i]), x, y - 4);
        const short = label.length > 12 ? label.slice(0,10) + ".." : label;
        ctx.save();
        ctx.translate(x+2, c.height-pad+12);
        ctx.rotate(-0.45);
        ctx.fillText(short, 0, 0);
        ctx.restore();
      });
    }
    function renderCategoryCards() {
      const el = document.getElementById("categoryCards");
      el.innerHTML = data.categories.map(c => `
        <div style="border-bottom:1px solid #d7dde5;padding:0.4rem 0;">
          <strong>${c.name}</strong><br/>
          files=${c.file_count}, dirs=${c.dir_count}, size=${fmtBytes(c.size_bytes)}<br/>
          ownership=${c.ownership_clarity}, redundancy=${c.redundancy_risk}, advisory-priority=${c.cleanup_priority}
        </div>
      `).join("");
    }
    function makeTable(targetId, rows, columns) {
      let sortKey = columns[0].key;
      let sortDir = -1;
      const root = document.getElementById(targetId);
      function render() {
        const sorted = [...rows].sort((a,b) => {
          const av = a[sortKey], bv = b[sortKey];
          if (typeof av === "number" && typeof bv === "number") return (av-bv) * sortDir;
          return String(av).localeCompare(String(bv)) * sortDir;
        });
        const head = "<tr>" + columns.map(c => `<th data-k="${c.key}">${c.label}</th>`).join("") + "</tr>";
        const body = sorted.slice(0, 200).map(r => "<tr>" + columns.map(c => `<td>${c.format ? c.format(r[c.key], r) : (r[c.key] ?? "")}</td>`).join("") + "</tr>").join("");
        root.innerHTML = `<table>${head}${body}</table>`;
        root.querySelectorAll("th").forEach(th => {
          th.addEventListener("click", () => {
            const k = th.dataset.k;
            if (sortKey === k) sortDir *= -1;
            else { sortKey = k; sortDir = -1; }
            render();
          });
        });
      }
      render();
    }
    function renderTables(files) {
      const fileRows = [...files].sort((a,b)=>b.size-a.size).slice(0, 80);
      makeTable("largestFiles", fileRows, [
        {key:"path", label:"path"},
        {key:"size", label:"size", format:v=>fmtBytes(v)},
        {key:"category", label:"category"},
        {key:"ownership", label:"ownership"},
      ]);
      makeTable("largestDirs", data.tables.largest_dirs, [
        {key:"path", label:"path"},
        {key:"size", label:"size", format:v=>fmtBytes(v)},
        {key:"count", label:"file_count"},
      ]);
      makeTable("denseDirs", data.tables.dense_dirs, [
        {key:"path", label:"path"},
        {key:"count", label:"file_count"},
        {key:"size", label:"size", format:v=>fmtBytes(v)},
      ]);
      makeTable("dups", data.tables.dup_candidates, [
        {key:"key", label:"dup_key"},
        {key:"count", label:"count"},
        {key:"total_size", label:"total_size", format:v=>fmtBytes(v)},
        {key:"paths", label:"sample_paths", format:v=>Array.isArray(v)?v.join("<br/>"):""},
      ]);
    }
    function renderAll() {
      const files = filteredFiles();
      renderSummary(files);
      renderFindings();
      renderCategoryCards();
      const countMap = {};
      const sizeMap = {};
      for (const f of files) {
        countMap[f.category] = (countMap[f.category] || 0) + 1;
        sizeMap[f.category] = (sizeMap[f.category] || 0) + f.size;
      }
      const labels = Object.keys(countMap);
      drawBarChart("countChart", labels, labels.map(k=>countMap[k]), "#0b7285");
      drawBarChart("sizeChart", labels, labels.map(k=>sizeMap[k]), "#3f8f4f");
      const tMap = {};
      for (const f of files) tMap[f.mtime_bucket] = (tMap[f.mtime_bucket] || 0) + 1;
      const tLabels = Object.keys(tMap).sort();
      drawBarChart("timeChart", tLabels, tLabels.map(k=>tMap[k]), "#8f5f2f");
      renderTables(files);
    }
    loadData();
  </script>
</body>
</html>
"""


def write_outputs(payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    HTML_PATH.write_text(HTML_TEMPLATE, encoding="utf-8")


def main() -> int:
    payload = scan()
    write_outputs(payload)
    print(f"Wrote {DATA_PATH}")
    print(f"Wrote {HTML_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
