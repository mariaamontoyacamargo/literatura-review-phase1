"""ui_v2.py - Enhanced Streamlit Dashboard for Literatura Review"""
import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter
import os

st.set_page_config(page_title="Literatura Review Dashboard", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
.metric-card {
    background-color: #f0f2f6;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
}
.status-accepted { color: #09ab3b; font-weight: bold; }
.status-review { color: #ffa421; font-weight: bold; }
.status-rejected { color: #ff2b2b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("📚 Literatura Review - AI Adoption & Productivity")
st.markdown("**BID-IA Project** | Interactive Dashboard for Paper Analysis")

# ============================================================================
# LOAD DATA
# ============================================================================
def load_data(pocket):
    """Load data for a specific pocket"""
    try:
        with open(f"data/{pocket}_reviewed.json") as f:
            reviewed = json.load(f)
        with open(f"data/{pocket}_synthesized.json") as f:
            synthesized = json.load(f)
        with open(f"data/{pocket}_graph.json") as f:
            graph_data = json.load(f)
        return reviewed, synthesized, graph_data
    except FileNotFoundError:
        return None, None, None

# Load pocket selector
st.sidebar.header("🎯 Pocket Selector")
available_pockets = []
for file in os.listdir("data"):
    if "_reviewed.json" in file:
        pocket = file.replace("_reviewed.json", "")
        available_pockets.append(pocket)

if not available_pockets:
    st.error("❌ No data files found. Please run the pipeline first.")
    st.stop()

selected_pocket = st.sidebar.selectbox("Select Pocket", available_pockets)
reviewed_papers, synthesized_papers, graph_data = load_data(selected_pocket)

if reviewed_papers is None:
    st.error(f"❌ Could not load data for {selected_pocket}")
    st.stop()

# ============================================================================
# SIDEBAR FILTERS
# ============================================================================
st.sidebar.header("🔍 Filters")

filter_status = st.sidebar.multiselect(
    "Filter by Status",
    options=["ACEPTADO", "REVISAR", "RECHAZADO"],
    default=["ACEPTADO"]
)

min_score = st.sidebar.slider("Minimum Score", 0, 10, 0, step=1)
min_citations = st.sidebar.slider("Minimum Citations", 0, 300, 0, step=10)

# Apply filters
filtered_papers = reviewed_papers.copy()
if filter_status:
    filtered_papers = [p for p in filtered_papers if p["status"] in filter_status]
if min_score > 0:
    filtered_papers = [p for p in filtered_papers if p["score"] >= min_score]
if min_citations > 0:
    filtered_papers = [p for p in filtered_papers if p["metadata"].get("citations", 0) >= min_citations]

# ============================================================================
# METRICS CARDS
# ============================================================================
st.header("📊 Quick Metrics")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("📄 Total Papers", len(filtered_papers))

with col2:
    accepted = len([p for p in filtered_papers if p["status"] == "ACEPTADO"])
    st.metric("✅ Accepted", accepted, f"{100*accepted/max(len(filtered_papers),1):.0f}%")

with col3:
    avg_score = sum(p["score"] for p in filtered_papers) / len(filtered_papers) if filtered_papers else 0
    st.metric("⭐ Avg Score", f"{avg_score:.1f}/10")

with col4:
    citations = sum(p["metadata"].get("citations", 0) for p in filtered_papers)
    st.metric("📈 Total Citations", int(citations))

with col5:
    network = graph_data.get("stats", {})
    st.metric("🕸️ Network Density", f"{network.get('density', 0):.2f}")

# ============================================================================
# TABS
# ============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 Papers", "🕸️ Network", "📊 Analysis", "🎯 Gaps", "📤 Export", "ℹ️ Info"
])

# ============================================================================
# TAB 1: PAPERS
# ============================================================================
with tab1:
    st.subheader("Papers List")

    col1, col2 = st.columns([2, 1])
    with col1:
        sort_by = st.selectbox("Sort by", ["Score (↓)", "Year (Recent)", "Citations (↓)", "Title (A-Z)"])
    with col2:
        show_count = st.number_input("Show", 1, 100, 10)

    if sort_by == "Score (↓)":
        filtered_papers = sorted(filtered_papers, key=lambda x: x["score"], reverse=True)
    elif sort_by == "Year (Recent)":
        filtered_papers = sorted(filtered_papers, key=lambda x: x["metadata"].get("year", 0), reverse=True)
    elif sort_by == "Citations (↓)":
        filtered_papers = sorted(filtered_papers, key=lambda x: x["metadata"].get("citations", 0), reverse=True)
    else:
        filtered_papers = sorted(filtered_papers, key=lambda x: x["title"])

    # Papers table
    papers_data = []
    for p in filtered_papers[:show_count]:
        papers_data.append({
            "Score": f"{p['score']:.0f}/10",
            "Status": p["status"],
            "Title": p["title"][:50] + "...",
            "Year": p["metadata"].get("year"),
            "Venue": p["metadata"].get("venue", "")[:30],
            "Citations": p["metadata"].get("citations", 0),
            "URL": "[Link](" + p["metadata"].get("url", "") + ")"
        })

    st.dataframe(pd.DataFrame(papers_data), use_container_width=True, hide_index=True)

    # Detailed view
    st.subheader("📄 Detailed View")
    selected_idx = st.selectbox("Select paper", range(len(filtered_papers[:show_count])), format_func=lambda i: filtered_papers[i]["title"][:60])

    if selected_idx < len(filtered_papers):
        paper = filtered_papers[selected_idx]
        synth = next((s for s in synthesized_papers if s["id"] == paper["title"]), None)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"### {paper['title']}")
            st.write(f"**Authors:** {', '.join(paper['metadata'].get('authors', [])[:3])}")
            st.write(f"**Year:** {paper['metadata'].get('year')} | **Venue:** {paper['metadata'].get('venue')}")
            st.write(f"\n**Abstract:** {paper['metadata'].get('abstract', 'N/A')[:400]}...")

        with col2:
            st.metric("Score", f"{paper['score']:.0f}/10")
            st.metric("Citations", paper['metadata'].get('citations', 0))
            st.metric("h-index", paper['metadata'].get('h_index', 'N/A'))

        st.write("#### Rubrica Breakdown")
        for criterion, score in paper["breakdown"].items():
            st.write(f"- **{criterion}**: +{score}")

# ============================================================================
# TAB 2: NETWORK
# ============================================================================
with tab2:
    st.subheader("🕸️ Thematic Network")

    if graph_data["stats"]["nodes"] > 0:
        # Network stats
        stats = graph_data["stats"]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Nodes", stats["nodes"])
        with col2:
            st.metric("Edges", stats["edges"])
        with col3:
            st.metric("Density", f"{stats.get('density', 0):.2f}")
        with col4:
            st.metric("Avg Degree", f"{stats.get('avg_degree', 0):.1f}")

        # Network visualization
        st.write("#### Network Relations by Type")
        if "relation_types" in stats:
            rel_types = stats["relation_types"]
            fig = go.Figure(data=[
                go.Bar(x=list(rel_types.keys()), y=list(rel_types.values()), marker_color="steelblue")
            ])
            fig.update_layout(title="Relation Types", xaxis_title="Type", yaxis_title="Count", height=300)
            st.plotly_chart(fig, use_container_width=True)

        # Papers by year timeline
        st.write("#### Papers Timeline")
        years = graph_data["gaps"]["distribution"]["years"]
        fig = go.Figure(data=[
            go.Scatter(x=list(years.keys()), y=list(years.values()), mode="lines+markers", marker_size=10)
        ])
        fig.update_layout(title="Papers by Year", xaxis_title="Year", yaxis_title="Count", height=300)
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("ℹ️ No network data available")

# ============================================================================
# TAB 3: ANALYSIS
# ============================================================================
with tab3:
    st.subheader("📊 Detailed Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.write("#### Score Distribution")
        scores = [p["score"] for p in filtered_papers]
        if scores:
            fig = px.histogram(x=scores, nbins=10, title="Score Distribution")
            fig.update_layout(height=300, xaxis_title="Score", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("#### Methodology Distribution")
        methodologies = Counter(p["metadata"].get("methodology", "Unknown") for p in filtered_papers)
        fig = px.pie(values=list(methodologies.values()), names=list(methodologies.keys()), title="Methodologies")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # Keywords wordcloud style
    st.write("#### Top Keywords")
    all_keywords = []
    for p in filtered_papers:
        all_keywords.extend(p["metadata"].get("keywords", []))

    keyword_counts = Counter(all_keywords)
    keywords_df = pd.DataFrame([{"Keyword": k, "Count": v} for k, v in keyword_counts.most_common(20)])

    fig = px.bar(keywords_df, x="Count", y="Keyword", orientation="h", title="Top Keywords")
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# TAB 4: GAPS
# ============================================================================
with tab4:
    st.subheader("🚨 Coverage Gaps")

    gaps = graph_data.get("gaps", {})

    if gaps.get("issues"):
        st.write("#### Identified Issues")
        for issue in gaps["issues"]:
            st.write(f"- {issue}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("#### By Pocket")
        pockets = gaps["distribution"]["pockets"]
        for pocket, count in pockets.items():
            status = "✅" if count >= 7 else "⚠️" if count >= 5 else "🔴"
            st.write(f"{status} {pocket}: {count}")

    with col2:
        st.write("#### By Methodology")
        methods = gaps["distribution"]["methodologies"]
        for method, count in methods.items():
            st.write(f"- {method[:25]}: {count}")

    with col3:
        st.write("#### By Year")
        years = sorted(gaps["distribution"]["years"].items())
        for year, count in years:
            status = "✅" if count >= 5 else "⚠️" if count >= 2 else "🔴"
            st.write(f"{status} {year}: {count}")

# ============================================================================
# TAB 5: EXPORT
# ============================================================================
with tab5:
    st.subheader("📤 Export Data")

    # Prepare exports
    export_df = pd.DataFrame([{
        "ID": p["title"][:50],
        "Score": f"{p['score']:.0f}",
        "Status": p["status"],
        "Year": p["metadata"].get("year"),
        "Venue": p["metadata"].get("venue"),
        "Citations": p["metadata"].get("citations", 0),
        "URL": p["metadata"].get("url")
    } for p in filtered_papers])

    col1, col2, col3 = st.columns(3)

    with col1:
        csv = export_df.to_csv(index=False)
        st.download_button(label="📥 Download CSV", data=csv, file_name=f"{selected_pocket}_papers.csv")

    with col2:
        json_data = json.dumps(filtered_papers, indent=2)
        st.download_button(label="📥 Download JSON", data=json_data, file_name=f"{selected_pocket}_papers.json")

    with col3:
        st.write("📋 BibTeX export coming soon")

    st.dataframe(export_df, use_container_width=True)

# ============================================================================
# TAB 6: INFO
# ============================================================================
with tab6:
    st.subheader("ℹ️ About This Dashboard")

    st.write("""
    ### Architecture

    **Pipeline Components:**
    1. **Researcher** - Collects papers from top-tier venues
    2. **Reviewer** - Validates quality with rubrica (0-10 scale)
    3. **Synthesizer** - Extracts structured metadata and insights
    4. **Mapper** - Builds thematic network and detects gaps
    5. **UI Dashboard** - This interactive interface

    ### Data Quality
    - Papers filtered by: h-index >20, citations >50, venue top-tier
    - Rubrica ensures methodological rigor
    - Network detects thematic clusters and gaps

    ### Gaps Detection
    - Identifies underrepresented pockets
    - Flags years with low coverage
    - Highlights isolated papers in network
    """)

    st.write("---")
    st.caption("BID-IA Project | Literature Review Phase 1 | Generated with Claude Code")
