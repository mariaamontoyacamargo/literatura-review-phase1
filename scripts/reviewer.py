"""reviewer.py - Quality validation & scoring based on rubrica"""
import json, logging, os
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class Reviewer:
    def __init__(self):
        self.papers = []

    def score_methodology(self, paper):
        """Score methodology (0-4) - FAIR scoring for empirical + conceptual papers

        0-4 scale:
        - 4: RCT/cuasi-experimental with causal ID
        - 3: Panel/observational with solid empirics
        - 2: Framework/conceptual model OR mixed methods
        - 1: Descriptive/exploratory with data
        - 0: Pure theory or no evidence
        """
        # Extraer texto para buscar
        methodology_text = paper.get("methodology", "").lower()
        abstract = paper.get("summary", paper.get("abstract", "")).lower()
        title = paper.get("title", "").lower()
        full_text = f"{methodology_text} {abstract} {title}"

        # LEVEL 1: Explicit causal/experimental design (4 points)
        strong_experimental = [
            "randomized controlled trial", "rct", "randomized experiment",
            "quasi-experimental", "treatment effect size",
            "instrumental variable", "iv estimate",
            "difference-in-differences", "did", "regression discontinuity", "rdd",
            "propensity score matching", "counterfactual"
        ]
        if any(term in full_text for term in strong_experimental):
            return 4

        # LEVEL 2: Panel data, fixed effects, or solid empirical methods (3 points)
        semi_experimental = [
            "panel data", "fixed effect", "within estimator",
            "event study", "synthetic control", "interrupted time series",
            "lagged dependent variable", "vector autoregression"
        ]
        if any(term in full_text for term in semi_experimental):
            return 3

        # LEVEL 3: Framework/Model/Mixed methods (2 points) - IMPROVED
        framework_keywords = [
            "framework", "model", "theoretical", "conceptual",
            "mixed method", "qualitative study", "case study",
            "survey design", "interviews", "ethnograph"
        ]
        if any(term in full_text for term in framework_keywords):
            return 2

        # LEVEL 4: Empirical with data (1 point)
        empirical_keywords = [
            "empirical analysis", "empirical evidence",
            "econometric", "statistical analysis", "analysis of",
            "examine", "investigate", "assess"
        ]
        if any(term in full_text for term in empirical_keywords):
            return 1

        # LEVEL 5: Everything else (0 points)
        return 0

    def score_causalidity(self, paper):
        """Score causal identification (+0 to +2) - IMPROVED

        Busca en: abstract, title, metodología
        Acepta papers con causal claims implícitas
        """
        causal_signals = [
            "causal", "causality", "cause", "effect",
            "iv", "instrumental variable", "rct", "randomized",
            "identified", "identification", "rdd", "regression discontinuity",
            "matching", "propensity score", "did", "difference-in-differences",
            "treatment effect", "counterfactual"
        ]

        title = paper.get("title", "").lower()
        abstract = paper.get("summary", paper.get("abstract", "")).lower()
        methodology = paper.get("methodology", "").lower()
        full_text = f"{title} {abstract} {methodology}"

        # Strong causal signals
        for signal in causal_signals:
            if signal in full_text:
                return 2

        # Check for negative signals (correlation-only, no causal claims)
        negative_signals = ["correlation", "correlate", "correlated", "associated"]
        positive_signals = ["effect", "impact", "change", "difference"]

        has_negative = any(s in full_text for s in negative_signals)
        has_positive = any(s in full_text for s in positive_signals)

        if has_negative and not has_positive:
            return -1  # Pure correlation claim
        elif has_positive:
            return 1  # Potential causal claim
        else:
            return 0  # Neutral

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

    def score_relevance(self, paper):
        """Score relevance to project pockets (+0 to +2) - IMPROVED

        Detecta si el paper responde preguntas centrales de cada pocket:
        - Evaluación: ¿impacto causal IA en productividad?
        - Labor: ¿impacto en empleo, salarios?
        - Desigualdad: ¿amplifica/reduce desigualdad?
        - Policy: ¿regulación, gobernanza IA?
        - HMI: ¿interacción humano-IA?
        - Innovación: ¿adopción, difusión IA?
        - Management: ¿implementación organizacional?
        """
        title = paper.get("title", "").lower()
        abstract = paper.get("summary", paper.get("abstract", "")).lower()
        keywords = paper.get("keywords", [])
        keywords_lower = [k.lower() for k in (keywords or [])]
        full_text = f"{title} {abstract} {' '.join(keywords_lower)}"

        # Core relevance (IA + productivity/labor context)
        core_ai = ["ai", "artificial intelligence", "machine learning", "generative", "llm", "large language model"]
        core_context = ["productivity", "worker", "firm", "task", "automation", "employment", "labor", "wage", "adoption"]

        ai_mention = any(term in full_text for term in core_ai)
        context_mention = any(term in full_text for term in core_context)

        # Strong relevance: answers core pocket questions
        strong_relevance = [
            # Evaluación: causal impact measurement
            "causal", "impact", "effect", "treatment", "experiment", "rct",
            # Labor: employment, wage effects
            "job", "employment", "wage", "income", "occupation", "skill",
            # Desigualdad: inequality, gaps
            "inequality", "inequity", "gap", "disparity", "divide",
            # Policy: regulation, governance
            "policy", "regulation", "governance", "governance", "compliance",
            # HMI: human interaction, user
            "user", "interaction", "interface", "usability", "design", "human",
            # Innovación: adoption, diffusion
            "adoption", "diffusion", "implementation", "deployment", "roll",
            # Management: organizational, business
            "organizational", "organization", "management", "business", "firm"
        ]

        strong_matches = sum(1 for term in strong_relevance if term in full_text)

        # Scoring
        if ai_mention and context_mention and strong_matches >= 2:
            # Paper directly addresses IA + productivity context + has strong relevance signals
            return 2
        elif ai_mention and (context_mention or strong_matches >= 1):
            # Paper has IA + some relevance
            return 1
        return 0

    def score_paper(self, paper):
        """Calculate total score for a paper"""
        score = 0
        breakdown = {}

        # Methodology (0-7) - IMPROVED: search in abstract too
        methodology_score = self.score_methodology(paper)
        breakdown["methodology"] = methodology_score
        score += methodology_score

        # Causalidity (+0 to +2) - IMPROVED: search in abstract
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

        # Relevance (+0 to +2) - IMPROVED: search in abstract
        relevance_score = self.score_relevance(paper)
        breakdown["relevance"] = relevance_score
        score += relevance_score

        # Determine status - FAIR thresholds for real papers
        # Score range: methodology (0-4) + causal (-1 to +2) + top_tier (0-2) + novelty (-1 to +1) + relevance (0-2)
        # Theoretical max: 11, realistic for good paper: 7-9
        # IMPROVED: Give credit to papers with frameworks/good relevance even if not experimental

        # Bonus: papers with strong relevance + framework/conceptual value
        has_framework = breakdown.get("methodology", 0) >= 2
        has_relevance = breakdown.get("relevance", 0) == 2
        has_causal_signal = breakdown.get("causalidity", 0) > 0

        if score >= 7:  # Strong: solid methodology + relevant + causal/novel
            status = "ACEPTADO"
        elif score >= 5 and has_framework and has_relevance:  # Framework + strong relevance = worth accepting
            status = "ACEPTADO"
        elif score >= 4 and has_relevance and breakdown.get("novelty", 0) >= 1:  # Recent + relevant
            status = "REVISAR"
        elif score >= 3:  # Some methodology + some relevance
            status = "REVISAR"
        else:  # Weak paper
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
