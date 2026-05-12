# Connectors — BID-IA Literature Review Agent

Each connector in `scripts/agent.py` is a self-contained function that fetches papers from one source
and returns them in the canonical contract format. If the source is unavailable or its key is missing,
it returns an empty list (with a WARNING log) — it never raises an exception.

---

## Canonical paper contract

All connectors return a list of objects with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `title` | str | Paper title |
| `authors` | str | Author names, up to 4 then "et al." |
| `year` | int \| null | Publication year |
| `abstract` | str | Abstract text |
| `url` | str | Best available URL (OA PDF > DOI > landing page) |
| `doi` | str | Raw DOI string (may be empty) |
| `full_text_url` | str | Direct PDF link if available |
| `venue` | str | Journal or series name |
| `citations` | int \| null | Citation count if available |
| `source` | str | Connector identifier (e.g. `"nber"`) |

---

## Connectors

### semantic_scholar
- **Endpoint**: `https://api.semanticscholar.org/graph/v1/paper/search`
- **Auth**: None required (100 req/min unauthenticated)
- **Rate limit**: 100 req/min; backs off 10s on 429
- **Good for**: Broad coverage — ArXiv, journals, working papers; CS/interdisciplinary
- **Activate**: Always available; pass `source="semantic_scholar"` to `search_papers`

### nber
- **Endpoint**: `https://www.nber.org/api/v1/working_paper/search`
- **Auth**: None
- **Rate limit**: ~30 results per request; be polite
- **Good for**: Economics working papers — Autor, Acemoglu, Brynjolfsson, Humlum
- **Activate**: `source="nber"`

### openalex
- **Endpoint**: `https://api.openalex.org/works`
- **Auth**: None (100k req/day; add email in User-Agent for higher limits)
- **Rate limit**: 100k req/day unauthenticated
- **Good for**: 240M works; best citation counts; journals + social science
- **Activate**: `source="openalex"`

### arxiv
- **Endpoint**: `http://export.arxiv.org/api/query`
- **Auth**: None
- **Rate limit**: 3 req/sec; use sparingly for very recent papers
- **Good for**: CS/AI preprints 2024–2026; papers not yet in journals
- **Activate**: `source="arxiv"`

### ssrn
- **Endpoint**: `https://api.ssrn.com/content/latest/search`
- **Auth**: `X-ELS-APIKey` header — set `ssrn_api_key` in `config.json` or `SSRN_API_KEY` env var
- **Rate limit**: Depends on Elsevier plan
- **Good for**: Economics, finance, and social science preprints
- **Activate**: Set API key; pass `source="ssrn"`. Skips silently without key.

### pubmed
- **Endpoint**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` (esearch + efetch)
- **Auth**: Optional — set `ncbi_api_key` / `NCBI_API_KEY` for 10 req/sec (vs 3 without)
- **Rate limit**: 3 req/sec without key; 10 req/sec with key
- **Good for**: Biomedical / occupational health / wellbeing papers
- **Activate**: `source="pubmed"`. **Automatically skipped** unless the active pocket has keywords
  overlapping `{health, wellbeing, burnout, stress, mental, ...}`. See `_HEALTH_KEYWORDS` in agent.py.

### core
- **Endpoint**: `https://api.core.ac.uk/v3/search/works`
- **Auth**: Bearer token — set `core_api_key` / `CORE_API_KEY`
- **Rate limit**: Depends on plan (free tier available at core.ac.uk)
- **Good for**: Open access full text; fallback when other sources lack PDFs
- **Activate**: Set API key; pass `source="core"`. Skips silently without key.

### worldbank
- **Endpoint**: `https://search.worldbank.org/api/v2/wds`
- **Auth**: None
- **Rate limit**: Reasonable; no documented limit
- **Good for**: World Bank working papers on development economics, labor markets, LATAM
- **Activate**: `source="worldbank"`. Always available.

### imf
- **Endpoint**: `https://www.elibrary.imf.org/api/search`
- **Auth**: `apikey` query param — set `imf_api_key` / `IMF_API_KEY`
- **Rate limit**: Depends on IMF plan
- **Good for**: IMF working papers on macro, finance, fiscal policy
- **Activate**: Set API key; pass `source="imf"`. Skips silently without key.

---

## Crossref enrichment (`enrich_metadata` tool)

- **Endpoint**: `https://api.crossref.org/works/{doi}`
- **Auth**: None — but add `mailto:` in User-Agent to get into the "polite pool" (faster)
- **Rate limit**: ~50 req/s in polite pool
- **Adds**: canonical DOI, journal name, ISSN, formal citation count, publication date, ORCID
- **Call timing**: After `search_papers`, before `review_papers_with_ai`

---

## Search cache

Results are cached in `search_cache.json` at the repo root.
- **Key**: SHA256 of `(pocket, source, query, limit, year_start)`
- **TTL**: `search_cache_ttl_hours` in `config.json` (default: 24h)
- **Invalidate**: Delete `search_cache.json` or change the query params

---

## Adding a new connector

1. Write `_search_newname(query, limit, ...) -> list` following the contract above
2. Add `"newname"` to `_ALL_SOURCES` in agent.py
3. Add a `lambda` branch in the `source_fns` dict inside `execute_tool`
4. Update the `search_papers` tool description
5. Add a test in `tests/test_connectors.py`
6. Document it here