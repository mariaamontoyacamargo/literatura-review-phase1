"""mapper.py - Build semantic graph & detect gaps"""
import json, logging, os
import networkx as nx
from collections import Counter

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class Mapper:
    def __init__(self):
        self.graph = nx.Graph()
        self.papers = []

    def build(self, papers):
        """Build semantic graph from papers"""
        logger.info(f"Building graph from {len(papers)} papers...")
        self.papers = papers

        # Add nodes
        for paper in papers:
            self.graph.add_node(
                paper.get("id"),
                title=paper.get("title"),
                year=paper.get("year"),
                pocket=paper.get("pocket"),
                keywords=paper.get("keywords", [])
            )

        # Add edges based on keyword overlap
        for i, paper1 in enumerate(papers):
            for paper2 in papers[i+1:]:
                overlap = self.keyword_overlap(paper1, paper2)
                if overlap > 0.2:
                    self.graph.add_edge(
                        paper1.get("id"),
                        paper2.get("id"),
                        weight=overlap,
                        relation="keyword-shared"
                    )

        logger.info(f"✓ Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        return self.graph

    def keyword_overlap(self, paper1, paper2):
        """Calculate keyword overlap"""
        keywords1 = set(paper1.get("keywords", []) or [])
        keywords2 = set(paper2.get("keywords", []) or [])
        if not keywords1 or not keywords2:
            return 0
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        return intersection / union if union > 0 else 0

    def detect_gaps(self):
        """Detect coverage gaps"""
        gaps = {"methodologies": {}, "pockets": {}, "years": {}}

        methodologies = Counter()
        pockets = Counter()
        years = Counter()

        for paper in self.papers:
            methodologies[paper.get("methodology", "unknown")] += 1
            pockets[paper.get("pocket", "unknown")] += 1
            years[paper.get("year", 0)] += 1

        # Identify underrepresented areas
        gaps["methodologies"] = dict(methodologies)
        gaps["pockets"] = dict(pockets)
        gaps["years"] = dict(years)

        underrep = []
        for pocket, count in gaps["pockets"].items():
            if count < 2:
                underrep.append(f"{pocket}: only {count} paper(s)")

        for year in [2023, 2024, 2025]:
            if gaps["years"].get(year, 0) < 2:
                underrep.append(f"Year {year}: only {gaps['years'].get(year, 0)} paper(s)")

        return {"identified": underrep, "distribution": gaps}

    def get_network_stats(self):
        """Get network statistics"""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(self.graph.number_of_nodes(), 1)
        }

if __name__ == '__main__':
    mapper = Mapper()
    print(f"✓ Mapper ready")
