"""researcher_scholar.py - Search Google Scholar for papers (public search)"""

import requests
import logging
import os
import time
import json
from typing import List, Dict
from datetime import datetime
from bs4 import BeautifulSoup

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'),
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResearcherScholar:
    """
    Busca papers en Google Scholar (búsqueda pública, no requiere API keys)

    Nota: Google Scholar puede tener rate limiting.
    Usamos User-Agent and delays para respetar sus términos.
    """

    def __init__(self):
        self.base_url = "https://scholar.google.com/scholar"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.papers = []

    def search_scholar(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Busca en Google Scholar
        Args:
            query: Búsqueda (ej: "AI adoption firm productivity")
            max_results: Máximo resultados deseados
        Returns:
            Lista de papers con {title, authors, year, url, source}
        """
        params = {
            'q': query,
            'as_ylo': 2023,      # Desde 2023
            'as_yhi': 2026,      # Hasta 2026
            'hl': 'en',
            'num': min(max_results, 100)  # Scholar maxea en 100
        }

        try:
            logger.info(f"🔍 Searching Scholar: {query[:50]}...")
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()

            papers = self._parse_scholar_results(response.text)
            logger.info(f"   ✓ Found {len(papers)} papers")
            time.sleep(2)  # Respetar rate limit
            return papers

        except requests.RequestException as e:
            logger.error(f"❌ Error searching Scholar: {e}")
            return []

    def _parse_scholar_results(self, html: str) -> List[Dict]:
        """Parsea resultados de Google Scholar"""
        papers = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Scholar usa divs con clase "gs_ri" para resultados
            for result in soup.find_all('div', class_='gs_ri'):
                try:
                    # Título y link
                    title_elem = result.find('a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')

                    # Metadatos (autores, año, source)
                    metadata = result.find('div', class_='gs_a')
                    if not metadata:
                        continue

                    metadata_text = metadata.get_text(separator=' | ', strip=True)
                    parts = [p.strip() for p in metadata_text.split('|')]

                    authors = parts[0] if len(parts) > 0 else "Unknown"
                    source = parts[1] if len(parts) > 1 else "Unknown"
                    year_text = parts[2] if len(parts) > 2 else ""

                    # Extraer año
                    year = self._extract_year(year_text)

                    # Skip si no tenemos año o es muy viejo
                    if year < 2023:
                        continue

                    paper = {
                        'title': title,
                        'authors': authors,
                        'source': source,
                        'year': year,
                        'url': url,
                        'scholar_link': f"https://scholar.google.com{url}" if url.startswith('/') else url,
                        'source_name': 'Google Scholar'
                    }

                    papers.append(paper)

                except (AttributeError, IndexError, ValueError) as e:
                    logger.debug(f"Skip malformed result: {e}")
                    continue

            return papers

        except Exception as e:
            logger.error(f"Error parsing Scholar HTML: {e}")
            return []

    def _extract_year(self, year_text: str) -> int:
        """Extrae año del texto (ej: '2024' o 'arXiv 2024')"""
        try:
            # Buscar números de 4 dígitos
            for word in year_text.split():
                if word.isdigit() and 2000 <= int(word) <= 2030:
                    return int(word)
            return datetime.now().year
        except:
            return datetime.now().year

    def search_all_pockets(self) -> Dict[str, List[Dict]]:
        """Busca papers para todos los pockets"""
        results = {}

        # Queries por pocket (más específicas que ArXiv)
        pockets_queries = {
            'evaluacion_experimental': [
                'randomized controlled trial AI productivity',
                'RCT generative AI workplace',
                'causal inference AI adoption'
            ],
            'labor': [
                'AI employment wage effects',
                'generative AI job displacement',
                'AI labor market impact 2024'
            ],
            'desigualdad': [
                'AI inequality wage gap',
                'generative AI skill premium',
                'AI digital divide'
            ],
            'policy': [
                'AI policy regulation labor',
                'generative AI governance',
                'AI regulation GDPR'
            ],
            'human_machine_interaction': [
                'human AI interaction design',
                'generative AI user adoption',
                'AI interface usability'
            ],
            'innovacion_difusion': [
                'AI adoption diffusion firms',
                'generative AI adoption barriers',
                'technology adoption curves AI'
            ],
            'management': [
                'AI organizational adoption',
                'generative AI business model',
                'AI strategy management'
            ]
        }

        logger.info("=" * 80)
        logger.info("🚀 RESEARCHER SCHOLAR - Búsqueda en Google Scholar")
        logger.info("=" * 80)

        for pocket_id, queries in pockets_queries.items():
            logger.info(f"\n📌 {pocket_id}")
            pocket_papers = []

            for query in queries:
                papers = self.search_scholar(query, max_results=15)
                pocket_papers.extend(papers)

            # Deduplicar por título
            unique_papers = {}
            for paper in pocket_papers:
                title_key = paper['title'].lower()
                if title_key not in unique_papers:
                    unique_papers[title_key] = paper

            pocket_papers = list(unique_papers.values())
            results[pocket_id] = pocket_papers

            logger.info(f"   ✓ Total unique: {len(pocket_papers)} papers")

        return results

    def filter_top_tier(self, papers: List[Dict]) -> List[Dict]:
        """Filtra papers por calidad (Scholar tiene buena selección)"""
        filtered = []

        for paper in papers:
            # Filtrar por año (ya filtrado en búsqueda, pero asegurar)
            year = paper.get('year', 0)
            if year < 2023:
                continue

            # Preferir sources académicos
            source = paper.get('source', '').lower()
            skip_sources = ['blog', 'news', 'twitter', 'linkedin']
            if any(skip in source for skip in skip_sources):
                continue

            filtered.append(paper)

        return filtered

    def save_papers_json(self, papers_dict: Dict[str, List[Dict]], output_dir: str = 'data'):
        """Guarda papers en JSON por pocket"""
        os.makedirs(output_dir, exist_ok=True)

        for pocket_id, papers in papers_dict.items():
            filename = f"{output_dir}/{pocket_id}_papers_scholar.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)
            logger.info(f"   💾 Saved: {filename} ({len(papers)} papers)")

    def run(self):
        """Ejecuta búsqueda completa"""
        logger.info("\n🔍 Iniciando búsqueda en Google Scholar...")

        # Buscar
        papers_by_pocket = self.search_all_pockets()

        # Filtrar
        logger.info("\n🔍 Aplicando filtros...")
        filtered_papers = {}
        for pocket_id, papers in papers_by_pocket.items():
            filtered = self.filter_top_tier(papers)
            filtered_papers[pocket_id] = filtered
            logger.info(f"   {pocket_id}: {len(filtered)}/{len(papers)} after filtering")

        # Guardar
        logger.info("\n💾 Guardando resultados...")
        self.save_papers_json(filtered_papers)

        # Resumen
        total = sum(len(p) for p in filtered_papers.values())
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ BÚSQUEDA EN SCHOLAR COMPLETADA: {total} papers encontrados")
        logger.info("=" * 80)
        logger.info("\n📊 Next: Combinar con ArXiv + ejecutar pipeline")

        return filtered_papers


if __name__ == '__main__':
    # Verificar si BeautifulSoup está instalada
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("❌ BeautifulSoup no instalada. Ejecuta: pip install beautifulsoup4")
        exit(1)

    researcher = ResearcherScholar()
    papers = researcher.run()
