"""Unit tests for agent.py connectors and helpers.

Run with:  pytest tests/test_connectors.py -v
All HTTP calls are mocked — no API keys or network needed.
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from agent import (
    _cache_key,
    _deduplicate,
    _enrich_with_crossref,
    _evaluate_coverage,
    _pocket_has_health_keywords,
    _search_arxiv,
    _search_core,
    _search_nber,
    _search_openalex,
    _search_semantic_scholar,
    _search_ssrn,
    _search_worldbank,
    _title_similar,
    safe_execute_tool,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_papers():
    return [
        {
            "title": "AI and Worker Productivity: Evidence from RCTs",
            "authors": "Brynjolfsson, E., Li, D.",
            "year": 2023,
            "venue": "QJE",
            "abstract": "We study the effect of generative AI on worker output.",
            "url": "https://doi.org/10.1093/fake",
            "doi": "10.1093/fake",
            "source": "nber",
            "full_text_url": "https://nber.org/papers/fake.pdf",
            "citations": 120,
        },
        {
            "title": "Machine Learning in Labor Markets",
            "authors": "Autor, D., Salomons, A.",
            "year": 2022,
            "venue": "AER",
            "abstract": "We analyze skill-biased technological change.",
            "url": "",
            "doi": "",
            "source": "openalex",
            "full_text_url": "",
            "citations": 80,
        },
    ]


# ── safe_execute_tool ─────────────────────────────────────────────────────────

def test_safe_execute_tool_success():
    fn = MagicMock(return_value=[{"title": "test"}])
    result = safe_execute_tool(fn, tool_name="test_tool")
    assert result == [{"title": "test"}]
    fn.assert_called_once()


def test_safe_execute_tool_retries_then_returns_error():
    fn = MagicMock(side_effect=ConnectionError("timeout"))
    result = safe_execute_tool(fn, max_retries=2, backoff=0, tool_name="flaky_source")
    assert isinstance(result, list)
    assert result[0]["error"] is True
    assert result[0]["tool"] == "flaky_source"
    assert fn.call_count == 2


def test_safe_execute_tool_succeeds_on_second_attempt():
    fn = MagicMock(side_effect=[ConnectionError("first fail"), [{"title": "ok"}]])
    result = safe_execute_tool(fn, max_retries=3, backoff=0, tool_name="flaky")
    assert result == [{"title": "ok"}]
    assert fn.call_count == 2


# ── _title_similar ────────────────────────────────────────────────────────────

def test_title_similar_exact():
    assert _title_similar("AI and Worker Productivity", "AI and Worker Productivity") is True


def test_title_similar_stopword_difference():
    assert _title_similar(
        "The Effect of AI on Worker Productivity",
        "Effect of AI on Worker Productivity",
    ) is True


def test_title_similar_different():
    assert _title_similar(
        "AI and Worker Productivity",
        "Labor Market Polarization and Robots",
    ) is False


# ── _deduplicate ──────────────────────────────────────────────────────────────

def test_deduplicate_by_doi(sample_papers):
    dup = {**sample_papers[0], "source": "arxiv", "title": "AI and Worker Productivity (v2)"}
    papers = sample_papers + [dup]
    deduped, log = _deduplicate(papers)
    assert len(deduped) == 2  # doi match removes dup
    assert sum(log.values()) == 1


def test_deduplicate_by_title_similarity():
    papers = [
        {"title": "Effect of AI on Productivity", "doi": "", "authors": "Smith J", "year": 2023, "source": "nber"},
        {"title": "The Effect of AI on Productivity", "doi": "", "authors": "Smith J", "year": 2023, "source": "arxiv"},
    ]
    deduped, log = _deduplicate(papers)
    assert len(deduped) == 1
    assert sum(log.values()) == 1


def test_deduplicate_by_author_year():
    # Same first-author last name + same year → treated as potential dup by fallback rule
    papers = [
        {"title": "Paper A on Generative AI Tools", "doi": "", "authors": "Jones, B., Smith, C.", "year": 2024, "source": "nber"},
        {"title": "Paper B on Generative AI Tools", "doi": "", "authors": "Jones, D. et al.", "year": 2024, "source": "ssrn"},
    ]
    deduped, log = _deduplicate(papers)
    # Titles are too different for title-match, but first author "jones" + year 2024 triggers fallback
    # Expected: 1 kept (second removed as dup)
    assert len(deduped) == 1
    assert sum(log.values()) == 1


def test_deduplicate_no_duplicates(sample_papers):
    deduped, log = _deduplicate(sample_papers)
    assert len(deduped) == len(sample_papers)
    assert sum(log.values()) == 0


# ── _evaluate_coverage ────────────────────────────────────────────────────────

def test_evaluate_coverage_empty():
    result = _evaluate_coverage([], "labor")
    assert result["score"] == 0.0


def test_evaluate_coverage_good(sample_papers):
    papers = sample_papers * 12  # 24 papers
    # Add source diversity
    for i, p in enumerate(papers):
        p = {**p, "source": ["nber", "arxiv", "openalex"][i % 3]}
        papers[i] = p
    result = _evaluate_coverage(papers, "labor")
    assert result["score"] >= 0.6
    assert result["needs_more"] is False


def test_evaluate_coverage_needs_more():
    papers = [{"title": f"Paper {i}", "year": 2023, "source": "nber", "full_text_url": ""}
              for i in range(5)]
    result = _evaluate_coverage(papers, "labor")
    assert result["score"] < 0.6
    assert result["needs_more"] is True


# ── _pocket_has_health_keywords ───────────────────────────────────────────────

def test_pocket_health_keywords_false():
    # All our pockets are about econ/AI, not health
    assert _pocket_has_health_keywords("labor") is False


def test_pocket_health_keywords_true(monkeypatch):
    import agent as ag
    monkeypatch.setitem(ag.POCKETS, "_test_health", {"keywords": ["burnout", "mental health", "AI"]})
    assert _pocket_has_health_keywords("_test_health") is True


# ── _cache_key ────────────────────────────────────────────────────────────────

def test_cache_key_deterministic():
    k1 = _cache_key("labor", "nber", "AI productivity")
    k2 = _cache_key("labor", "nber", "AI productivity")
    assert k1 == k2


def test_cache_key_different_query():
    k1 = _cache_key("labor", "nber", "AI productivity")
    k2 = _cache_key("labor", "nber", "labor displacement")
    assert k1 != k2


# ── Search connectors (mocked HTTP) ──────────────────────────────────────────

class MockResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.content = b""

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_search_semantic_scholar_returns_normalized():
    mock_data = {
        "data": [{
            "title": "Test Paper",
            "abstract": "An abstract.",
            "authors": [{"name": "Smith, J."}],
            "year": 2023,
            "venue": "Nature",
            "citationCount": 50,
            "externalIds": {"DOI": "10.1234/test"},
            "openAccessPdf": {"url": "https://example.com/test.pdf"},
        }]
    }
    with patch("requests.get", return_value=MockResponse(mock_data)):
        results = _search_semantic_scholar("AI productivity", 10, 2020)
    assert len(results) == 1
    assert results[0]["title"] == "Test Paper"
    assert results[0]["doi"] == "10.1234/test"
    assert results[0]["source"] == "semantic_scholar"


def test_search_nber_returns_normalized():
    mock_data = {
        "results": [{
            "title": "AI and Wages",
            "abstract": "We study wages.",
            "authors": [{"first_name": "David", "last_name": "Autor"}],
            "pubDate": "2023-01-01",
            "url": "/papers/w12345",
        }]
    }
    with patch("requests.get", return_value=MockResponse(mock_data)):
        results = _search_nber("AI wages", 10)
    assert len(results) == 1
    assert results[0]["source"] == "nber"
    assert results[0]["year"] == 2023


def test_search_openalex_reconstructs_abstract():
    mock_data = {
        "results": [{
            "title": "AI Paper",
            "abstract_inverted_index": {"AI": [0], "affects": [1], "workers": [2]},
            "authorships": [{"author": {"display_name": "Jones, A."}}],
            "publication_year": 2024,
            "primary_location": {"source": {"display_name": "AER"}},
            "cited_by_count": 30,
            "doi": "10.1111/test",
            "open_access": {"oa_url": ""},
        }]
    }
    with patch("requests.get", return_value=MockResponse(mock_data)):
        results = _search_openalex("AI workers", 10, 2020)
    assert len(results) == 1
    assert "AI" in results[0]["abstract"]


def test_search_ssrn_skips_without_key(monkeypatch):
    monkeypatch.setenv("SSRN_API_KEY", "")
    import agent as ag
    monkeypatch.setitem(ag.CONFIG.get("api_keys", {}), "ssrn_api_key", "")
    results = _search_ssrn("AI", 10)
    assert results == []


def test_search_worldbank_returns_normalized():
    mock_data = {
        "documents": {
            "total": 1,
            "doc1": {
                "display_title": "World Bank AI Paper",
                "authr": ["John Smith"],
                "docdt": "2023-05-01",
                "abstract": "Development context.",
                "url": "https://openknowledge.worldbank.org/fake",
                "doi": "",
                "pdfurl": "",
            }
        }
    }
    with patch("requests.get", return_value=MockResponse(mock_data)):
        results = _search_worldbank("AI labor", 10)
    assert any(r["title"] == "World Bank AI Paper" for r in results)


def test_search_core_skips_without_key(monkeypatch):
    monkeypatch.setenv("CORE_API_KEY", "")
    results = _search_core("AI", 10)
    assert results == []


# ── _enrich_with_crossref ─────────────────────────────────────────────────────

def test_enrich_with_crossref_adds_fields():
    mock_cr = {
        "message": {
            "container-title": ["Quarterly Journal of Economics"],
            "ISSN": ["0033-5533"],
            "is-referenced-by-count": 200,
            "published": {"date-parts": [[2023, 3, 1]]},
            "author": [
                {"given": "Erik", "family": "Brynjolfsson", "ORCID": "https://orcid.org/0000-0001-fake"},
            ],
        }
    }
    paper = {"title": "Test", "doi": "10.1093/qje/fake", "authors": "Brynjolfsson", "source": "nber"}
    with patch("requests.get", return_value=MockResponse(mock_cr)):
        result = _enrich_with_crossref([paper])
    assert result[0]["journal"] == "Quarterly Journal of Economics"
    assert result[0]["citations"] == 200
    assert result[0]["formal_year"] == 2023
    assert "0000-0001-fake" in result[0]["authors_normalized"]


def test_enrich_with_crossref_skips_no_doi():
    paper = {"title": "No DOI Paper", "doi": "", "source": "arxiv"}
    with patch("requests.get") as mock_get:
        result = _enrich_with_crossref([paper])
    mock_get.assert_not_called()
    assert result[0]["title"] == "No DOI Paper"