"""generate_main_dashboard.py — Single dashboard: stats + paper cards + network.

Tabs:
  1. Resumen    — corpus stats per pocket, progress toward goal
  2. Papers     — filterable cards with abstract, score, criteria
  3. Red        — citation + keyword network visualization

Usage:
  python scripts/generate_main_dashboard.py
  open http://localhost:8000/outputs/main_dashboard.html
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pockets import POCKETS

POCKET_COLORS = {
    "evaluacion_experimental": "#10b981",
    "human_machine_interaction": "#8b5cf6",
    "innovacion_difusion": "#ec4899",
    "labor": "#f59e0b",
    "desigualdad": "#ef4444",
    "management": "#6366f1",
    "policy": "#3b82f6",
}


def load_all_papers() -> list:
    papers = []
    for pocket in POCKETS:
        for fname in [f"data/{pocket}_reviewed_enriched.json",
                      f"data/{pocket}_reviewed.json"]:
            f = Path(fname)
            if not f.exists():
                continue
            raw = json.loads(f.read_text())
            for p in raw:
                meta = p.get("metadata", p)
                authors = meta.get("authors", "")
                if isinstance(authors, list):
                    authors = ", ".join(str(a) for a in authors[:3])
                    if len(meta.get("authors", [])) > 3:
                        authors += " et al."
                abstract = (p.get("abstract") or
                            meta.get("summary") or
                            meta.get("abstract") or "")
                synthesis = p.get("synthesis") or {}
                papers.append({
                    "title": p.get("title", meta.get("title", "")),
                    "authors": authors,
                    "year": str(meta.get("year") or str(meta.get("published", ""))[:4] or ""),
                    "venue": meta.get("venue", ""),
                    "url": meta.get("url", ""),
                    "score": p.get("score", 0),
                    "status": p.get("status", ""),
                    "pocket": pocket,
                    "pocket_label": POCKETS[pocket]["label"],
                    "pocket_color": POCKET_COLORS[pocket],
                    "abstract": abstract[:400] + ("…" if len(abstract) > 400 else ""),
                    "breakdown": p.get("breakdown", {}),
                    "criteria": p.get("criteria", []),
                    "synthesis": synthesis,
                })
            break
    return papers


def compute_stats(papers: list) -> dict:
    stats = {}
    for pocket in POCKETS:
        pocket_papers = [p for p in papers if p["pocket"] == pocket]
        stats[pocket] = {
            "label": POCKETS[pocket]["label"],
            "color": POCKET_COLORS[pocket],
            "priority": POCKETS[pocket]["priority"],
            "total": len(pocket_papers),
            "accepted": sum(1 for p in pocket_papers if p["status"] == "ACEPTADO"),
            "revisar": sum(1 for p in pocket_papers if p["status"] == "REVISAR"),
            "rejected": sum(1 for p in pocket_papers if p["status"] == "RECHAZADO"),
            "target": 60,
        }
    total_accepted = sum(s["accepted"] for s in stats.values())
    return {"pockets": stats, "total_accepted": total_accepted, "goal": 420}


def generate_html(papers: list, stats: dict) -> str:
    papers_json = json.dumps(papers, ensure_ascii=False)
    stats_json = json.dumps(stats, ensure_ascii=False)

    # Load network data if it exists
    net_path = Path("data/bid_network.json")
    if net_path.exists():
        net_data = net_path.read_text()
        network_script = f"const NETWORK_DATA = {net_data};"
    else:
        network_script = "const NETWORK_DATA = null;"

    pocket_filter_options = "\n".join(
        f'<option value="{k}">{POCKETS[k]["label"]}</option>'
        for k in POCKETS
    )

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>BID-IA — Revisión de Literatura</title>
<script src="https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.js"></script>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0 }}
:root {{
  --bid1: #00296B; --bid2: #003F88; --bid3: #00509D; --bidl: #4AABE8;
  --bg: #0a1628; --card: #0f1f3d; --sidebar: #0d1a30;
  --border: #1e3a5f; --muted: #7a9bc4; --text: #e2e8f0;
}}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: var(--bg); color: var(--text); height: 100vh;
        display: flex; flex-direction: column; overflow: hidden }}

/* ── Topbar ── */
.topbar {{ background: var(--bid1); border-bottom: 2px solid var(--bid3);
           padding: 10px 20px; display: flex; align-items: center; gap: 12px; flex-shrink: 0 }}
.badge {{ background: var(--bid3); color: white; font-size: 10px; font-weight: 700;
          padding: 3px 8px; border-radius: 4px; letter-spacing: .5px }}
.topbar h1 {{ font-size: 15px; font-weight: 700 }}
.topbar-sub {{ font-size: 11px; color: #a0c4e8 }}
.topbar-stats {{ margin-left: auto; display: flex; gap: 8px }}
.stat-pill {{ background: rgba(0,0,0,.3); padding: 4px 10px; border-radius: 20px;
              font-size: 11px; border: 1px solid var(--border) }}

/* ── Tabs ── */
.tabs {{ background: var(--bid2); display: flex; gap: 0; flex-shrink: 0;
         border-bottom: 1px solid var(--border) }}
.tab {{ padding: 10px 24px; font-size: 13px; font-weight: 500; color: #7a9bc4;
        cursor: pointer; border-bottom: 2px solid transparent; transition: all .15s }}
.tab:hover {{ color: white }}
.tab.active {{ color: white; border-bottom-color: var(--bidl) }}

/* ── Content area ── */
.panel {{ display: none; flex: 1; overflow: hidden }}
.panel.active {{ display: flex; flex-direction: column }}

/* ─── TAB 1: RESUMEN ─── */
.resumen-body {{ overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px }}
.summary-hero {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px }}
.hero-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
              padding: 18px; text-align: center }}
.hero-val {{ font-size: 32px; font-weight: 800; color: var(--bidl) }}
.hero-lbl {{ font-size: 11px; color: var(--muted); margin-top: 4px; text-transform: uppercase }}

.pocket-grid {{ display: flex; flex-direction: column; gap: 10px }}
.pocket-row {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
               padding: 14px 18px; display: grid;
               grid-template-columns: 180px 1fr 80px 80px 80px 40px;
               align-items: center; gap: 12px }}
.pocket-name {{ font-size: 13px; font-weight: 600 }}
.pocket-bar-wrap {{ background: var(--bg); border-radius: 4px; height: 8px; overflow: hidden }}
.pocket-bar {{ height: 100%; border-radius: 4px; transition: width .4s }}
.count {{ font-size: 12px; text-align: center }}
.pri-badge {{ font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 3px;
              letter-spacing: .5px }}
.pri-H {{ background: #ef444422; color: #ef4444 }}
.pri-M {{ background: #f59e0b22; color: #f59e0b }}

/* ─── TAB 2: PAPERS ─── */
.papers-toolbar {{ padding: 12px 20px; background: var(--card);
                   border-bottom: 1px solid var(--border);
                   display: flex; gap: 10px; align-items: center; flex-shrink: 0 }}
.papers-toolbar select, .papers-toolbar input {{
  background: var(--bg); border: 1px solid var(--border); color: var(--text);
  padding: 6px 10px; border-radius: 6px; font-size: 12px }}
.papers-toolbar select:focus, .papers-toolbar input:focus {{
  outline: none; border-color: var(--bid3) }}
.pill-filters {{ display: flex; gap: 6px }}
.pill {{ padding: 4px 12px; border-radius: 20px; border: 1px solid var(--border);
         font-size: 11px; cursor: pointer; color: var(--muted); background: var(--bg) }}
.pill.active {{ background: var(--bid3); color: white; border-color: var(--bid3) }}
.count-label {{ font-size: 12px; color: var(--muted); margin-left: auto }}

.papers-grid {{ overflow-y: auto; padding: 16px 20px;
                display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 12px; align-content: start }}

.paper-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
               overflow: hidden; display: flex; flex-direction: column;
               border-left: 4px solid transparent; transition: border-color .15s }}
.paper-card:hover {{ border-left-color: var(--bidl) }}
.paper-card-header {{ padding: 14px 16px 10px }}
.paper-title {{ font-size: 13px; font-weight: 600; line-height: 1.4; margin-bottom: 6px }}
.paper-meta {{ font-size: 11px; color: var(--muted); display: flex; gap: 8px; flex-wrap: wrap }}
.paper-tags {{ padding: 0 16px 10px; display: flex; gap: 6px; flex-wrap: wrap }}
.ptag {{ padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500 }}
.paper-abstract {{ padding: 0 16px; font-size: 12px; color: #94a3b8; line-height: 1.6;
                   border-top: 1px solid var(--border); padding-top: 10px }}
.paper-scores {{ padding: 10px 16px; display: flex; gap: 6px; border-top: 1px solid var(--border) }}
.score-mini {{ background: var(--bg); border-radius: 4px; padding: 4px 8px;
               text-align: center; flex: 1; font-size: 10px }}
.score-mini-val {{ font-weight: 700; font-size: 13px }}
.paper-footer {{ padding: 10px 16px; display: flex; gap: 8px; align-items: center;
                 border-top: 1px solid var(--border) }}
.criteria-dots {{ display: flex; gap: 4px }}
.cdot {{ width: 8px; height: 8px; border-radius: 50% }}
.btn-sm {{ font-size: 11px; padding: 4px 10px; border-radius: 5px; border: none;
           cursor: pointer; font-weight: 600; text-decoration: none;
           display: inline-flex; align-items: center }}
.btn-view {{ background: var(--bid3); color: white }}
.btn-view:hover {{ background: var(--bid2) }}

/* ─── TAB 3: RED ─── */
.network-container {{ display: flex; flex-direction: column; flex: 1; overflow: hidden }}
.network-toolbar {{ padding: 10px 20px; background: var(--card);
                    border-bottom: 1px solid var(--border);
                    display: flex; gap: 8px; align-items: center; flex-shrink: 0 }}
.net-filter {{ padding: 5px 14px; border-radius: 20px; border: 1px solid var(--border);
               font-size: 11px; cursor: pointer; color: var(--muted); background: var(--bg);
               font-weight: 500 }}
.net-filter.active {{ color: white }}
.network-wrap {{ position: relative; flex: 1; overflow: hidden }}
#network-canvas {{ width: 100%; height: 100% }}
.net-legend {{ position: absolute; bottom: 12px; left: 12px; background: rgba(10,22,40,.85);
               border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px;
               font-size: 11px; color: var(--muted) }}
.legend-item {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px }}
.legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0 }}
.net-tooltip {{ position: absolute; background: var(--card); border: 1px solid var(--border);
                border-radius: 8px; padding: 12px; font-size: 12px; max-width: 280px;
                pointer-events: none; display: none; z-index: 10 }}
.no-network {{ display: flex; align-items: center; justify-content: center;
               height: 100%; flex-direction: column; gap: 12px; color: var(--muted) }}
.no-network code {{ background: var(--card); padding: 8px 14px; border-radius: 6px;
                    font-size: 12px; color: var(--text); border: 1px solid var(--border) }}
</style>
</head>
<body>

<!-- Topbar -->
<div class="topbar">
  <span class="badge">BID</span>
  <div>
    <h1>Revisión de Literatura — Adopción IA en Firmas</h1>
    <div class="topbar-sub">Fedesarrollo &amp; BID · Colombia y LATAM · 2026</div>
  </div>
  <div class="topbar-stats">
    <span class="stat-pill" style="color:#22c55e" id="stat-acc">— aceptados</span>
    <span class="stat-pill" style="color:#f97316" id="stat-rev">— revisar</span>
    <span class="stat-pill" id="stat-tot">— total</span>
  </div>
</div>

<!-- Tabs -->
<div class="tabs">
  <div class="tab active" onclick="switchTab('resumen',this)">📊 Resumen</div>
  <div class="tab" onclick="switchTab('papers',this)">📄 Papers</div>
  <div class="tab" onclick="switchTab('red',this)">🕸 Red de Literatura</div>
</div>

<!-- ─── TAB 1: RESUMEN ─── -->
<div class="panel active" id="panel-resumen">
<div class="resumen-body">
  <div class="summary-hero" id="hero-cards"></div>
  <div id="pocket-rows"></div>
</div>
</div>

<!-- ─── TAB 2: PAPERS ─── -->
<div class="panel" id="panel-papers">
  <div class="papers-toolbar">
    <input type="text" id="search-input" placeholder="Buscar título, autor..." oninput="filterPapers()">
    <select id="pocket-select" onchange="filterPapers()">
      <option value="">Todos los pockets</option>
      {pocket_filter_options}
    </select>
    <div class="pill-filters">
      <div class="pill active" onclick="setStatusFilter('',this)">Todos</div>
      <div class="pill" onclick="setStatusFilter('ACEPTADO',this)" style="color:#22c55e;border-color:#22c55e22">✅ Aceptados</div>
      <div class="pill" onclick="setStatusFilter('REVISAR',this)" style="color:#f97316;border-color:#f97316">🔄 Revisar</div>
      <div class="pill" onclick="setStatusFilter('RECHAZADO',this)" style="color:#ef4444;border-color:#ef444422">❌ Rechazados</div>
    </div>
    <span class="count-label" id="count-label">— papers</span>
  </div>
  <div class="papers-grid" id="papers-grid"></div>
</div>

<!-- ─── TAB 3: RED ─── -->
<div class="panel" id="panel-red">
<div class="network-container">
  <div class="network-toolbar" id="net-toolbar">
    <span style="font-size:12px;color:var(--muted);margin-right:4px">Filtrar:</span>
    <div class="net-filter active" onclick="filterNetwork('',this)" style="color:white">Todos</div>
  </div>
  <div class="network-wrap">
    <div id="network-canvas"></div>
    <div class="net-legend" id="net-legend"></div>
    <div class="net-tooltip" id="net-tooltip"></div>
  </div>
</div>
</div>

<script>
const PAPERS = {papers_json};
const STATS  = {stats_json};
{network_script}

// ── Init ─────────────────────────────────────────────────────────────
let statusFilter = '';
let networkInstance = null;

document.addEventListener('DOMContentLoaded', () => {{
  renderTopStats();
  renderResumen();
  renderPapers();
}});

function switchTab(name, el) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
  if (name === 'red' && !networkInstance) initNetwork();
}}

// ── Topbar stats ──────────────────────────────────────────────────────
function renderTopStats() {{
  const acc = PAPERS.filter(p => p.status === 'ACEPTADO').length;
  const rev = PAPERS.filter(p => p.status === 'REVISAR').length;
  document.getElementById('stat-acc').textContent = acc + ' aceptados';
  document.getElementById('stat-rev').textContent = rev + ' revisar';
  document.getElementById('stat-tot').textContent = PAPERS.length + ' total';
}}

// ── TAB 1: RESUMEN ────────────────────────────────────────────────────
function renderResumen() {{
  const s = STATS;
  const acc = s.total_accepted;
  const pct = Math.round(acc / s.goal * 100);
  const tot = PAPERS.length;
  const rev = PAPERS.filter(p => p.status === 'REVISAR').length;

  document.getElementById('hero-cards').innerHTML = `
    <div class="hero-card">
      <div class="hero-val" style="color:#22c55e">${{acc}}</div>
      <div class="hero-lbl">Aceptados</div>
    </div>
    <div class="hero-card">
      <div class="hero-val" style="color:#f97316">${{rev}}</div>
      <div class="hero-lbl">Para revisar</div>
    </div>
    <div class="hero-card">
      <div class="hero-val">${{tot}}</div>
      <div class="hero-lbl">Total papers</div>
    </div>
    <div class="hero-card">
      <div class="hero-val" style="color:var(--bidl)">${{pct}}%</div>
      <div class="hero-lbl">del objetivo (${{s.goal}})</div>
    </div>
  `;

  const rows = Object.entries(s.pockets).map(([key, p]) => {{
    const pct = Math.min(100, Math.round(p.accepted / p.target * 100));
    const priClass = p.priority === 'HIGH' ? 'pri-H' : 'pri-M';
    return `<div class="pocket-row" style="border-left: 3px solid ${{p.color}}">
      <div class="pocket-name" style="color:${{p.color}}">${{p.label}}</div>
      <div class="pocket-bar-wrap">
        <div class="pocket-bar" style="width:${{pct}}%;background:${{p.color}}"></div>
      </div>
      <div class="count" style="color:#22c55e">${{p.accepted}} ✅</div>
      <div class="count" style="color:#f97316">${{p.revisar}} 🔄</div>
      <div class="count" style="color:#64748b">${{p.total}}</div>
      <div class="pri-badge ${{priClass}}">${{p.priority}}</div>
    </div>`;
  }}).join('');

  document.getElementById('pocket-rows').innerHTML =
    `<div class="pocket-grid">${{rows}}</div>`;
}}

// ── TAB 2: PAPERS ─────────────────────────────────────────────────────
function filterPapers() {{ renderPapers(); }}

function setStatusFilter(val, el) {{
  statusFilter = val;
  document.querySelectorAll('.pill-filters .pill').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  renderPapers();
}}

function renderPapers() {{
  const search = document.getElementById('search-input').value.toLowerCase();
  const pocket = document.getElementById('pocket-select').value;

  const filtered = PAPERS.filter(p => {{
    if (statusFilter && p.status !== statusFilter) return false;
    if (pocket && p.pocket !== pocket) return false;
    if (search) {{
      const hay = (p.title + ' ' + p.authors).toLowerCase();
      if (!hay.includes(search)) return false;
    }}
    return true;
  }});

  document.getElementById('count-label').textContent = filtered.length + ' papers';

  document.getElementById('papers-grid').innerHTML = filtered.map(p => {{
    const scoreColor = p.score >= 7 ? '#22c55e' : p.score >= 5 ? '#f97316' : '#64748b';
    const statusIcon = p.status === 'ACEPTADO' ? '✅' : p.status === 'REVISAR' ? '🔄' : '❌';
    const bd = p.breakdown || {{}};

    const scoreItems = [
      ['Met', bd.methodology, 4],
      ['Cau', bd.causalidity, 2],
      ['Top', bd.top_tier, 2],
      ['Nov', bd.novelty, 1],
      ['Rel', bd.relevance, 2],
    ].map(([n, v, m]) => {{
      const c = v >= m * .7 ? '#22c55e' : v > 0 ? '#f59e0b' : v < 0 ? '#ef4444' : '#475569';
      return `<div class="score-mini">
        <div class="score-mini-val" style="color:${{c}}">${{v ?? '—'}}</div>
        <div style="font-size:9px;color:var(--muted)">${{n}}/${{m}}</div>
      </div>`;
    }}).join('');

    const critDots = (p.criteria || []).map(c =>
      `<div class="cdot" style="background:${{c.met ? '#22c55e' : '#dc2626'}}"
           title="${{c.desc}}"></div>`
    ).join('');

    const abstract = p.abstract
      ? `<div class="paper-abstract" style="margin-bottom:10px">${{p.abstract}}</div>`
      : '';

    return `<div class="paper-card" style="border-left-color:${{p.pocket_color}}22">
      <div class="paper-card-header">
        <div class="paper-title">${{p.title}}</div>
        <div class="paper-meta">
          ${{p.authors ? `<span>👤 ${{p.authors}}</span>` : ''}}
          ${{p.year ? `<span>📅 ${{p.year}}</span>` : ''}}
          ${{p.venue ? `<span>📰 ${{p.venue.substring(0,30)}}</span>` : ''}}
        </div>
      </div>
      <div class="paper-tags">
        <span class="ptag" style="background:${{p.pocket_color}}22;color:${{p.pocket_color}}">${{p.pocket_label}}</span>
        <span class="ptag" style="background:${{scoreColor}}22;color:${{scoreColor}}">${{statusIcon}} ${{p.score}}/11</span>
      </div>
      ${{abstract}}
      <div class="paper-scores">${{scoreItems}}</div>
      <div class="paper-footer">
        <div class="criteria-dots" title="Criterios del pocket">${{critDots}}</div>
        ${{p.url ? `<a class="btn-sm btn-view" href="${{p.url}}" target="_blank">↗ Ver paper</a>` : ''}}
      </div>
    </div>`;
  }}).join('');
}}

// ── TAB 3: RED ────────────────────────────────────────────────────────
function initNetwork() {{
  const container = document.getElementById('network-canvas');

  if (!NETWORK_DATA) {{
    container.innerHTML = `<div class="no-network">
      <div>Red de literatura no generada aún</div>
      <code>python scripts/build_network.py --keywords-only</code>
      <div style="font-size:11px;color:var(--muted)">Con tokens: python scripts/build_network.py</div>
    </div>`;
    return;
  }}

  const COLORS = {json.dumps(POCKET_COLORS)};
  const POCKET_LABELS = {json.dumps({k: POCKETS[k]["label"] for k in POCKETS})};

  // Build vis.js datasets
  const nodes = new vis.DataSet(NETWORK_DATA.nodes.map(n => ({{
    id: n.id,
    label: n.label,
    title: buildTooltip(n),
    color: {{ background: n.color + '33', border: n.color, highlight: {{ background: n.color + '88', border: n.color }} }},
    size: n.size || 12,
    font: {{ color: '#e2e8f0', size: 10 }},
    pocket: n.pocket,
    url: n.url,
  }})));

  const edges = new vis.DataSet(NETWORK_DATA.edges.map((e, i) => ({{
    id: i,
    from: e.from,
    to: e.to,
    width: Math.min(e.value * 0.4, 4),
    color: {{ color: e.type && e.type.includes('citation') ? '#4AABE888' : '#1e3a5f', opacity: 0.6 }},
    title: e.type === 'citation' ? 'Citación directa' :
           e.type === 'citation+keyword' ? 'Citación + keywords' : 'Keywords compartidos',
  }})));

  const options = {{
    physics: {{
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {{ gravitationalConstant: -30, centralGravity: 0.005, springLength: 120 }},
      stabilization: {{ iterations: 120 }},
    }},
    interaction: {{ hover: true, tooltipDelay: 200 }},
    nodes: {{ shape: 'dot', borderWidth: 2 }},
    edges: {{ smooth: {{ type: 'continuous' }} }},
  }};

  networkInstance = new vis.Network(container, {{ nodes, edges }}, options);

  networkInstance.on('click', params => {{
    if (params.nodes.length > 0) {{
      const node = nodes.get(params.nodes[0]);
      if (node && node.url) window.open(node.url, '_blank');
    }}
  }});

  // Build pocket filter buttons
  const toolbar = document.getElementById('net-toolbar');
  Object.entries(COLORS).forEach(([key, color]) => {{
    const label = POCKET_LABELS[key] || key;
    const btn = document.createElement('div');
    btn.className = 'net-filter';
    btn.style.borderColor = color + '44';
    btn.style.color = color;
    btn.textContent = label.split(' ')[0];
    btn.onclick = () => filterNetwork(key, btn);
    toolbar.appendChild(btn);
  }});

  // Legend
  document.getElementById('net-legend').innerHTML =
    '<div style="font-weight:600;margin-bottom:6px;color:white">Pockets</div>' +
    Object.entries(COLORS).map(([k, c]) => {{
      const label = POCKET_LABELS[k] || k;
      return `<div class="legend-item"><div class="legend-dot" style="background:${{c}}"></div>${{label}}</div>`;
    }}).join('') +
    '<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">' +
    '<div class="legend-item"><div style="width:20px;height:2px;background:#4AABE8;border-radius:1px"></div>Citacion directa</div>' +
    '<div class="legend-item"><div style="width:20px;height:1px;background:#1e3a5f;border-radius:1px"></div>Keywords compartidos</div>' +
    '</div>';
}}

function buildTooltip(n) {{
  return `<div style="max-width:260px;font-size:12px;padding:4px">
    <strong style="color:white">${{n.title_full}}</strong><br>
    <span style="color:var(--muted)">${{n.pocket_label}} · ${{n.year}} · Score ${{n.score}}/11</span><br>
    <span style="color:#94a3b8;font-size:11px">${{n.abstract}}</span>
  </div>`;
}}

function filterNetwork(pocket, el) {{
  document.querySelectorAll('.net-filter').forEach(b => {{
    b.classList.remove('active');
    b.style.color = b.style.borderColor.replace('44', '');
  }});
  el.classList.add('active');
  if (!pocket) el.style.color = 'white';

  if (!networkInstance) return;
  const allNodes = NETWORK_DATA.nodes;
  const updates = allNodes.map(n => ({{
    id: n.id,
    opacity: !pocket || n.pocket === pocket ? 1 : 0.1,
  }}));
  // Use network node update
  allNodes.forEach(n => {{
    const alpha = !pocket || n.pocket === pocket ? 'cc' : '15';
    networkInstance.body.data.nodes.update({{
      id: n.id,
      color: {{ background: n.color + alpha, border: n.color }},
      font: {{ color: !pocket || n.pocket === pocket ? '#e2e8f0' : '#333' }},
    }});
  }});
}}
</script>
</body>
</html>'''


def main():
    os.chdir(Path(__file__).parent.parent)
    print("Loading papers...")
    papers = load_all_papers()
    print(f"  {len(papers)} papers loaded")

    stats = compute_stats(papers)
    acc = stats["total_accepted"]
    print(f"  Accepted: {acc}/{stats['goal']} ({round(acc/stats['goal']*100,1)}%)")

    html = generate_html(papers, stats)
    out = Path("outputs/main_dashboard.html")
    out.write_text(html, encoding="utf-8")
    print(f"\n✅ Dashboard → {out}")
    print("   Open: http://localhost:8000/outputs/main_dashboard.html")


if __name__ == "__main__":
    main()