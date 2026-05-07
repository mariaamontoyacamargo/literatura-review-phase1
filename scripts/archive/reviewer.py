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

    # Pocket-specific relevance keywords (aligned to BID-IA deck, Fedesarrollo & BID, abril 2026)
    POCKET_RELEVANCE = {
        "evaluacion_experimental": {
            "strong": ["rct", "randomized", "treatment effect", "causal effect", "quasi-experimental",
                       "difference-in-differences", "did", "instrumental variable", "regression discontinuity",
                       "field experiment", "generative ai", "llm", "copilot", "productivity", "worker",
                       "task", "knowledge worker", "staggered", "jagged frontier"],
            "core_ai": ["ai", "artificial intelligence", "generative", "llm", "large language model", "gpt"],
            "description": "causal/experimental evidence on AI adoption effects at worker/task/firm level",
        },
        "human_machine_interaction": {
            "strong": ["human-ai", "complementarity", "over-reliance", "automation bias", "algorithm aversion",
                       "algorithm appreciation", "trust", "calibration", "delegation", "augmentation",
                       "human machine", "human-machine", "ai assistance", "decision support",
                       "ai literacy", "collaboration", "teaming", "ai interaction"],
            "core_ai": ["ai", "artificial intelligence", "algorithm", "machine learning", "recommendation system"],
            "description": "when/why human-AI interaction creates or destroys value",
        },
        "innovacion_difusion": {
            "strong": ["diffusion", "adoption", "j-curve", "productivity paradox", "s-curve",
                       "complementary investment", "intangible capital", "organizational capital",
                       "technology adoption", "spillover", "measurement lag", "pilot to production",
                       "digital transformation", "ai maturity", "adoption pattern", "adoption barrier",
                       "adoption determinant", "innovation diffusion", "technology diffusion",
                       "scale", "implement", "deployment"],
            "core_ai": ["ai", "artificial intelligence", "machine learning", "automation", "digital"],
            "description": "how AI diffuses within/between firms and translates into productivity",
        },
        "labor": {
            "strong": ["wage", "employment", "job", "occupation", "task automation", "worker displacement",
                       "skill premium", "retraining", "reskilling", "labor market", "within-firm",
                       "task-based", "routine", "non-routine", "labor demand", "income", "salary",
                       "reallocation", "job creation", "job destruction"],
            "core_ai": ["ai", "artificial intelligence", "automation", "machine learning", "robot"],
            "description": "how AI adoption redistributes work and value within/between firms",
        },
        "desigualdad": {
            "strong": ["inequality", "heterogeneous", "skill premium", "digital divide",
                       "frontier firm", "laggard", "gender gap", "polarization",
                       "distributional", "access to ai", "technology gap",
                       "disparity", "income distribution", "wage gap", "wage inequality",
                       "skill bias", "skill-biased", "unequal", "low-skill", "high-skill",
                       "disadvantaged", "minority", "small firm", "sme"],
            "core_ai": ["ai", "artificial intelligence", "automation", "digital", "machine learning"],
            "description": "under what conditions AI adoption amplifies or reduces existing gaps",
        },
        "management": {
            "strong": ["organizational", "management", "implementation", "change management",
                       "complementary investment", "process redesign", "ai governance", "firm capabilities",
                       "digital strategy", "ai adoption", "organizational capital", "ai strategy",
                       "adoption", "organization", "firm", "business", "strategy",
                       "talent", "upskilling", "readiness", "capability", "leadership"],
            "core_ai": ["ai", "artificial intelligence", "machine learning", "automation", "digital"],
            "description": "how internal organization and decision structures determine AI adoption and value capture",
        },
        "policy": {
            "strong": ["regulation", "policy", "governance", "eu ai act", "gdpr", "lgpd",
                       "compliance", "transparency", "explainability", "accountability",
                       "algorithmic", "public policy", "regulatory", "incentive", "data governance",
                       "ai ethics", "algorithmic bias", "responsible ai"],
            "core_ai": ["ai", "artificial intelligence", "algorithm", "machine learning", "automation"],
            "description": "how regulatory frameworks and governance affect AI adoption decisions",
        },
    }

    def score_relevance(self, paper):
        """Score relevance to project pockets (+0 to +2) — pocket-specific rubric.

        Uses pocket-specific keywords from BID-IA deck (Fedesarrollo & BID, April 2026).
        Falls back to generic relevance if pocket not recognized.
        """
        title = paper.get("title", "").lower()
        abstract = paper.get("summary", paper.get("abstract", "")).lower()
        keywords = paper.get("keywords", [])
        keywords_lower = [k.lower() for k in (keywords or [])]
        full_text = f"{title} {abstract} {' '.join(keywords_lower)}"

        pocket = paper.get("pocket", paper.get("metadata", {}).get("pocket", "")).lower()

        # Pocket-specific scoring
        if pocket in self.POCKET_RELEVANCE:
            cfg = self.POCKET_RELEVANCE[pocket]
            ai_match = any(term in full_text for term in cfg["core_ai"])
            strong_matches = sum(1 for term in cfg["strong"] if term in full_text)

            if ai_match and strong_matches >= 2:
                return 2  # Directly addresses core pocket question + AI
            elif ai_match and strong_matches >= 1:
                return 1  # AI + some pocket relevance
            elif strong_matches >= 2:
                return 1  # Strong pocket match even without explicit AI mention
            return 0

        # Fallback: generic relevance
        core_ai = ["ai", "artificial intelligence", "machine learning", "generative", "llm"]
        core_context = ["productivity", "worker", "firm", "task", "automation", "employment", "labor", "wage", "adoption"]
        strong_relevance = [
            "causal", "impact", "effect", "treatment", "experiment", "rct",
            "job", "employment", "wage", "income", "occupation", "skill",
            "inequality", "inequity", "gap", "disparity",
            "policy", "regulation", "governance",
            "user", "interaction", "interface", "human",
            "adoption", "diffusion", "implementation",
            "organizational", "management", "business", "firm"
        ]
        ai_mention = any(term in full_text for term in core_ai)
        context_mention = any(term in full_text for term in core_context)
        strong_matches = sum(1 for term in strong_relevance if term in full_text)

        if ai_mention and context_mention and strong_matches >= 2:
            return 2
        elif ai_mention and (context_mention or strong_matches >= 1):
            return 1
        return 0

    def score_paper(self, paper, pocket=None):
        """Calculate total score for a paper"""
        score = 0
        breakdown = {}

        # Inject pocket into paper dict for relevance scoring
        if pocket:
            paper = {**paper, "pocket": pocket}

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

        # Relevance (+0 to +2) — pocket-specific
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

        criteria = self.check_acceptance_criteria(paper, pocket or paper.get("pocket", ""))

        return {
            "title": paper.get("title"),
            "score": score,
            "status": status,
            "breakdown": breakdown,
            "criteria": criteria,
            "metadata": paper
        }

    POCKET_CRITERIA = {
        "evaluacion_experimental": [
            ("ai_focus",        "Estudia IA/LLM/GenAI específicamente",
             ["ai", "artificial intelligence", "generative", "llm", "large language model", "gpt", "chatgpt", "copilot"]),
            ("experimental",    "Diseño experimental o cuasi-experimental (RCT, DiD, IV, RDD)",
             ["rct", "randomized", "difference-in-differences", "did", "instrumental variable", "quasi-experimental", "field experiment"]),
            ("productivity",    "Mide productividad, output, calidad o eficiencia",
             ["productivity", "output", "efficiency", "performance", "quality", "speed", "throughput"]),
            ("worker_task",     "Nivel de análisis: tarea o trabajador (no solo macro)",
             ["worker", "task", "employee", "agent", "individual", "user", "knowledge worker"]),
            ("causal_id",       "Identificación causal explícita",
             ["causal", "treatment effect", "counterfactual", "identification", "exogenous"]),
        ],
        "human_machine_interaction": [
            ("ai_focus",        "Estudia IA/algoritmo/sistema ML",
             ["ai", "artificial intelligence", "algorithm", "machine learning", "recommendation", "automated"]),
            ("human_ai",        "Estudia interacción humano-IA (no solo IA sola)",
             ["human-ai", "human ai", "human-machine", "collaboration", "human oversight", "human judgment"]),
            ("trust_reliance",  "Analiza confianza, calibración u over-reliance",
             ["trust", "over-reliance", "reliance", "calibration", "automation bias", "algorithm aversion", "algorithm appreciation"]),
            ("complementarity", "Mide complementariedad o cuando humano+IA > ambos solos",
             ["complementarity", "complement", "augment", "synergy", "teaming", "delegation"]),
            ("outcome",         "Tiene outcome medible (calidad, error, decisión)",
             ["performance", "accuracy", "quality", "decision", "error", "outcome"]),
        ],
        "innovacion_difusion": [
            ("ai_focus",        "Estudia IA/automatización/tecnología digital",
             ["ai", "artificial intelligence", "automation", "digital technology", "machine learning"]),
            ("adoption",        "Estudia proceso de adopción o difusión",
             ["adoption", "diffusion", "implementation", "deployment", "scale", "spread"]),
            ("firm_level",      "Nivel de análisis: firma u organización",
             ["firm", "organization", "company", "enterprise", "business", "sme"]),
            ("productivity_link", "Conecta adopción con productividad o valor",
             ["productivity", "value", "performance", "impact", "return", "benefit", "roi"]),
            ("temporal",        "Tiene dimensión temporal (panel, longitudinal)",
             ["panel", "longitudinal", "over time", "time series", "dynamic", "years", "lag"]),
        ],
        "labor": [
            ("ai_focus",        "Estudia IA/automatización/robots",
             ["ai", "artificial intelligence", "automation", "robot", "machine learning"]),
            ("wage_employment",  "Mide salarios, empleo o outcomes laborales",
             ["wage", "employment", "job", "salary", "income", "labor", "occupation", "earnings"]),
            ("heterogeneity",   "Distingue por habilidad, tarea u ocupación",
             ["skill", "occupation", "task", "routine", "non-routine", "high-skill", "low-skill", "worker type"]),
            ("within_firm",     "Estudia efectos dentro de firmas o a nivel trabajador",
             ["within-firm", "within firm", "worker-level", "individual", "employee", "team"]),
            ("causal",          "Tiene estrategia causal o cuasi-causal",
             ["causal", "instrumental", "did", "randomized", "quasi-experimental", "exogenous"]),
        ],
        "desigualdad": [
            ("ai_focus",        "Estudia IA/automatización/tecnología digital",
             ["ai", "artificial intelligence", "automation", "digital", "technology"]),
            ("inequality",      "Mide desigualdad, brecha o disparidad",
             ["inequality", "gap", "disparity", "divide", "unequal", "polarization", "wage gap"]),
            ("heterogeneous",   "Analiza efectos heterogéneos por característica",
             ["heterogeneous", "heterogeneity", "differential", "by skill", "by gender", "by size", "by firm"]),
            ("distributional",  "Análisis distributivo (no solo efecto promedio)",
             ["distributional", "distribution", "gini", "percentile", "quantile", "top bottom", "skill premium"]),
            ("context",         "Contexto MiPyME / LATAM / economía en desarrollo",
             ["sme", "small firm", "developing", "latam", "latin america", "colombia", "low income", "informal"]),
        ],
        "management": [
            ("ai_focus",        "Estudia IA/digital/automatización",
             ["ai", "artificial intelligence", "automation", "digital", "machine learning"]),
            ("organizational",  "Estudia factores organizacionales o de gestión",
             ["organizational", "management", "firm", "business", "strategy", "leadership", "governance"]),
            ("adoption_impl",   "Estudia adopción, implementación o escalamiento",
             ["adoption", "implementation", "deploy", "scale", "pilot", "rollout", "integration"]),
            ("capabilities",    "Analiza capacidades, complementariedades o cambio organizacional",
             ["capability", "complementar", "change management", "talent", "upskilling", "readiness", "process"]),
            ("performance",     "Conecta con desempeño o captura de valor",
             ["performance", "productivity", "value", "return", "roi", "impact", "outcome", "profit"]),
        ],
        "policy": [
            ("ai_focus",        "Estudia IA/algoritmos/automatización",
             ["ai", "artificial intelligence", "algorithm", "automation", "machine learning"]),
            ("policy_reg",      "Estudia política pública, regulación o gobernanza",
             ["policy", "regulation", "governance", "law", "framework", "compliance", "legislation"]),
            ("adoption_effect", "Analiza efecto de política en decisiones de adopción",
             ["adoption", "implementation", "firm decision", "barrier", "incentive", "effect on"]),
            ("institutional",   "Contexto institucional o de gobierno",
             ["government", "public", "institutional", "regulator", "authority", "gdpr", "eu ai act"]),
            ("evidence",        "Evidencia empírica (no solo normativo/descriptivo)",
             ["evidence", "empirical", "data", "survey", "experiment", "causal", "impact"]),
        ],
    }

    def check_acceptance_criteria(self, paper, pocket):
        """Check pocket-specific acceptance criteria for a paper. Returns list of {label, met, desc}."""
        if not pocket or pocket not in self.POCKET_CRITERIA:
            return []
        text = (paper.get("title","") + " " + paper.get("abstract", paper.get("summary",""))).lower()
        results = []
        for key, desc, keywords in self.POCKET_CRITERIA[pocket]:
            met = any(k in text for k in keywords)
            results.append({"key": key, "desc": desc, "met": met})
        return results

    def review(self, papers, pocket=None):
        """Review a batch of papers"""
        logger.info(f"Reviewing {len(papers)} papers...")
        reviewed = [self.score_paper(p, pocket=pocket) for p in papers]

        accepted = [p for p in reviewed if p["status"] == "ACEPTADO"]
        review = [p for p in reviewed if p["status"] == "REVISAR"]
        rejected = [p for p in reviewed if p["status"] == "RECHAZADO"]

        logger.info(f"✓ ACEPTADO: {len(accepted)} | REVISAR: {len(review)} | RECHAZADO: {len(rejected)}")

        return reviewed

if __name__ == '__main__':
    reviewer = Reviewer()
    print(f"✓ Reviewer ready. Use: reviewer.review(papers)")
