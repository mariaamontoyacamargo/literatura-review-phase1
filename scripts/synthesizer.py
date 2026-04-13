"""synthesizer.py - Extraction of insights & structured metadata"""
import json, logging, os
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class Synthesizer:
    def extract_insights(self, paper):
        """Extract structured insights from paper"""
        return {
            "id": paper.get("id"),
            "title": paper.get("title"),
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "url": paper.get("url"),
            "methodology": paper.get("methodology"),
            "pocket": paper.get("pocket"),
            "keywords": paper.get("keywords", []),
            "abstract": paper.get("abstract", ""),
            "key_findings": paper.get("key_findings", []),
            "citations_count": paper.get("citations", 0),
            "h_index_author": paper.get("h_index", 0),
            "related_papers": [],
            "limitations": self.extract_limitations(paper),
            "impact_score": self.calculate_impact(paper),
            "relevance_tags": self.extract_relevance_tags(paper)
        }

    def synthesize(self, papers):
        """Synthesize a batch of papers"""
        logger.info(f"Synthesizing {len(papers)} papers...")
        synthesized = [self.extract_insights(p) for p in papers]

        for i, paper in enumerate(synthesized):
            for j, other in enumerate(synthesized):
                if i != j and self.overlap(paper, other) > 0.3:
                    synthesized[i]["related_papers"].append(other["id"])

        logger.info(f"✓ Synthesized {len(synthesized)} papers with links")
        return synthesized

    def extract_limitations(self, paper):
        """Extract paper limitations"""
        limitations = []
        text = (paper.get("abstract", "") or "").lower()
        if "limited" in text or "constraint" in text:
            limitations.append("Scope limitations")
        return limitations

    def calculate_impact(self, paper):
        """Calculate impact score"""
        citations = paper.get("citations", 0)
        h_index = paper.get("h_index", 0)
        impact = 0
        if citations > 100:
            impact += 3
        elif citations > 50:
            impact += 2
        if h_index > 50:
            impact += 2
        elif h_index > 30:
            impact += 1
        return min(impact, 10)

    def extract_relevance_tags(self, paper):
        """Extract relevance tags for filtering"""
        tags = []
        keywords = paper.get("keywords", []) or []
        pocket = paper.get("pocket", "")
        if pocket:
            tags.append(pocket)
        text = paper.get("abstract", "").lower()
        if "rct" in text or "randomized" in text:
            tags.append("rct")
        elif "quasi" in text or "panel" in text:
            tags.append("quasi-experimental")
        return list(set(tags))

    def overlap(self, paper1, paper2):
        """Calculate keyword overlap between papers"""
        keywords1 = set(paper1.get("keywords", []) or [])
        keywords2 = set(paper2.get("keywords", []) or [])
        if not keywords1 or not keywords2:
            return 0
        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        return intersection / union if union > 0 else 0

if __name__ == '__main__':
    synthesizer = Synthesizer()
    print(f"✓ Synthesizer ready")
