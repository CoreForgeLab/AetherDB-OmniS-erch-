[![中文](https://img.shields.io/badge/lang-中文-red.svg)](README_CN.md) [![English](https://img.shields.io/badge/lang-English-blue.svg)](README.md)

# Worldview Database Management System

A **FastAPI + SQLite**-based database system for managing worldbuilding (novel setting) data. Supports 8 entity types, relationship graphs, tag indexing, version history, timeline, semantic search, LLM-assisted import, data backup, and logging.

---
> **🔒 API Stability Commitment**
>
> Before version **v1.15.0**, this project commits to **no large-scale breaking changes**.
>
> - ✅ Existing API paths, request/response formats remain backward-compatible
> - ✅ Database schema will not undergo breaking migrations
> - ✅ Configuration items and key parameters remain compatible
> - ✅ New features are added in a backward-compatible manner
>
> Any necessary changes will be clearly documented in Release Notes with migration guides.
> *Starting from v1.15.0, breaking changes will follow semantic versioning (SemVer).*

---

## Quick Start

```bash
# 1. Clone
git clone <repo-url> && cd novel-world-db

# 2. Install dependencies
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# 3. Start the server
python main.py

# 4. Open browser
# Web UI: http://localhost:8000
# API docs: http://localhost:8000/docs
```

## Configuration

Copy `config.yaml` and modify as needed:

```yaml
extractor:
  backend: "openai_compatible"   # or "ollama"
  openai_compatible:
    api_base: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
```

API keys are set via environment variables (takes precedence over config file):

```bash
export ADMIN_API_KEY="your-admin-key"
export USER_API_KEY="your-user-key"
```

Detailed config reference: [config.yaml](config.yaml).

## What's New in v1.19.1

### 🐍 Environment Compatibility & Dependency Locking
- **Python 3.10 ~ 3.13** fully verified and supported
- All dependency versions are **pinned to exact versions** proven to work together
- Starlette `TemplateResponse` API compatibility fix (0.27.0 old-sig / 1.3.1+ new-sig)
- OpenAI SDK made **optional** (uncomment in `requirements.txt` when using LLM extraction)
- Added `httptools` (optional uvicorn HTTP parser accelerator)
- Comprehensive documentation in `requirements.txt` for troubleshooting

## V1.x Roadmap

| Version | Status | Key Features |
|---------|--------|--------------|
| v1.0.0Beta | ✅ Released | Initial: 8 entity types, CRUD, relations, tags, timeline |
| v1.15.0 | ✅ Released | Service layer, semantic search, consistency checker, vector store, rate limiter |
| v1.18.0 | ✅ Released | Logging system, backup API, route splitting, Alembic migrations |
| v1.19.1 | ✅ Current | Python 3.10-3.13 compat, dependency pinning, Starlette fix |
| v1.1.0 | ✅ Released (in v1.15.0) | Advanced RAG, sqlite-vec, hybrid search, consistency checking |
| v1.2.0 | 📅 Planned | Multi-language (entity_translations table, cross-language search) |
| v1.3.0 | 📅 Planned | Cache (diskcache), LLMProvider abstraction, D3.js knowledge graph |
| v2.0+ | 🔮 Future | FAISS/Qdrant vector DB, PostgreSQL, Docker deployment |

## Project Structure

```
├── main.py                          # Entry point (FastAPI)
├── routes/web.py                    # Web page routes
├── api/                             # API route modules
│   ├── backup.py                    #   Data backup API
│   ├── search_semantic.py           #   Semantic search
│   ├── rag_context.py               #   RAG context retrieval
│   └── consistency_check.py         #   Consistency checker
├── services/                        # Service layer
│   ├── logger.py                    #   Logging system
│   ├── db.py                        #   DB connection pool
│   ├── embedding.py                 #   Embedding service
│   ├── vector_store.py              #   Vector storage
│   ├── consistency.py               #   Consistency engine
│   ├── auth.py                      #   Authentication
│   └── rate_limiter.py              #   Rate limiter
├── app/dependencies/auth.py         # Auth dependency injection
├── extractors/                      # LLM entity extractors
│   ├── base.py                      #   Abstract base + JSON parsing
│   ├── openai_compatible.py         #   OpenAI-compatible backend
│   └── ollama.py                    #   Ollama backend
├── prompts/extract_entities.txt     # Extraction prompt template
├── templates/                       # Jinja2 frontend templates
│   ├── index.html                   #   Homepage
│   ├── add.html                     #   Add entity
│   ├── search.html                  #   Search
│   ├── timeline.html                #   Timeline
│   ├── admin.html                   #   Admin panel
│   └── import.html                  #   LLM import
├── static/style.css                 # Global styles
├── alembic/                         # Database migrations
├── scripts/                         # CLI tools
│   └── backup.py                    #   CLI backup tool
├── config.yaml                      # Config file example
├── requirements.txt                 # Python dependencies (pinned)
└── tests/                           # Unit tests
    ├── test_extractors.py           #   Extractor tests (9 cases)
    └── test_crud.py                 #   CRUD tests (13 cases)
```

## API Overview

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| POST | /api/entity | user | Create entity |
| GET | /api/entity/{id} | user | Get entity details |
| PUT | /api/entity/{id} | admin | Update entity |
| DELETE | /api/entity/{id} | admin | Soft-delete entity |
| POST | /api/search | user | Search entities |
| POST | /api/search/semantic | user | Semantic search (hybrid) |
| POST | /api/rag/context | user | RAG context retrieval |
| POST | /api/consistency/check | admin | Consistency check |
| POST | /api/import/preview | admin | LLM extraction preview |
| POST | /api/import/confirm | admin | Confirm import |
| POST | /api/backup/create | admin | Create data backup |
| GET | /api/backup/list | user | List backups |
| GET | /api/backup/stats | user | Backup statistics |
| POST | /api/backup/restore/{name} | admin | Restore from backup |
| POST | /api/backup/cleanup | admin | Clean old backups |
| GET | /api/backup/auto-backup | user | Check auto-backup status |
| POST | /api/backup/auto-backup | admin | Toggle auto-backup |
| GET | /api/logs/{log_type} | user | Read logs |
| GET | /api/logs/{log_type}/stats | user | Log statistics |
| GET | /api/stats | user | System statistics |

Authentication: `X-API-Key` header or `?api_key=` query parameter.

## Running Tests

```bash
python -m unittest discover tests -v
```

Coverage: Extractor JSON parsing boundaries, input sanitization, CRUD boundary conditions (null values, foreign key constraints, soft delete, version history).

## License

This project is licensed under the MIT License.