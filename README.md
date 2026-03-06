# Football RAG Intelligence

[Streamlit App](https://football-rag-intelligence-wcib5jk9shbywatdgaeeya.streamlit.app/) | [Hugging Face Spaces](https://huggingface.co/spaces)

A self-hosted data platform that turns match event data into natural language. Browse Eredivisie 2025-26 teams and matches, and get AI-powered tactical reports grounded in real event data, built for analysts and scouts who need fast, reliable post-match insights without tab-switching.

## The Problem
After a match, coaches, scouts, and analysts bounce between WhoScored, FotMob, and spreadsheets to reconstruct what happened. Generic LLMs often fabricate statistics instead of retrieving them:

- "PSV dominated possession" (actual: 45%)
- "Heracles created few chances" (actual: 24 shots)
- Tactical commentary with no grounding in real data

This project fixes that. A production RAG pipeline retrieves real match metrics (xG, PPDA, progressive passes, field tilt, compactness) from a live data warehouse and feeds them to an LLM that writes from numbers, not around them. The result is scout-style reports in seconds, grounded in event data, with full traceability from query to source.

## Status
- Phase 1-4a complete
- UI v1.5 deployed on Streamlit Cloud

### Completed Milestones
1. Data pipeline: 412 matches, 279k events, dbt + MotherDuck + CI
2. RAG engine: DuckDB VSS retrieval, Opik tracing, multi-path routing
3. Evaluation locked: retrieval_accuracy=1.0, tactical_insight=0.91, answer_relevance=0.84
4. Streamlit UI v1.5: Team -> Match -> Report workflow on Streamlit Cloud
5. Hybrid pipeline automation: scrape -> dbt -> embed -> HF deploy via Dagster sensors

## Results
| Metric | Value | Meaning |
|---|---:|---|
| Retrieval Accuracy | 1.0000 (10/10) | Every query returns the correct match (Recall@1) |
| Tactical Insight | 0.9142 | Domain judge validates grounding + specificity + terminology |
| Answer Relevance | 0.8380 | LLM output remains on-topic to user query |
| Pipeline Coverage | 205/205 (100%) | All Eredivisie 2025-26 matches in schema |
| Latency (local) | ~1.5s | Query embed + VSS + LLM response |
| Data Freshness | Mon/Thu 7am UTC | GitHub Actions dbt run (CI integrated) |
| Tests | 57 passing, 0 failing | End-to-end pipeline + RAG + observability |

Baseline: 10 tactical analysis test cases evaluated via `opik.evaluate()`, all metrics locked in production.

## Architecture

```text
DATA COLLECTION (local)
WhoScored + FotMob -> Playwright/SSR extractors -> Dagster assets

STORAGE
MinIO (raw JSON) -> DuckDB (bronze/silver) -> MotherDuck (cloud sync)

TRANSFORMATION
dbt Core: bronze -> silver_events -> gold_match_summaries

EMBEDDINGS
gold summaries -> all-mpnet-base-v2 -> DuckDB VSS (HNSW)

RAG ENGINE
query router -> semantic retrieval or viz path -> LLM generation

OBSERVABILITY
Opik traces + EDD scorers (retrieval_accuracy, tactical_insight, answer_relevance)

UI
Streamlit Cloud, three-panel workflow: Team -> Match -> Report
```

## Tech Stack
| Layer | Tool | Notes |
|---|---|---|
| Language | Python 3.12 via uv | |
| Orchestration | Dagster | Assets, schedules, sensors |
| Object Storage | MinIO | Bronze JSON |
| Analytics DB | DuckDB + MotherDuck | Local + cloud SQL parity |
| Transformation | dbt Core (dbt-duckdb) | Versioned + tested models |
| Embeddings | sentence-transformers/all-mpnet-base-v2 | 768-dim semantic vectors |
| Vector Search | DuckDB VSS (`array_distance`) | No external vector DB |
| LLM (default) | Cerebras llama3.1-8b | ~1s inference, free tier |
| Frontend | Streamlit Cloud | Auto deploy on push |
| CI/CD | GitHub Actions | dbt production runs |
| Observability | Opik | End-to-end tracing + EDD |

## LLM Providers
| Provider | Model | Notes |
|---|---|---|
| Cerebras (default) | llama3.1-8b | Free tier, no key required for app users |
| Anthropic | claude-sonnet-4-6 | BYOK |
| OpenAI | gpt-4o-mini | BYOK |
| Google | gemini-1.5-flash | BYOK |

## Data Coverage
- League: Eredivisie 2025-26
- Matches: 205 (100% coverage)
- Events: 279,104 tactical events
- Metrics: 24 tactical metrics per team per match
- Embeddings: 205 summary vectors (HNSW indexed)
- Sources: WhoScored + FotMob (cross-linked by match mapping)

## Visualizations
| Type | What it shows |
|---|---|
| Dashboard | Full 3x3 match report |
| Passing Network | Player positions + connection strengths |
| Defensive Heatmap | Defensive action density + compactness |
| Progressive Passes | Forward pass zones and trajectories |
| Shot Map | Team shots by type and xG |
| xT Momentum | Match flow over time (expected threat) |

## Project Structure
```text
football-rag-intelligence/
+-- orchestration/
+-- dbt_project/
+-- src/football_rag/
+-- data/
+-- scripts/
+-- tests/
+-- docs/assets/
+-- .streamlit/config.toml
+-- ARCHITECTURE.md
+-- SCRATCHPAD.md
+-- CLAUDE.md
```

## Quick Start
```bash
git clone https://github.com/ricardoherediaj/football-rag-intelligence
cd football-rag-intelligence
uv sync

# Run dbt transformations (local)
cd dbt_project && uv run dbt run

# Run dbt against MotherDuck (cloud)
MOTHERDUCK_TOKEN=<token> uv run dbt run --target prod

# Start Dagster UI
uv run dagster dev

# Verify vector search
uv run python scripts/test_vector_search.py

# Run tests
uv run pytest
```

## Pipeline Status
| Layer | Status | Details |
|---|---|---|
| Data Collection | Live | WhoScored + FotMob scrapers, 412 raw matches |
| Match Mapping | Live | 205/205 mapped |
| dbt Silver | Live | 279,104 events, CI passing |
| dbt Gold | Live | 205 summaries, 24 metrics/match |
| Embeddings | Live | 205 vectors in DuckDB |
| RAG Engine | Done | VSS retrieval + routing + tracing |
| EDD Evaluation | Done | 3 scorers + locked baselines |
| Streamlit UI | Done | v1.5 deployed |
| Pipeline Automation | Done | Sensor chain scrape -> transform -> deploy |
| Extended Inference | Planned | More OSS providers + CI evaluation |

## Roadmap
### Phase 1 - Data Pipeline (Complete)
- Bronze/Silver/Gold medallion pipeline
- 205 matches with 24 tactical metrics each
- MotherDuck sync + CI/CD runs

### Phase 2 - RAG Engine (Complete)
- DuckDB VSS retrieval
- Intent router (semantic vs visualization)
- `orchestrator.query()` as single entry point
- Multi-provider LLM support

### Phase 3a - Observability (Complete)
- `@opik.track` across orchestrator -> pipeline -> generation
- EDD harness with 3 scorers and 21 tests
- Locked production baselines

### Phase 3b - Streamlit UI + Deploy (Complete)
- Three-panel drill-down UI
- Cerebras default + BYOK providers
- Deployed on Streamlit Cloud

### Phase 4a - Hybrid Pipeline Automation (Complete)
- Dagster sensor chain for full pipeline
- HF dataset upload of `lakehouse.duckdb`
- daemon auto-start and scheduled runs

### Phase 4b - Extended Inference (Planned)
- Additional OSS model providers
- EDD evaluation in CI
- Prompt versioning tied to eval scores

## Engineering Log
Build decisions and notes are documented in `docs/engineering_diary/`.

## License
MIT
