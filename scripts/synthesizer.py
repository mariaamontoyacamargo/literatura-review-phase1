"""synthesizer.py - Enhanced extraction of insights & structured metadata"""
import json, logging, os
import re
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class Synthesizer:
    def extract_insights(self, paper):
        """Extract structured insights from paper"""
        return {
            # Metadata
            "id": paper.get("id"),
            "title": paper.get("title"),
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
            "venue": paper.get("venue"),
            "url": paper.get("url"),
            "doi": paper.get("doi", ""),

            # Methodology & Details
            "methodology": paper.get("methodology"),
            "methodology_details": paper.get("methodology_details", ""),
            "treatment_effect_size": paper.get("treatment_effect_size", ""),
            "external_validity": paper.get("external_validity", ""),

            # Content
            "pocket": paper.get("pocket"),
            "keywords": paper.get("keywords", []),
            "abstract": paper.get("abstract", ""),
            "key_findings": paper.get("key_findings", []),

            # Metrics
            "citations_count": paper.get("citations", 0),
            "h_index_author": paper.get("h_index", 0),

            # Extracted insights
            "limitations": self.extract_limitations(paper),
            "impact_score": self.calculate_impact(paper),
            "relevance_tags": self.extract_relevance_tags(paper),
            "methodology_category": self.categorize_methodology(paper),
            "outcome_variables": self.extract_outcomes(paper),

            # Relationships
            "related_papers": []
        }

    def synthesize(self, papers):
        """Synthesize a batch of papers with improved linking"""
        logger.info(f"Synthesizing {len(papers)} papers...")
        synthesized = [self.extract_insights(p) for p in papers]

        # Link papers by keyword overlap + same pocket + methodology
        for i, paper in enumerate(synthesized):
            for j, other in enumerate(synthesized):
                if i != j:
                    overlap = self.overlap(paper, other)
                    same_pocket = paper.get("pocket") == other.get("pocket")
                    # Link if: overlap > 0.2 OR same pocket AND similar methodology
                    if overlap > 0.2 or (same_pocket and self.similar_methodology(paper, other)):
                        if other["id"] not in synthesized[i]["related_papers"]:
                            synthesized[i]["related_papers"].append(other["id"])

        logger.info(f"✓ Synthesized {len(synthesized)} papers with enhanced links")
        return synthesized

    def extract_limitations(self, paper):
        """Extract paper limitations"""
        limitations = []
        abstract = (paper.get("abstract", "") or "").lower()

        patterns = {
            "scope": ["limited", "constraint", "single firm", "one context"],
            "sample": ["small sample", "sample size", "n=", "limited data"],
            "external": ["external validity", "generalizability"],
            "method": ["potential bias", "selection bias", "confound"]
        }

        for category, keywords in patterns.items():
            if any(kw in abstract for kw in keywords):
                limitations.append(f"{category.capitalize()} considerations")

        return list(set(limitations)) if limitations else ["No explicit limitations noted"]

    def extract_outcomes(self, paper):
        """Extract outcome variables measured"""
        outcomes = set()
        keywords = [kw.lower() for kw in paper.get("keywords", [])]
        findings_text = " ".join([str(f).lower() for f in paper.get("key_findings", [])])

        outcome_markers = {
            "productivity": ["productivity", "output", "throughput", "performance"],
            "time": ["time", "speed", "duration", "faster"],
            "quality": ["quality", "accuracy", "error", "mistake"],
            "adoption": ["adoption", "usage", "uptake"],
            "satisfaction": ["satisfaction", "engagement", "experience"],
            "wage": ["wage", "salary", "income", "earnings"],
            "employment": ["employment", "job", "displacement"]
        }

        for outcome, markers in outcome_markers.items():
            if any(m in findings_text for m in markers):
                outcomes.add(outcome)

        return list(outcomes) if outcomes else ["general performance"]

    def categorize_methodology(self, paper):
        """Categorize methodology type"""
        methodology = (paper.get("methodology") or "").lower()

        if "rct" in methodology or "randomized" in methodology:
            return "RCT"
        elif "quasi" in methodology or "did" in methodology or "iv" in methodology:
            return "Quasi-experimental"
        elif "panel" in methodology or "fixed effect" in methodology:
            return "Panel data"
        elif "survey" in methodology or "experiment" in methodology:
            return "Experimental"
        else:
            return "Other"

    def similar_methodology(self, paper1, paper2):
        """Check if papers use similar methodologies"""
        method1 = self.categorize_methodology(paper1)
        method2 = self.categorize_methodology(paper2)
        return method1 == method2

    def calculate_impact(self, paper):
        """Calculate impact score (0-10)"""
        citations = paper.get("citations", 0)
        h_index = paper.get("h_index", 0)
        impact = 0

        if citations > 100:
            impact += 3
        elif citations > 50:
            impact += 2
        elif citations > 20:
            impact += 1

        if h_index > 50:
            impact += 2
        elif h_index > 30:
            impact += 1

        return min(impact, 10)

    def extract_relevance_tags(self, paper):
        """Extract relevance tags for filtering"""
        tags = set()

        # Pocket
        pocket = paper.get("pocket", "")
        if pocket:
            tags.add(pocket)

        # Methodology
        text = (paper.get("abstract", "") or "").lower()
        if "rct" in text or "randomized" in text:
            tags.add("rct")
        elif "quasi" in text or "panel" in text or "did" in text:
            tags.add("quasi-experimental")

        # Methodology category
        cat = self.categorize_methodology(paper)
        tags.add(cat.lower())

        return list(tags)

    def overlap(self, paper1, paper2):
        """Calculate keyword overlap (0-1) using Jaccard similarity"""
        keywords1 = set(paper1.get("keywords", []) or [])
        keywords2 = set(paper2.get("keywords", []) or [])

        if not keywords1 or not keywords2:
            return 0

        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)
        return intersection / union if union > 0 else 0

if __name__ == '__main__':
    synthesizer = Synthesizer()
    print(f"✓ Synthesizer v2 ready with enhanced extraction")
