"""researcher_v2.py - Enhanced paper collection for 7 pockets temáticos"""
import json
import logging
import os
from datetime import datetime

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class ResearcherV2:
    def __init__(self):
        self.pockets = {
            "evaluacion_experimental": {
                "queries": [
                    "generative AI RCT randomized controlled trial 2024-2026",
                    "AI quasi-experimental field experiment productivity",
                    "machine learning causal inference experiment"
                ],
                "description": "Evaluación Experimental - RCTs y field experiments"
            },
            "hmi": {
                "queries": [
                    "human-machine interaction AI design user experience",
                    "AI collaboration worker behavior adoption",
                    "generative AI interface design human factors"
                ],
                "description": "Human-Machine Interaction - Diseño y comportamiento"
            },
            "innovacion_difusion": {
                "queries": [
                    "AI innovation adoption diffusion firms 2023-2026",
                    "generative AI technology adoption curves",
                    "AI adoption barriers firm implementation"
                ],
                "description": "Innovación y Difusión - Adopción tecnológica"
            },
            "labor": {
                "queries": [
                    "AI impact labor markets employment 2024-2026",
                    "generative AI job displacement automation",
                    "AI worker productivity labor economics"
                ],
                "description": "Labor Markets - Mercados de trabajo"
            },
            "desigualdad": {
                "queries": [
                    "AI inequality wage gaps income distribution",
                    "generative AI skill premium labor",
                    "AI digital divide regional disparities"
                ],
                "description": "Desigualdad - Distribución de ingresos y oportunidades"
            },
            "policy": {
                "queries": [
                    "AI policy regulation governance 2024-2026",
                    "generative AI labor policy frameworks",
                    "AI data privacy policy recommendations"
                ],
                "description": "Policy - Políticas y regulación"
            },
            "management": {
                "queries": [
                    "AI organizational adoption management strategy",
                    "generative AI firm implementation change",
                    "AI business models organizational structure"
                ],
                "description": "Management - Adopción organizacional"
            }
        }
        self.papers = []

    def get_search_queries(self):
        """Get all search queries organized by pocket"""
        queries = {}
        for pocket_id, pocket_data in self.pockets.items():
            queries[pocket_id] = {
                "description": pocket_data["description"],
                "queries": pocket_data["queries"]
            }
        return queries

    def log_search_status(self):
        """Log search status and guidance"""
        logger.info("=" * 80)
        logger.info("RESEARCHER V2 - Búsqueda para 7 Pockets Temáticos")
        logger.info("=" * 80)

        for pocket_id, pocket_data in self.pockets.items():
            logger.info(f"\n📌 {pocket_data['description']}")
            for i, query in enumerate(pocket_data["queries"], 1):
                logger.info(f"   Query {i}: {query}")

        logger.info("\n" + "=" * 80)
        logger.info("Para ejecutar búsquedas automáticas:")
        logger.info("  1. Configura SerpAPI_KEY en .env")
        logger.info("  2. python scripts/researcher_v2.py --search")
        logger.info("  3. O usa WebSearch manual en Google Scholar/arXiv")
        logger.info("=" * 80)

if __name__ == '__main__':
    researcher = ResearcherV2()
    researcher.log_search_status()

    # Export queries
    queries = researcher.get_search_queries()
    with open('data/search_queries.json', 'w') as f:
        json.dump(queries, f, indent=2)

    print("\n✅ Search queries exported to data/search_queries.json")
    print("📊 7 pockets × 3 queries = 21 search directions")
