"""mapper.py - Build semantic graph with multiple relation types & gap detection"""
import json, logging, os
import networkx as nx
from collections import Counter, defaultdict

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class Mapper:
    def __init__(self):
        self.graph = nx.Graph()
        self.papers = []
        self.relation_types = defaultdict(int)

    def build(self, papers):
        """Build semantic graph from papers with multiple relation types"""
        logger.info(f"Building enhanced graph from {len(papers)} papers...")
        self.papers = papers

        # Add nodes with rich metadata
        for paper in papers:
            self.graph.add_node(
                paper.get("id"),
                title=paper.get("title"),
                year=paper.get("year"),
                pocket=paper.get("pocket"),
                keywords=paper.get("keywords", []),
                authors=paper.get("authors", []),
                methodology=paper.get("methodology", ""),
                citations=paper.get("citations", 0)
            )

        # Add edges based on multiple relation types
        for i, paper1 in enumerate(papers):
            for paper2 in papers[i+1:]:
                relations = self.find_relations(paper1, paper2)

                if relations:  # If any relation found
                    combined_weight = min(sum(r[1] for r in relations), 1.0)
                    relation_names = [r[0] for r in relations]

                    self.graph.add_edge(
                        paper1.get("id"),
                        paper2.get("id"),
                        weight=combined_weight,
                        relations=relation_names,
                        relation_count=len(relations)
                    )

                    for rel_type, _ in relations:
                        self.relation_types[rel_type] += 1

        logger.info(f"✓ Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        logger.info(f"   Relations: {dict(self.relation_types)}")
        return self.graph

    def find_relations(self, paper1, paper2):
        """Find all types of relations between two papers"""
        relations = []

        # 1. Keyword overlap (semantic similarity)
        keyword_overlap = self.keyword_overlap(paper1, paper2)
        if keyword_overlap > 0.15:
            relations.append(("keyword-shared", keyword_overlap))

        # 2. Same pocket (thematic)
        if paper1.get("pocket") == paper2.get("pocket"):
            relations.append(("same-pocket", 0.3))

        # 3. Similar methodology
        if self.similar_methodology(paper1, paper2):
            relations.append(("similar-methodology", 0.25))

        # 4. Temporal sequence (close years)
        year1 = paper1.get("year", 0)
        year2 = paper2.get("year", 0)
        if abs(year1 - year2) <= 1 and year1 > 0 and year2 > 0:
            relations.append(("temporal-sequence", 0.15))

        # 5. Author overlap (shared authorship)
        if self.shared_author(paper1, paper2):
            relations.append(("shared-author", 0.4))

        return relations

    def keyword_overlap(self, paper1, paper2):
        """Calculate keyword overlap (Jaccard similarity)"""
        keywords1 = set(paper1.get("keywords", []) or [])
        keywords2 = set(paper2.get("keywords", []) or [])

        if not keywords1 or not keywords2:
            return 0

        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        return intersection / union if union > 0 else 0

    def similar_methodology(self, paper1, paper2):
        """Check if papers use similar methodologies"""
        method1 = self.categorize_methodology(paper1)
        method2 = self.categorize_methodology(paper2)
        return method1 == method2

    def categorize_methodology(self, paper):
        """Categorize methodology type"""
        methodology = (paper.get("methodology") or "").lower()

        if "rct" in methodology or "randomized" in methodology:
            return "RCT"
        elif "quasi" in methodology or "did" in methodology or "iv" in methodology:
            return "Quasi-experimental"
        elif "panel" in methodology or "fixed effect" in methodology:
            return "Panel data"
        else:
            return "Other"

    def shared_author(self, paper1, paper2):
        """Check if papers share authors"""
        authors1 = set(paper1.get("authors", []) or [])
        authors2 = set(paper2.get("authors", []) or [])
        return bool(authors1 & authors2)

    def detect_gaps(self):
        """Detect coverage gaps comprehensively"""
        gaps = {"methodologies": {}, "pockets": {}, "years": {}, "issues": []}

        methodologies = Counter()
        pockets = Counter()
        years = Counter()

        for paper in self.papers:
            methodologies[paper.get("methodology", "unknown")] += 1
            pockets[paper.get("pocket", "unknown")] += 1
            years[paper.get("year", 0)] += 1

        gaps["methodologies"] = dict(methodologies)
        gaps["pockets"] = dict(pockets)
        gaps["years"] = dict(years)

        # Identify issues
        issues = []

        # Pocket coverage
        for pocket, count in gaps["pockets"].items():
            if count < 3:
                issues.append(f"🔴 {pocket}: only {count} paper(s) - CRITICAL")
            elif count < 5:
                issues.append(f"🟡 {pocket}: only {count} papers - needs more")

        # Year coverage
        required_years = [2023, 2024, 2025]
        for year in required_years:
            count = gaps["years"].get(year, 0)
            if count == 0:
                issues.append(f"🔴 Year {year}: no papers - CRITICAL")
            elif count < 2:
                issues.append(f"🟡 Year {year}: only {count} paper(s)")

        # Network connectivity
        if self.graph.number_of_edges() == 0:
            issues.append(f"🔴 Network: papers are isolated (0 edges) - consider reviewing similarity thresholds")

        gaps["issues"] = issues
        return gaps

    def get_network_stats(self):
        """Get comprehensive network statistics"""
        n_nodes = self.graph.number_of_nodes()
        n_edges = self.graph.number_of_edges()

        stats = {
            "nodes": n_nodes,
            "edges": n_edges,
            "density": nx.density(self.graph),
            "avg_degree": sum(dict(self.graph.degree()).values()) / max(n_nodes, 1),
            "components": nx.number_connected_components(self.graph),
            "relation_types": dict(self.relation_types)
        }

        if n_nodes > 1:
            try:
                stats["avg_clustering"] = nx.average_clustering(self.graph)
            except:
                stats["avg_clustering"] = 0

        return stats

    def get_top_papers_by_connectivity(self, n=5):
        """Get papers with most connections"""
        if self.graph.number_of_nodes() == 0:
            return []

        degree_dict = dict(self.graph.degree())
        sorted_papers = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)
        return sorted_papers[:n]

if __name__ == '__main__':
    mapper = Mapper()
    print(f"✓ Mapper v2 ready with enhanced relation detection")
