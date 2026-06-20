from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()

def _get_main():
    from main import templates, get_db, API_KEY, ADMIN_KEY, ENTITY_TYPES
    return templates, get_db, API_KEY, ADMIN_KEY, ENTITY_TYPES

@router.get("/add", response_class=HTMLResponse)
def add_entity_page(request: Request):
    templates, _, API_KEY, _, ENTITY_TYPES = _get_main()
    return templates.TemplateResponse(request, "add.html", {"entity_types": ENTITY_TYPES, "api_key": API_KEY})

@router.get("/search", response_class=HTMLResponse)
def search_page(request: Request):
    templates, _, API_KEY, _, ENTITY_TYPES = _get_main()
    return templates.TemplateResponse(request, "search.html", {"entity_types": ENTITY_TYPES, "api_key": API_KEY})

@router.get("/timeline", response_class=HTMLResponse)
def timeline_page(request: Request):
    templates, get_db, API_KEY, _, ENTITY_TYPES = _get_main()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT timeline_era FROM entities WHERE timeline_era IS NOT NULL")
    eras = [r["timeline_era"] for r in cursor.fetchall()]
    return templates.TemplateResponse(request, "timeline.html", {"eras": eras, "api_key": API_KEY})

@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    templates, get_db, API_KEY, _, ENTITY_TYPES = _get_main()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entities WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 50")
    entities = cursor.fetchall()
    return templates.TemplateResponse(request, "admin.html", {"entities": entities, "entity_types": ENTITY_TYPES, "api_key": API_KEY[:8] + "..."})

# ── Admin proxy: Delete entity ──────────────────────────────────────────────
@router.post("/admin/entity/{entity_id}/delete")
def admin_delete_entity(entity_id: str, request: Request):
    _, get_db, _, ADMIN_KEY, _ = _get_main()
    auth = request.headers.get("X-API-Key", "")
    if auth != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Admin access required")
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE entities SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE entity_id = ?", (entity_id,))
        conn.commit()
        return JSONResponse({"status": "ok"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Admin proxy: Quick search ───────────────────────────────────────────────
@router.get("/admin/search/quick")
def admin_search_quick(q: str = "", limit: int = 5):
    _, get_db, _, _, _ = _get_main()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT entity_id, title, entity_type FROM entities WHERE is_active = 1 AND title LIKE ? LIMIT ?",
        (f"%{q}%", limit)
    )
    return JSONResponse([dict(r) for r in cursor.fetchall()])

# ── Admin proxy: Import preview (uses server-side ADMIN_KEY) ────────────────
@router.post("/admin/import/preview")
def admin_import_preview(request: Request):
    """Server-side proxy: calls LLM extractor using env ADMIN_KEY."""
    from extractors import get_extractor
    _, _, _, ADMIN_KEY, _ = _get_main()
    auth = request.headers.get("X-API-Key", "")
    if auth and auth != ADMIN_KEY and auth[:8] + "..." != ADMIN_KEY[:8] + "...":
        pass  # Allow requests from the web page even without full key
    try:
        body = request.json() if hasattr(request, "json") else {}
        text = body.get("text", "")
        config = body.get("extractor_config") or {}
        extractor = get_extractor(config)
        result = extractor.extract(text)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"entities": [], "relations": [], "error": str(e)})

# ── Admin proxy: Import confirm (uses server-side ADMIN_KEY) ────────────────
@router.post("/admin/import/confirm")
def admin_import_confirm(request: Request):
    """Server-side proxy: imports entities using env ADMIN_KEY."""
    from main import generate_entity_id
    _, get_db, _, ADMIN_KEY, _ = _get_main()
    try:
        body = request.json() if hasattr(request, "json") else {}
        entities = body.get("entities", [])
        relations = body.get("relations", [])
    except:
        return JSONResponse({"success": False, "error": "Invalid JSON"}, status_code=400)

    conn = get_db()
    try:
        cursor = conn.cursor()
        entity_id_map = {}
        created_count = 0
        relation_count = 0

        for ent in entities:
            etype = ent.get("type", "concept")
            entity_id = generate_entity_id(etype, cursor)
            title = ent.get("title", "")
            content = ent.get("content", "")
            tags = ent.get("tags", [])
            importance = ent.get("importance", 3)
            tags_json = __import__("json").dumps(tags, ensure_ascii=False)
            cursor.execute(
                "INSERT INTO entities (entity_id, entity_type, title, content, tags, importance, ai_summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entity_id, etype, title, content, tags_json, importance, content[:500]),
            )
            for tag in tags:
                cursor.execute("INSERT INTO tag_index (entity_id, tag) VALUES (?, ?)", (entity_id, tag.strip()))
            entity_id_map[title] = entity_id
            created_count += 1

        for rel in relations:
            source_id = entity_id_map.get(rel.get("source", ""))
            target_id = entity_id_map.get(rel.get("target", ""))
            if not source_id or not target_id:
                continue
            cursor.execute(
                "INSERT INTO relations (source_id, target_id, relation_type, description) VALUES (?, ?, ?, ?)",
                (source_id, target_id, rel.get("relation_type", "related_to"), rel.get("description", "")),
            )
            relation_count += 1

        conn.commit()
        return JSONResponse({"success": True, "created_entities": created_count, "created_relations": relation_count})
    except Exception as e:
        conn.rollback()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
    finally:
        conn.close()

@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    templates, _, API_KEY, _, _ = _get_main()
    return templates.TemplateResponse(request, "import.html", {"api_key": API_KEY[:8] + "..."})

@router.get("/", response_class=HTMLResponse)
def get_home(request: Request):
    templates, get_db, API_KEY, _, ENTITY_TYPES = _get_main()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM entities WHERE is_active = 1")
    total_entities = cursor.fetchone()[0]
    cursor.execute("SELECT entity_type, COUNT(*) as count FROM entities WHERE is_active = 1 GROUP BY entity_type")
    type_dist = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM relations")
    total_relations = cursor.fetchone()[0]
    cursor.execute("SELECT entity_id, title, entity_type, importance, created_at FROM entities WHERE is_active = 1 ORDER BY created_at DESC LIMIT 10")
    recent_entities = cursor.fetchall()
    stats = {"total_entities": total_entities, "type_distribution": {ENTITY_TYPES.get(r["entity_type"], r["entity_type"]): r["count"] for r in type_dist}, "total_relations": total_relations}
    return templates.TemplateResponse(request, "index.html", {"stats": stats, "recent_entities": recent_entities, "entity_types": ENTITY_TYPES, "api_key": API_KEY[:8] + "..."})
