"""Hybrid approach: OpenAlex for older papers + Claude for recent papers"""
import json
import requests
import time
from pathlib import Path
from collections import defaultdict

class HybridCitationBuilder:
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.papers = []
        self.paper_index = {}
        self.citations = []  # List of (source_title, target_title)
        
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
                        # Index by title (normalized)
                        title_key = p.get('title', '').lower()
                        self.paper_index[title_key] = p
        
        print(f"✓ Loaded {len(self.papers)} papers")
        
        # Separate by year
        self.recent = [p for p in self.papers if p.get('metadata', {}).get('year', 0) >= 2026]
        self.older = [p for p in self.papers if p.get('metadata', {}).get('year', 0) < 2026]
        
        print(f"  • Recent (2026+): {len(self.recent)}")
        print(f"  • Older (<2026): {len(self.older)}")
    
    def openalex_search(self, title):
        """Search paper in OpenAlex"""
        try:
            url = "https://api.openalex.org/works"
            params = {'search': f'"{title}"', 'per-page': 1}
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                results = response.json().get('results', [])
                if results:
                    return results[0]
        except:
            pass
        return None
    
    def openalex_get_references(self, openalex_id):
        """Get reference titles from OpenAlex work"""
        try:
            url = f"https://api.openalex.org/works/{openalex_id}"
            response = requests.get(url, params={'select': 'referenced_works'}, timeout=5)
            
            if response.status_code == 200:
                ref_ids = response.json().get('referenced_works', [])
                
                # Fetch titles for first 15 references
                titles = []
                for ref_id in ref_ids[:15]:
                    try:
                        ref_url = f"https://api.openalex.org/works/{ref_id}"
                        ref_resp = requests.get(ref_url, params={'select': 'title'}, timeout=5)
                        if ref_resp.status_code == 200:
                            title = ref_resp.json().get('title', '')
                            if title:
                                titles.append(title)
                    except:
                        pass
                    time.sleep(0.1)
                
                return titles
        except:
            pass
        return []
    
    def extract_openalex_citations(self):
        """Extract citations from older papers using OpenAlex"""
        print(f"\n🔍 OPENALEX EXTRACTION ({len(self.older)} papers)...")
        
        for idx, paper in enumerate(self.older[:10], 1):  # Limit to 10 for pilot
            title = paper.get('title', '')
            print(f"\n[{idx}] {title[:70]}...")
            
            # Search in OpenAlex
            oa_paper = self.openalex_search(title)
            if not oa_paper:
                print(f"  ✗ Not found")
                time.sleep(0.5)
                continue
            
            oa_id = oa_paper.get('id', '')
            print(f"  ✓ Found in OpenAlex")
            
            # Get references
            ref_titles = self.openalex_get_references(oa_id)
            print(f"  → {len(ref_titles)} references")
            
            # Match with our papers
            matches = 0
            for ref_title in ref_titles:
                ref_lower = ref_title.lower()
                
                # Check against our papers
                for our_paper in self.papers:
                    our_title_lower = our_paper.get('title', '').lower()
                    
                    # Exact match or very close match
                    if ref_lower == our_title_lower or (len(ref_title) > 30 and ref_lower[:30] == our_title_lower[:30]):
                        self.citations.append({
                            'from': title,
                            'to': our_paper.get('title', ''),
                            'method': 'openalex',
                            'confidence': 0.9
                        })
                        print(f"    ✓ CITATION: → {our_paper.get('title', '')[:50]}...")
                        matches += 1
                        break
            
            if matches == 0:
                print(f"  (no references matched our dataset)")
            
            time.sleep(0.5)
    
    def extract_claude_citations(self):
        """Placeholder for Claude extraction"""
        print(f"\n🤖 CLAUDE EXTRACTION ({len(self.recent)} papers)...")
        print("   (Will use Claude to analyze abstracts)")
        print(f"   Need to process {min(len(self.recent), 20)} recent papers for pilot")
    
    def run_hybrid_pilot(self):
        """Run hybrid extraction"""
        print("\n" + "=" * 70)
        print("HYBRID CITATION EXTRACTION PILOT")
        print("=" * 70)
        
        self.load_papers()
        
        # Step 1: OpenAlex
        self.extract_openalex_citations()
        
        # Step 2: Claude (placeholder)
        self.extract_claude_citations()
        
        # Summary
        print(f"\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"Citations found via OpenAlex: {len(self.citations)}")
        print(f"Expected from Claude: ~5-10 per 20 papers")
        
        if self.citations:
            print(f"\nSample citations found:")
            for c in self.citations[:5]:
                print(f"  • {c['from'][:40]}... → {c['to'][:40]}...")


if __name__ == '__main__':
    builder = HybridCitationBuilder()
    builder.run_hybrid_pilot()
