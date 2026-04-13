"""reviewer.py - Quality validation & scoring based on rubrica"""
import json, logging, os
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class Reviewer:
    def __init__(self):
        self.papers = []

    def score_methodology(self, methodology):
        """Score empirical methodology (0-7)"""
        methodology_scores = {
            "RCT": 7,
            "randomized": 7,
            "quasi-experimental": 7,
            "IV": 7,
            "RDD": 7,
            "DID": 7,
            "matching": 7,
            "panel": 5,
            "fixed_effects": 5,
            "observational": 3,
            "theoretical": 1,
            "review": 1
        }
        methodology_lower = methodology.lower()
        for key, score in methodology_scores.items():
            if key in methodology_lower:
                return score
        return 3  # Default to observational

    def score_causalidity(self, metadata):
        """Score causal identification (+0 to +2)"""
        causal_signals = ["IV", "RCT", "randomized", "causal", "identified", "RDD", "matching"]
        text = json.dumps(metadata).lower()

        for signal in causal_signals:
            if signal in text:
                return 2
        if "bias" in text or "selection" in text:
            return -1
        return 0

    def score_top_tier(self, metadata):
        """Score top-tier indicators (+0 to +2)"""
        score = 0

        # h-index check
        h_index = metadata.get("h_index", 0)
        citations = metadata.get("citations", 0)
        venue = (metadata.get("venue", "") or "").lower()
        year = metadata.get("year", 2020)

        top_venues = ["nature", "science", "nber", "ssrn", "arxiv"]
        venue_match = any(v in venue for v in top_venues)

        if h_index > 30 and citations > 100 and (venue_match or "top" in venue):
            return 2
        elif h_index > 20 and citations > 50:
            return 1
        elif "arxiv" in venue and year >= 2025:
            return 1

        return score

    def score_novelty(self, year):
        """Score novelty/recency (+1, 0, or -1)"""
        if year >= 2024:
            return 1
        elif year >= 2020:
            return 0
        else:
            return -1

    def score_relevance(self, keywords, pockets):
        """Score relevance to project pockets (+0 to +2)"""
        relevant_keywords = [
            "ai", "adoption", "productivity", "generative", "llm",
            "worker", "firm", "team", "task", "automation"
        ]

        keywords_lower = [k.lower() for k in (keywords or [])]
        matches = sum(1 for k in keywords_lower if any(r in k for r in relevant_keywords))

        if matches >= 3:
            return 2
        elif matches >= 1:
            return 1
        return 0

    def score_paper(self, paper):
        """Calculate total score for a paper"""
        score = 0
        breakdown = {}

        # Methodology (0-7)
        methodology_score = self.score_methodology(paper.get("methodology", ""))
        breakdown["methodology"] = methodology_score
        score += methodology_score

        # Causalidity (+0 to +2)
        causal_score = self.score_causalidity(paper)
        breakdown["causalidity"] = causal_score
        score += causal_score

        # Top-tier (+0 to +2)
        toptier_score = self.score_top_tier(paper)
        breakdown["top_tier"] = toptier_score
        score += toptier_score

        # Novelty (+1, 0, -1)
        novelty_score = self.score_novelty(paper.get("year", 2020))
        breakdown["novelty"] = novelty_score
        score += novelty_score

        # Relevance (+0 to +2)
        relevance_score = self.score_relevance(paper.get("keywords", []), [])
        breakdown["relevance"] = relevance_score
        score += relevance_score

        # Determine status
        if score >= 6:
            status = "ACEPTADO"
        elif score >= 3:
            status = "REVISAR"
        else:
            status = "RECHAZADO"

        return {
            "title": paper.get("title"),
            "score": score,
            "status": status,
            "breakdown": breakdown,
            "metadata": paper
        }

    def review(self, papers):
        """Review a batch of papers"""
        logger.info(f"Reviewing {len(papers)} papers...")
        reviewed = [self.score_paper(p) for p in papers]

        accepted = [p for p in reviewed if p["status"] == "ACEPTADO"]
        review = [p for p in reviewed if p["status"] == "REVISAR"]
        rejected = [p for p in reviewed if p["status"] == "RECHAZADO"]

        logger.info(f"✓ ACEPTADO: {len(accepted)} | REVISAR: {len(review)} | RECHAZADO: {len(rejected)}")

        return reviewed

if __name__ == '__main__':
    reviewer = Reviewer()
    print(f"✓ Reviewer ready. Use: reviewer.review(papers)")
