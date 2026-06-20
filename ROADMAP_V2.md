# Consolidated Roadmap v2.1 - FINAL

> Confirmed 2026-06-17. All decisions from full conversation audit captured.

## Locked Architecture Decisions

| Decision | Choice | Timeline |
|---|---|---|
| Vector DB | sqlite-vec V1.x -> FAISS/Qdrant V2.0 | V1.1 / V2.0 |
| Multi-language | entity_translations table (NOT JSON) | V1.2 |
| Consistency Checker | Rule engine + LLM supplement | V1.1 basic / V1.3 advanced |
| Embedding | Ollama (dev) -> OpenAI (prod) | V1.1 |
| LLM Interface | Abstract LLMProvider | V1.3 |
| Multi-Book | book_id V1.1; full hierarchy V1.5 | V1.1 / V1.5 |
| Cache | diskcache (zero-dep, file-based) | V1.3 |
| Open Source | Already live; external contributor wants integration | NOW |
| Hybrid Search Ratio | semantic 0.7 + keyword 0.3 (RRF merge) | V1.1 |
| API Stability | No breaking changes until V1.1.0 | NOW |

---

## V1.0 Patch - Immediate (Week 1)

**Constraint**: No breaking API changes.
- **Intranet/No-Domain**: All deployment targets must support zero-domain local operation. No hardcoded URLs or DNS dependencies.
- **Single-DB Multi-Book**: One database supports multiple books via book_id isolation.
- Security audit P0 fixes (XSS innerHTML removal, API Key Query -> Header, Admin Key from page source)
- Schema: add book_id to all 6 tables (entities, relations, tag_index, entity_versions, references_map, timeline_events)
- Fix missing API endpoints (/api/timeline, /api/search/quick, /api/import/preview, /api/import/confirm)
- Soft delete cascade cleanup
- Update CODEX_PROJECT_CONTEXT.md to reflect current roadmap

## V1.1.0 - Advanced RAG + Basic Consistency Checker (Week 2-5)

### Phase 1: Advanced RAG (Week 2-3)
- sqlite-vec integration + vector_chunks table
- Chunking pipeline (title/summary/content/tag chunks)
- EmbeddingProvider abstract interface (Ollama nomic-embed-text first)
- Auto-rebuild embeddings on entity create/update
- /api/search/semantic (hybrid: vector + FTS5 + tags, RRF merge)
- Upgrade /api/rag/context (entity + relation + timeline joint retrieval)
- Multi-book isolation: all queries filter by book_id

### Phase 2: Basic Consistency Checker (Week 4-5)
- Rule engine for deterministic checks
- /api/consistency/check endpoint
- 4 check types: timeline, character, rule, faction
- Book-aware: scope limited to same book_id
- Output: structured conflict reports with severity levels

---

---

## V1.1.5 - Security & Performance Iteration (Week 3-4)

**No breaking API changes**.

- **Connection Pool** (`services/db.py`) ? Thread-local SQLite connections with auto-reconnect
- **Rate Limiter** (`services/rate_limiter.py`) ? Sliding-window middleware (120 req/min per key)
- **Dual Auth** (`services/auth.py`) ? X-API-Key header + Query param fallback
- **SQL Injection Fix** ? ALLOWED_FIELDS whitelist in update_entity
- **LLM Extraction Module** (`extractors/base.py`, `extractors/ollama.py`, `extractors/openai_compatible.py`)
  - Robust JSON parsing (Markdown code blocks, trailing commas, single quotes)
  - `sanitize_input()` truncation + control char filtering
- **Prompt Injection Defense** (`prompts/extract_entities.txt`)
  - System prompt marked as ABSOLUTE BINDING
  - Explicit ignore-user-override instructions
- **Performance Fix** ? All 18 data endpoints `async def` to `def` (FastAPI thread pool)
  - Eliminates event loop blocking from synchronous sqlite3 calls
  - Thread-local connection pool works correctly per thread

## V1.2.0 - Multi-Language Architecture (Week 6-7)
- entity_translations table (entity_id, language, title, content)
- Migration script for existing single-language data
- Cross-language search
- Entity translation API endpoint
- Update EmbeddingProvider for multi-language (bge-m3)

## V1.3.0 - Infrastructure and Integration (Week 8-10)
- Cache: diskcache (zero-dep, file-based, no Redis needed)
- Consistency Checker Phase 2: history-aware, cross-entity deep checks
- LLMProvider abstract interface (OpenAI, DeepSeek, Claude, Gemini, Ollama)
- D3.js Knowledge Graph force-directed graph page
- Complete CRUD endpoints coverage
- Deploy scripts: NSSM (Windows), systemd (Linux)

## V1.4.0 - Open Platform Polish (Week 11-12)
- README, CONTRIBUTING, LICENSE files
- Complete API documentation
- Plugin interface reservation

## V1.5.0 - Graph Layer and Full Hierarchy (Week 13-14)
- Neo4j compatibility layer for relation data
- Full hierarchy: Project -> Universe -> Series -> Book -> Entity
- Graph query API

## V2.0+ - Production and Simulation (Future)
- VectorIndex interface switch to FAISS/Qdrant
- PostgreSQL + object storage
- Docker deployment
- Redis full caching
- V3.0 timeline: State system, deduction engine, multi-agent

---

## V1.x Capabilities Mapping

| Capability | Version | Implementation |
|---|---|---|
| World Search | V1.1.0 | Semantic search API |
| World Context | V1.1.0 | RAG context upgrade |
| Timeline Builder | V1.0 + V1.1 | Fixes + RAG pipeline |
| Faction Analysis | V1.1.0 | Consistency Checker |
| Power Scaling | V2.0+ | Reserved for later |
| Consistency Check | V1.1 basic / V1.3 advanced | Rule engine + LLM |
| Knowledge Graph | V1.3.0 | D3.js visualization |

---

## Conflict Resolution Log

1. Consistency Checker -> V1.1.0 Phase 2 (basic) + V1.3.0 (advanced)
2. Knowledge Graph -> V1.3.0 (not V1.0 patch)
3. Multi-language -> entity_translations table (not JSON fields)
4. Server Deploy -> combined into V1.3.0
5. Vector DB -> sqlite-vec V1.x, FAISS/Qdrant V2.0
6. Cache -> diskcache (zero-dep) for V1.3.0
7. Schema depth -> book_id only for V1.1; full hierarchy V1.5
8. API Stability -> no breaking changes until V1.1.0

---
Confirmed 2026-06-17 | This replaces all prior versioning. All requirements from full conversation audit (37/37) covered.