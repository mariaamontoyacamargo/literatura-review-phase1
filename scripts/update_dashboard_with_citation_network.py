"""Update dashboard to use citation network instead of consolidated graph"""
import json
from pathlib import Path

# Load the citation network
citation_network_path = Path('data/citation_network.json')
if not citation_network_path.exists():
    print("Citation network not found!")
    exit(1)

with open(citation_network_path) as f:
    citation_network = json.load(f)

print(f"Loaded citation network: {citation_network['stats']['nodes']} nodes, {citation_network['stats']['edges']} edges")

# Create a simplified citation network for visualization (Vis.js format)
nodes_data = []
edges_data = []

# Add nodes
for node in citation_network['nodes']:
    color = {
        'ACEPTADO': '#10b981',
        'REVISAR': '#f59e0b', 
        'RECHAZADO': '#ef4444'
    }.get(node['status'], '#6b7280')
    
    nodes_data.append({
        'id': node['id'],
        'label': node['title'][:60],
        'title': node['title'],
        'pocket': node['pocket'],
        'score': node['score'],
        'status': node['status'],
        'year': node['year'],
        'color': color,
        'size': 25 + node['score'] * 3
    })

# Add edges (limit to first 5000 for performance)
edge_weight_map = {}
for i, edge in enumerate(citation_network['edges'][:5000]):
    edges_data.append({
        'from': edge['source'],
        'to': edge['target'],
        'weight': edge['weight'],
        'relation': edge['relation'],
        'label': edge.get('reason', edge['relation']),
        'width': 0.5 + edge['weight'] * 2,
        'color': {
            'rgba(102, 126, 234, 0.4)': 'blue',  # same-pocket
            'rgba(16, 185, 129, 0.4)': 'green',  # similar-methodology
            'rgba(139, 92, 246, 0.4)': 'purple'  # temporal-adjacent
        }.get(edge['relation'], 'gray')
    })

# Save for dashboard
output = {
    'nodes': nodes_data,
    'edges': edges_data,
    'metadata': {
        'total_nodes': citation_network['stats']['nodes'],
        'total_edges': citation_network['stats']['edges'],
        'visualized_edges': len(edges_data),
        'density': citation_network['stats']['density'],
        'edge_types': {}
    }
}

# Count edge types
for edge in citation_network['edges']:
    rel = edge['relation']
    output['metadata']['edge_types'][rel] = output['metadata']['edge_types'].get(rel, 0) + 1

with open('data/citation_network_vis.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"✓ Created citation_network_vis.json with {len(nodes_data)} nodes and {len(edges_data)} edges")
print(f"\nEdge type distribution:")
for rel, count in sorted(output['metadata']['edge_types'].items(), key=lambda x: -x[1]):
    pct = 100 * count / citation_network['stats']['edges']
    print(f"  {rel}: {count} ({pct:.1f}%)")
