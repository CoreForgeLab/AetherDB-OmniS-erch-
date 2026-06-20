from fastapi import APIRouter, Query, Body, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import os, sqlite3, json

router = APIRouter(tags=["translation"])

class TranslationCreate(BaseModel):
    language: str
    title: str
    content: Optional[str] = ""
    full_content: Optional[str] = ""
    ai_summary: Optional[str] = ""

class TranslationResponse(BaseModel):
    id: int
    entity_id: str
    language: str
    title: str
    content: str
    full_content: str
    ai_summary: str
    created_at: str
    updated_at: str

def _get_key(request: Request, api_key: str) -> str:
    key = request.headers.get("X-API-Key") or api_key
    expected = os.environ.get("NOVEL_API_KEY") or ""
    if key != expected and expected:
        raise HTTPException(401, "Invalid API key")
    return key

@router.post("/api/entity/{entity_id}/translate")
async def set_translation(entity_id: str, body: TranslationCreate, request: Request, api_key: str = Query(None)):
    _get_key(request, api_key)
    from main import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ?", (entity_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Entity not found")
        cursor.execute(
            "INSERT INTO entity_translations (entity_id, language, title, content, full_content, ai_summary) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(entity_id, language) DO UPDATE SET "
            "title=excluded.title, content=excluded.content, "
            "full_content=excluded.full_content, ai_summary=excluded.ai_summary, "
            "updated_at=CURRENT_TIMESTAMP",
            (entity_id, body.language, body.title, body.content or "",
             body.full_content or "", body.ai_summary or "")
        )
        conn.commit()
        cursor.execute(
            "SELECT * FROM entity_translations WHERE entity_id=? AND language=?",
            (entity_id, body.language))
        row = dict(cursor.fetchone())
        return row
    finally:
        conn.close()

@router.get("/api/entity/{entity_id}/translations")
async def get_translations(entity_id: str, request: Request, api_key: str = Query(None)):
    _get_key(request, api_key)
    from main import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM entity_translations WHERE entity_id=? ORDER BY language",
            (entity_id,))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
