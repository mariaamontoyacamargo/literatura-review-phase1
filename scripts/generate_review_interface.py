"""generate_review_interface.py — Manual review UI: read abstract, accept/reject, annotate"""
import json, os

POCKET_COLORS = {
    "management": "#6366f1", "labor": "#f59e0b",
    "evaluacion_experimental": "#10b981", "desigualdad": "#ef4444",
    "policy": "#3b82f6", "human_machine_interaction": "#8b5cf6",
    "innovacion_difusion": "#ec4899"
}
POCKET_LABELS = {
    "management": "Management", "labor": "Labor Markets",
    "evaluacion_experimental": "Evaluación Experimental", "desigualdad": "Desigualdad",
    "policy": "Policy", "human_machine_interaction": "HMI",
    "innovacion_difusion": "Innovación y Difusión"
}

def load_papers():
    all_papers = []
    pockets = list(POCKET_LABELS.keys())
    for pocket in pockets:
        f = f"data/{pocket}_reviewed_enriched.json"
        if not os.path.exists(f):
            f = f"data/{pocket}_reviewed.json"
        if not os.path.exists(f):
            continue
        with open(f) as fp:
            papers = json.load(fp)
        for p in papers:
            meta = p.get("metadata", p)
            p["_pocket"] = pocket
            p["_pocket_label"] = POCKET_LABELS[pocket]
            p["_pocket_color"] = POCKET_COLORS[pocket]
            p["_abstract"] = meta.get("abstract", meta.get("summary", ""))
            p["_url"] = meta.get("url", meta.get("scholar_link", ""))
            p["_year"] = meta.get("year", "")
            p["_authors"] = meta.get("authors", "")
            if isinstance(p["_authors"], list):
                p["_authors"] = ", ".join(p["_authors"][:3]) + (" et al." if len(meta.get("authors",[])) > 3 else "")
            p["_venue"] = meta.get("venue", "")
            p["_citations"] = meta.get("citations", "")
            all_papers.append(p)
    return all_papers

def generate_html(papers):
    pocket_filter_btns = " ".join(
        f'<button class="filter-btn" onclick="setFilter(\"{k}\",this)" style="border-color:{v};color:{v}">{POCKET_LABELS[k][:8]}</button>'
        for k, v in POCKET_COLORS.items()
    )
    # Serialise to JSON for JS
    papers_json = json.dumps([{
        "id": i,
        "title": p.get("title",""),
        "score": p.get("score", 0),
        "status": p.get("status",""),
        "pocket": p.get("_pocket",""),
        "pocket_label": p.get("_pocket_label",""),
        "pocket_color": p.get("_pocket_color","#666"),
        "abstract": p.get("_abstract",""),
        "url": p.get("_url",""),
        "year": p.get("_year",""),
        "authors": p.get("_authors",""),
        "venue": p.get("_venue",""),
        "citations": p.get("_citations",""),
        "breakdown": p.get("breakdown",{}),
        "criteria": p.get("criteria", []),
        "manual_decision": p.get("manual_decision",""),
        "manual_note": p.get("manual_note",""),
    } for i, p in enumerate(papers)], ensure_ascii=False)

    pockets_list = list(POCKET_LABELS.items())

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BID-IA — Manual Paper Review</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0 }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0a1628; color:#e2e8f0; height:100vh; display:flex; flex-direction:column }}

/* BID institutional palette */
:root {{
  --bid-azul1: #00296B;
  --bid-azul2: #003F88;
  --bid-azul3: #00509D;
  --bid-light: #4AABE8;
  --bg-dark: #0a1628;
  --bg-card: #0f1f3d;
  --bg-sidebar: #0d1a30;
  --border: #1e3a5f;
  --text-muted: #7a9bc4;
}}

/* Layout */
.topbar {{ background:var(--bid-azul1); border-bottom:2px solid var(--bid-azul3); padding:10px 20px; display:flex; align-items:center; gap:16px; flex-shrink:0 }}
.topbar-brand {{ display:flex; align-items:center; gap:10px }}
.topbar-badge {{ background:var(--bid-azul3); color:white; font-size:10px; font-weight:700; padding:3px 8px; border-radius:4px; letter-spacing:0.5px }}
.topbar h1 {{ font-size:15px; font-weight:700; color:#ffffff }}
.topbar-sub {{ font-size:11px; color:#a0c4e8; margin-left:2px }}
.topbar .stats {{ font-size:12px; color:#94a3b8; margin-left:auto; display:flex; gap:12px }}
.stat-pill {{ background:rgba(0,0,0,0.3); padding:4px 10px; border-radius:20px; font-size:12px; border:1px solid var(--border) }}
.stat-pill.green {{ color:#22c55e }}
.stat-pill.orange {{ color:#f97316 }}
.stat-pill.red {{ color:#ef4444 }}

.main {{ display:flex; flex:1; overflow:hidden }}

/* Sidebar */
.sidebar {{ width:260px; background:var(--bg-sidebar); border-right:1px solid var(--border); display:flex; flex-direction:column; flex-shrink:0 }}
.sidebar-header {{ padding:12px 16px; border-bottom:1px solid var(--border) }}
.search-box {{ width:100%; background:var(--bg-dark); border:1px solid var(--border); color:#e2e8f0; padding:8px 12px; border-radius:6px; font-size:13px }}
.search-box:focus {{ outline:none; border-color:var(--bid-azul3) }}
.filters {{ padding:8px 12px; border-bottom:1px solid var(--border); display:flex; gap:4px; flex-wrap:wrap }}
.filter-btn {{ background:var(--bg-dark); border:1px solid var(--border); color:var(--text-muted); padding:3px 8px; border-radius:12px; cursor:pointer; font-size:11px }}
.filter-btn.active {{ background:var(--bid-azul3); color:white; border-color:var(--bid-azul3) }}

.paper-list {{ flex:1; overflow-y:auto; padding:4px }}
.paper-item {{ padding:10px 12px; border-radius:6px; cursor:pointer; margin-bottom:2px; border-left:3px solid transparent }}
.paper-item:hover {{ background:rgba(0,64,136,0.25) }}
.paper-item.selected {{ background:var(--bid-azul2); border-left-color:var(--bid-light) }}
.paper-item.decided-accept {{ border-left-color:#22c55e }}
.paper-item.decided-reject {{ border-left-color:#ef4444 }}
.paper-title-small {{ font-size:12px; font-weight:500; color:#e2e8f0; line-height:1.3; margin-bottom:3px }}
.paper-meta-small {{ font-size:11px; color:var(--text-muted); display:flex; gap:6px; align-items:center }}
.score-badge {{ font-size:11px; font-weight:700; padding:1px 5px; border-radius:3px }}

/* Main content */
.content {{ flex:1; overflow-y:auto; padding:24px; display:flex; flex-direction:column; gap:20px; background:var(--bg-dark) }}
.no-selection {{ display:flex; align-items:center; justify-content:center; height:100%; color:var(--text-muted); font-size:15px }}

/* Paper detail */
.paper-detail {{ background:var(--bg-card); border:1px solid var(--border); border-radius:10px; overflow:hidden }}
.paper-detail-header {{ padding:20px 24px; border-bottom:1px solid var(--border) }}
.paper-title-full {{ font-size:18px; font-weight:700; color:#f1f5f9; line-height:1.4; margin-bottom:10px }}
.paper-tags {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px }}
.tag {{ padding:3px 10px; border-radius:12px; font-size:12px; font-weight:500 }}
.paper-info-row {{ display:flex; gap:20px; font-size:13px; color:var(--text-muted); flex-wrap:wrap; align-items:center }}
.paper-info-row a {{ color:var(--bid-light); text-decoration:none }}
.paper-info-row a:hover {{ text-decoration:underline }}
.btn-link {{ display:inline-flex; align-items:center; gap:5px; background:var(--bid-azul3); color:white !important; padding:5px 14px; border-radius:6px; font-size:12px; font-weight:600; text-decoration:none !important; border:none; cursor:pointer }}
.btn-link:hover {{ background:var(--bid-azul2) !important }}

.abstract-section {{ padding:20px 24px; border-bottom:1px solid var(--border) }}
.section-label {{ font-size:11px; text-transform:uppercase; letter-spacing:1px; color:var(--text-muted); margin-bottom:10px; font-weight:600 }}
.abstract-text {{ font-size:14px; line-height:1.7; color:#cbd5e1 }}
.no-abstract {{ font-size:13px; color:var(--text-muted); font-style:italic; padding:16px; background:var(--bg-dark); border-radius:6px; border:1px dashed var(--border) }}

/* Score breakdown */
.score-section {{ padding:20px 24px; border-bottom:1px solid var(--border) }}
.score-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-top:10px }}
.score-cell {{ background:var(--bg-dark); border:1px solid var(--border); border-radius:6px; padding:10px; text-align:center }}
.score-cell-val {{ font-size:22px; font-weight:700 }}
.score-cell-lbl {{ font-size:10px; color:var(--text-muted); margin-top:2px; text-transform:uppercase; letter-spacing:0.5px }}
.score-cell-max {{ font-size:11px; color:#3a5a80 }}

/* Criteria checklist */
.criteria-section {{ padding:20px 24px; border-bottom:1px solid var(--border) }}
.criteria-grid {{ display:flex; flex-direction:column; gap:8px; margin-top:10px }}
.criteria-item {{ display:flex; align-items:flex-start; gap:10px; padding:8px 12px; border-radius:6px; background:var(--bg-dark); border:1px solid var(--border) }}
.criteria-item.met {{ border-color:#16a34a44; background:#16a34a11 }}
.criteria-item.unmet {{ border-color:#dc262633; background:#dc262611 }}
.criteria-icon {{ font-size:14px; flex-shrink:0; margin-top:1px }}
.criteria-text {{ font-size:12px; color:#cbd5e1 }}
.criteria-text strong {{ color:#e2e8f0; font-size:12px }}

/* Decision panel */
.decision-section {{ padding:20px 24px }}
.decision-btns {{ display:flex; gap:10px; margin-bottom:14px }}
.btn-accept {{ background:#16a34a; color:white; border:none; padding:10px 24px; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:6px }}
.btn-accept:hover {{ background:#15803d }}
.btn-accept.active {{ background:#22c55e; box-shadow:0 0 0 3px #16a34a44 }}
.btn-reject {{ background:#dc2626; color:white; border:none; padding:10px 24px; border-radius:8px; font-size:14px; font-weight:600; cursor:pointer; display:flex; align-items:center; gap:6px }}
.btn-reject:hover {{ background:#b91c1c }}
.btn-reject.active {{ background:#ef4444; box-shadow:0 0 0 3px #dc262644 }}
.btn-pending {{ background:#1e3a5f; color:#7a9bc4; border:none; padding:10px 24px; border-radius:8px; font-size:14px; cursor:pointer }}
.btn-pending:hover {{ background:#264d7a }}
.note-input {{ width:100%; background:var(--bg-dark); border:1px solid var(--border); color:#e2e8f0; padding:10px 14px; border-radius:6px; font-size:13px; resize:vertical; min-height:70px }}
.note-input:focus {{ outline:none; border-color:var(--bid-azul3) }}
.save-btn {{ margin-top:10px; background:var(--bid-azul3); color:white; border:none; padding:8px 20px; border-radius:6px; font-size:13px; font-weight:600; cursor:pointer }}
.save-btn:hover {{ background:var(--bid-azul2) }}
.save-confirm {{ color:#22c55e; font-size:13px; display:none; margin-left:10px }}

/* Nav arrows */
.nav-btns {{ display:flex; gap:8px; align-items:center; margin-left:auto }}
.nav-btn {{ background:rgba(255,255,255,0.15); color:#e2e8f0; border:none; padding:6px 14px; border-radius:6px; cursor:pointer; font-size:13px }}
.nav-btn:hover {{ background:rgba(255,255,255,0.25) }}
.nav-btn:disabled {{ opacity:0.3; cursor:default }}

/* Progress bar */
.progress-bar {{ height:3px; background:var(--bid-azul1); border-radius:2px; overflow:hidden }}
.progress-fill {{ height:100%; background:linear-gradient(90deg,var(--bid-azul3),#22c55e); transition:width 0.3s }}

/* Export */
.export-bar {{ padding:10px 16px; border-top:1px solid var(--border); background:var(--bid-azul1); display:flex; gap:8px; align-items:center; font-size:12px; color:#a0c4e8 }}
.export-btn {{ background:var(--bid-azul3); color:white; border:none; padding:5px 12px; border-radius:5px; cursor:pointer; font-size:12px }}
.export-btn:hover {{ background:var(--bid-azul2) }}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-brand">
    <span class="topbar-badge">BID</span>
    <div>
      <h1>Revisión de Literatura — Adopción IA en Firmas</h1>
      <div class="topbar-sub">Fedesarrollo &amp; BID · Colombia y LATAM · Revisión manual de papers</div>
    </div>
  </div>
  <div class="stats">
    <span class="stat-pill green" id="stat-accepted">✅ 0 aceptados</span>
    <span class="stat-pill orange" id="stat-pending">⏳ 0 pendientes</span>
    <span class="stat-pill red" id="stat-rejected">❌ 0 rechazados</span>
    <span class="stat-pill" id="stat-total" style="color:#94a3b8">0 total</span>
  </div>
  <div class="nav-btns">
    <button class="nav-btn" id="btn-prev" onclick="navigate(-1)" disabled>← Anterior</button>
    <span id="nav-counter" style="font-size:12px;color:#64748b">—</span>
    <button class="nav-btn" id="btn-next" onclick="navigate(1)">Siguiente →</button>
  </div>
</div>

<div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0%"></div></div>

<div class="main">
  <!-- Sidebar -->
  <div class="sidebar">
    <div class="sidebar-header">
      <input class="search-box" type="text" placeholder="Buscar papers..." oninput="filterPapers()" id="search-input">
    </div>
    <div class="filters" id="filter-btns">
      <button class="filter-btn active" onclick="setFilter('all',this)">Todos</button>
      <button class="filter-btn" onclick="setFilter('pending',this)">Pendientes</button>
      <button class="filter-btn" onclick="setFilter('ACEPTADO',this)">✅ Acept.</button>
      <button class="filter-btn" onclick="setFilter('REVISAR',this)">🔄 Revisar</button>
      <button class="filter-btn" onclick="setFilter('manual_accept',this)" style="color:#22c55e">★ Manuales ✅</button>
      <button class="filter-btn" onclick="setFilter('manual_reject',this)" style="color:#ef4444">★ Manuales ❌</button>
      {pocket_filter_btns}
    </div>
    <div class="paper-list" id="paper-list"></div>
  </div>

  <!-- Main content -->
  <div class="content" id="main-content">
    <div class="no-selection">← Selecciona un paper para revisar</div>
  </div>
</div>

<div class="export-bar">
  <span>Exportar decisiones manuales:</span>
  <button class="export-btn" onclick="exportJSON()">JSON</button>
  <button class="export-btn" onclick="exportCSV()">CSV</button>
  <button class="export-btn" onclick="exportAccepted()">Solo Aceptados</button>
  <span id="export-msg" style="color:#22c55e;display:none">✅ Descargado</span>
</div>

<script>
const PAPERS = {papers_json};
let currentFilter = 'all';
let currentId = null;
let filteredIds = [];
let decisions = {{}};

// Load saved decisions from localStorage
function loadDecisions() {{
  const saved = localStorage.getItem('bid_ia_decisions');
  if (saved) decisions = JSON.parse(saved);
}}

function saveDecisions() {{
  localStorage.setItem('bid_ia_decisions', JSON.stringify(decisions));
}}

function init() {{
  loadDecisions();
  renderList();
  updateStats();
}}

function renderList() {{
  const search = document.getElementById('search-input').value.toLowerCase();
  const list = document.getElementById('paper-list');
  
  filteredIds = PAPERS
    .filter(p => {{
      if (search && !p.title.toLowerCase().includes(search) && !p.authors.toLowerCase().includes(search)) return false;
      const dec = decisions[p.id];
      if (currentFilter === 'all') return true;
      if (currentFilter === 'pending') return !dec;
      if (currentFilter === 'manual_accept') return dec === 'ACEPTADO';
      if (currentFilter === 'manual_reject') return dec === 'RECHAZADO';
      if (currentFilter === 'ACEPTADO' || currentFilter === 'REVISAR') return p.status === currentFilter;
      return p.pocket === currentFilter;
    }})
    .map(p => p.id);

  list.innerHTML = filteredIds.map(id => {{
    const p = PAPERS[id];
    const dec = decisions[id];
    const scoreColor = p.score >= 7 ? '#22c55e' : p.score >= 5 ? '#f97316' : '#64748b';
    const itemClass = id === currentId ? 'selected' : dec === 'ACEPTADO' ? 'decided-accept' : dec === 'RECHAZADO' ? 'decided-reject' : '';
    const decIcon = dec === 'ACEPTADO' ? '✅ ' : dec === 'RECHAZADO' ? '❌ ' : '';
    return `<div class="paper-item ${{itemClass}}" onclick="selectPaper(${{id}})" data-id="${{id}}">
      <div class="paper-title-small">${{decIcon}}${{p.title.substring(0,80)}}${{p.title.length>80?'...':''}}</div>
      <div class="paper-meta-small">
        <span style="color:${{p.pocket_color}};font-size:10px">${{p.pocket_label.substring(0,10)}}</span>
        <span class="score-badge" style="background:${{scoreColor}}22;color:${{scoreColor}}">${{p.score}}</span>
        <span style="font-size:10px">${{p.year||''}}</span>
      </div>
    </div>`;
  }}).join('');
  
  document.getElementById('nav-counter').textContent = `${{filteredIds.length}} papers`;
}}

function selectPaper(id) {{
  currentId = id;
  const posInFiltered = filteredIds.indexOf(id);
  document.getElementById('btn-prev').disabled = posInFiltered <= 0;
  document.getElementById('btn-next').disabled = posInFiltered >= filteredIds.length - 1;
  document.getElementById('nav-counter').textContent = `${{posInFiltered+1}} / ${{filteredIds.length}}`;
  
  // Update sidebar selection
  document.querySelectorAll('.paper-item').forEach(el => el.classList.remove('selected'));
  const el = document.querySelector(`[data-id="${{id}}"]`);
  if (el) {{ el.classList.add('selected'); el.scrollIntoView({{block:'nearest'}}); }}
  
  renderDetail(id);
  updateProgress();
}}

function navigate(dir) {{
  const pos = filteredIds.indexOf(currentId);
  const newPos = pos + dir;
  if (newPos >= 0 && newPos < filteredIds.length) selectPaper(filteredIds[newPos]);
}}

function renderDetail(id) {{
  const p = PAPERS[id];
  const dec = decisions[id] || '';
  const note = (decisions[id + '_note']) || '';
  const bd = p.breakdown || {{}};
  
  const scoreColor = p.score >= 7 ? '#22c55e' : p.score >= 5 ? '#f97316' : '#64748b';
  
  const abstractHtml = p.abstract
    ? `<div class="abstract-text">${{p.abstract}}</div>`
    : `<div class="no-abstract">⚠️ Abstract no disponible — el scoring automático se basó solo en el título.<br><br>
       ${{p.url ? `<a class="btn-link" href="${{p.url}}" target="_blank">↗ Abrir paper original</a>` : '<em>Sin URL disponible</em>'}}
       </div>`;
  
  const breakdownCells = [
    ['Metodología', bd.methodology, 4],
    ['Causalidad', bd.causalidity, 2],
    ['Top-Tier', bd.top_tier, 2],
    ['Novedad', bd.novelty, 1],
    ['Relevancia', bd.relevance, 2],
  ].map(([name, val, max]) => {{
    const c = val >= max*0.7 ? '#22c55e' : val > 0 ? '#f59e0b' : val < 0 ? '#ef4444' : '#475569';
    return `<div class="score-cell">
      <div class="score-cell-val" style="color:${{c}}">${{val}}</div>
      <div class="score-cell-lbl">${{name}}</div>
      <div class="score-cell-max">/${{max}}</div>
    </div>`;
  }}).join('');

  document.getElementById('main-content').innerHTML = `
    <div class="paper-detail">
      <div class="paper-detail-header">
        <div class="paper-title-full">${{p.title}}</div>
        <div class="paper-tags">
          <span class="tag" style="background:${{p.pocket_color}}22;color:${{p.pocket_color}}">${{p.pocket_label}}</span>
          <span class="tag" style="background:${{scoreColor}}22;color:${{scoreColor}}">Score: ${{p.score}}/11</span>
          <span class="tag" style="background:#33415544;color:#94a3b8">${{p.status}}</span>
          ${{dec ? `<span class="tag" style="background:${{dec==='ACEPTADO'?'#16a34a':'#dc2626'}}44;color:${{dec==='ACEPTADO'?'#22c55e':'#ef4444'}}">★ Manual: ${{dec}}</span>` : ''}}
        </div>
        <div class="paper-info-row">
          ${{p.authors ? `<span>👤 ${{p.authors}}</span>` : ''}}
          ${{p.year ? `<span>📅 ${{p.year}}</span>` : ''}}
          ${{p.venue ? `<span>📰 ${{p.venue}}</span>` : ''}}
          ${{p.citations ? `<span>📊 ${{p.citations}} citas</span>` : ''}}
          ${{p.url ? `<a class="btn-link" href="${{p.url}}" target="_blank">↗ Ver paper</a>` : '<span style="color:#3a5a80;font-size:12px">Sin URL</span>'}}
        </div>
      </div>
      
      <div class="abstract-section">
        <div class="section-label">Abstract</div>
        ${{abstractHtml}}
      </div>
      
      <div class="score-section">
        <div class="section-label">Score automático: ${{p.score}}/11 — ${{p.status}}</div>
        <div class="score-grid">${{breakdownCells}}</div>
        <p style="font-size:11px;color:#475569;margin-top:10px">
          Scores calculados automáticamente. Tu decisión manual override al score automático.
        </p>
      </div>

      ${{p.criteria && p.criteria.length ? `
      <div class="criteria-section">
        <div class="section-label">Requisitos de aceptación — ${{p.pocket_label}}</div>
        <div class="criteria-grid">
          ${{p.criteria.map(c => `
            <div class="criteria-item ${{c.met ? 'met' : 'unmet'}}">
              <span class="criteria-icon">${{c.met ? '✅' : '❌'}}</span>
              <div class="criteria-text"><strong>${{c.desc}}</strong></div>
            </div>
          `).join('')}}
        </div>
        <p style="font-size:11px;color:#475569;margin-top:8px">
          ${{p.criteria.filter(c=>c.met).length}}/${{p.criteria.length}} criterios cumplidos. Basado en texto del abstract/título.
        </p>
      </div>` : ''}}

      <div class="decision-section">
        <div class="section-label">Tu decisión manual</div>
        <div class="decision-btns">
          <button class="btn-accept ${{dec==='ACEPTADO'?'active':''}}" onclick="decide(${{id}},'ACEPTADO')">✅ Aceptar</button>
          <button class="btn-reject ${{dec==='RECHAZADO'?'active':''}}" onclick="decide(${{id}},'RECHAZADO')">❌ Rechazar</button>
          <button class="btn-pending ${{!dec?'active':''}}" onclick="decide(${{id}},'')">⏳ Pendiente</button>
        </div>
        <div class="section-label" style="margin-top:12px">Notas (opcional)</div>
        <textarea class="note-input" id="note-${{id}}" placeholder="Por qué aceptas/rechazas, qué nivel analiza (tarea/trabajador/equipo/firma), metodología, gap que cubre...">${{note}}</textarea>
        <div style="display:flex;align-items:center">
          <button class="save-btn" onclick="saveNote(${{id}})">Guardar nota</button>
          <span class="save-confirm" id="save-confirm-${{id}}">✅ Guardado</span>
        </div>
      </div>
    </div>`;
}}

function decide(id, decision) {{
  decisions[id] = decision;
  saveDecisions();
  renderDetail(id);
  renderList();
  updateStats();
  // Auto-advance to next paper if decision made
  if (decision) {{
    setTimeout(() => navigate(1), 400);
  }}
}}

function saveNote(id) {{
  const note = document.getElementById(`note-${{id}}`).value;
  decisions[id + '_note'] = note;
  saveDecisions();
  const confirm = document.getElementById(`save-confirm-${{id}}`);
  confirm.style.display = 'inline';
  setTimeout(() => confirm.style.display = 'none', 2000);
}}

function setFilter(filter, btn) {{
  currentFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderList();
}}

function filterPapers() {{ renderList(); }}

function updateStats() {{
  const accepted = Object.values(decisions).filter(d => d === 'ACEPTADO').length;
  const rejected = Object.values(decisions).filter(d => d === 'RECHAZADO').length;
  const pending = PAPERS.length - accepted - rejected;
  document.getElementById('stat-accepted').textContent = `✅ ${{accepted}} aceptados`;
  document.getElementById('stat-pending').textContent = `⏳ ${{pending}} pendientes`;
  document.getElementById('stat-rejected').textContent = `❌ ${{rejected}} rechazados`;
  document.getElementById('stat-total').textContent = `${{PAPERS.length}} total`;
}}

function updateProgress() {{
  const decided = Object.keys(decisions).filter(k => !k.includes('_note') && decisions[k]).length;
  const pct = (decided / PAPERS.length) * 100;
  document.getElementById('progress-fill').style.width = pct + '%';
}}

function exportJSON() {{
  const result = PAPERS.map(p => ({{
    ...p,
    manual_decision: decisions[p.id] || '',
    manual_note: decisions[p.id + '_note'] || '',
  }}));
  download('bid_ia_reviewed.json', JSON.stringify(result, null, 2));
}}

function exportCSV() {{
  const rows = [['ID','Title','Pocket','Score','Auto Status','Manual Decision','Note','URL','Year','Authors']];
  PAPERS.forEach(p => rows.push([
    p.id, `"${{p.title.replace(/"/g,'""')}}"`, p.pocket_label, p.score,
    p.status, decisions[p.id]||'', `"${{(decisions[p.id+'_note']||'').replace(/"/g,'""')}}"`,
    p.url, p.year, `"${{p.authors}}"`
  ]));
  download('bid_ia_reviewed.csv', rows.map(r => r.join(',')).join(String.fromCharCode(10)));
}}

function exportAccepted() {{
  const accepted = PAPERS.filter(p => decisions[p.id] === 'ACEPTADO' || (!decisions[p.id] && p.status === 'ACEPTADO'));
  download('bid_ia_accepted.json', JSON.stringify(accepted, null, 2));
}}

function download(filename, content) {{
  const a = document.createElement('a');
  a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(content);
  a.download = filename;
  a.click();
  document.getElementById('export-msg').style.display = 'inline';
  setTimeout(() => document.getElementById('export-msg').style.display = 'none', 2000);
}}

// Keyboard shortcuts
document.addEventListener('keydown', e => {{
  if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
  if (e.key === 'ArrowRight' || e.key === 'j') navigate(1);
  if (e.key === 'ArrowLeft' || e.key === 'k') navigate(-1);
  if (e.key === 'a' || e.key === 'A') currentId !== null && decide(currentId, 'ACEPTADO');
  if (e.key === 'r' || e.key === 'R') currentId !== null && decide(currentId, 'RECHAZADO');
  if (e.key === 'p' || e.key === 'P') currentId !== null && decide(currentId, '');
}});

init();
// Select first paper automatically
if (PAPERS.length > 0) setTimeout(() => selectPaper(filteredIds[0]), 100);
</script>
</body>
</html>'''

if __name__ == "__main__":
    papers = load_papers()
    html = generate_html(papers)
    with open("outputs/review_interface.html", "w") as f:
        f.write(html)
    print(f"✅ Interfaz creada: outputs/review_interface.html")
    print(f"   {len(papers)} papers cargados")
    print(f"   Abre en: http://localhost:8000/outputs/review_interface.html")
    print("   Shortcuts de teclado:")
    print(f"   A = Aceptar | R = Rechazar | P = Pendiente | → / ← = Navegar")
