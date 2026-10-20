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

- **Language**: Python 3.12+
- **Framework**: FastAPI
- **AI/Orchestration**: LangChain + LangGraph
- **LLM**: OpenAI GPT-4o-mini (swappable to Ollama)
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
│   │   │   └── recommend.py       # Recommendation endpoint
│   │   └── deps.py                # API dependencies
│   ├── core/
│   │   ├── database.py            # Async SQLAlchemy setup
│   │   ├── llm.py                 # LLM client configuration
│   │   └── scoring.py             # Deterministic scoring engine
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── db_models.py           # SQLAlchemy models
│   ├── services/
│   │   └── movie_service.py       # Business logic
│   ├── workflow/
│   │   ├── graph.py               # LangGraph workflow
│   │   ├── nodes/                 # Workflow nodes
│   │   └── state.py               # Workflow state
│   ├── config.py                  # App configuration
│   └── main.py                    # FastAPI app
├── tests/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Development Setup

### Prerequisites

- Python 3.12+
- Docker & docker-compose
- (Optional) OpenAI API key for LLM features

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

## Development Phases

### ✅ Phase 1: Project Skeleton (Current)
- [x] Project structure
- [x] FastAPI app with `/health`
- [x] Docker + docker-compose
- [x] Basic tests
- [x] Configuration with pydantic-settings

### 🚧 Phase 2: Deterministic Scoring Engine
- [ ] Pydantic models (MoodAnswers, Film, Recommendation)
- [ ] `/api/v1/recommend` endpoint
- [ ] Scoring based on era + genre affinity + energy/company weights
- [ ] Anti-hallucination: validate slug ∈ pool
- [ ] Tests with sample pools

### ⏳ Phase 3: LLM Integration
- [ ] LangChain + OpenAI structured output
- [ ] `extract_preferences` node with LLM
- [ ] `final_recommendation` node with LLM
- [ ] Fallback to deterministic engine on LLM failure
- [ ] Tests with mocked LLM

### ⏳ Phase 4: Complete LangGraph Workflow
- [ ] Full graph with 4 nodes
- [ ] Typed workflow state
- [ ] End-to-end integration
- [ ] Metrics (latency, pool_size, eligible_count)

### ⏳ Phase 5: Pool Enrichment (Optional)
- [ ] Scrape genres/synopsis from Letterboxd
- [ ] Store in PostgreSQL + pgvector
- [ ] Semantic search for improved scoring

### ⏳ Phase 6: Mobile App Integration
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
| `OPENAI_API_KEY` | `""` | OpenAI API key (required for LLM features) |
| `LLM_PROVIDER` | `openai` | LLM provider (openai/ollama) |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |

## License

See the main [RandomBoxd repository](https://github.com/nacchofer31/randomboxd) for license information.

## Related Projects

- [RandomBoxd Mobile App](https://github.com/nacchofer31/randomboxd) - KMP Android/iOS app

## Author

[nacchofer31](https://github.com/nacchofer31)
