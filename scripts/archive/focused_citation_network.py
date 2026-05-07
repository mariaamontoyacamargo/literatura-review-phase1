"""Create focused citation network - only papers with real connections"""
import json
import networkx as nx

# Load network
with open('data/real_citation_network.json') as f:
    network = json.load(f)

# Build graph
G = nx.DiGraph()
for node in network['nodes']:
    G.add_node(node['id'], **node)

for edge in network['edges']:
    G.add_edge(edge['source'], edge['target'])

print("Creating focused citation network...")

# Get only ACEPTADO + REVISAR papers (not RECHAZADO)
significant_nodes = set()
for node_id in G.nodes():
    status = G.nodes[node_id].get('status', 'REVISAR')
    if status in ['ACEPTADO', 'REVISAR']:
        significant_nodes.add(node_id)

print(f"  Selected papers: {len(significant_nodes)} (ACEPTADO + REVISAR)")

# Filter graph to significant papers
G_focused = G.subgraph(significant_nodes).copy()
print(f"  Resulting network: {G_focused.number_of_nodes()} nodes, {G_focused.number_of_edges()} edges")

# Remove isolated nodes in this subgraph
isolated = [n for n in G_focused.nodes() if G_focused.degree(n) == 0]
G_focused.remove_nodes_from(isolated)
print(f"  After removing isolated: {G_focused.number_of_nodes()} nodes, {G_focused.number_of_edges()} edges")

# Compute layout on undirected version
print("  Computing layout...")
G_undirected = G_focused.to_undirected()
pos = nx.spring_layout(G_undirected, k=2, iterations=100, seed=42)

# Prepare visualization
vis_nodes = []
for node_id in G_focused.nodes():
    node_data = G_focused.nodes[node_id]
    x, y = pos[node_id]
    
    color_map = {
        'ACEPTADO': '#10b981',
        'REVISAR': '#f59e0b',
        'RECHAZADO': '#ef4444'
    }
    color = color_map.get(node_data.get('status', 'REVISAR'), '#6b7280')
    
    in_deg = G_focused.in_degree(node_id)
    out_deg = G_focused.out_degree(node_id)
    size = 20 + (in_deg + out_deg) * 3
    
    vis_nodes.append({
        'id': node_id,
        'label': node_data.get('title', 'Unknown')[:40],
        'title': node_data.get('title', 'Unknown'),
        'x': float(x),
        'y': float(y),
        'color': color,
        'size': min(size, 60),
        'score': node_data.get('score', 5),
        'status': node_data.get('status', 'REVISAR'),
        'pocket': node_data.get('pocket', 'unknown'),
        'year': node_data.get('year', 2025),
    })

# Prepare edges
vis_edges = []
for u, v, data in G_focused.edges(data=True):
    vis_edges.append({
        'from': u,
        'to': v,
        'weight': data.get('weight', 1.0),
        'relation': data.get('relation', 'cites'),
        'label': f"{G_focused.nodes[u].get('title', '')[:30]}..."
    })

vis_data = {
    'nodes': vis_nodes,
    'edges': vis_edges,
    'metadata': {
        'total_nodes': len(vis_nodes),
        'total_edges': len(vis_edges),
        'density': nx.density(G_focused) if len(vis_nodes) > 1 else 0,
        'type': 'Real Citation Network - Focused (ACEPTADO + REVISAR)',
        'original_total_nodes': G.number_of_nodes(),
        'original_total_edges': G.number_of_edges(),
    }
}

with open('data/real_citation_network_vis.json', 'w') as f:
    json.dump(vis_data, f, indent=2)

print(f"\n✓ Focused network saved:")
print(f"  - {len(vis_nodes)} nodes (significant papers)")
print(f"  - {len(vis_edges)} edges (real citations)")
print(f"  - Density: {vis_data['metadata']['density']:.4f}")
print(f"\nOriginal network:")
print(f"  - {vis_data['metadata']['original_total_nodes']} nodes")
print(f"  - {vis_data['metadata']['original_total_edges']} edges")

# Stats
in_degrees = dict(G_focused.in_degree())
out_degrees = dict(G_focused.out_degree())

print(f"\nTop cited papers in focused network:")
top_cited = sorted(in_degrees.items(), key=lambda x: -x[1])[:5]
for node, count in top_cited:
    if count > 0:
        title = G_focused.nodes[node].get('title', 'Unknown')[:50]
        print(f"  • {title}... ({count} citations)")
