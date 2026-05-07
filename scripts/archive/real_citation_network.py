"""Build citation network based on REAL citations using Semantic Scholar API"""
import json
import logging
import time
from pathlib import Path
from collections import defaultdict
import networkx as nx
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealCitationNetworkBuilder:
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.papers = []
        self.paper_by_doi = {}  # DOI -> paper
        self.paper_by_title = {}  # title -> paper
        self.graph = nx.DiGraph()
        self.session = requests.Session()
        
    def load_papers(self):
        """Load all reviewed papers"""
        logger.info("Loading papers...")
        pockets = ['evaluacion_experimental', 'management', 'labor', 'desigualdad',
                   'policy', 'human_machine_interaction', 'innovacion_difusion']
        
        for pocket in pockets:
            file_path = self.data_dir / f'{pocket}_reviewed.json'
            if file_path.exists():
                with open(file_path) as f:
                    papers = json.load(f)
                    for paper in papers:
                        paper['pocket'] = pocket
                        self.papers.append(paper)
                        
                        # Index by title for lookup
                        title = paper.get('title', '').lower()
                        self.paper_by_title[title] = paper
        
        logger.info(f"✓ Loaded {len(self.papers)} papers")
        return self.papers
    
    def search_semantic_scholar(self, title, authors=None, year=None):
        """Search for paper in Semantic Scholar API"""
        try:
            # Build query
            query = title
            if authors and len(authors) > 0:
                query += f" {authors[0]}"
            
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': query,
                'limit': 1,
                'fields': 'paperId,externalIds,citationCount,title,authors,year'
            }
            
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    paper = data['data'][0]
                    # Verify it's the same paper
                    if paper['title'].lower() == title.lower():
                        return paper
            
        except Exception as e:
            logger.debug(f"Semantic Scholar search failed: {e}")
        
        return None
    
    def get_citations(self, semantic_id):
        """Get papers that cite this paper"""
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/{semantic_id}/citations"
            params = {
                'limit': 100,
                'fields': 'paperId,title,externalIds,year'
            }
            
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            
        except Exception as e:
            logger.debug(f"Get citations failed: {e}")
        
        return []
    
    def get_references(self, semantic_id):
        """Get papers that this paper cites"""
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/{semantic_id}/references"
            params = {
                'limit': 100,
                'fields': 'paperId,title,externalIds,year'
            }
            
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            
        except Exception as e:
            logger.debug(f"Get references failed: {e}")
        
        return []
    
    def build_citation_network(self):
        """Build network by searching for real citations"""
        logger.info("\n🕸️ Building real citation network from Semantic Scholar...")
        logger.info("   (This may take 2-3 minutes, limited to 10 papers for demo)")
        
        # Add all papers as nodes
        for paper in self.papers:
            title = paper.get('title', 'Unknown')
            paper_id = f"{paper.get('pocket')}:{title[:40]}"
            
            self.graph.add_node(
                paper_id,
                title=title[:70],
                score=paper.get('score', 5),
                pocket=paper.get('pocket', 'unknown'),
                status=paper.get('status', 'REVISAR'),
                year=paper.get('metadata', {}).get('year', 2025),
                original_paper=paper
            )
        
        # Process first N papers to find real citations
        max_papers = 10
        citation_edges = 0
        papers_searched = 0
        
        for idx, paper in enumerate(self.papers[:max_papers]):
            papers_searched += 1
            title = paper.get('title', '')
            authors = paper.get('metadata', {}).get('authors', [])
            year = paper.get('metadata', {}).get('year')
            
            logger.info(f"  [{papers_searched}/{max_papers}] Searching citations for: {title[:60]}...")
            
            # Search for paper in Semantic Scholar
            ss_paper = self.search_semantic_scholar(title, authors, year)
            if not ss_paper:
                logger.info(f"    ✗ Not found in Semantic Scholar")
                time.sleep(1)
                continue
            
            semantic_id = ss_paper.get('paperId')
            if not semantic_id:
                logger.info(f"    ✗ No Semantic ID")
                time.sleep(1)
                continue
            
            logger.info(f"    ✓ Found (Semantic ID: {semantic_id})")
            
            # Get papers it CITES (references)
            logger.info(f"    → Fetching papers it cites...")
            references = self.get_references(semantic_id)
            
            if references:
                logger.info(f"    ✓ Found {len(references)} references")
                
                for ref in references[:10]:  # Limit to 10 refs per paper
                    ref_title = ref.get('title', '').lower()
                    
                    # Check if referenced paper is in our dataset
                    for our_paper in self.papers:
                        our_title = our_paper.get('title', '').lower()
                        if our_title == ref_title or (len(our_title) > 20 and ref_title in our_title):
                            # Found a real citation!
                            from_id = f"{paper.get('pocket')}:{paper.get('title', '')[:40]}"
                            to_id = f"{our_paper.get('pocket')}:{our_paper.get('title', '')[:40]}"
                            
                            if from_id != to_id and not self.graph.has_edge(from_id, to_id):
                                self.graph.add_edge(
                                    from_id,
                                    to_id,
                                    weight=1.0,
                                    relation='cites',
                                    source='semantic-scholar'
                                )
                                citation_edges += 1
                                logger.info(f"      ✓ CITATION FOUND: {paper.get('title')[:40]}... → {our_paper.get('title')[:40]}...")
            else:
                logger.info(f"    → No references found")
            
            time.sleep(2)  # Rate limit
        
        logger.info(f"\n✓ Citation network built: {self.graph.number_of_nodes()} nodes, {citation_edges} REAL citation edges")
        return self.graph
    
    def save_network(self, output_file='data/real_citation_network.json'):
        """Save network"""
        logger.info(f"\n💾 Saving network...")
        
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
                    'weight': data.get('weight', 1.0),
                    'relation': data.get('relation', 'cites'),
                    'source_db': data.get('source_db', 'semantic-scholar')
                }
                for u, v, data in self.graph.edges(data=True)
            ],
            'stats': {
                'nodes': self.graph.number_of_nodes(),
                'edges': self.graph.number_of_edges(),
                'density': nx.density(self.graph),
                'edge_type': 'REAL CITATIONS from Semantic Scholar'
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(network_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"  ✓ Saved: {output_file}")
    
    def print_summary(self):
        """Print summary"""
        print("\n" + "=" * 70)
        print("📊 REAL CITATION NETWORK SUMMARY")
        print("=" * 70)
        print(f"Total papers loaded: {len(self.papers)}")
        print(f"Network nodes: {self.graph.number_of_nodes()}")
        print(f"Network edges: {self.graph.number_of_edges()}")
        print(f"Network density: {nx.density(self.graph):.4f}")
        print()
        print("📌 IMPORTANT:")
        print("  Each edge = ONE PAPER CITES ANOTHER (verified from Semantic Scholar)")
        print("  Edge direction: A → B means 'A cites B'")
        print()
        
        if self.graph.number_of_edges() > 0:
            in_degrees = dict(self.graph.in_degree())
            out_degrees = dict(self.graph.out_degree())
            
            print("🔗 Most Cited Papers (in our dataset):")
            top_cited = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
            for paper_id, count in top_cited:
                if count > 0:
                    title = self.graph.nodes[paper_id].get('title', 'Unknown')
                    print(f"  • {title[:50]}... ({count} citations)")
            
            print("\n📝 Most Citing Papers:")
            top_citing = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
            for paper_id, count in top_citing:
                if count > 0:
                    title = self.graph.nodes[paper_id].get('title', 'Unknown')
                    print(f"  • {title[:50]}... (cites {count} papers)")
        else:
            print("⚠️  No citations found between papers in this dataset")
            print("   (This is expected for initial run - need to process more papers)")
        
        print("\n" + "=" * 70)


if __name__ == '__main__':
    builder = RealCitationNetworkBuilder()
    builder.load_papers()
    builder.build_citation_network()
    builder.save_network()
    builder.print_summary()
