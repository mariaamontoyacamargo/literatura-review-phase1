"""Extract real citation relationships by searching abstracts for paper references"""
import json
import re
from pathlib import Path
from collections import defaultdict
import networkx as nx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DOICitationExtractor:
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.papers = []
        self.paper_index = {}  # arxiv_id -> paper mapping
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
                        arxiv_id = paper.get('metadata', {}).get('arxiv_id', '')
                        if arxiv_id:
                            self.paper_index[arxiv_id] = paper
                            paper['doi'] = f"arxiv:{arxiv_id}"
                        self.papers.append(paper)
        
        logger.info(f"✓ Loaded {len(self.papers)} papers")
        logger.info(f"✓ Indexed {len(self.paper_index)} papers by arXiv ID")
        return self.papers
    
    def extract_arxiv_references(self, text):
        """Extract arXiv IDs from text (e.g., 2604.09413, arXiv:2604.09413)"""
        if not text:
            return []
        
        # Look for arXiv ID patterns: YYMM.NNNNN or YYMM.NNNNNVN
        patterns = [
            r'\b(\d{4}\.\d{4,5}(?:v\d+)?)\b',  # 2604.09413 or 2604.09413v1
            r'arxiv[:\s]+(\d{4}\.\d{4,5}(?:v\d+)?)',  # arxiv:2604.09413
        ]
        
        references = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            references.update(matches)
        
        # Normalize (remove version numbers)
        normalized = set()
        for ref in references:
            base_id = ref.split('v')[0]
            normalized.add(base_id)
        
        return list(normalized)
    
    def build_citation_graph(self):
        """Build citation network from paper abstracts"""
        logger.info("\n🕸️ Extracting citation relationships from abstracts...")
        
        # Add all papers as nodes
        for paper in self.papers:
            arxiv_id = paper.get('metadata', {}).get('arxiv_id', '')
            if arxiv_id:
                self.graph.add_node(
                    arxiv_id,
                    title=paper.get('metadata', {}).get('title', 'Unknown')[:70],
                    score=paper.get('score', 5),
                    pocket=paper.get('pocket', 'unknown'),
                    status=paper.get('status', 'REVISAR'),
                    year=paper.get('metadata', {}).get('year', 2025),
                    doi=paper.get('doi', f"arxiv:{arxiv_id}")
                )
        
        # Extract citations from abstracts
        citation_count = 0
        no_refs_count = 0
        
        for paper in self.papers:
            arxiv_id = paper.get('metadata', {}).get('arxiv_id', '')
            if not arxiv_id:
                continue
            
            summary = paper.get('metadata', {}).get('summary', '')
            referenced_ids = self.extract_arxiv_references(summary)
            
            if not referenced_ids:
                no_refs_count += 1
                continue
            
            # Add edges for cited papers that exist in our database
            for ref_id in referenced_ids:
                if ref_id in self.paper_index and ref_id != arxiv_id:
                    self.graph.add_edge(
                        arxiv_id,
                        ref_id,
                        weight=1.0,
                        relation='cites',
                        source='abstract'
                    )
                    citation_count += 1
        
        logger.info(f"✓ Extracted {citation_count} direct citations from {self.graph.number_of_nodes()} papers")
        logger.info(f"✓ Papers with no references in abstract: {no_refs_count}")
        
        return self.graph
    
    def get_network_stats(self):
        """Get network statistics"""
        stats = {
            'nodes': self.graph.number_of_nodes(),
            'edges': self.graph.number_of_edges(),
            'density': nx.density(self.graph),
            'avg_degree': 0,
            'connected_components': nx.number_connected_components(self.graph.to_undirected()),
        }
        
        if self.graph.number_of_nodes() > 0:
            degrees = [d for n, d in self.graph.degree()]
            stats['avg_degree'] = sum(degrees) / len(degrees) if degrees else 0
        
        return stats
    
    def save_network(self, output_file='data/doi_citation_network.json'):
        """Save network as JSON"""
        logger.info(f"\n💾 Saving citation network...")
        
        # Prepare edge data
        edges_data = []
        for u, v, data in self.graph.edges(data=True):
            edges_data.append({
                'source': u,
                'target': v,
                'weight': data.get('weight', 1.0),
                'relation': data.get('relation', 'cites'),
                'source_db': data.get('source', 'abstract')
            })
        
        network_data = {
            'nodes': [
                {
                    'id': node,
                    'title': self.graph.nodes[node].get('title', 'Unknown'),
                    'score': self.graph.nodes[node].get('score', 5),
                    'pocket': self.graph.nodes[node].get('pocket', 'unknown'),
                    'status': self.graph.nodes[node].get('status', 'REVISAR'),
                    'year': self.graph.nodes[node].get('year', 2025),
                    'doi': self.graph.nodes[node].get('doi', f"arxiv:{node}")
                }
                for node in self.graph.nodes()
            ],
            'edges': edges_data,
            'stats': self.get_network_stats()
        }
        
        with open(output_file, 'w') as f:
            json.dump(network_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"  ✓ Saved: {output_file}")
        return network_data
    
    def print_summary(self):
        """Print summary"""
        stats = self.get_network_stats()
        
        print("\n" + "=" * 70)
        print("📊 DOI CITATION NETWORK SUMMARY")
        print("=" * 70)
        print(f"Total papers: {len(self.papers)}")
        print(f"Papers with arXiv ID: {len(self.paper_index)}")
        print()
        print(f"Citation network nodes: {stats['nodes']}")
        print(f"Citation network edges: {stats['edges']}")
        print(f"Network density: {stats['density']:.4f}")
        print(f"Avg citations per paper: {stats['avg_degree']:.2f}")
        print(f"Connected components: {stats['connected_components']}")
        
        # Find top cited papers
        if self.graph.number_of_nodes() > 0:
            in_degrees = dict(self.graph.in_degree())
            out_degrees = dict(self.graph.out_degree())
            
            print("\n🔗 Most Cited Papers (in-degree):")
            top_cited = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
            for arxiv_id, count in top_cited:
                if count > 0:
                    title = self.graph.nodes[arxiv_id].get('title', 'Unknown')
                    print(f"  • {arxiv_id}: {count} citations")
                    print(f"    {title[:60]}...")
            
            print("\nMost Citing Papers (out-degree):")
            top_citing = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
            for arxiv_id, count in top_citing:
                if count > 0:
                    title = self.graph.nodes[arxiv_id].get('title', 'Unknown')
                    print(f"  • {arxiv_id}: cites {count} papers")
                    print(f"    {title[:60]}...")
        
        print("\n" + "=" * 70)


if __name__ == '__main__':
    extractor = DOICitationExtractor()
    extractor.load_papers()
    extractor.build_citation_graph()
    extractor.save_network()
    extractor.print_summary()
