"""network_builder.py - Build semantic network from ACEPTADO papers with real relationships"""

import json
import os
import logging
from collections import defaultdict
import networkx as nx
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkBuilder:
    """Build semantic graph from papers with meaningful relationships"""

    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.papers = []
        self.graph = nx.Graph()

    def load_papers(self):
        """Load all reviewed papers from all pockets"""
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
                    self.papers.extend(pocket_papers)

        logger.info(f"✓ Loaded {len(self.papers)} papers total")
        return self.papers

    def build_graph(self):
        """Build graph from ACEPTADO papers only"""
        # Filter to ACEPTADO papers
        accepted = [p for p in self.papers if p.get('status') == 'ACEPTADO']
        logger.info(f"✓ Building graph from {len(accepted)} ACEPTADO papers")

        # Add nodes
        for i, paper in enumerate(accepted):
            self.graph.add_node(
                i,
                title=paper.get('title', 'Unknown'),
                score=paper.get('score', 5),
                pocket=paper.get('pocket', 'unknown'),
                year=paper.get('metadata', {}).get('year', 2025),
                methodology=paper.get('breakdown', {}).get('methodology', 0)
            )

        # Add edges based on relationships
        for i in range(len(accepted)):
            for j in range(i+1, len(accepted)):
                paper1 = accepted[i]
                paper2 = accepted[j]

                # Check for relationships
                relations = self._find_relations(paper1, paper2)

                if relations:
                    weight = sum(w for _, w in relations) / len(relations)
                    relation_types = [t for t, _ in relations]

                    self.graph.add_edge(
                        i, j,
                        weight=weight,
                        relations=relation_types,
                        relation_count=len(relations)
                    )

        logger.info(f"✓ Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        return self.graph

    def _find_relations(self, paper1, paper2):
        """Find relationships between two papers"""
        relations = []

        # 1. Same pocket (strong thematic link)
        if paper1.get('pocket') == paper2.get('pocket'):
            relations.append(('same-pocket', 0.8))

        # 2. Similar methodology
        method1 = paper1.get('breakdown', {}).get('methodology', 0)
        method2 = paper2.get('breakdown', {}).get('methodology', 0)
        if method1 > 0 and method2 > 0 and abs(method1 - method2) <= 1:
            relations.append(('similar-methodology', 0.6))

        # 3. Similar score (quality level)
        score1 = paper1.get('score', 5)
        score2 = paper2.get('score', 5)
        if abs(score1 - score2) <= 1:
            relations.append(('similar-quality', 0.4))

        # 4. Temporal proximity (same year)
        year1 = paper1.get('metadata', {}).get('year', 2025)
        year2 = paper2.get('metadata', {}).get('year', 2025)
        if year1 == year2:
            relations.append(('same-year', 0.3))

        # 5. Keyword overlap
        keywords1 = set(paper1.get('metadata', {}).get('keywords', []) or [])
        keywords2 = set(paper2.get('metadata', {}).get('keywords', []) or [])
        if keywords1 and keywords2:
            overlap = len(keywords1 & keywords2) / len(keywords1 | keywords2)
            if overlap > 0.3:
                relations.append(('keyword-overlap', overlap))

        return relations

    def detect_clusters(self):
        """Detect clusters using Louvain algorithm"""
        try:
            import community
        except ImportError:
            logger.warning("python-louvain not installed, using basic clustering")
            # Fallback: group by pocket
            clusters = defaultdict(list)
            for node in self.graph.nodes():
                pocket = self.graph.nodes[node].get('pocket', 'unknown')
                clusters[pocket].append(node)
            return clusters

        # Use Louvain clustering
        partition = community.best_partition(self.graph)
        clusters = defaultdict(list)
        for node, cluster_id in partition.items():
            clusters[cluster_id].append(node)
        return clusters

    def save_visualization(self, output_file='outputs/network_interactive.html'):
        """Save interactive visualization using Plotly"""
        try:
            import plotly.graph_objects as go
        except ImportError:
            logger.error("Plotly not installed: pip install plotly")
            return

        # Calculate positions using spring layout
        pos = nx.spring_layout(self.graph, k=0.5, iterations=50, seed=42)

        # Build edge traces with hover details
        edge_x = []
        edge_y = []
        edge_hover = []
        edge_color = []
        edge_width = []

        # Color map for relations
        color_map = {
            'same-pocket': 'rgba(102, 126, 234, 0.6)',      # Blue
            'similar-methodology': 'rgba(16, 185, 129, 0.5)', # Green
            'similar-quality': 'rgba(245, 158, 11, 0.4)',   # Orange
            'same-year': 'rgba(139, 92, 246, 0.3)',         # Purple
            'keyword-overlap': 'rgba(239, 68, 68, 0.4)'     # Red
        }

        for u, v, data in self.graph.edges(data=True):
            x0, y0 = pos[u]
            x1, y1 = pos[v]

            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

            # Build hover text with connection details
            title1 = self.graph.nodes[u].get('title', 'Unknown')[:50]
            title2 = self.graph.nodes[v].get('title', 'Unknown')[:50]
            relations = data.get('relations', [])
            weight = data.get('weight', 0)

            hover_text = f"<b>{title1}</b><br>↔<br><b>{title2}</b><br><br>"
            hover_text += f"<b>Connections:</b><br>"
            for rel in relations:
                hover_text += f"• {rel}<br>"
            hover_text += f"<br><b>Strength:</b> {weight:.2f}"

            # Get primary relation type for coloring
            primary_rel = relations[0] if relations else 'other'
            color = color_map.get(primary_rel, 'rgba(100, 100, 100, 0.2)')

            edge_hover.extend([hover_text, hover_text, hover_text])
            edge_color.extend([color, color, color])
            edge_width.extend([1.5 + weight * 2, 1.5 + weight * 2, 1.5 + weight * 2])

        # Create single edge trace with all edges
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=1.5, color='rgba(125, 125, 125, 0.2)'),
            hovertext=edge_hover,
            hoverinfo='text',
            showlegend=False,
            name='Connections'
        )
        edge_traces = [edge_trace]

        # Build node trace
        node_x = [pos[node][0] for node in self.graph.nodes()]
        node_y = [pos[node][1] for node in self.graph.nodes()]
        node_text = []
        node_color = []
        node_size = []

        for node in self.graph.nodes():
            title = self.graph.nodes[node].get('title', 'Unknown')
            score = self.graph.nodes[node].get('score', 5)
            pocket = self.graph.nodes[node].get('pocket', 'unknown')

            node_text.append(f"{title}<br>Score: {score}/10<br>Pocket: {pocket}")

            # Color by score
            if score >= 8:
                node_color.append('rgba(16, 185, 129, 0.8)')  # Green
            elif score >= 7:
                node_color.append('rgba(59, 130, 246, 0.8)')  # Blue
            elif score >= 6:
                node_color.append('rgba(139, 92, 246, 0.8)')  # Purple
            else:
                node_color.append('rgba(245, 158, 11, 0.8)')  # Orange

            # Size by degree
            degree = self.graph.degree(node)
            node_size.append(15 + degree * 1.5)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            hovertext=node_text,
            text=node_text,
            marker=dict(
                size=node_size,
                color=node_color,
                line=dict(color='white', width=1)
            ),
            name='Papers'
        )

        # Create figure
        fig = go.Figure(data=edge_traces + [node_trace])

        fig.update_layout(
            title='Semantic Network of ACEPTADO Papers<br><sub>Nodes colored by score, sized by connections</sub>',
            showlegend=True,
            hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='#f8f9fa',
            height=800,
            width=1200
        )

        # Save
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))
        logger.info(f"✓ Network visualization saved: {output_file}")

    def print_summary(self):
        """Print network summary"""
        clusters = self.detect_clusters()

        print("\n" + "="*60)
        print("📊 NETWORK SUMMARY")
        print("="*60)
        print(f"Nodes (ACEPTADO papers): {self.graph.number_of_nodes()}")
        print(f"Edges (relationships): {self.graph.number_of_edges()}")
        print(f"Network density: {nx.density(self.graph):.3f}")
        print(f"Average clustering coefficient: {nx.average_clustering(self.graph):.3f}")
        print(f"\nClusters detected: {len(clusters)}")
        for cluster_id, nodes in clusters.items():
            print(f"  Cluster {cluster_id}: {len(nodes)} papers")

        # Print top hubs
        print("\n🔗 Top Hub Papers (most connected):")
        degrees = dict(self.graph.degree())
        top_hubs = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]
        for node_id, degree in top_hubs:
            title = self.graph.nodes[node_id].get('title', 'Unknown')
            print(f"  {degree} connections: {title[:60]}")

        print("\n" + "="*60)


if __name__ == '__main__':
    builder = NetworkBuilder()
    builder.load_papers()
    builder.build_graph()
    builder.save_visualization()
    builder.print_summary()
