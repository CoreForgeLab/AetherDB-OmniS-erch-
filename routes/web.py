from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

# Lazy imports to break circular import with main.py
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
    templates, get_db, _, ADMIN_KEY, ENTITY_TYPES = _get_main()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entities WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 50")
    entities = cursor.fetchall()
    return templates.TemplateResponse(request, "admin.html", {"entities": entities, "entity_types": ENTITY_TYPES, "admin_key": ADMIN_KEY})

@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    templates, _, _, ADMIN_KEY, _ = _get_main()
    return templates.TemplateResponse(request, "import.html", {"admin_key": ADMIN_KEY})

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
