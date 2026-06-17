from fastapi import APIRouter, Query, Body, HTTPException, Request
from typing import Optional
from pydantic import BaseModel
import json

router = APIRouter(tags=["rag_context"])

class RagContextRequest(BaseModel):
    query: str
    max_tokens: int = 2048
    include_timeline: bool = True
    include_relations: bool = True
    book_id: Optional[str] = None

@router.post("/api/rag/context")
async def upgraded_rag_context(req: RagContextRequest, request: Request, api_key: str = Query(None)):
    # Verify API key via env
    import os
    expected = os.environ.get("NOVEL_API_KEY") or ""
    if api_key != expected and expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    store = request.app.state.vector_store
    if not store:
        raise HTTPException(500, "Vector store not initialized")
    results = store.search(query=req.query, top_k=5, book_id=req.book_id)
    entity_ids = [r.entity_id for r in results]
    if not entity_ids:
        return {"context": "", "references": [], "token_estimate": 0, "entities": [], "relations": [], "timeline": []}
    conn = request.app.state.get("db_conn")
    import sqlite3
    db = sqlite3.connect("novel_world_zh.db")
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    entities = []
    for eid in entity_ids:
        cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (eid,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d["tags"] = json.loads(d["tags"]) if d.get("tags") else []
            entities.append(d)
    relations = []
    if req.include_relations and entity_ids:
        placeholders = ",".join(["?"] * len(entity_ids))
        cursor.execute(
            f"SELECT r.*, e1.title as source_title, e2.title as target_title "
            f"FROM relations r "
            f"LEFT JOIN entities e1 ON r.source_id = e1.entity_id "
            f"LEFT JOIN entities e2 ON r.target_id = e2.entity_id "
            f"WHERE r.source_id IN ({placeholders}) OR r.target_id IN ({placeholders})",
            entity_ids + entity_ids
        )
        relations = [dict(r) for r in cursor.fetchall()]
    timeline = []
    if req.include_timeline and entity_ids:
        placeholders = ",".join(["?"] * len(entity_ids))
        cursor.execute(
            f"SELECT * FROM timeline_events WHERE entity_id IN ({placeholders}) ORDER BY year",
            entity_ids
        )
        timeline = [dict(t) for t in cursor.fetchall()]
    db.close()
    context_parts = []
    context_parts.append("=== ENTITIES ===")
    for e in entities[:5]:
        summary = e.get("ai_summary") or e.get("content", "")[:300]
        tags_str = ", ".join(e.get("tags", []))
        context_parts.append(
            f"  [{e['entity_id']}] {e['title']} ({e['entity_type']} | importance {e['importance']})"
        )
        if summary:
            context_parts.append(f"    Summary: {summary[:500]}")
        if tags_str:
            context_parts.append(f"    Tags: {tags_str}")
    context_parts.append("")
    if relations:
        context_parts.append("=== RELATIONS ===")
        for r in relations[:15]:
            line = f"  {r.get('source_title','?')} --[{r['relation_type']}]--> {r.get('target_title','?')}"
            if r.get("description"):
                line += f": {r['description'][:100]}"
            context_parts.append(line)
        context_parts.append("")
    if timeline:
        context_parts.append("=== TIMELINE ===")
        for t in timeline[:15]:
            year_str = f"[{t['year']}]" if t.get("year") else ""
            era_str = f"({t['era']})" if t.get("era") else ""
            context_parts.append(f"  {year_str} {era_str} {t.get('title','')}: {t.get('description','')[:200]}")
        context_parts.append("")
    full_context = "\n".join(context_parts)
    token_est = len(full_context) // 2
    if token_est > req.max_tokens:
        full_context = full_context[:req.max_tokens * 2] + "\n...[truncated]"
    return {
        "context": full_context,
        "references": entity_ids,
        "token_estimate": min(token_est, req.max_tokens),
        "entities": [{"entity_id": e["entity_id"], "title": e["title"], "type": e["entity_type"]} for e in entities[:5]],
        "relations": [{"source": r.get("source_title"), "type": r["relation_type"], "target": r.get("target_title")} for r in relations[:10]],
        "timeline": [{"year": t.get("year"), "era": t.get("era"), "title": t.get("title")} for t in timeline[:10]]
    }
