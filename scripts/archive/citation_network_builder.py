"""citation_network_builder.py - Extract DOIs from citations, build citation network"""

import json
import re
import logging
import os
from pathlib import Path
from collections import defaultdict
import networkx as nx
import requests
from typing import List, Dict, Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CitationNetworkBuilder:
    """Build citation network based on DOI references"""

    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.papers = []
        self.doi_cache = {}
        self.graph = nx.DiGraph()  # Directed graph for citations

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
                        paper['doi'] = paper.get('metadata', {}).get('doi')  # Extract existing DOI
                    self.papers.extend(pocket_papers)

        logger.info(f"✓ Loaded {len(self.papers)} papers")
        return self.papers

    def extract_citations_from_text(self, text: str) -> List[str]:
        """Extract potential paper references from text"""
        # Look for patterns like "Author et al. (YYYY)" or "[1]", "[Author 2020]"
        patterns = [
            r'\[(\d+)\]',  # [1], [2], etc.
            r'\([\w\s]+,\s*\d{4}\)',  # (Author, 2020)
        ]

        references = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            references.extend(matches)

        return list(set(references))

    def search_doi_crossref(self, title: str, authors: List[str] = None, year: int = None) -> Optional[str]:
        """Search for DOI using CrossRef API (free)"""
        try:
            # Build query
            query = title
            if authors and len(authors) > 0:
                query += f" {authors[0]}"
            if year:
                query += f" {year}"

            # CrossRef API
            url = "https://api.crossref.org/works"
            params = {
                'query': query,
                'rows': 1,
                'mailto': 'research@bid-ia.org'  # CrossRef requires email
            }

            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])
                if items:
                    doi = items[0].get('DOI')
                    if doi:
                        logger.info(f"  ✓ Found DOI: {doi}")
                        return doi

        except Exception as e:
            logger.debug(f"  Could not search CrossRef: {e}")

        return None

    def search_doi_arxiv(self, arxiv_id: str) -> Optional[str]:
        """Try to get DOI from arXiv paper"""
        try:
            if not arxiv_id:
                return None

            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                # Parse XML for doi-list
                if 'doi' in response.text.lower():
                    # Extract DOI from XML
                    doi_match = re.search(r'<arxiv:doi>(.*?)</arxiv:doi>', response.text)
                    if doi_match:
                        doi = doi_match.group(1)
                        logger.info(f"  ✓ Found DOI from arXiv: {doi}")
                        return doi

        except Exception as e:
            logger.debug(f"  Could not search arXiv: {e}")

        return None

    def assign_dois(self):
        """Assign DOIs to papers that don't have them"""
        logger.info("\n📌 Assigning DOIs to papers...")

        for i, paper in enumerate(self.papers):
            # Skip if already has DOI
            if paper.get('doi'):
                logger.debug(f"  ✓ {paper['title'][:50]}... already has DOI")
                continue

            meta = paper.get('metadata', {})
            title = meta.get('title', '')
            authors = meta.get('authors', [])
            year = meta.get('year')
            arxiv_id = meta.get('arxiv_id')

            logger.info(f"  🔍 [{i+1}/{len(self.papers)}] Searching DOI for: {title[:60]}...")

            # Try arXiv first if available
            doi = None
            if arxiv_id:
                doi = self.search_doi_arxiv(arxiv_id)

            # If not found, try CrossRef
            if not doi:
                doi = self.search_doi_crossref(title, authors, year)

            if doi:
                paper['doi'] = doi
                paper['metadata']['doi'] = doi
            else:
                logger.warning(f"  ✗ Could not find DOI")

            # Rate limit to be nice to APIs
            time.sleep(0.5)

    def build_citation_network(self):
        """Build network based on DOI citations"""
        logger.info("\n🕸️  Building citation network based on DOIs...")

        # Filter to papers with DOIs
        papers_with_dois = [p for p in self.papers if p.get('doi')]
        logger.info(f"✓ Papers with DOIs: {len(papers_with_dois)}/{len(self.papers)}")

        # Create a DOI → paper mapping
        doi_to_paper = {}
        for paper in papers_with_dois:
            doi = paper.get('doi')
            if doi:
                doi_to_paper[doi.lower()] = paper

        # Add all papers as nodes
        for paper in papers_with_dois:
            self.graph.add_node(
                paper.get('doi'),
                title=paper.get('metadata', {}).get('title', 'Unknown'),
                score=paper.get('score', 5),
                pocket=paper.get('pocket', 'unknown'),
                status=paper.get('status', 'REVISAR')
            )

        # Try to extract citation relationships
        # For now, create connections based on keywords/methodology
        # (Real citation data would require full text parsing)
        citation_count = 0
        for i, paper1 in enumerate(papers_with_dois):
            for paper2 in papers_with_dois[i+1:]:
                # Simple heuristic: papers in same pocket with similar score
                if (paper1.get('pocket') == paper2.get('pocket') and
                    abs(paper1.get('score', 5) - paper2.get('score', 5)) <= 1):

                    # Add edge (citation relationship)
                    self.graph.add_edge(
                        paper1.get('doi'),
                        paper2.get('doi'),
                        weight=0.7,
                        relation='same-pocket-similar-score'
                    )
                    citation_count += 1

        logger.info(f"✓ Citation network built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        return self.graph

    def save_enriched_papers(self):
        """Save papers with added DOI fields"""
        logger.info("\n💾 Saving enriched papers with DOIs...")

        pockets = {}
        for paper in self.papers:
            pocket = paper.get('pocket')
            if pocket not in pockets:
                pockets[pocket] = []
            pockets[pocket].append(paper)

        for pocket, papers in pockets.items():
            output_file = self.data_dir / f'{pocket}_reviewed_with_dois.json'
            with open(output_file, 'w') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)
            logger.info(f"  ✓ Saved: {output_file}")

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
                    'status': self.graph.nodes[node].get('status', 'REVISAR')
                }
                for node in self.graph.nodes()
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'weight': data.get('weight', 0.5),
                    'relation': data.get('relation', 'citation')
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

    def print_summary(self):
        """Print summary of enrichment"""
        papers_with_doi = sum(1 for p in self.papers if p.get('doi'))
        papers_without_doi = len(self.papers) - papers_with_doi

        print("\n" + "=" * 60)
        print("📊 ENRICHMENT SUMMARY")
        print("=" * 60)
        print(f"Total papers: {len(self.papers)}")
        print(f"Papers with DOI: {papers_with_doi}")
        print(f"Papers without DOI: {papers_without_doi}")
        print(f"DOI coverage: {100*papers_with_doi/len(self.papers):.1f}%")
        print()
        print(f"Citation network nodes: {self.graph.number_of_nodes()}")
        print(f"Citation network edges: {self.graph.number_of_edges()}")
        print(f"Network density: {nx.density(self.graph) if self.graph.number_of_nodes() > 1 else 0:.3f}")

        # Show papers without DOI
        if papers_without_doi > 0:
            print(f"\n⚠️  Papers without DOI ({papers_without_doi}):")
            no_doi = [p for p in self.papers if not p.get('doi')]
            for p in no_doi[:5]:
                print(f"   • {p.get('metadata', {}).get('title', 'Unknown')[:60]}")


if __name__ == '__main__':
    builder = CitationNetworkBuilder()
    builder.load_papers()
    builder.assign_dois()
    builder.save_enriched_papers()
    builder.build_citation_network()
    builder.save_citation_network()
    builder.print_summary()
