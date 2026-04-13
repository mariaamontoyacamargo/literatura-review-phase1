"""Extract citations from paper abstracts using Claude API"""
import json
import os
from pathlib import Path
import anthropic
from collections import defaultdict

class ClaudeCitationExtractor:
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        self.papers = []
        self.paper_titles = []
        self.citations = []
        
    def load_papers(self):
        """Load all papers"""
        pockets = ['evaluacion_experimental', 'management', 'labor', 'desigualdad',
                   'policy', 'human_machine_interaction', 'innovacion_difusion']
        
        for pocket in pockets:
            file_path = self.data_dir / f'{pocket}_reviewed.json'
            if file_path.exists():
                with open(file_path) as f:
                    papers = json.load(f)
                    for p in papers:
                        p['pocket'] = pocket
                        self.papers.append(p)
                        self.paper_titles.append(p.get('title', ''))
        
        print(f"✓ Loaded {len(self.papers)} papers")
        
        # Get papers with abstracts
        self.papers_with_abstract = [p for p in self.papers if p.get('metadata', {}).get('summary')]
        print(f"✓ Papers with abstracts: {len(self.papers_with_abstract)}")
    
    def extract_citations_from_abstract(self, source_paper):
        """Use Claude to find cited papers in abstract"""
        title = source_paper.get('title', '')
        abstract = source_paper.get('metadata', {}).get('summary', '')
        
        if not abstract:
            return []
        
        # Create list of possible papers for matching
        all_paper_titles = '\n'.join(self.paper_titles[:100])  # Limit for token efficiency
        
        prompt = f"""Analiza este abstract académico e identifica qué otros papers de nuestra colección están siendo citados, mencionados o referenciados.

PAPER ACTUAL:
Título: {title}

ABSTRACT:
{abstract}

PAPERS EN NUESTRA COLECCIÓN (muestra):
{all_paper_titles}

TAREA:
1. Busca menciones explícitas de otros papers (por autor, año, o tema específico)
2. Para cada mención encontrada, intenta encontrar el match más cercano en nuestra colección
3. SÉ CONSERVADOR: solo incluye si estás >80% seguro del match
4. Ignora menciones vagas o genéricas

RESPUESTA:
Retorna SOLO los títulos exactos de papers de nuestra colección que encuentres citados.
Un match por línea, sin explicaciones.
Si no encuentras matches claros, retorna: NONE"""

        try:
            message = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text.strip()
            
            if response_text == "NONE" or not response_text:
                return []
            
            # Parse matches
            matches = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line and line != "NONE":
                    # Find if this matches a paper in our dataset
                    for paper in self.papers:
                        if line.lower() == paper.get('title', '').lower():
                            matches.append(paper.get('title', ''))
                            break
            
            return matches
        
        except Exception as e:
            print(f"  Error: {e}")
            return []
    
    def run_extraction(self, n_papers=None):
        """Extract citations from all papers with abstracts"""
        if n_papers is None:
            n_papers = len(self.papers_with_abstract)
        
        print(f"\n🤖 CLAUDE CITATION EXTRACTION ({min(n_papers, len(self.papers_with_abstract))} papers)...\n")
        
        for idx, paper in enumerate(self.papers_with_abstract[:n_papers], 1):
            title = paper.get('title', '')
            print(f"[{idx}/{min(n_papers, len(self.papers_with_abstract))}] {title[:70]}...")
            
            # Extract citations
            cited_papers = self.extract_citations_from_abstract(paper)
            
            if cited_papers:
                print(f"  ✓ Found {len(cited_papers)} citations:")
                for cited in cited_papers:
                    print(f"    → {cited[:60]}...")
                    self.citations.append({
                        'from': title,
                        'to': cited,
                        'method': 'claude',
                        'confidence': 0.85
                    })
            else:
                print(f"  (no citations found in our dataset)")
    
    def save_results(self):
        """Save citations to JSON"""
        output = {
            'citations': self.citations,
            'stats': {
                'total_citations': len(self.citations),
                'papers_analyzed': len(self.papers_with_abstract),
                'method': 'claude-abstract-analysis'
            }
        }
        
        with open('data/claude_extracted_citations.json', 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(self.citations)} citations to: data/claude_extracted_citations.json")
    
    def print_summary(self):
        """Print summary"""
        print(f"\n" + "=" * 70)
        print("EXTRACTION RESULTS")
        print("=" * 70)
        print(f"Papers analyzed: {len(self.papers_with_abstract)}")
        print(f"Citations found: {len(self.citations)}")
        
        if self.citations:
            print(f"\nTop cited papers in our dataset:")
            citation_counts = defaultdict(int)
            for c in self.citations:
                citation_counts[c['to']] += 1
            
            for paper, count in sorted(citation_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"  • {paper[:60]}... ({count} citations)")


if __name__ == '__main__':
    extractor = ClaudeCitationExtractor()
    extractor.load_papers()
    extractor.run_extraction(n_papers=10)  # Pilot: 10 papers
    extractor.save_results()
    extractor.print_summary()
