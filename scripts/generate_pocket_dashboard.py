"""generate_pocket_dashboard.py — Dashboard detallado por pocket con abstracts visibles"""
import json, os, glob

POCKET_LABELS = {
    "management": "Management",
    "labor": "Labor Markets",
    "evaluacion_experimental": "Evaluación Experimental",
    "desigualdad": "Desigualdad",
    "policy": "Policy",
    "human_machine_interaction": "Human-Machine Interaction",
    "innovacion_difusion": "Innovación y Difusión"
}

POCKET_COLORS = {
    "management": "#6366f1", "labor": "#f59e0b",
    "evaluacion_experimental": "#10b981", "desigualdad": "#ef4444",
    "policy": "#3b82f6", "human_machine_interaction": "#8b5cf6",
    "innovacion_difusion": "#ec4899"
}

def load_all_pockets():
    pockets = {}
    for pocket_key, label in POCKET_LABELS.items():
        f = f"data/{pocket_key}_reviewed_enriched.json"
        if not os.path.exists(f):
            f = f"data/{pocket_key}_reviewed.json"
        if os.path.exists(f):
            with open(f) as fp:
                papers = json.load(fp)
            pockets[pocket_key] = {"label": label, "papers": papers, "color": POCKET_COLORS[pocket_key]}
    return pockets

def score_bar(score, max_score=11):
    pct = min(100, int(score / max_score * 100))
    color = "#22c55e" if score >= 7 else "#f97316" if score >= 5 else "#6b7280"
    return f'<div style="background:#e5e7eb;border-radius:4px;height:8px;width:120px;display:inline-block;vertical-align:middle"><div style="background:{color};height:8px;border-radius:4px;width:{pct}%"></div></div>'

def status_badge(status):
    colors = {"ACEPTADO": "#22c55e", "REVISAR": "#f97316", "RECHAZADO": "#ef4444"}
    c = colors.get(status, "#6b7280")
    return f'<span style="background:{c};color:white;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600">{status}</span>'

def render_paper_card(p):
    meta = p.get("metadata", p)
    abstract = meta.get("abstract", meta.get("summary", ""))
    title = p.get("title") or meta.get("title","Sin título")
    score = p.get("score", 0)
    status = p.get("status","")
    year = meta.get("year","")
    venue = meta.get("venue","")
    url = meta.get("url","")
    authors = meta.get("authors","")
    if isinstance(authors, list): authors = ", ".join(authors[:3]) + (" et al." if len(meta.get("authors",[])) > 3 else "")
    citations = meta.get("citations","")
    breakdown = p.get("breakdown",{})
    
    abstract_html = ""
    if abstract:
        abstract_html = f'''
        <div style="margin-top:10px;font-size:13px;color:#374151;line-height:1.6;background:#f9fafb;padding:12px;border-radius:6px;border-left:3px solid #e5e7eb">
          <strong style="color:#6b7280;font-size:11px;text-transform:uppercase;letter-spacing:0.5px">Abstract</strong><br>
          <span id="abs_{hash(title)}" style="display:none">{abstract}</span>
          <span id="abs_short_{hash(title)}">{abstract[:280]}{'...' if len(abstract)>280 else ''}</span>
          {'<a href="#" onclick="toggleAbstract('+str(hash(title))+');return false;" style="color:#6366f1;font-size:12px;margin-left:4px" id="abs_btn_'+str(hash(title))+'">ver más</a>' if len(abstract)>280 else ''}
        </div>'''
    else:
        abstract_html = '<div style="margin-top:8px;font-size:12px;color:#9ca3af;font-style:italic">⚠️ Abstract no disponible — solo título disponible para scoring</div>'

    breakdown_html = ""
    if breakdown:
        items = [
            ("Metodología", breakdown.get("methodology",0), 4, "RCT/quasi-exp=4, Panel=3, Framework=2"),
            ("Causalidad", breakdown.get("causalidity",0), 2, "Causal identificada=2, Correlacional=0, -1"),
            ("Top-Tier", breakdown.get("top_tier",0), 2, "h-index>30+citas>100+venue=2"),
            ("Novedad", breakdown.get("novelty",0), 1, "≥2024=+1, ≥2020=0, <2020=-1"),
            ("Relevancia", breakdown.get("relevance",0), 2, "IA+productividad+contexto=2")
        ]
        rows = ""
        for name, val, mx, tip in items:
            bar_w = max(0, int(val/mx*60)) if mx>0 else 0
            col = "#22c55e" if val>=mx*0.7 else "#f59e0b" if val>0 else "#ef4444"
            rows += f'<tr title="{tip}"><td style="padding:2px 8px 2px 0;font-size:12px;color:#6b7280;white-space:nowrap">{name}</td><td><div style="background:#e5e7eb;border-radius:3px;height:6px;width:80px;display:inline-block"><div style="background:{col};height:6px;border-radius:3px;width:{bar_w}px"></div></div></td><td style="padding-left:6px;font-size:12px;color:#374151;font-weight:600">{val}/{mx}</td></tr>'
        breakdown_html = f'<details style="margin-top:8px"><summary style="font-size:12px;color:#6366f1;cursor:pointer">Ver desglose de score</summary><table style="margin-top:6px">{rows}</table></details>'

    url_html = f'<a href="{url}" target="_blank" style="color:#6366f1;font-size:12px;margin-left:8px">🔗 Ver paper</a>' if url else ''
    
    return f'''
    <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:12px;border-left:4px solid {"#22c55e" if score>=7 else "#f97316" if score>=5 else "#6b7280"}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
        <div style="flex:1">
          <div style="font-weight:600;font-size:14px;color:#111827;line-height:1.4">{title}</div>
          <div style="margin-top:4px;font-size:12px;color:#6b7280">{authors} {'· '+str(year) if year else ''} {'· '+str(venue) if venue else ''} {'· '+str(citations)+' citas' if citations else ''}</div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          {status_badge(status)}<br>
          <span style="font-size:18px;font-weight:700;color:{"#22c55e" if score>=7 else "#f97316" if score>=5 else "#6b7280"}">{score}</span>
          <span style="font-size:11px;color:#9ca3af">/11</span>
          {url_html}
        </div>
      </div>
      {abstract_html}
      {breakdown_html}
    </div>'''

def generate_html(pockets):
    # Stats globales
    all_papers = [p for d in pockets.values() for p in d["papers"]]
    total = len(all_papers)
    accepted = sum(1 for p in all_papers if p.get("status")=="ACEPTADO")
    revisar = sum(1 for p in all_papers if p.get("status")=="REVISAR")
    rejected = sum(1 for p in all_papers if p.get("status")=="RECHAZADO")
    with_abstract = sum(1 for p in all_papers if (p.get("metadata") or p).get("abstract"))
    avg_score = sum(p.get("score",0) for p in all_papers) / max(len(all_papers),1)

    # Tabs de pockets
    tab_buttons = ""
    tab_contents = ""
    
    for i, (key, data) in enumerate(pockets.items()):
        papers = data["papers"]
        label = data["label"]
        color = data["color"]
        active = "active" if i==0 else ""
        
        p_accepted = [p for p in papers if p.get("status")=="ACEPTADO"]
        p_revisar  = [p for p in papers if p.get("status")=="REVISAR"]
        p_rejected = [p for p in papers if p.get("status")=="RECHAZADO"]
        p_with_abs = sum(1 for p in papers if (p.get("metadata") or p).get("abstract"))
        avg_s = sum(p.get("score",0) for p in papers) / max(len(papers),1)
        
        # Score distribution data
        score_dist = {}
        for p in papers:
            s = p.get("score",0)
            score_dist[s] = score_dist.get(s,0)+1
        
        score_chart_data = json.dumps([{"score": k, "count": v} for k,v in sorted(score_dist.items())])
        
        # Methodology distribution
        meth_dist = {}
        for p in papers:
            m = p.get("breakdown",{}).get("methodology",0)
            label_m = {0:"Sin datos",1:"Empírico básico",2:"Framework/Modelo",3:"Panel/FE",4:"RCT/Quasi-exp"}.get(m, str(m))
            meth_dist[label_m] = meth_dist.get(label_m,0)+1
        
        # Papers ordenados: aceptados primero, luego revisar, luego rechazados
        sorted_papers = sorted(papers, key=lambda p: ({"ACEPTADO":0,"REVISAR":1,"RECHAZADO":2}.get(p.get("status",""),3), -p.get("score",0)))
        
        cards_html = "".join(render_paper_card(p) for p in sorted_papers)
        
        tab_buttons += f'''
        <button class="tab-btn {'active' if i==0 else ''}" 
                onclick="switchTab('{key}')"
                id="btn_{key}"
                style="{'background:'+color+';color:white;border:2px solid '+color if i==0 else 'background:white;color:#374151;border:2px solid #e5e7eb'};
                       padding:8px 16px;border-radius:20px;cursor:pointer;font-size:13px;font-weight:600;margin:4px;white-space:nowrap">
          {label} ({len(papers)})
        </button>'''
        
        tab_contents += f'''
        <div id="tab_{key}" style="display:{'block' if i==0 else 'none'}">
          <!-- Stats del pocket -->
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px">
            <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:24px;font-weight:700;color:{color}">{len(papers)}</div>
              <div style="font-size:12px;color:#6b7280">Total papers</div>
            </div>
            <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:24px;font-weight:700;color:#22c55e">{len(p_accepted)}</div>
              <div style="font-size:12px;color:#6b7280">ACEPTADO ({int(len(p_accepted)/max(len(papers),1)*100)}%)</div>
            </div>
            <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:24px;font-weight:700;color:#f97316">{len(p_revisar)}</div>
              <div style="font-size:12px;color:#6b7280">REVISAR ({int(len(p_revisar)/max(len(papers),1)*100)}%)</div>
            </div>
            <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:24px;font-weight:700;color:#ef4444">{len(p_rejected)}</div>
              <div style="font-size:12px;color:#6b7280">RECHAZADO ({int(len(p_rejected)/max(len(papers),1)*100)}%)</div>
            </div>
            <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:24px;font-weight:700;color:#6366f1">{avg_s:.1f}</div>
              <div style="font-size:12px;color:#6b7280">Score promedio /11</div>
            </div>
            <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:24px;font-weight:700;color:#0ea5e9">{p_with_abs}</div>
              <div style="font-size:12px;color:#6b7280">Con abstract ({int(p_with_abs/max(len(papers),1)*100)}%)</div>
            </div>
          </div>
          
          <!-- Nota sobre abstracts faltantes -->
          {'<div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:12px;margin-bottom:16px;font-size:13px;color:#92400e"><strong>⚠️ Nota:</strong> '+str(len(papers)-p_with_abs)+' papers ('+str(int((len(papers)-p_with_abs)/max(len(papers),1)*100))+'%) vienen de Google Scholar y no tienen abstract. El score de esos papers se calculó solo con el título. Pueden estar sub-valorados.</div>' if p_with_abs < len(papers) else ''}
          
          <!-- Metodología distribution -->
          <div style="background:white;border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:20px">
            <h3 style="margin:0 0 12px;font-size:14px;color:#374151">Distribución por Metodología detectada</h3>
            <div style="display:flex;flex-wrap:wrap;gap:8px">
              {''.join(f'<div style="background:#f3f4f6;border-radius:6px;padding:6px 12px;font-size:13px"><strong>{v}</strong> {k}</div>' for k,v in sorted(meth_dist.items(), key=lambda x:-x[1]))}
            </div>
            <p style="font-size:12px;color:#9ca3af;margin:8px 0 0">
              Sin datos = Google Scholar papers sin abstract. Framework/Modelo = papers con texto pero sin metodología empírica explícita.
            </p>
          </div>
          
          <!-- Filtros -->
          <div style="margin-bottom:16px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
            <span style="font-size:13px;color:#6b7280">Filtrar:</span>
            <button onclick="filterPocket('{key}','all')" id="{key}_f_all" style="background:#6366f1;color:white;border:none;padding:4px 12px;border-radius:12px;cursor:pointer;font-size:12px">Todos ({len(papers)})</button>
            <button onclick="filterPocket('{key}','ACEPTADO')" id="{key}_f_ACEPTADO" style="background:#e5e7eb;color:#374151;border:none;padding:4px 12px;border-radius:12px;cursor:pointer;font-size:12px">✅ Aceptados ({len(p_accepted)})</button>
            <button onclick="filterPocket('{key}','REVISAR')" id="{key}_f_REVISAR" style="background:#e5e7eb;color:#374151;border:none;padding:4px 12px;border-radius:12px;cursor:pointer;font-size:12px">🔄 Revisar ({len(p_revisar)})</button>
            <button onclick="filterPocket('{key}','RECHAZADO')" id="{key}_f_RECHAZADO" style="background:#e5e7eb;color:#374151;border:none;padding:4px 12px;border-radius:12px;cursor:pointer;font-size:12px">❌ Rechazados ({len(p_rejected)})</button>
            <button onclick="filterPocket('{key}','abstract')" id="{key}_f_abstract" style="background:#e5e7eb;color:#374151;border:none;padding:4px 12px;border-radius:12px;cursor:pointer;font-size:12px">📄 Con abstract ({p_with_abs})</button>
          </div>
          
          <!-- Papers list -->
          <div id="papers_{key}">
            {cards_html}
          </div>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BID-IA Literatura Review — Por Pocket</title>
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0 }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#f1f5f9; color:#111827 }}
    .header {{ background:linear-gradient(135deg,#1e1b4b,#312e81); color:white; padding:24px 32px }}
    .header h1 {{ font-size:22px; font-weight:700 }}
    .header p {{ font-size:14px; opacity:0.8; margin-top:4px }}
    .global-stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:12px; padding:20px 32px; background:white; border-bottom:1px solid #e5e7eb }}
    .stat {{ text-align:center }}
    .stat-val {{ font-size:26px; font-weight:700; color:#312e81 }}
    .stat-lbl {{ font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px }}
    .tabs-bar {{ padding:16px 32px; background:white; border-bottom:1px solid #e5e7eb; overflow-x:auto; white-space:nowrap }}
    .content {{ padding:24px 32px; max-width:1200px; margin:0 auto }}
  </style>
</head>
<body>

<div class="header">
  <h1>BID-IA: Literature Review — Análisis por Pocket</h1>
  <p>Papers sobre adopción de IA y productividad · 7 pockets temáticos · Scores basados en metodología, causalidad, top-tier, novedad y relevancia</p>
</div>

<div class="global-stats">
  <div class="stat"><div class="stat-val">{total}</div><div class="stat-lbl">Total papers</div></div>
  <div class="stat"><div class="stat-val" style="color:#22c55e">{accepted}</div><div class="stat-lbl">Aceptados</div></div>
  <div class="stat"><div class="stat-val" style="color:#f97316">{revisar}</div><div class="stat-lbl">Por revisar</div></div>
  <div class="stat"><div class="stat-val" style="color:#ef4444">{rejected}</div><div class="stat-lbl">Rechazados</div></div>
  <div class="stat"><div class="stat-val">{avg_score:.1f}</div><div class="stat-lbl">Score avg /11</div></div>
  <div class="stat"><div class="stat-val" style="color:#0ea5e9">{with_abstract}</div><div class="stat-lbl">Con abstract</div></div>
  <div class="stat"><div class="stat-val" style="color:#9ca3af">{total-with_abstract}</div><div class="stat-lbl">Sin abstract ⚠️</div></div>
</div>

<div class="tabs-bar">
  {tab_buttons}
</div>

<div class="content">
  <div style="background:#dbeafe;border:1px solid #93c5fd;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:13px;color:#1e40af">
    <strong>Cómo leer los scores:</strong> 
    Metodología (0-4) + Causalidad (-1 a +2) + Top-Tier (0-2) + Novedad (-1 a +1) + Relevancia (0-2) = máx 11 pts.
    <strong>Verde ≥7</strong> (ACEPTADO sólido) · <strong>Naranja 5-6</strong> (revisar con atención) · <strong>Gris &lt;5</strong> (débil o sin abstract).
    Papers sin abstract fueron evaluados solo por título — pueden estar sub-valorados.
  </div>
  {tab_contents}
</div>

<script>
const pocketPapers = {{}};

function switchTab(key) {{
  document.querySelectorAll('[id^="tab_"]').forEach(t => t.style.display='none');
  document.querySelectorAll('.tab-btn').forEach(b => {{
    b.style.background='white'; b.style.color='#374151'; b.style.borderColor='#e5e7eb';
  }});
  document.getElementById('tab_'+key).style.display='block';
  const btn = document.getElementById('btn_'+key);
  const colors = {{management:'#6366f1',labor:'#f59e0b',evaluacion_experimental:'#10b981',desigualdad:'#ef4444',policy:'#3b82f6',human_machine_interaction:'#8b5cf6',innovacion_difusion:'#ec4899'}};
  btn.style.background = colors[key] || '#6366f1';
  btn.style.color = 'white';
  btn.style.borderColor = colors[key] || '#6366f1';
}}

function filterPocket(pocket, status) {{
  const container = document.getElementById('papers_'+pocket);
  const cards = container.querySelectorAll('[data-status]');
  cards.forEach(c => {{
    if (status==='all') c.style.display='block';
    else if (status==='abstract') c.style.display = c.dataset.hasAbstract==='true' ? 'block':'none';
    else c.style.display = c.dataset.status===status ? 'block':'none';
  }});
  // Update active filter button
  document.querySelectorAll('[id^="'+pocket+'_f_"]').forEach(b => {{
    b.style.background='#e5e7eb'; b.style.color='#374151';
  }});
  const activeBtn = document.getElementById(pocket+'_f_'+status);
  if(activeBtn) {{ activeBtn.style.background='#6366f1'; activeBtn.style.color='white'; }}
}}

function toggleAbstract(id) {{
  const full = document.getElementById('abs_'+id);
  const short = document.getElementById('abs_short_'+id);
  const btn = document.getElementById('abs_btn_'+id);
  if(full.style.display==='none') {{
    full.style.display='inline'; short.style.display='none'; if(btn) btn.textContent='ver menos';
  }} else {{
    full.style.display='none'; short.style.display='inline'; if(btn) btn.textContent='ver más';
  }}
}}
</script>

</body>
</html>'''

if __name__ == "__main__":
    pockets = load_all_pockets()
    html = generate_html(pockets)
    
    # Add data-status attributes to cards for filtering
    # We need to post-process the HTML to add data attributes
    import re
    
    # Add data attributes to paper cards
    def add_data_attrs(html):
        # Find all paper cards and add data-status based on border color
        html = re.sub(
            r'(border-left:4px solid #22c55e.*?</div>\s*</div>)',
            r'\1',
            html, flags=re.DOTALL
        )
        return html
    
    with open("outputs/dashboard_per_pocket.html","w") as f:
        f.write(html)
    
    print(f"✅ Dashboard creado: outputs/dashboard_per_pocket.html")
    print(f"   Accede en: http://localhost:8000/outputs/dashboard_per_pocket.html")
