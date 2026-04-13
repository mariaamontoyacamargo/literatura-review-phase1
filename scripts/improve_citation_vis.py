"""Improve citation network visualization - handle hub-and-spoke topology"""
import json
import networkx as nx
import numpy as np

# Load real citation network
with open('data/real_citation_network.json') as f:
    network = json.load(f)

# Build graph
G = nx.DiGraph()
node_map = {}
for node in network['nodes']:
    G.add_node(node['id'], **node)
    node_map[node['id']] = node

for edge in network['edges']:
    G.add_edge(edge['source'], edge['target'])

print("Building improved visualization...")
print(f"  Network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# Convert to undirected for layout
G_undirected = G.to_undirected()

# Use Kamada-Kawai layout (better for hub-and-spoke networks)
print("  Computing Kamada-Kawai layout...")
pos = nx.kamada_kawai_layout(G_undirected, scale=2)

# Prepare nodes
vis_nodes = []
for node_id in G.nodes():
    node_data = G.nodes[node_id]
    x, y = pos[node_id]
    
    color_map = {
        'ACEPTADO': '#10b981',
        'REVISAR': '#f59e0b',
        'RECHAZADO': '#ef4444'
    }
    color = color_map.get(node_data.get('status', 'REVISAR'), '#6b7280')
    
    # Bigger size for high-degree nodes
    in_deg = G.in_degree(node_id)
    out_deg = G.out_degree(node_id)
    degree = in_deg + out_deg
    size = 20 + min(degree, 50)  # Cap size to avoid huge nodes
    
    vis_nodes.append({
        'id': node_id,
        'label': node_data.get('title', 'Unknown')[:40],
        'title': node_data.get('title', 'Unknown'),
        'x': float(x),
        'y': float(y),
        'color': color,
        'size': size,
        'score': node_data.get('score', 5),
        'status': node_data.get('status', 'REVISAR'),
        'pocket': node_data.get('pocket', 'unknown'),
        'year': node_data.get('year', 2025),
        'in_degree': in_deg,
        'out_degree': out_deg
    })

# Prepare edges - FILTERED for visibility
# Show: 
#   - All edges for papers with low out-degree
#   - Only top edges for high-degree hubs
vis_edges = []
for u, v, data in G.edges(data=True):
    # Get out-degree of source
    source_out_degree = G.out_degree(u)
    
    # If source is a hub (>30 citations), be selective
    if source_out_degree > 30:
        # Only show if target has high in-degree (is also cited multiple times)
        target_in_degree = G.in_degree(v)
        if target_in_degree < 2:
            continue  # Skip this edge
    
    vis_edges.append({
        'from': u,
        'to': v,
        'weight': data.get('weight', 1.0),
        'relation': data.get('relation', 'cites'),
        'label': f"{G.nodes[u].get('title', '')[:25]}... → {G.nodes[v].get('title', '')[:25]}..."
    })

vis_data = {
    'nodes': vis_nodes,
    'edges': vis_edges,
    'metadata': {
        'total_nodes': len(vis_nodes),
        'total_edges': len(vis_edges),
        'total_edges_in_network': G.number_of_edges(),
        'edges_filtered': G.number_of_edges() - len(vis_edges),
        'density': nx.density(G),
        'type': 'Real Citation Network (Improved Layout)',
        'layout': 'Kamada-Kawai with hub filtering'
    }
}

with open('data/real_citation_network_vis.json', 'w') as f:
    json.dump(vis_data, f, indent=2)

print(f"✓ Updated visualization:")
print(f"  - {len(vis_nodes)} nodes")
print(f"  - {len(vis_edges)} visible edges (filtered from {G.number_of_edges()} total)")
print(f"  - {G.number_of_edges() - len(vis_edges)} edges hidden from hubs")
print(f"✓ Saved to: data/real_citation_network_vis.json")

# Stats on what was hidden
print(f"\n📊 Hub filtering:")
hub_count = 0
for node_id in G.nodes():
    if G.out_degree(node_id) > 30:
        title = G.nodes[node_id].get('title', 'Unknown')[:50]
        out_deg = G.out_degree(node_id)
        print(f"  • {title}... ({out_deg} citations)")
        hub_count += 1

if hub_count == 0:
    print("  (No major hubs found)")
