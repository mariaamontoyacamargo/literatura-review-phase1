"""citation_network_fast.py - Build citation network using existing metadata (no API calls)"""

import json
import logging
from pathlib import Path
from collections import defaultdict
import networkx as nx
import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FastCitationNetworkBuilder:
    """Build citation network using arxiv IDs and metadata"""

    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.papers = []
        self.graph = nx.DiGraph()

    def load_papers(self):
        """Load all reviewed papers"""
        logger.info("Loading papers from all pockets...")
        pockets = ['evaluacion_experimental', 'management', 'labor', 'desigualdad',
                   'policy', 'human_machine_interaction', 'innovacion_difusion']

        for pocket in pockets:
            file_path = self.data_dir / f'{pocket}_reviewed.json'
            if file_path.exists():
                with open(file_path) as f:
                    pocket_papers = json.load(f)
                    for paper in pocket_papers:
                        paper['pocket'] = pocket
                        # Create DOI-like ID from arxiv_id
                        arxiv_id = paper.get('metadata', {}).get('arxiv_id', '')
                        if arxiv_id:
                            paper['doi'] = f"arxiv:{arxiv_id}"
                        else:
                            paper['doi'] = f"gs:{paper.get('title', 'unknown')[:30]}"
                    self.papers.extend(pocket_papers)

        logger.info(f"✓ Loaded {len(self.papers)} papers")
        papers_with_arxiv = sum(1 for p in self.papers if 'arxiv:' in p.get('doi', ''))
        logger.info(f"✓ Papers with arXiv ID: {papers_with_arxiv}")
        return self.papers

    def build_citation_network(self):
        """Build network based on methodology, topic, and temporal proximity"""
        logger.info("\n🕸️ Building citation network...")

        # Filter to ACEPTADO papers for core network
        accepted = [p for p in self.papers if p.get('status') == 'ACEPTADO']
        logger.info(f"✓ Core network: {len(accepted)} ACEPTADO papers")

        # Add all papers as nodes
        for paper in self.papers:
            self.graph.add_node(
                paper.get('doi'),
                title=paper.get('metadata', {}).get('title', 'Unknown')[:70],
                score=paper.get('score', 5),
                pocket=paper.get('pocket', 'unknown'),
                status=paper.get('status', 'REVISAR'),
                year=paper.get('metadata', {}).get('year', 2025),
                methodology=paper.get('breakdown', {}).get('methodology', 0)
            )

        # Create edges based on multiple criteria
        citation_count = 0

        # 1. Papers in same pocket (strong thematic connection)
        pockets_dict = defaultdict(list)
        for paper in self.papers:
            pocket = paper.get('pocket')
            pockets_dict[pocket].append(paper)

        for pocket, papers_in_pocket in pockets_dict.items():
            for i, paper1 in enumerate(papers_in_pocket):
                for paper2 in papers_in_pocket[i+1:]:
                    # Weight based on score proximity
                    score_diff = abs(paper1.get('score', 5) - paper2.get('score', 5))
                    weight = max(0.3, 1.0 - (score_diff * 0.1))

                    self.graph.add_edge(
                        paper1.get('doi'),
                        paper2.get('doi'),
                        weight=weight,
                        relation='same-pocket',
                        reason=f'Both in {pocket}'
                    )
                    citation_count += 1

        # 2. Papers with similar methodology (cross-pocket connections)
        methods_dict = defaultdict(list)
        for paper in self.papers:
            method = paper.get('breakdown', {}).get('methodology', 0)
            methods_dict[method].append(paper)

        for method, papers_with_method in methods_dict.items():
            for i, paper1 in enumerate(papers_with_method):
                # Only connect across pockets if both are ACEPTADO
                if paper1.get('status') != 'ACEPTADO':
                    continue

                for paper2 in papers_with_method[i+1:]:
                    if paper2.get('status') != 'ACEPTADO':
                        continue

                    # Skip if already connected
                    if self.graph.has_edge(paper1.get('doi'), paper2.get('doi')):
                        continue

                    self.graph.add_edge(
                        paper1.get('doi'),
                        paper2.get('doi'),
                        weight=0.6,
                        relation='similar-methodology',
                        reason='Same methodology approach'
                    )
                    citation_count += 1

        # 3. Temporal connections (adjacent years)
        years_dict = defaultdict(list)
        for paper in accepted:  # Only for ACEPTADO
            year = paper.get('metadata', {}).get('year', 2025)
            years_dict[year].append(paper)

        for year in sorted(years_dict.keys()):
            if year + 1 in years_dict:
                for paper1 in years_dict[year]:
                    for paper2 in years_dict[year + 1]:
                        if self.graph.has_edge(paper1.get('doi'), paper2.get('doi')):
                            continue

                        self.graph.add_edge(
                            paper1.get('doi'),
                            paper2.get('doi'),
                            weight=0.4,
                            relation='temporal-adjacent',
                            reason=f'{year} → {year+1}'
                        )
                        citation_count += 1

        logger.info(f"✓ Citation network built: {self.graph.number_of_nodes()} nodes, {citation_count} edges")
        return self.graph

    def save_citation_network(self, output_file='data/citation_network.json'):
        """Save network as JSON"""
        logger.info(f"\n💾 Saving citation network...")

        network_data = {
            'nodes': [
                {
                    'id': node,
                    'title': self.graph.nodes[node].get('title', 'Unknown'),
                    'score': self.graph.nodes[node].get('score', 5),
                    'pocket': self.graph.nodes[node].get('pocket', 'unknown'),
                    'status': self.graph.nodes[node].get('status', 'REVISAR'),
                    'year': self.graph.nodes[node].get('year', 2025),
                }
                for node in self.graph.nodes()
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'weight': data.get('weight', 0.5),
                    'relation': data.get('relation', 'citation'),
                    'reason': data.get('reason', '')
                }
                for u, v, data in self.graph.edges(data=True)
            ],
            'stats': {
                'nodes': self.graph.number_of_nodes(),
                'edges': self.graph.number_of_edges(),
                'density': nx.density(self.graph) if self.graph.number_of_nodes() > 1 else 0
            }
        }

        with open(output_file, 'w') as f:
            json.dump(network_data, f, ensure_ascii=False, indent=2)
        logger.info(f"  ✓ Saved: {output_file}")

    def save_enriched_papers(self):
        """Save papers with DOI fields"""
        logger.info("\n💾 Saving papers with DOI assignments...")

        pockets = defaultdict(list)
        for paper in self.papers:
            pocket = paper.get('pocket')
            pockets[pocket].append(paper)

        for pocket, papers in pockets.items():
            output_file = self.data_dir / f'{pocket}_reviewed_with_dois.json'
            with open(output_file, 'w') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)
            logger.info(f"  ✓ Saved: {output_file}")

    def print_summary(self):
        """Print summary"""
        papers_with_arxiv = sum(1 for p in self.papers if 'arxiv:' in p.get('doi', ''))

        print("\n" + "=" * 70)
        print("📊 CITATION NETWORK SUMMARY")
        print("=" * 70)
        print(f"Total papers: {len(self.papers)}")
        print(f"Papers with arXiv ID: {papers_with_arxiv}")
        print(f"Papers with Google Scholar ID: {len(self.papers) - papers_with_arxiv}")
        print()
        print(f"Citation network nodes: {self.graph.number_of_nodes()}")
        print(f"Citation network edges: {self.graph.number_of_edges()}")
        print(f"Network density: {nx.density(self.graph) if self.graph.number_of_nodes() > 1 else 0:.3f}")
        print()

        # Analyze edges by type
        edge_types = defaultdict(int)
        for u, v, data in self.graph.edges(data=True):
            rel = data.get('relation', 'unknown')
            edge_types[rel] += 1

        print("Edge types:")
        for rel_type, count in sorted(edge_types.items(), key=lambda x: -x[1]):
            print(f"  • {rel_type}: {count}")

        print("\n" + "=" * 70)


if __name__ == '__main__':
    builder = FastCitationNetworkBuilder()
    builder.load_papers()
    builder.build_citation_network()
    builder.save_enriched_papers()
    builder.save_citation_network()
    builder.print_summary()
