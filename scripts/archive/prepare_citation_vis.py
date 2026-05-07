"""Prepare citation network for visualization"""
import json
import networkx as nx

# Load real citation network
with open('data/real_citation_network.json') as f:
    network = json.load(f)

print(f"Loaded network: {network['stats']['nodes']} nodes, {network['stats']['edges']} edges")

# Build networkx graph for layout
G = nx.DiGraph()
for node in network['nodes']:
    G.add_node(node['id'], **node)

for edge in network['edges']:
    G.add_edge(edge['source'], edge['target'], weight=edge['weight'])

# Compute layout (spring layout for directed graphs)
print("Computing network layout (spring layout)...")
pos = nx.spring_layout(G, k=1, iterations=50, seed=42)

# Prepare visualization data
vis_nodes = []
for node_id in G.nodes():
    node_data = G.nodes[node_id]
    x, y = pos[node_id]
    
    # Color by status
    color_map = {
        'ACEPTADO': '#10b981',
        'REVISAR': '#f59e0b',
        'RECHAZADO': '#ef4444'
    }
    color = color_map.get(node_data.get('status', 'REVISAR'), '#6b7280')
    
    vis_nodes.append({
        'id': node_id,
        'label': node_data.get('title', 'Unknown')[:50],
        'title': node_data.get('title', 'Unknown'),
        'x': float(x),
        'y': float(y),
        'color': color,
        'size': 20 + node_data.get('score', 5) * 2,
        'score': node_data.get('score', 5),
        'status': node_data.get('status', 'REVISAR'),
        'pocket': node_data.get('pocket', 'unknown'),
        'year': node_data.get('year', 2025)
    })

# Prepare edges
vis_edges = []
for u, v, data in G.edges(data=True):
    vis_edges.append({
        'from': u,
        'to': v,
        'weight': data.get('weight', 1.0),
        'relation': data.get('relation', 'cites'),
        'label': f"{G.nodes[u].get('title', '')[:30]}... cites {G.nodes[v].get('title', '')[:30]}..."
    })

vis_data = {
    'nodes': vis_nodes,
    'edges': vis_edges,
    'metadata': {
        'total_nodes': len(vis_nodes),
        'total_edges': len(vis_edges),
        'density': nx.density(G),
        'type': 'Real Citation Network from Semantic Scholar'
    }
}

with open('data/real_citation_network_vis.json', 'w') as f:
    json.dump(vis_data, f, indent=2)

print(f"✓ Created visualization data: {len(vis_nodes)} nodes, {len(vis_edges)} edges")
print(f"✓ Saved to: data/real_citation_network_vis.json")

# Summary stats
in_degree = dict(G.in_degree())
out_degree = dict(G.out_degree())

print("\n📊 Network Summary:")
print(f"  Nodes: {len(vis_nodes)}")
print(f"  Edges: {len(vis_edges)}")
print(f"  Density: {nx.density(G):.4f}")
print(f"  Avg citations per paper: {sum(out_degree.values())/len(out_degree):.2f}" if out_degree else "  No edges")

top_cited = sorted(in_degree.items(), key=lambda x: -x[1])[:5]
print("\n🔗 Top 5 Cited Papers:")
for node_id, count in top_cited:
    if count > 0:
        title = G.nodes[node_id].get('title', 'Unknown')
        print(f"  • {title[:60]}... ({count} citations)")

top_citing = sorted(out_degree.items(), key=lambda x: -x[1])[:5]
print("\n📝 Top 5 Most Citing Papers:")
for node_id, count in top_citing:
    if count > 0:
        title = G.nodes[node_id].get('title', 'Unknown')
        print(f"  • {title[:60]}... (→ {count} papers)")
