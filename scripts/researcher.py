"""researcher.py - Paper collection from SerpAPI + Arxiv"""
import json, csv, os, logging
from datetime import datetime
load_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(level=load_level, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Researcher:
    def __init__(self):
        self.papers = {}
    
    def search_all(self):
        logger.info("Starting paper collection...")
        # Placeholder for now
        logger.info(f"Collected {len(self.papers)} papers")
        return list(self.papers.values())

if __name__ == '__main__':
    researcher = Researcher()
    papers = researcher.search_all()
    print(f"✓ Collected {len(papers)} papers. Next: python reviewer.py")
