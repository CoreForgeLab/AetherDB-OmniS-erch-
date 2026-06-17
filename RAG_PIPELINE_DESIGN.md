# RAG Pipeline Design: Worldview Database

> Revision 1.0 | 2026-06-17 | Target: Knowledge-Graph-Enhanced QA System

This document defines the end-to-end RAG pipeline that transforms
user questions into context-aware LLM responses using the worldview
database as the knowledge graph backbone.

## Design Decisions (from User)

| Decision | Choice | Rationale |
| --- | --- | --- |
| Embedding | Hybrid (local first, then API) | Dev speed + production quality |
| Vector Storage | sqlite-vec | Zero infra, keep SQLite |
| LLM Integration | Abstract Provider interface | Flexibility for future models |

---

# 1. Pipeline Architecture

```
User Question
    |
    v
+------------------+
|   Query Parser   |  Intent + entity extraction
+------------------+
    |
    v
+--------------------+
|  Semantic Search   |  Hybrid: Embedding + FTS5 + Tags
+--------------------+
    |
    v
+--------------------+
|  Entity Retrieval  |  Full rows by ID
+--------------------+
    |
    v
+--------------------+
|  Graph Traversal   |  Relations + Timeline + Refs
+--------------------+
    |
    v
+--------------------+
|  Context Assembly  |  Merge / Dedup / Rank
+--------------------+
    |
    v
+--------------------+
|  Auto-Compression  |  Token budget + priority prune
+--------------------+
    |
    v
+--------------------+
|  LLM Generation    |  Prompt assembly + API call
+--------------------+
```

## Pipeline Request/Response

| Stage | Input | Output | Storage |
| --- | --- | --- | --- |
| Query Parser | User text | ParsedQuery object | In-memory |
| Semantic Search | ParsedQuery | N candidates + scores | vector_chunks + FTS5 |
| Entity Retrieval | Entity IDs | Full entity rows | entities table |
| Graph Traversal | Entity IDs | Multi-layer graph | relations / timelines / refs |
| Context Assembly | Graph context | Structured dict | In-memory |
| Auto-Compression | Context dict | Pruned context | In-memory |
| LLM Generation | Pruned + Question | Answer string | In-memory / log |

## Core Data Packet: ContextPacket

```python
@dataclass
class ContextPacket:
    user_question: str
    parsed_intent: str
    entities: List[Entity]
    relations: List[Relation]
    timeline: List[TimelineEvent]
    references: List[Reference]
    total_tokens: int = 0
    budget: int = 8000
    compressed: bool = False
```

---
# 2. Stage 1: Query Parser

Two-tier parsing:

### 2.1 Lightweight Rule Parser (fast path)

- Extract entity_type keywords: "character", "location", "faction"
- Extract relation keywords: "relationship", "between", "connection"
- Extract timeline keywords: "before", "after", "timeline", "era", "year"
- Regex-based extraction for known patterns

### 2.2 LLM-Enhanced Extraction (heavy path)

When the rule parser has low confidence, fall back to a lightweight
LLM call to extract intent and named entities:

```python
@dataclass
class ParsedQuery:
    raw: str
    intent: str  # entity_query | relation_query | timeline_query | general
    entity_types: List[str]
    keywords: List[str]
    time_range: Optional[Tuple[int,int]]
    confidence: float
```

---
# 3. Stage 2: Semantic Search

Three parallel indexes, merged via Reciprocal Rank Fusion (RRF).

## 3.1 Vector Index (sqlite-vec)

New table:

```sql
CREATE TABLE IF NOT EXISTS vector_chunks (
    chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    chunk_type TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    chunk_text TEXT NOT NULL,
    embedding BLOB,
    token_count INTEGER,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);
CREATE INDEX idx_vc_entity ON vector_chunks(entity_id);
```

## 3.2 Chunking Strategy

| Chunk Type | Source | Size | Overlap |
| --- | --- | --- | --- |
| Title Chunk | entity.title | Full title | N/A |
| Summary Chunk | entity.ai_summary | 512 chars | 0 |
| Content Chunks | entity.full_content | 1024 chars | 128 |
| Tag Chunks | entity.tags | Single tag | N/A |

## 3.3 FTS5 Index (Lexical)

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts
USING fts5(
    entity_id UNINDEXED,
    title, content, full_content,
    tokenize="unicode61 remove_diacritics 2"
);
```

## 3.4 Hybrid Search Algorithm

```python
def hybrid_search(query: str, top_k: int = 10):
    q_vec = embed(query)
    vec_results = sqlite_vec_search(q_vec, top_k * 2)
    fts_results = fts5_search(query, top_k * 2)
    tag_results = tag_exact_search(query, top_k)
    merged = rrf_merge([vec_results, fts_results, tag_results])
    return merged[:top_k]
```

## 3.5 Embedding Adapter (Abstract Layer)

```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]: ...
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...

class OllamaEmbedding(EmbeddingProvider):
    def __init__(self, model="nomic-embed-text"):
        self.model = model
    def embed(self, text):
        resp = requests.post("http://localhost:11434/api/embeddings",
            json={"model": self.model, "prompt": text})
        return resp.json()["embedding"]

class OpenAIEmbedding(EmbeddingProvider):
    def __init__(self, model="text-embedding-3-small"):
        self.model = model
        self.client = OpenAI()
    def embed(self, text):
        resp = self.client.embeddings.create(
            model=self.model, input=text)
        return resp.data[0].embedding
```

---
# 4. Stage 3-5: Entity + Graph + Timeline

After semantic search returns candidate entity IDs, the pipeline
expands the context through three graph layers.

## 4.1 Entity Retrieval

Fetch full entity rows for candidate IDs + filter by is_active.
Also fetch related entities from references_map.

## 4.2 Relation Traversal

| Traversal | Depth | Description |
| --- | --- | --- |
| Direct 1-hop | 1 | Immediate relations (in/out/both) |
| Weighted n-hop | 2 | Second-degree with importance > 3 threshold |
| Type-filtered | 1 | Only specific relation types |

## 4.3 Timeline Gathering

Collect timeline_events for entity IDs, sorted by year.
Generate consolidated timeline view across all related entities.

## 4.4 Reference Resolution

```python
def gather_references(entity_ids: List[str]):
    out_refs = query_source_refs(entity_ids)
    in_refs = query_target_refs(entity_ids)
    return dedup(out_refs + in_refs)
```

---
# 5. Stage 6: Context Assembly

All collected data is merged into a unified ContextPacket.

## 5.1 Deduplication

- Entities deduped by entity_id
- Relations deduped by (source, target, type)
- Timeline events deduped by event_id
- Dead-entity filter: drop all data referencing is_active=0 entities

## 5.2 Relevance Scoring

```python
def score_entity(entity, search_score):
    score = search_score * 0.5
    score += entity.importance / 10 * 0.3
    score += rel_count * 0.05
    score += has_timeline * 0.05
    score += freshness(entity.updated_at) * 0.1
    return score
```

---
# 6. Stage 7: Auto-Compression

Ensures context fits within the LLM token budget (default 8K).

## 6.1 Budget Allocation (8K model)

| Component | Tokens | % of Budget |
| --- | --- | --- |
| System instructions | 500 | 6% |
| Core entities (top-3) | 1500 | 19% |
| Relations (top-10) | 500 | 6% |
| Timeline events | 400 | 5% |
| Supporting entities (next-5) | 800 | 10% |
| User question | 100 | 1% |
| Answer buffer | 2000 | 25% |
| Reserve | 2200 | 28% |

## 6.2 Compression Strategies

| Strategy | Action | Lossy | Trigger |
| --- | --- | --- | --- |
| Priority Pruning | Drop below score threshold | Yes | Always (pre-filter) |
| Summary Truncation | Trim ai_summary to 300 chars | Yes | Over budget < 20% |
| Relation Condense | Drop descriptions, keep type only | Yes | Over budget |
| Timeline Rollup | Group by era, keep count | Yes | Severe over-budget |
| Chunk Priority | Keep highest-score chunks/entity | Yes | Always when over budget |

## 6.3 Algorithm

```python
def auto_compress(packet, max_tokens=8000):
    if packet.total_tokens <= max_tokens:
        packet.compressed = True
        return packet
    strategies = [
        priority_pruning,
        summary_truncation,
        relation_condensation,
        chunk_priority_filter,
        timeline_rollup,
    ]
    for s in strategies:
        if packet.total_tokens <= max_tokens:
            break
        packet = s(packet)
    packet.compressed = True
    return packet
```

---
# 7. Stage 8: LLM Generation

The compressed context is assembled into a structured prompt.

## 7.1 LLM Provider Interface

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[dict], max_tokens: int) -> str: ...

class OpenAIProvider(LLMProvider):
    def __init__(self, model="gpt-4o-mini"):
        self.model = model
        self.client = OpenAI()
    def generate(self, messages, max_tokens=4096):
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages,
            max_tokens=max_tokens)
        return resp.choices[0].message.content
```

## 7.2 Prompt Template

```python
SYSTEM_PROMPT = "You are a worldbuilding knowledge assistant." + NL
SYSTEM_PROMPT += "Use ONLY the provided context." + NL
SYSTEM_PROMPT += "Cite entity IDs as @CHR_0012." + NL
SYSTEM_PROMPT += "Respect timeline order." + NL
SYSTEM_PROMPT += "Respond in the user language."
```

## 7.3 Context Assembly for Prompt

```python
def build_context_block(packet):
    blocks = []
    blocks.append("=== ENTITIES ===")
    for e in packet.entities[:5]:
        blocks.append(f"  {e.entity_id} ({e.title}): {e.ai_summary[:500]}")
    blocks.append("=== RELATIONS ===")
    for r in packet.relations[:10]:
        line = f"  {r.source_title} --[{r.relation_type}]--> {r.target_title}"
        if r.description: line += f": {r.description[:100]}"
        blocks.append(line)
    blocks.append("=== TIMELINE ===")
    for t in packet.timeline[:15]:
        blocks.append(f"  [{t.year}] {t.era} -- {t.title}")
    return NL.join(blocks)
```

---
# 8. API Endpoints

Three endpoints that compose the full pipeline:

## 8.1 Single-Step Query (recommended for most calls)

```python
@app.post("/api/rag/query")
async def rag_query(question: str = Body(...),
    top_k: int = 5,
    max_tokens: int = 8000,
    api_key: str = Query(None)):
    # Full pipeline in one call
    ctx = semantic_search(question, top_k)
    ctx = expand_context(ctx.entity_ids)
    packet = assemble_context(ctx)
    compressed = auto_compress(packet, max_tokens)
    prompt = build_prompt(compressed, question)
    answer = llm.generate(prompt)
    return {"answer": answer, "citations": compressed.entity_ids}
```

## 8.2 Step-by-Step (debugging / inspection)

| Endpoint | Stage | Usage |
| --- | --- | --- |
| POST /api/rag/search | Semantic Search | Get candidate entities + scores |
| POST /api/rag/expand | Graph Traversal | Expand with relations/timeline/refs |
| POST /api/rag/compress | Compression | Compress context within budget |
| POST /api/rag/query | Full pipeline | End-to-end with LLM generation |

---
# 9. Implementation Roadmap

## Phase 1: Foundation (Week 1-2)

- Add vector_chunks table to init_db()
- Implement OllamaEmbedding + sqlite-vec search
- Build /api/rag/search with hybrid search (vec + FTS5 + tags)
- Write chunking pipeline for existing entities

## Phase 2: Graph Expansion (Week 3-4)

- Build expand_context with 1-hop relation traversal
- Add timeline gathering + reference resolution
- Implement dedup and scoring in Context Assembly

## Phase 3: Compression (Week 5)

- Implement token counting + budget allocation
- Build auto_compress pipeline (5 strategies)
- Benchmark and tune thresholds

## Phase 4: LLM Integration (Week 6+)

- Design LLMProvider abstract interface
- Implement OpenAIProvider
- Build /api/rag/query endpoint
- End-to-end evaluation with sample worldview questions

---
# 10. Key Design Decisions

| Question | A | B | Chosen | Why |
| --- | --- | --- | --- | --- |
| Embedding storage | sqlite-vec | pgvector | sqlite-vec | Keep SQLite, zero infra |
| Chunking method | Recursive split | Semantic split | Recursive | Simple, predictable size |
| Graph traversal | Synchronous 1-hop | Async graph query | Synchronous | Depth is always small |
| Compression | Rule-based prune | LLM re-summarize | Hybrid | Speed + quality balance |
| Citation format | @ENTITY_ID | Markdown link | @ENTITY_ID | Tokenizer-friendly |

---

Document v1.0 | Generated 2026-06-17