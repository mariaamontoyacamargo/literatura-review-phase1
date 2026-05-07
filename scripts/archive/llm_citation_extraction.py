"""Use Claude to extract citations from abstracts"""
import json
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

class LLMCitationExtractor:
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.papers = []
        self.paper_index = {}
        
    def load_papers(self):
        """Load papers"""
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
                        # Index by title
                        title_lower = p.get('title', '').lower()
                        self.paper_index[title_lower] = p
        
        print(f"✓ Loaded {len(self.papers)} papers")
    
    def extract_citations_from_abstract(self, title, abstract):
        """Use Claude to find cited papers in abstract"""
        if not abstract:
            return []
        
        # Create a list of paper titles for matching
        all_titles = [p.get('title', '') for p in self.papers]
        titles_str = '\n'.join(all_titles[:50])  # Limit to first 50
        
        prompt = f"""Analiza este abstract de paper y encuentra qué otros papers de nuestra colección están siendo citados o mencionados.

ABSTRACT DEL PAPER:
"{abstract[:500]}"

PAPERS EN NUESTRA COLECCIÓN (muestra):
{titles_str}

TAREA:
1. Identifica mencionas de otros papers por autor, año o tema
2. Para cada mención, intenta encontrar el match más cercano en nuestra colección
3. Retorna SOLO matches con alta confianza (>80%)

FORMATO:
- Si encuentra matches, lista: "CITED: [título exacto del paper citado]"
- Si no encuentra matches claros, retorna: "NO CLEAR CITATIONS"

Sé muy conservador - solo incluye si estás muy seguro del match."""

        try:
            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=300,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text
            return response_text
        
        except Exception as e:
            print(f"Error: {e}")
            return "ERROR"
    
    def run_pilot(self, n_papers=5):
        """Run pilot on N papers with abstracts"""
        print(f"\n🤖 LLM CITATION EXTRACTION PILOT - {n_papers} papers\n")
        
        papers_with_abstract = [p for p in self.papers if p.get('metadata', {}).get('summary')]
        print(f"Papers with abstracts: {len(papers_with_abstract)}")
        
        for idx, paper in enumerate(papers_with_abstract[:n_papers]):
            title = paper.get('title', '')
            abstract = paper.get('metadata', {}).get('summary', '')
            
            print(f"\n[{idx+1}/{n_papers}] {title[:70]}...")
            print(f"Abstract length: {len(abstract)} chars")
            
            result = self.extract_citations_from_abstract(title, abstract)
            print(f"Claude response:\n{result}")
            print("-" * 70)


if __name__ == '__main__':
    extractor = LLMCitationExtractor()
    extractor.load_papers()
    extractor.run_pilot(n_papers=5)
