"""ui.py - Streamlit Dashboard for Literatura Review"""
import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Literatura Review", layout="wide")

st.title("📚 Literatura Review Phase 1: AI Adoption & Productivity")
st.markdown("*BID-IA Project | Global Top-Tier Papers on AI Adoption & Productivity*")

# Load data
try:
    with open("data/reviewed_papers.json") as f:
        reviewed_papers = json.load(f)
    with open("data/graph.json") as f:
        graph_data = json.load(f)
except FileNotFoundError:
    st.error("❌ Data files not found. Please run the pipeline first.")
    st.stop()

# Sidebar filters
st.sidebar.header("🔍 Filters")
show_status = st.sidebar.multiselect(
    "Filter by Status",
    options=["ACEPTADO", "REVISAR", "RECHAZADO"],
    default=["ACEPTADO"]
)

show_pockets = st.sidebar.multiselect(
    "Filter by Pocket",
    options=["worker-level", "firm-level", "team-level", "task-level", "multi-level"],
    default=None
)

min_score = st.sidebar.slider("Minimum Score", 0, 10, 0)

# Filter papers
filtered_papers = reviewed_papers
if show_status:
    filtered_papers = [p for p in filtered_papers if p["status"] in show_status]
if show_pockets:
    filtered_papers = [p for p in filtered_papers if p["metadata"].get("pocket") in show_pockets]
if min_score > 0:
    filtered_papers = [p for p in filtered_papers if p["score"] >= min_score]

# Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📄 Total Papers", len(filtered_papers))
with col2:
    accepted = len([p for p in filtered_papers if p["status"] == "ACEPTADO"])
    st.metric("✅ Accepted", accepted)
with col3:
    avg_score = sum(p["score"] for p in filtered_papers) / len(filtered_papers) if filtered_papers else 0
    st.metric("⭐ Avg Score", f"{avg_score:.1f}/10")
with col4:
    citations_sum = sum(p["metadata"].get("citations", 0) for p in filtered_papers)
    st.metric("📊 Total Citations", int(citations_sum))

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Papers", "Graph", "Gaps", "Export"])

with tab1:
    st.header("Papers List")

    # Sort options
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox("Sort by", ["Score (Desc)", "Year (Recent)", "Citations (Desc)", "Title (A-Z)"])
    with col2:
        show_count = st.number_input("Show papers", 1, 50, 10)

    if sort_by == "Score (Desc)":
        filtered_papers = sorted(filtered_papers, key=lambda x: x["score"], reverse=True)
    elif sort_by == "Year (Recent)":
        filtered_papers = sorted(filtered_papers, key=lambda x: x["metadata"].get("year", 0), reverse=True)
    elif sort_by == "Citations (Desc)":
        filtered_papers = sorted(filtered_papers, key=lambda x: x["metadata"].get("citations", 0), reverse=True)
    else:
        filtered_papers = sorted(filtered_papers, key=lambda x: x["title"])

    # Display papers
    for i, paper in enumerate(filtered_papers[:show_count]):
        with st.expander(f"**{paper['score']:.0f}/10** - {paper['title'][:70]}..."):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Authors:** {', '.join(paper['metadata'].get('authors', [])[:2])}")
                st.write(f"**Year:** {paper['metadata'].get('year')} | **Venue:** {paper['metadata'].get('venue')}")
                st.write(f"**Status:** {paper['status']} | **Pocket:** {paper['metadata'].get('pocket')}")

            with col2:
                st.metric("Score", f"{paper['score']}/10")
                st.metric("Citations", paper['metadata'].get('citations', 0))

            st.write(f"**Abstract:** {paper['metadata'].get('abstract', 'N/A')[:300]}...")

            if "breakdown" in paper:
                st.write("**Rubrica Breakdown:**")
                for criterion, score in paper["breakdown"].items():
                    st.write(f"  - {criterion}: +{score}")

with tab2:
    st.header("Thematic Network")

    # Create network visualization
    if graph_data["nodes"]:
        fig = go.Figure()

        # Add edges
        edge_x = []
        edge_y = []
        for edge in graph_data["edges"]:
            x0 = next((n["id"] for n in graph_data["nodes"] if n["id"] == edge["source"]), None)
            y0 = next((n["id"] for n in graph_data["nodes"] if n["id"] == edge["target"]), None)

        # Simplified network view
        st.info(f"📊 Network: {graph_data['stats']['nodes']} papers, {graph_data['stats']['edges']} connections (density: {graph_data['stats']['density']:.2f})")

        # Papers by pocket
        pocket_counts = {}
        for node in graph_data["nodes"]:
            pocket = node.get("pocket", "unknown")
            pocket_counts[pocket] = pocket_counts.get(pocket, 0) + 1

        fig_pocket = go.Figure(data=[go.Bar(x=list(pocket_counts.keys()), y=list(pocket_counts.values()))])
        fig_pocket.update_layout(title="Papers by Pocket", xaxis_title="Pocket", yaxis_title="Count")
        st.plotly_chart(fig_pocket, use_container_width=True)

with tab3:
    st.header("Coverage Gaps Identified")

    gaps = graph_data.get("gaps", {})
    if "identified" in gaps:
        st.warning("**Underrepresented Areas:**")
        for gap in gaps["identified"]:
            st.write(f"  - {gap}")

    st.info("**Coverage Distribution:**")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**By Pocket:**")
        for pocket, count in gaps.get("distribution", {}).get("pockets", {}).items():
            st.write(f"  {pocket}: {count}")

    with col2:
        st.write("**By Methodology:**")
        for method, count in gaps.get("distribution", {}).get("methodologies", {}).items():
            st.write(f"  {method}: {count}")

    with col3:
        st.write("**By Year:**")
        for year, count in sorted(gaps.get("distribution", {}).get("years", {}).items()):
            st.write(f"  {year}: {count}")

with tab4:
    st.header("Export Data")

    # Papers table
    papers_table = []
    for p in filtered_papers:
        papers_table.append({
            "Title": p["title"],
            "Authors": ", ".join(p["metadata"].get("authors", [])[:2]),
            "Year": p["metadata"].get("year"),
            "Venue": p["metadata"].get("venue"),
            "Score": p["score"],
            "Status": p["status"],
            "Pocket": p["metadata"].get("pocket"),
            "Citations": p["metadata"].get("citations", 0),
            "URL": p["metadata"].get("url", "")
        })

    df = pd.DataFrame(papers_table)

    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(label="📥 Download CSV", data=csv, file_name="papers.csv")

    with col2:
        json_str = json.dumps(filtered_papers, indent=2)
        st.download_button(label="📥 Download JSON", data=json_str, file_name="papers.json")

    st.dataframe(df, use_container_width=True)

st.markdown("---")
st.caption("BID-IA Project | Literature Review Phase 1 | Generated with Claude Code")
