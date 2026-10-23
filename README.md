# RandomBoxd Backend

AI-powered movie recommender backend for the [RandomBoxd](https://github.com/nacchofer31/randomboxd) mobile app.

## Overview

This backend receives:
1. A **mood form** from the user (era, genre, energy, company preferences)
2. A **movie pool** (watchlist scraped from Letterboxd by the mobile app)

And returns **ONE validated recommendation** with structured, localizable output (no free-text to maintain 13-language support).

### Key Features

- **Anti-hallucination**: Recommends only films from the provided pool (validates slug ∈ pool)
- **Hybrid scoring**: Deterministic engine (always available) + optional LLM layer for "AI flavor"
- **Structured output**: Returns enum tags + template keys for client-side localization
- **Fallback-first**: LLM failures gracefully fall back to deterministic scoring

## Tech Stack

- **Language**: Python 3.14+
- **Framework**: FastAPI
- **AI/Orchestration**: LangChain + LangGraph
- **LLM Providers**: OpenAI, Google Gemini, Anthropic Claude, OpenRouter, Ollama (local)
- **Database**: PostgreSQL + pgvector
- **ORM**: SQLAlchemy 2.0+ (async)
- **Serialization**: Pydantic v2
- **Containerization**: Docker + docker-compose
- **Testing**: pytest + httpx
- **Linting**: ruff

## Project Structure

```
randomboxd-backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── health.py          # Health check endpoint
│   │   │   ├── recommend.py       # Recommendation endpoint
│   │   │   └── enrich.py          # Pool enrichment endpoint (Phase 4)
│   │   └── deps.py                # API dependencies
│   ├── core/
│   │   ├── database.py            # Async SQLAlchemy setup
│   │   ├── llm.py                 # LLM client configuration
│   │   ├── scoring.py             # Deterministic scoring engine
│   │   └── letterboxd_scraper.py  # Letterboxd scraper (Phase 4)
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── db_models.py           # SQLAlchemy models (includes FilmEnriched)
│   ├── services/
│   │   ├── movie_service.py       # Business logic
│   │   └── enrichment_service.py  # Pool enrichment service (Phase 4)
│   ├── workflow/
│   │   ├── graph.py               # LangGraph workflow
│   │   ├── nodes/                 # Workflow nodes
│   │   └── state.py               # Workflow state
│   ├── config.py                  # App configuration
│   └── main.py                    # FastAPI app
├── tests/
│   ├── test_health.py             # Health endpoint tests
│   ├── test_recommend.py          # Recommendation tests (Phase 2)
│   ├── test_phase3.py             # LLM integration tests (Phase 3)
│   └── test_enrichment.py         # Enrichment tests (Phase 4)
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Development Setup

### Prerequisites

- Python 3.14+
- Docker & docker-compose
- (Optional) API key for any LLM provider:
  - OpenAI (`OPENAI_API_KEY`)
  - Google Gemini (`GOOGLE_API_KEY`)
  - Anthropic Claude (`ANTHROPIC_API_KEY`)
  - OpenRouter (`OPENROUTER_API_KEY`)
  - Ollama (local, no key needed)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd randomboxd-backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings (OpenAI API key, etc.)
   ```

5. **Run with Docker** (recommended):
   ```bash
   docker-compose up --build
   ```

   Or run locally:
   ```bash
   # Start PostgreSQL
   docker-compose up -d db
   
   # Run the app
   uvicorn app.main:app --reload
   ```

6. **Verify installation**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status": "ok"}
   ```

## API Endpoints

### Health Check

```http
GET /health
```

Returns: `{"status": "ok"}`

### Root

```http
GET /
```

Returns API information.

### Recommend Movie (Phase 2)

```http
POST /api/v1/recommend
```

**Request**:
```json
{
  "mood_answers": {
    "era": "MODERN",
    "genre": "SPECIFIC_ACTION",
    "energy": "HIGH",
    "company": "FRIENDS"
  },
  "movie_pool": [
    {
      "slug": "inception-2010",
      "name": "Inception",
      "releaseYear": 2010,
      "imageUrl": "https://..."
    }
  ],
  "pool_context": {
    "userNames": ["user1"],
    "searchMode": "UNION",
    "genres": ["action", "sci-fi"]
  }
}
```

**Response**:
```json
{
  "recommendation": {
    "film": {
      "slug": "mad-max-fury-road-2015",
      "name": "Mad Max: Fury Road",
      "releaseYear": 2015,
      "imageUrl": "https://..."
    },
    "reason_tags": ["ERA_RECENT", "ENERGY_HIGH", "COMPANY_FRIENDS"],
    "reason_template_key": "mood_reason_high_energy_recent",
    "confidence": 0.87,
    "user_profile_summary": "..."
  },
  "fallback_used": false,
  "metadata": {
    "pool_size": 127,
    "eligible_count": 23,
    "llm_model": "gpt-4o-mini",
    "latency_ms": 1432
  }
}
```

### Enrich Pool (Phase 4)

```http
POST /api/v1/enrich
```

Pre-enriches a pool of films with per-film genres from Letterboxd. This is optional — the `/recommend` endpoint automatically enriches when the database is available, but this endpoint allows you to warm the cache beforehand for faster recommendation latency.

**Request**:
```json
{
  "slugs": ["inception-2010", "mad-max-fury-road-2015"]
}
```

**Response**:
```json
{
  "enriched_count": 2,
  "total_count": 2,
  "results": {
    "inception-2010": ["action", "sci-fi", "thriller"],
    "mad-max-fury-road-2015": ["action", "adventure", "sci-fi"]
  }
}
```

**Notes**:
- Returns 503 if the database is unavailable (enrichment requires PostgreSQL)
- Films already in cache are returned immediately without scraping
- Only uncached films trigger Letterboxd scraping
- Results are cached in the database for future recommendations

## Development Phases

### ✅ Phase 1: Project Skeleton (Complete)
- [x] Project structure
- [x] FastAPI app with `/health`
- [x] Docker + docker-compose
- [x] Basic tests
- [x] Configuration with pydantic-settings

### ✅ Phase 2: Deterministic Scoring Engine (Complete)
- [x] Pydantic models (MoodAnswers, Film, Recommendation)
- [x] `/api/v1/recommend` endpoint
- [x] Scoring based on era + genre affinity + energy/company weights
- [x] Anti-hallucination: validate slug ∈ pool
- [x] Tests with sample pools (22 tests)
- [x] camelCase JSON API contract (matches mobile app)
- [x] Deterministic scoring (same input = same output)

### ✅ Phase 3: Multi-Provider LLM Integration (Complete)
- [x] LLM client factory supporting 5 providers (OpenAI, Gemini, Claude, OpenRouter, Ollama)
- [x] LangGraph workflow with 4 nodes (validate_pool, extract_preferences, score_movies, final_recommendation)
- [x] Conditional routing with error handling
- [x] Structured output support for LLM responses
- [x] Deterministic fallback when LLM is unavailable
- [x] Tests for LLM factory and workflow execution (9 new tests)
- [x] All 33 tests passing

### ✅ Phase 4: Pool Enrichment (Complete)
- [x] Letterboxd scraper for per-film genres
- [x] PostgreSQL caching with FilmEnriched model
- [x] Enrichment service with lazy enrichment
- [x] Enhanced scoring using per-film genres when available
- [x] `/api/v1/enrich` endpoint for pre-enrichment
- [x] Automatic enrichment in `/api/v1/recommend` when DB is available
- [x] Graceful degradation when DB is unavailable
- [x] Tests for enrichment service, scraper, and endpoints (8 new tests)
- [x] All 41 tests passing

### ⏳ Phase 5: Mobile App Integration
- [ ] Out of scope for backend (handled in mobile project)

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_health.py
```

## Linting

```bash
# Check code
ruff check .

# Format code
ruff format .

# Auto-fix issues
ruff check --fix .
```

## Architecture Decisions

### Why Deterministic Scoring First?

The movie pool has **weak signal** (only slug, name, year, imageUrl — no per-film genres, synopsis, runtime). The deterministic engine:
- Always works (no API dependencies)
- Provides a reliable fallback
- Is fast and cheap
- Handles edge cases gracefully

The LLM layer is optional and adds "AI flavor" when available.

### Anti-Hallucination Strategy

The backend **MUST** validate that the recommended film's slug exists in the input pool. If the LLM returns a slug not in the pool:
1. Reject the recommendation
2. Fall back to deterministic scoring
3. Return a valid film from the pool

### Structured Output (No Free-Text)

The mobile app supports 13 languages. The backend returns:
- `reason_tags`: Enum values like `"ERA_RECENT"`, `"ENERGY_HIGH"`
- `reason_template_key`: String resource key like `"mood_reason_high_energy_recent"`

The app renders the actual text using localized templates. This prevents untranslated content from breaking the i18n contract.

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment (development/production) |
| `DEBUG` | `true` | Enable debug mode |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `LLM_PROVIDER` | `openai` | LLM provider (openai/gemini/claude/openrouter/ollama) |
| `OPENAI_API_KEY` | `""` | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `GOOGLE_API_KEY` | `""` | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model to use |
| `ANTHROPIC_API_KEY` | `""` | Anthropic Claude API key |
| `CLAUDE_MODEL` | `claude-3-haiku-20240307` | Claude model to use |
| `OPENROUTER_API_KEY` | `""` | OpenRouter API key |
| `OPENROUTER_MODEL` | `anthropic/claude-3.5-sonnet` | OpenRouter model to use |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Ollama model to use |

## License

See the main [RandomBoxd repository](https://github.com/nacchofer31/randomboxd) for license information.

## Related Projects

- [RandomBoxd Mobile App](https://github.com/nacchofer31/randomboxd) - KMP Android/iOS app

## Author

[nacchofer31](https://github.com/nacchofer31)
