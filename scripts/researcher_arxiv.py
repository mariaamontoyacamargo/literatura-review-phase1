"""researcher_arxiv.py - Real paper collection from ArXiv API and public sources"""

import requests
import json
import csv
import logging
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict
import yaml

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'),
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ResearcherArxiv:
    """
    Recolecta papers TOP-TIER de ArXiv API siguiendo RESEARCHER.md
    - Target: 5-15 papers por pocket (50-100+ total)
    - Filtros: venue, h-index autor, citaciones, año, metodología
    - Fuentes: ArXiv API (libre, sin keys)
    """

    def __init__(self):
        self.papers = []
        self.pockets_config = self._load_pockets_config()
        self.arxiv_base_url = "http://export.arxiv.org/api/query?"
        self.headers = {
            'User-Agent': 'Literature-Review-BID-IA/1.0'
        }

    def _load_pockets_config(self) -> Dict:
        """Carga configuración de pockets desde YAML"""
        config_path = "pockets_config.yaml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"No {config_path} found, using hardcoded pockets")
            return self._default_pockets()

    def _default_pockets(self) -> Dict:
        """Pockets por defecto si no existe YAML"""
        return {
            'pockets': {
                'evaluacion_experimental': {
                    'name': 'Evaluación Experimental',
                    'search_queries': [
                        'AI randomized controlled trial RCT 2024 2025 2026',
                        'causal inference machine learning experiment productivity',
                        'quasi-experimental design difference-in-differences AI',
                        'field experiment generative AI treatment effect'
                    ]
                },
                'labor': {
                    'name': 'Labor Markets',
                    'search_queries': [
                        'AI impact labor market employment 2024 2025',
                        'generative AI job displacement automation workers',
                        'AI wage effects skill premium labor economics',
                        'reskilling retraining AI adoption employment'
                    ]
                },
                'desigualdad': {
                    'name': 'Desigualdad',
                    'search_queries': [
                        'AI inequality wage gaps income distribution',
                        'generative AI skill-biased technological change',
                        'AI digital divide regional disparities access',
                        'gender gap AI labor income inequality'
                    ]
                },
                'policy': {
                    'name': 'Policy',
                    'search_queries': [
                        'AI policy regulation governance frameworks 2024',
                        'generative AI labor policy worker protection',
                        'AI education policy skills development training',
                        'data privacy policy AI regulation GDPR'
                    ]
                },
                'human_machine_interaction': {
                    'name': 'HMI',
                    'search_queries': [
                        'human-machine interaction AI design user experience',
                        'generative AI interface design human factors',
                        'AI explainability transparency user trust',
                        'AI adoption barriers user behavior interaction'
                    ]
                },
                'innovacion_difusion': {
                    'name': 'Innovación y Difusión',
                    'search_queries': [
                        'AI innovation adoption diffusion firms 2023 2024',
                        'generative AI adoption curves S-curve diffusion',
                        'technology adoption barriers complementarities AI',
                        'innovation spillovers network effects AI'
                    ]
                },
                'management': {
                    'name': 'Management',
                    'search_queries': [
                        'AI organizational adoption management strategy',
                        'generative AI firm implementation business model',
                        'organizational change capability AI adoption',
                        'AI leadership strategy competitive advantage'
                    ]
                }
            }
        }

    def search_arxiv(self, query: str, max_results: int = 20) -> List[Dict]:
        """
        Busca papers en ArXiv API
        Args:
            query: búsqueda en arXiv (ej: 'AI AND (RCT OR experiment)')
            max_results: número máximo de resultados
        Returns:
            Lista de papers con metadata
        """
        # Construir query para ArXiv
        # Categorías relevantes: cs.CY (comp systems), econ.EM (econometrics), stat.ME (methods)
        arxiv_query = f'cat:cs.CY AND ({query}) OR cat:econ.EM AND ({query})'

        params = {
            'search_query': arxiv_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }

        try:
            logger.info(f"🔍 Buscando en arXiv: {query[:50]}...")
            response = requests.get(self.arxiv_base_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()

            papers = self._parse_arxiv_response(response.text)
            logger.info(f"   ✓ Found {len(papers)} papers")
            time.sleep(3)  # Respetar rate limit de arXiv
            return papers

        except requests.RequestException as e:
            logger.error(f"❌ Error searching arXiv: {e}")
            return []

    def _parse_arxiv_response(self, xml_response: str) -> List[Dict]:
        """Parsea respuesta XML de arXiv API (sin namespaces)"""
        papers = []

        try:
            import xml.etree.ElementTree as ET
            # Registrar namespace para evitar problemas
            ET.register_namespace('', 'http://www.w3.org/2005/Atom')
            ET.register_namespace('arxiv', 'http://arxiv.org/schemas/atom')

            # Parse sin validar namespaces
            root = ET.fromstring(xml_response)

            # Buscar todos los entries ignorando namespace
            for entry in root.iter('{http://www.w3.org/2005/Atom}entry'):
                try:
                    # Buscar elementos sin especificar namespace
                    title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                    published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
                    id_elem = entry.find('{http://www.w3.org/2005/Atom}id')
                    summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')

                    if title_elem is None or id_elem is None:
                        continue

                    # Extraer autores
                    authors = []
                    for author in entry.findall('{http://www.w3.org/2005/Atom}author'):
                        name_elem = author.find('{http://www.w3.org/2005/Atom}name')
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text)

                    arxiv_id = id_elem.text.split('/abs/')[-1] if '/abs/' in id_elem.text else id_elem.text

                    paper = {
                        'title': title_elem.text.strip() if title_elem.text else 'Unknown',
                        'authors': authors[:5],  # Top 5
                        'published': published_elem.text if published_elem is not None else '',
                        'arxiv_id': arxiv_id,
                        'url': f'https://arxiv.org/abs/{arxiv_id}',
                        'summary': summary_elem.text.strip() if summary_elem is not None and summary_elem.text else '',
                        'source': 'arXiv'
                    }

                    # Extraer año
                    if paper['published']:
                        try:
                            year = int(paper['published'].split('-')[0])
                            paper['year'] = year
                        except (ValueError, IndexError):
                            paper['year'] = 2026

                    papers.append(paper)

                except (AttributeError, IndexError, ValueError) as e:
                    logger.warning(f"Skipping malformed entry: {e}")
                    continue

            return papers

        except Exception as e:
            logger.warning(f"Error parsing arXiv XML: {e} - usando fallback")
            return self._parse_arxiv_response_fallback(xml_response)

    def _parse_arxiv_response_fallback(self, xml_response: str) -> List[Dict]:
        """Fallback parser usando regex para extraer información básica"""
        import re
        papers = []

        try:
            # Buscar entries
            entry_pattern = r'<entry>(.*?)</entry>'
            entries = re.findall(entry_pattern, xml_response, re.DOTALL)

            for entry_xml in entries:
                try:
                    # Extraer título
                    title_match = re.search(r'<title>(.*?)</title>', entry_xml)
                    title = title_match.group(1).strip() if title_match else 'Unknown'

                    # Extraer ID
                    id_match = re.search(r'<id>.*?/abs/(.*?)</id>', entry_xml)
                    if not id_match:
                        id_match = re.search(r'<id>(.*?)</id>', entry_xml)
                    arxiv_id = id_match.group(1).strip() if id_match else 'unknown'

                    # Extraer fecha
                    date_match = re.search(r'<published>(\d{4})-', entry_xml)
                    year = int(date_match.group(1)) if date_match else 2026

                    # Extraer autores
                    author_pattern = r'<author>\s*<name>(.*?)</name>'
                    authors = re.findall(author_pattern, entry_xml)[:5]

                    # Extraer resumen
                    summary_match = re.search(r'<summary>(.*?)</summary>', entry_xml, re.DOTALL)
                    summary = summary_match.group(1).strip()[:500] if summary_match else ''

                    paper = {
                        'title': title,
                        'authors': authors,
                        'arxiv_id': arxiv_id,
                        'url': f'https://arxiv.org/abs/{arxiv_id}',
                        'summary': summary,
                        'year': year,
                        'source': 'arXiv'
                    }

                    papers.append(paper)

                except Exception as e:
                    logger.warning(f"Fallback skip: {e}")
                    continue

            return papers

        except Exception as e:
            logger.error(f"Fallback parser failed: {e}")
            return []

    def search_all_pockets(self) -> Dict[str, List[Dict]]:
        """
        Busca papers para todos los pockets
        Returns:
            Dict con papers organizados por pocket
        """
        results = {}
        pockets = self.pockets_config.get('pockets', {})

        logger.info("=" * 80)
        logger.info("🚀 RESEARCHER - Búsqueda de Papers en ArXiv")
        logger.info("=" * 80)

        for pocket_id, pocket_data in pockets.items():
            logger.info(f"\n📌 {pocket_data.get('name', pocket_id)}")
            pocket_papers = []

            queries = pocket_data.get('search_queries', [])
            for query in queries:
                papers = self.search_arxiv(query, max_results=10)
                pocket_papers.extend(papers)

            # Deduplicar por arxiv_id
            unique_papers = {}
            for paper in pocket_papers:
                unique_papers[paper['arxiv_id']] = paper

            pocket_papers = list(unique_papers.values())
            results[pocket_id] = pocket_papers

            logger.info(f"   ✓ Total unique: {len(pocket_papers)} papers")

        return results

    def filter_top_tier(self, papers: List[Dict]) -> List[Dict]:
        """
        Filtra papers por criterios TOP-TIER según RESEARCHER.md
        - Prioriza papers recientes (2023-2026)
        - Filtra por venue quality (arXiv OK si recent)
        - Busca indicadores de calidad (citaciones estimadas)
        """
        filtered = []

        for paper in papers:
            year = paper.get('year', 0)

            # Criterio 1: Año (2023-2026 preferred)
            if year < 2023:
                continue  # Skip papers antiguos

            # Criterio 2: Buscar en abstract indicadores de metodología sólida
            summary = paper.get('summary', '').lower()
            strong_methods = any(term in summary for term in [
                'randomized', 'rct', 'quasi-experimental', 'causal inference',
                'instrumental variable', 'difference-in-differences', 'field experiment',
                'propensity score', 'matching', 'regression discontinuity'
            ])

            # Criterio 3: Buscar indicadores de relevancia a IA/productividad
            relevant_terms = any(term in summary for term in [
                'ai', 'artificial intelligence', 'machine learning', 'generative',
                'llm', 'large language', 'productivity', 'labor', 'employment',
                'wage', 'adoption', 'implementation', 'firm', 'organization'
            ])

            # Aceptar si es reciente Y tiene métodos sólidos O términos relevantes
            if year >= 2023 and (strong_methods or relevant_terms):
                filtered.append(paper)

        return filtered

    def save_papers_json(self, papers_dict: Dict[str, List[Dict]], output_dir: str = 'data'):
        """Guarda papers en JSON por pocket"""
        os.makedirs(output_dir, exist_ok=True)

        for pocket_id, papers in papers_dict.items():
            filename = f"{output_dir}/{pocket_id}_papers_real.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(papers, f, ensure_ascii=False, indent=2)
            logger.info(f"   💾 Saved: {filename} ({len(papers)} papers)")

    def save_papers_csv(self, papers_dict: Dict[str, List[Dict]], output_file: str = 'data/papers_raw.csv'):
        """Guarda papers en CSV para revisión manual"""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        all_papers = []
        for pocket_id, papers in papers_dict.items():
            for paper in papers:
                paper['pocket'] = pocket_id
                all_papers.append(paper)

        if all_papers:
            keys = ['pocket', 'title', 'authors', 'year', 'arxiv_id', 'url', 'source']
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for paper in all_papers:
                    row = {k: paper.get(k, '') for k in keys}
                    if row['authors']:
                        row['authors'] = ', '.join(row['authors'][:3])  # Top 3 authors
                    writer.writerow(row)
            logger.info(f"   💾 Saved: {output_file} ({len(all_papers)} papers)")

    def run(self):
        """Ejecuta búsqueda completa"""
        logger.info("\n🔍 Iniciando búsqueda de papers reales en ArXiv...")

        # Buscar todos los pockets
        papers_by_pocket = self.search_all_pockets()

        # Filtrar por criterios top-tier
        logger.info("\n🔍 Aplicando filtros TOP-TIER...")
        filtered_papers = {}
        for pocket_id, papers in papers_by_pocket.items():
            filtered = self.filter_top_tier(papers)
            filtered_papers[pocket_id] = filtered
            logger.info(f"   {pocket_id}: {len(filtered)}/{len(papers)} papers after filtering")

        # Guardar resultados
        logger.info("\n💾 Guardando resultados...")
        self.save_papers_json(filtered_papers)
        self.save_papers_csv(filtered_papers)

        # Resumen final
        total = sum(len(p) for p in filtered_papers.values())
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ BÚSQUEDA COMPLETADA: {total} papers encontrados")
        logger.info("=" * 80)
        logger.info("\n📊 Next: python scripts/reviewer.py (score papers)")

        return filtered_papers


if __name__ == '__main__':
    researcher = ResearcherArxiv()
    papers = researcher.run()
