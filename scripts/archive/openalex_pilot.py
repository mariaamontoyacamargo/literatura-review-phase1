"""Pilot: Extract real references using OpenAlex API"""
import json
import requests
import time
from pathlib import Path

class OpenAlexPilot:
    def __init__(self, data_dir='data'):
        self.data_dir = Path(data_dir)
        self.papers = []
        self.paper_index = {}
        
    def load_papers(self):
        """Load all reviewed papers"""
        pockets = ['evaluacion_experimental', 'management', 'labor', 'desigualdad',
                   'policy', 'human_machine_interaction', 'innovacion_difusion']
        
        for pocket in pockets:
            file_path = self.data_dir / f'{pocket}_reviewed.json'
            if file_path.exists():
                with open(file_path) as f:
                    pocket_papers = json.load(f)
                    for paper in pocket_papers:
                        paper['pocket'] = pocket
                        self.papers.append(paper)
                        # Index by title
                        title_key = paper.get('title', '').lower()
                        self.paper_index[title_key] = paper
        
        print(f"✓ Loaded {len(self.papers)} papers")
        return self.papers
    
    def search_openalex(self, title, authors=None):
        """Search for paper in OpenAlex"""
        try:
            # Build query
            query = f'"{title}"'
            
            url = "https://api.openalex.org/works"
            params = {
                'search': query,
                'per-page': 5
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    # Return top result
                    return results[0]
        
        except Exception as e:
            print(f"  Error: {e}")
        
        return None
    
    def get_references(self, openalex_id):
        """Get references (cited works) from OpenAlex work"""
        try:
            url = f"https://api.openalex.org/works/{openalex_id}"
            params = {'select': 'id,title,referenced_works'}
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                # Get the referenced works IDs
                ref_ids = data.get('referenced_works', [])
                return ref_ids[:20]  # Limit to 20 references
        
        except Exception as e:
            print(f"  Error fetching references: {e}")
        
        return []
    
    def get_work_title(self, openalex_id):
        """Get title from OpenAlex work ID"""
        try:
            url = f"https://api.openalex.org/works/{openalex_id}"
            params = {'select': 'title'}
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('title', '')
        
        except Exception as e:
            pass
        
        return None
    
    def run_pilot(self, n_papers=10):
        """Run pilot on first N papers"""
        print(f"\n🔍 OPENALEX PILOT - Processing {n_papers} papers...\n")
        
        found_citations = 0
        papers_processed = 0
        
        for idx, paper in enumerate(self.papers[:n_papers]):
            papers_processed += 1
            title = paper.get('title', '')
            authors = paper.get('metadata', {}).get('authors', [])
            
            print(f"\n[{papers_processed}/{n_papers}] {title[:70]}...")
            
            # Search in OpenAlex
            oa_paper = self.search_openalex(title, authors)
            if not oa_paper:
                print(f"  ✗ Not found in OpenAlex")
                time.sleep(0.5)
                continue
            
            oa_id = oa_paper.get('id', '')
            oa_title = oa_paper.get('title', '')
            print(f"  ✓ Found in OpenAlex: {oa_title[:60]}...")
            
            # Get references
            ref_ids = self.get_references(oa_id)
            print(f"  → Fetching {len(ref_ids)} references...")
            
            matches = 0
            for ref_id in ref_ids[:10]:  # Check first 10 references
                ref_title = self.get_work_title(ref_id)
                if not ref_title:
                    continue
                
                # Try to match with papers in our dataset
                ref_title_lower = ref_title.lower()
                our_title_lower = title.lower()
                
                # Check if this reference exists in our dataset
                for our_paper in self.papers:
                    our_paper_title = our_paper.get('title', '').lower()
                    
                    # Simple match: check if titles are very similar
                    if ref_title_lower == our_paper_title:
                        print(f"      ✓ MATCH: '{ref_title[:50]}...' in our dataset")
                        matches += 1
                        found_citations += 1
                        break
                    # Fuzzy match: if significant overlap
                    elif len(ref_title) > 30 and ref_title[:30].lower() == our_paper_title[:30]:
                        print(f"      ✓ FUZZY MATCH: '{ref_title[:50]}...'")
                        matches += 1
                        found_citations += 1
                        break
                
                time.sleep(0.2)
            
            if matches == 0:
                print(f"  → No references found in our dataset")
            else:
                print(f"  ✓ Found {matches} citations to papers in our dataset")
            
            time.sleep(0.5)
        
        print(f"\n" + "=" * 70)
        print(f"📊 PILOT RESULTS")
        print(f"=" * 70)
        print(f"Papers processed: {papers_processed}")
        print(f"Citations found in our dataset: {found_citations}")
        print(f"Success rate: {100*found_citations/max(papers_processed, 1):.1f}%")
        print()
        print(f"📌 ASSESSMENT:")
        if found_citations == 0:
            print(f"  ✗ OpenAlex approach not working - references don't match our papers")
        elif found_citations < papers_processed:
            print(f"  ⚠️  Limited matches - might need fuzzy matching or manual curation")
        else:
            print(f"  ✓ Works well! Can proceed with full extraction")


if __name__ == '__main__':
    pilot = OpenAlexPilot()
    pilot.load_papers()
    pilot.run_pilot(n_papers=10)
