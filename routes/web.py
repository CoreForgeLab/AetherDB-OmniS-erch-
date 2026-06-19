 from fastapi import APIRouter, Request
 from fastapi.responses import HTMLResponse
 
 from main import templates, get_db, API_KEY, ADMIN_KEY, ENTITY_TYPES
 
 web_router = APIRouter()
 
 
 @web_router.get("/", response_class=HTMLResponse)
 def get_home(request: Request):
     conn = get_db()
     try:
         cursor = conn.cursor()
         cursor.execute("SELECT COUNT(*) FROM entities WHERE is_active = 1")
         total_entities = cursor.fetchone()[0]
         cursor.execute("SELECT entity_type, COUNT(*) as count FROM entities WHERE is_active = 1 GROUP BY entity_type")
         type_dist = cursor.fetchall()
         cursor.execute("SELECT COUNT(*) FROM relations")
         total_relations = cursor.fetchone()[0]
         cursor.execute("SELECT entity_id, title, entity_type, importance, created_at FROM entities WHERE is_active = 1 ORDER BY created_at DESC LIMIT 10")
         recent_entities = cursor.fetchall()
     finally:
         conn.close()
     return templates.TemplateResponse("index.html", {
         "request": request,
         "stats": {"total_entities": total_entities, "type_distribution": {ENTITY_TYPES.get(r["entity_type"], r["entity_type"]): r["count"] for r in type_dist}, "total_relations": total_relations},
         "recent_entities": recent_entities,
         "entity_types": ENTITY_TYPES,
         "api_key": API_KEY[:8] + "..."
     })
 
 
 @web_router.get("/add", response_class=HTMLResponse)
 def add_entity_page(request: Request):
     return templates.TemplateResponse("add.html", {"request": request, "entity_types": ENTITY_TYPES, "api_key": API_KEY})
 
 
 @web_router.get("/search", response_class=HTMLResponse)
 def search_page(request: Request):
     return templates.TemplateResponse("search.html", {"request": request, "entity_types": ENTITY_TYPES, "api_key": API_KEY})
 
 
 @web_router.get("/timeline", response_class=HTMLResponse)
 def timeline_page(request: Request):
     conn = get_db()
     try:
         cursor = conn.cursor()
         cursor.execute("SELECT DISTINCT timeline_era FROM entities WHERE timeline_era IS NOT NULL")
         eras = [r["timeline_era"] for r in cursor.fetchall()]
     finally:
         conn.close()
     return templates.TemplateResponse("timeline.html", {"request": request, "eras": eras, "api_key": API_KEY})
 
 
 @web_router.get("/admin", response_class=HTMLResponse)
 def admin_page(request: Request):
     conn = get_db()
     try:
         cursor = conn.cursor()
         cursor.execute("SELECT * FROM entities WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 50")
         entities = cursor.fetchall()
     finally:
         conn.close()
     return templates.TemplateResponse("admin.html", {"request": request, "entities": entities, "entity_types": ENTITY_TYPES, "admin_key": ADMIN_KEY})
 
 
 @web_router.get("/import", response_class=HTMLResponse)
 def import_page(request: Request):
     return templates.TemplateResponse("import.html", {"request": request, "entity_types": ENTITY_TYPES, "api_key": API_KEY, "admin_key": ADMIN_KEY})
