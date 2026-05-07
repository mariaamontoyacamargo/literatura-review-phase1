"""Generate updated dashboard with citation network"""
import json
from pathlib import Path

# Load all data
pockets = ['evaluacion_experimental', 'management', 'labor', 'desigualdad', 'policy', 'human_machine_interaction', 'innovacion_difusion']
pocket_names = {
    'evaluacion_experimental': 'Evaluación Experimental',
    'management': 'Management',
    'labor': 'Labor Markets',
    'desigualdad': 'Desigualdad',
    'policy': 'Policy',
    'human_machine_interaction': 'HMI',
    'innovacion_difusion': 'Innovación y Difusión'
}

all_papers = []
for pocket in pockets:
    with open(f'data/{pocket}_reviewed.json') as f:
        papers = json.load(f)
        for p in papers:
            if not p.get('metadata'): p['metadata'] = {}
            p['metadata']['pocket'] = pocket
            p['metadata']['pocket_name'] = pocket_names[pocket]
        all_papers.extend(papers)

# Load citation network visualization data
with open('data/citation_network_vis.json') as f:
    citation_network = json.load(f)

print(f"Loaded {len(all_papers)} papers")
print(f"Loaded citation network with {len(citation_network['nodes'])} nodes and {len(citation_network['edges'])} edges")
