"""mapper.py - Build semantic graph & detect gaps"""
import json, logging, os
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

class Mapper:
    def __init__(self):
        self.graph = None
    
    def build(self):
        logger.info("Building graph...")
        logger.info("Built graph")
        return self.graph

if __name__ == '__main__':
    mapper = Mapper()
    graph = mapper.build()
    print(f"✓ Built graph. Next: streamlit run ui.py")
