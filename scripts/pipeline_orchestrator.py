"""
pipeline_orchestrator.py - Orchestrate complete literature review pipeline
Processes all pockets: Researcher → Reviewer → Synthesizer → Mapper → UI
"""
import json
import os
import sys
import logging
from pathlib import Path
import yaml
from collections import defaultdict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from reviewer import Reviewer
from synthesizer import Synthesizer
from mapper import Mapper


class PipelineOrchestrator:
    """Orchestrate end-to-end literature review pipeline"""

    def __init__(self, data_dir="data", config_file="pockets_config.yaml"):
        self.data_dir = Path(data_dir)
        self.config_dir = Path(__file__).parent.parent
        self.config_file = self.config_dir / config_file

        # Load pockets configuration
        with open(self.config_file) as f:
            self.config = yaml.safe_load(f)

        self.pockets = self.config['pockets']
        self.all_papers = []
        self.all_reviewed = []
        self.all_synthesized = []

    def process_pocket(self, pocket_name):
        """Process a single pocket through the full pipeline"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing pocket: {pocket_name}")
        logger.info(f"{'='*70}")

        # Load papers for this pocket
        papers_file = self.data_dir / f"{pocket_name}_papers.json"
        if not papers_file.exists():
            logger.warning(f"  ⚠️  No papers file found: {papers_file}")
            logger.info(f"     Skipping pocket {pocket_name}")
            return

        logger.info(f"  📥 Loading papers...")
        with open(papers_file) as f:
            papers = json.load(f)
        logger.info(f"     Loaded {len(papers)} papers")

        # Step 1: Review
        logger.info(f"  🔍 Reviewing papers...")
        reviewer = Reviewer()
        reviewed_papers = reviewer.review(papers)
        logger.info(f"     ✓ Reviewed {len(reviewed_papers)} papers")

        # Log review breakdown
        status_counts = defaultdict(int)
        for p in reviewed_papers:
            status_counts[p['status']] += 1
        logger.info(f"       Status: {dict(status_counts)}")
        avg_score = sum(p['score'] for p in reviewed_papers) / len(reviewed_papers)
        logger.info(f"       Avg Score: {avg_score:.1f}/10")

        # Save reviewed papers
        reviewed_file = self.data_dir / f"{pocket_name}_reviewed.json"
        with open(reviewed_file, 'w') as f:
            json.dump(reviewed_papers, f, indent=2, ensure_ascii=False)
        logger.info(f"  💾 Saved: {reviewed_file.name}")

        # Step 2: Synthesize
        logger.info(f"  🧪 Synthesizing insights...")
        synthesizer = Synthesizer()
        synthesized_papers = synthesizer.synthesize(reviewed_papers)
        logger.info(f"     ✓ Synthesized {len(synthesized_papers)} papers")

        # Count extracted features
        total_keywords = sum(len(p.get('keywords', [])) for p in synthesized_papers)
        total_outcomes = sum(len(p.get('outcome_variables', [])) for p in synthesized_papers)
        total_relations = sum(len(p.get('related_papers', [])) for p in synthesized_papers)
        logger.info(f"       Keywords extracted: {total_keywords}")
        logger.info(f"       Outcome variables: {total_outcomes}")
        logger.info(f"       Paper relations found: {total_relations}")

        # Save synthesized papers
        synthesized_file = self.data_dir / f"{pocket_name}_synthesized.json"
        with open(synthesized_file, 'w') as f:
            json.dump(synthesized_papers, f, indent=2, ensure_ascii=False)
        logger.info(f"  💾 Saved: {synthesized_file.name}")

        # Store for consolidated processing
        self.all_papers.extend(papers)
        self.all_reviewed.extend(reviewed_papers)
        self.all_synthesized.extend(synthesized_papers)

        return {
            'pocket': pocket_name,
            'papers_count': len(papers),
            'reviewed': reviewed_papers,
            'synthesized': synthesized_papers
        }

    def process_all_pockets(self):
        """Process all active pockets in sequence"""
        active_pockets = [
            name for name, config in self.pockets.items()
            if config.get('status') == 'active'
        ]

        logger.info(f"\n📋 Found {len(active_pockets)} active pockets")
        logger.info(f"   {', '.join(active_pockets)}")

        results = {}
        for pocket_name in active_pockets:
            result = self.process_pocket(pocket_name)
            if result:
                results[pocket_name] = result

        return results

    def build_consolidated_graph(self):
        """Build consolidated network graph for all pockets"""
        logger.info(f"\n{'='*70}")
        logger.info("Building consolidated network graph...")
        logger.info(f"{'='*70}")

        # Use all synthesized papers
        logger.info(f"  📊 Processing {len(self.all_synthesized)} papers across all pockets...")

        mapper = Mapper()

        # Build nodes from all papers
        for paper in self.all_synthesized:
            mapper.graph.add_node(
                paper.get("id") or paper.get("title"),
                title=paper.get("title"),
                year=paper.get("year"),
                pocket=paper.get("pocket"),
                keywords=paper.get("keywords", []),
                authors=paper.get("authors", []),
                methodology=paper.get("methodology"),
                citations=paper.get("citations_count", 0),
                status="ACEPTADO"  # All in consolidated are accepted
            )

        # Find relations across all papers
        for i, paper1 in enumerate(self.all_synthesized):
            for paper2 in self.all_synthesized[i+1:]:
                id1 = paper1.get("id") or paper1.get("title")
                id2 = paper2.get("id") or paper2.get("title")

                relations = mapper.find_relations(paper1, paper2)

                if relations:
                    combined_weight = min(sum(r[1] for r in relations), 1.0)
                    relation_names = [r[0] for r in relations]

                    mapper.graph.add_edge(
                        id1, id2,
                        weight=combined_weight,
                        relations=relation_names,
                        relation_count=len(relations)
                    )

                    for rel_type, _ in relations:
                        mapper.relation_types[rel_type] += 1

        logger.info(f"  ✓ Graph built: {mapper.graph.number_of_nodes()} nodes, {mapper.graph.number_of_edges()} edges")
        logger.info(f"    Density: {mapper.get_network_stats().get('density', 0):.3f}")

        # Get gaps
        gaps = mapper.detect_gaps()

        # Prepare graph output
        graph_data = {
            "nodes": [
                {
                    "id": node,
                    "label": self.all_synthesized[[p.get("id") or p.get("title") for p in self.all_synthesized].index(node) if node in [p.get("id") or p.get("title") for p in self.all_synthesized] else 0].get("title", "Unknown")[:50],
                    "title": self.all_synthesized[[p.get("id") or p.get("title") for p in self.all_synthesized].index(node) if node in [p.get("id") or p.get("title") for p in self.all_synthesized] else 0].get("title", "Unknown"),
                    "pocket": mapper.graph.nodes[node].get('pocket', 'unknown'),
                    "citations": mapper.graph.nodes[node].get('citations', 0)
                }
                for node in mapper.graph.nodes()
            ],
            "edges": [
                {
                    "source": edge[0],
                    "target": edge[1],
                    "weight": mapper.graph[edge[0]][edge[1]].get('weight', 0),
                    "relations": mapper.graph[edge[0]][edge[1]].get('relations', [])
                }
                for edge in mapper.graph.edges()
            ],
            "stats": mapper.get_network_stats(),
            "gaps": gaps
        }

        # Save consolidated graph
        graph_file = self.data_dir / "consolidated_graph.json"
        with open(graph_file, 'w') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        logger.info(f"  💾 Saved: {graph_file.name}")

        return graph_data

    def generate_summary(self):
        """Generate summary report of entire pipeline"""
        logger.info(f"\n{'='*70}")
        logger.info("📊 PIPELINE SUMMARY")
        logger.info(f"{'='*70}")

        logger.info(f"  Total papers processed: {len(self.all_papers)}")
        logger.info(f"  Total papers reviewed: {len(self.all_reviewed)}")

        # Breakdown by status
        status_counts = defaultdict(int)
        for p in self.all_reviewed:
            status_counts[p.get('status', 'UNKNOWN')] += 1
        logger.info(f"  Status breakdown: {dict(status_counts)}")

        # Average score
        if self.all_reviewed:
            avg_score = sum(p.get('score', 0) for p in self.all_reviewed) / len(self.all_reviewed)
            logger.info(f"  Average review score: {avg_score:.1f}/10")

        # Network stats
        if hasattr(self, 'graph_data'):
            stats = self.graph_data.get('stats', {})
            logger.info(f"  Network nodes: {stats.get('nodes', 0)}")
            logger.info(f"  Network edges: {stats.get('edges', 0)}")
            logger.info(f"  Network density: {stats.get('density', 0):.3f}")

        logger.info(f"\n✅ Pipeline execution complete!")
        logger.info(f"   Check outputs/ directory for dashboard and data/ for JSON files")


def main():
    """Main pipeline execution"""
    logger.info("🚀 Starting Literature Review Pipeline Orchestrator...")

    orchestrator = PipelineOrchestrator()

    # Process all pockets
    results = orchestrator.process_all_pockets()

    # Build consolidated graph if we have papers
    if orchestrator.all_synthesized:
        orchestrator.graph_data = orchestrator.build_consolidated_graph()

    # Generate summary
    orchestrator.generate_summary()

    logger.info("\n📈 Next steps:")
    logger.info("   1. Review dashboard at http://localhost:8000/dashboard_v3.html")
    logger.info("   2. Check JSON files in data/ directory")
    logger.info("   3. Refine papers based on gaps identified")


if __name__ == '__main__':
    main()
