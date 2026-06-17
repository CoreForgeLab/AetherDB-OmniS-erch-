# -*- coding: utf-8 -*-
"""
世界观数据库管理系统 v1.15.0 中文版
使用 FastAPI + Jinja2 模板
"""


import sys, site
# Auto-add system site-packages when running in virtual environment
if sys.prefix != sys.base_prefix:
    for p in site.getsitepackages():
        if p not in sys.path:
            sys.path.insert(0, p)
import sqlite3
import uvicorn
import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query, Form, Request, Depends
from services.embedding import MockEmbeddingProvider
from services.vector_store import VectorStore
from api.search_semantic import router as semantic_router
from api.rag_context import router as rag_router
from api.consistency_check import router as consistency_router
from pydantic import BaseModel
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ============================================================
# 安全密钥管理
# ============================================================
from app.dependencies.auth import (
    ADMIN_API_KEY as ADMIN_KEY,
    USER_API_KEY as API_KEY,
    get_current_user_role,
    require_admin,
    VALID_KEYS,
)

# ============================================================
# 实体类型定义（中文）
# ============================================================
ENTITY_TYPES = {
    "character": "人物",
    "faction": "阵营",
    "location": "地点",
    "rule": "规则",
    "event": "事件",
    "item": "物品",
    "concept": "概念",
    "system": "系统"
}

ENTITY_PREFIXES = {
    "character": "CHR",
    "faction": "FAC",
    "location": "LOC",
    "rule": "RUL",
    "event": "EVT",
    "item": "ITM",
    "concept": "CON",
    "system": "SYS"
}

# ============================================================
# FastAPI应用初始化
# ============================================================
app = FastAPI(
    title="世界观数据库管理系统 v1.15.0",
    version="1.0.0",
    description="支持 AI 协作的世界观数据库系统"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板
templates = Jinja2Templates(directory="templates")
templates.env.filters["from_json"] = json.loads

# ============================================================
# 数据模型
# ============================================================
class EntityCreate(BaseModel):
    entity_type: str = "character"
    title: str
    content: str = ""
    full_content: Optional[str] = None
    ai_summary: Optional[str] = None
    tags: List[str] = []
    timeline_year: Optional[int] = None
    timeline_era: Optional[str] = None
    importance: int = 5
    references: List[str] = []

class EntityUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    full_content: Optional[str] = None
    ai_summary: Optional[str] = None
    tags: Optional[List[str]] = None
    timeline_year: Optional[int] = None
    timeline_era: Optional[str] = None
    importance: Optional[int] = None
    references: Optional[List[str]] = None

class RelationCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    description: Optional[str] = None

class SearchQuery(BaseModel):
    keyword: str
    entity_type: Optional[str] = None
    tags: Optional[List[str]] = None
    fuzzy: bool = True
    limit: int = 20

# ============================================================
# 数据模型 - LLM导入
# ============================================================
class ImportPreviewEntity(BaseModel):
    title: str
    type: str = "concept"
    content: str = ""
    tags: list[str] = []
    importance: int = 3

class ImportPreviewRelation(BaseModel):
    source: str
    target: str
    relation_type: str = "related_to"
    description: str = ""

class ImportPreviewRequest(BaseModel):
    text: str
    extractor_config: Optional[dict] = None

class ImportConfirmRequest(BaseModel):
    entities: list[ImportPreviewEntity]
    relations: list[ImportPreviewRelation] = []


# ============================================================
# 数据库初始化
# ============================================================
DB_PATH = "novel_world_zh.db"

def get_db():
    from services.db import get_connection
    conn = get_connection(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA encoding = 'UTF-8'")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def generate_entity_id(entity_type, cursor):
    prefix = ENTITY_PREFIXES.get(entity_type, "GEN")
    cursor.execute(
        "SELECT MAX(CAST(SUBSTR(entity_id, 5) AS INTEGER)) FROM entities WHERE entity_id LIKE ?",
        (prefix + "_%",)
    )
    max_id = cursor.fetchone()[0]
    next_id = (max_id or 0) + 1
    return f"{prefix}_{next_id:04d}"

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            full_content TEXT DEFAULT '',
            ai_summary TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            timeline_year INTEGER,
            timeline_era TEXT,
            importance INTEGER DEFAULT 5,
            version INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES entities(entity_id),
            FOREIGN KEY (target_id) REFERENCES entities(entity_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tag_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            title TEXT,
            content TEXT,
            full_content TEXT,
            ai_summary TEXT,
            tags TEXT,
            importance INTEGER,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS references_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES entities(entity_id),
            FOREIGN KEY (target_id) REFERENCES entities(entity_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timeline_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT,
            year INTEGER,
            era TEXT,
            title TEXT,
            description TEXT,
            importance INTEGER DEFAULT 5,
            FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_tags ON entities(tags)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_source ON relations(source_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_relation_target ON relations(target_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_entity ON tag_index(entity_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag_name ON tag_index(tag)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_version ON entity_versions(entity_id)")
    
    conn.commit()
    conn.close()

# ============================================================
# API密钥验证
# ============================================================
# ============================================================
# API接口 - 实体管理
# ============================================================
@app.post("/api/entity")
def create_entity(entity: EntityCreate, request: Request, role: str = Depends(get_current_user_role)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        if entity.entity_type not in ENTITY_TYPES:
            raise HTTPException(status_code=400, detail=f"无效类型。支持：{list(ENTITY_TYPES.keys())}")
        
        entity_id = generate_entity_id(entity.entity_type, cursor)
        tags_json = json.dumps(entity.tags, ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO entities (entity_id, entity_type, title, content, full_content, 
                ai_summary, tags, timeline_year, timeline_era, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (entity_id, entity.entity_type, entity.title, entity.content,
              entity.full_content or entity.content, entity.ai_summary or "",
              tags_json, entity.timeline_year, entity.timeline_era, entity.importance))
        
        for tag in entity.tags:
            cursor.execute("INSERT INTO tag_index (entity_id, tag) VALUES (?, ?)", (entity_id, tag.strip()))
        
        for ref_id in entity.references:
            cursor.execute("INSERT INTO references_map (source_id, target_id) VALUES (?, ?)", (entity_id, ref_id))
        
        if entity.timeline_year or entity.timeline_era:
            cursor.execute("""
                INSERT INTO timeline_events (entity_id, year, era, title, description, importance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (entity_id, entity.timeline_year, entity.timeline_era,
                  entity.title, entity.ai_summary or entity.content[:200], entity.importance))
        
        conn.commit()
        return {"entity_id": entity_id, "message": "创建成功", "entity_type": ENTITY_TYPES[entity.entity_type]}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/entity/{entity_id}")
def get_entity(entity_id: str, include_history: bool = False, include_relations: bool = True, role: str = Depends(get_current_user_role)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
        entity = cursor.fetchone()
        if not entity:
            raise HTTPException(status_code=404, detail="未找到该实体")
        
        result = dict(entity)
        result["tags"] = json.loads(result["tags"]) if result["tags"] else []
        
        if include_relations:
            cursor.execute("""
                SELECT r.*, e1.title as source_title, e2.title as target_title
                FROM relations r LEFT JOIN entities e1 ON r.source_id = e1.entity_id
                LEFT JOIN entities e2 ON r.target_id = e2.entity_id
                WHERE r.source_id = ? OR r.target_id = ?
            """, (entity_id, entity_id))
            result["relations"] = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("""
            SELECT rm.*, e.title as referenced_title
            FROM references_map rm LEFT JOIN entities e ON rm.target_id = e.entity_id
            WHERE rm.source_id = ?
        """, (entity_id,))
        result["references"] = [dict(r) for r in cursor.fetchall()]
        
        if include_history:
            cursor.execute("SELECT * FROM entity_versions WHERE entity_id = ? ORDER BY version DESC", (entity_id,))
            result["history"] = [dict(v) for v in cursor.fetchall()]
        
        return result
    finally:
        conn.close()

@app.put("/api/entity/{entity_id}")
def update_entity(entity_id: str, update: EntityUpdate, request: Request, _: None = Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
        entity = cursor.fetchone()
        if not entity:
            raise HTTPException(status_code=404, detail="未找到该实体")
        
        cursor.execute("""
            INSERT INTO entity_versions (entity_id, version, title, content, full_content, ai_summary, tags, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (entity_id, entity["version"], entity["title"], entity["content"],
              entity["full_content"], entity["ai_summary"], entity["tags"], entity["importance"]))
        
        update_fields = []
        update_values = []
        
        ALLOWED_FIELDS = {"title", "content", "full_content", "ai_summary",
                          "timeline_year", "timeline_era", "importance"}
        for field, value in {"title": update.title, "content": update.content, "full_content": update.full_content,
                             "ai_summary": update.ai_summary, "timeline_year": update.timeline_year,
                             "timeline_era": update.timeline_era, "importance": update.importance}.items():
            if value is not None and field in ALLOWED_FIELDS:
                update_fields.append(f"{field} = ?")
                update_values.append(value)
        
        if update.tags is not None:
            update_fields.append("tags = ?")
            update_values.append(json.dumps(update.tags))
            cursor.execute("DELETE FROM tag_index WHERE entity_id = ?", (entity_id,))
            for tag in update.tags:
                cursor.execute("INSERT INTO tag_index (entity_id, tag) VALUES (?, ?)", (entity_id, tag.strip()))
        
        update_fields.append("version = version + 1")
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        if update_fields:
            update_values.append(entity_id)
            cursor.execute(f"UPDATE entities SET {', '.join(update_fields)} WHERE entity_id = ?", update_values)
        
        if update.references is not None:
            cursor.execute("DELETE FROM references_map WHERE source_id = ?", (entity_id,))
            for ref_id in update.references:
                cursor.execute("INSERT INTO references_map (source_id, target_id) VALUES (?, ?)", (entity_id, ref_id))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,))
        result = dict(cursor.fetchone())
        result["tags"] = json.loads(result["tags"]) if result["tags"] else []
        return result
    finally:
        conn.close()

@app.delete("/api/entity/{entity_id}")
def delete_entity(entity_id: str, request: Request, _: None = Depends(require_admin)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE entities SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE entity_id = ?", (entity_id,))
        conn.commit()
        return {"message": "删除成功", "entity_id": entity_id}
    finally:
        conn.close()

# ============================================================
# API接口 - 关系管理
# ============================================================
@app.post("/api/relation")
def create_relation(relation: RelationCreate, role: str = Depends(get_current_user_role)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ?", (relation.source_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"未找到源实体 {relation.source_id}")
        cursor.execute("SELECT entity_id FROM entities WHERE entity_id = ?", (relation.target_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"未找到目标实体 {relation.target_id}")
        
        cursor.execute("INSERT INTO relations (source_id, target_id, relation_type, description) VALUES (?, ?, ?, ?)",
                      (relation.source_id, relation.target_id, relation.relation_type, relation.description))
        conn.commit()
        return {"message": "关系创建成功", "source": relation.source_id, "target": relation.target_id, "type": relation.relation_type}
    finally:
        conn.close()

@app.get("/api/entity/{entity_id}/relations")
def get_entity_relations(entity_id: str, direction: str = "both", role: str = Depends(get_current_user_role)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        if direction == "out":
            cursor.execute("SELECT r.*, e.title as target_title FROM relations r LEFT JOIN entities e ON r.target_id = e.entity_id WHERE r.source_id = ?", (entity_id,))
        elif direction == "in":
            cursor.execute("SELECT r.*, e.title as source_title FROM relations r LEFT JOIN entities e ON r.source_id = e.entity_id WHERE r.target_id = ?", (entity_id,))
        else:
            cursor.execute("SELECT r.*, e1.title as source_title, e2.title as target_title FROM relations r LEFT JOIN entities e1 ON r.source_id = e1.entity_id LEFT JOIN entities e2 ON r.target_id = e2.entity_id WHERE r.source_id = ? OR r.target_id = ?", (entity_id, entity_id))
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

# ============================================================
# API接口 - 搜索
# ============================================================
@app.post("/api/search")
def search_entities(query: SearchQuery, role: str = Depends(get_current_user_role)):
    conn = get_db()
    try:
        cursor = conn.cursor()
        conditions = ["e.is_active = 1"]
        params = []
        
        if query.keyword:
            keyword = f"%{query.keyword}%"
            conditions.append("(e.title LIKE ? OR e.content LIKE ? OR e.full_content LIKE ? OR e.ai_summary LIKE ?)")
            params.extend([keyword, keyword, keyword, keyword])
        
        if query.entity_type:
            conditions.append("e.entity_type = ?")
            params.append(query.entity_type)
        
        if query.tags:
            for tag in query.tags:
                conditions.append("e.entity_id IN (SELECT entity_id FROM tag_index WHERE tag = ?)")
                params.append(tag)
        
        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT e.*, (SELECT COUNT(*) FROM relations WHERE source_id = e.entity_id OR target_id = e.entity_id) as relation_count
            FROM entities e WHERE {where_clause}
            ORDER BY e.importance DESC, e.updated_at DESC LIMIT ?
        """
        params.append(query.limit)
        
        cursor.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            result["tags"] = json.loads(result["tags"]) if result["tags"] else []
            results.append(result)
        
        return {"total": len(results), "results": results, "query": query.keyword}
    finally:
        conn.close()

# ============================================================
# API接口 - 统计
# ============================================================
@app.get("/api/stats")
def get_stats(role: str = Depends(get_current_user_role)):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM entities WHERE is_active = 1")
    total = c.fetchone()[0]
    c.execute("SELECT entity_type, COUNT(*) as count FROM entities WHERE is_active = 1 GROUP BY entity_type")
    type_dist = {ENTITY_TYPES.get(r["entity_type"], r["entity_type"]): r["count"] for r in c.fetchall()}
    c.execute("SELECT COUNT(*) FROM relations")
    rels = c.fetchone()[0]
    c.execute("SELECT tag, COUNT(*) as count FROM tag_index GROUP BY tag ORDER BY count DESC LIMIT 20")
    tags = [{"tag": r["tag"], "count": r["count"]} for r in c.fetchall()]
    c.execute("SELECT COUNT(*) FROM timeline_events")
    tl = c.fetchone()[0]
    return {"total_entities": total, "type_distribution": type_dist, "total_relations": rels, "top_tags": tags, "timeline_events": tl}

# ============================================================
# WEB界面 - 首页
# ============================================================
@app.get("/", response_class=HTMLResponse)
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

@app.get("/add", response_class=HTMLResponse)
def add_entity_page(request: Request):
    return templates.TemplateResponse("add.html", {"request": request, "entity_types": ENTITY_TYPES, "api_key": API_KEY})

@app.get("/search", response_class=HTMLResponse)
def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request, "entity_types": ENTITY_TYPES, "api_key": API_KEY})

@app.get("/timeline", response_class=HTMLResponse)
def timeline_page(request: Request):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT timeline_era FROM entities WHERE timeline_era IS NOT NULL")
        eras = [r["timeline_era"] for r in cursor.fetchall()]
    finally:
        conn.close()
    return templates.TemplateResponse("timeline.html", {"request": request, "eras": eras, "api_key": API_KEY})

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entities WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 50")
        entities = cursor.fetchall()
    finally:
        conn.close()
    return templates.TemplateResponse("admin.html", {"request": request, "entities": entities, "entity_types": ENTITY_TYPES, "admin_key": ADMIN_KEY})



@app.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    """LLM 导入页面。"""
    return templates.TemplateResponse("import.html", {"request": request, "entity_types": ENTITY_TYPES, "api_key": API_KEY, "admin_key": ADMIN_KEY})

# ============================================================
# RAG API
# ============================================================
# [DEPRECATED by api/rag_context.py] @app.post('/api/rag/context')
# [DEPRECATED by api/rag_context.py] async def get_rag_context(query: str = Query(""), max_entities: int = 5, focus_entities: str = "", role: str = Depends(get_current_user_role)):
# [DEPRECATED by api/rag_context.py]     conn = get_db()
# [DEPRECATED by api/rag_context.py]     try:
# [DEPRECATED by api/rag_context.py]         cursor = conn.cursor()
# [DEPRECATED by api/rag_context.py]         context = {"summaries": [], "details": [], "relations": []}
# [DEPRECATED by api/rag_context.py]         keyword = f"%{query}%"
# [DEPRECATED by api/rag_context.py]         cursor.execute("SELECT entity_id, title, ai_summary, importance, tags FROM entities WHERE is_active = 1 AND (title LIKE ? OR ai_summary LIKE ? OR content LIKE ?) ORDER BY importance DESC LIMIT ?", (keyword, keyword, keyword, max_entities))
# [DEPRECATED by api/rag_context.py]         entities = cursor.fetchall()
        
# [DEPRECATED by api/rag_context.py]         for entity in entities:
# [DEPRECATED by api/rag_context.py]             if entity["ai_summary"]:
# [DEPRECATED by api/rag_context.py]                 context["summaries"].append({"entity_id": entity["entity_id"], "title": entity["title"], "summary": entity["ai_summary"][:500], "importance": entity["importance"], "tags": json.loads(entity["tags"]) if entity["tags"] else []})
        
# [DEPRECATED by api/rag_context.py]         if focus_entities:
# [DEPRECATED by api/rag_context.py]             for focus_id in [e.strip() for e in focus_entities.split(",") if e.strip()]:
# [DEPRECATED by api/rag_context.py]                 cursor.execute("SELECT entity_id, title, ai_summary, tags FROM entities WHERE entity_id = ? AND is_active = 1", (focus_id,))
# [DEPRECATED by api/rag_context.py]                 entity = cursor.fetchone()
# [DEPRECATED by api/rag_context.py]                 if entity:
# [DEPRECATED by api/rag_context.py]                     context["details"].append({"entity_id": entity["entity_id"], "title": entity["title"], "content": entity["ai_summary"] or "", "tags": json.loads(entity["tags"]) if entity["tags"] else []})
        
# [DEPRECATED by api/rag_context.py]         entity_ids = [e["entity_id"] for e in entities[:5]]
# [DEPRECATED by api/rag_context.py]         if entity_ids:
# [DEPRECATED by api/rag_context.py]             placeholders = ",".join(["?"] * len(entity_ids))
# [DEPRECATED by api/rag_context.py]             cursor.execute(f"SELECT r.*, e1.title as source_title, e2.title as target_title FROM relations r JOIN entities e1 ON r.source_id = e1.entity_id JOIN entities e2 ON r.target_id = e2.entity_id WHERE r.source_id IN ({placeholders}) OR r.target_id IN ({placeholders})", entity_ids + entity_ids)
# [DEPRECATED by api/rag_context.py]             context["relations"] = [dict(r) for r in cursor.fetchall()]
        
# [DEPRECATED by api/rag_context.py]         return context
# [DEPRECATED by api/rag_context.py]     finally:
# [DEPRECATED by api/rag_context.py]         conn.close()

# ============================================================
# 启动
# ============================================================

# ============================================================
# API?? - ???
# ============================================================
@app.get("/api/timeline")
def get_timeline_events(era: str = None, role: str = Depends(get_current_user_role)):
    """??????????????"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        if era:
            cursor.execute("SELECT te.*, e.title as entity_title FROM timeline_events te LEFT JOIN entities e ON te.entity_id = e.entity_id WHERE te.era = ? ORDER BY te.year ASC", (era,))
        else:
            cursor.execute("SELECT te.*, e.title as entity_title FROM timeline_events te LEFT JOIN entities e ON te.entity_id = e.entity_id ORDER BY te.year, te.id ASC")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


# ============================================================
# API接口 - 快速搜索（给前端自动补全用）
# ============================================================
@app.get("/api/search/quick")
def quick_search(q: str = Query(""), limit: int = 5, role: str = Depends(get_current_user_role)):
    """快速搜索实体，返回精简结果（给前端自动补全用）。"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        keyword = f"%{q}%"
        cursor.execute(
            "SELECT entity_id, title, entity_type, importance FROM entities WHERE is_active = 1 AND title LIKE ? ORDER BY importance DESC LIMIT ?",
            (keyword, limit),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


@app.post("/api/import/preview")
def import_preview(req: ImportPreviewRequest, _: None = Depends(require_admin)):
    """自然语言导入预览：调用 LLM 抽取候选实体和关系。"""
    try:
        from extractors import get_extractor
        config = req.extractor_config or {}
        extractor = get_extractor(config)
        result = extractor.extract(req.text)
        return result
    except Exception as e:
        return {"entities": [], "relations": [], "error": str(e)}


@app.post("/api/import/confirm")
def import_confirm(req: ImportConfirmRequest, _: None = Depends(require_admin)):
    """确认导入实体和关系到数据库。"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        entity_id_map = {}
        created_count = 0
        relation_count = 0

        for ent in req.entities:
            entity_id = generate_entity_id(ent.type, cursor)
            tags_json = json.dumps(ent.tags, ensure_ascii=False)
            cursor.execute(
                "INSERT INTO entities (entity_id, entity_type, title, content, tags, importance, ai_summary) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entity_id, ent.type, ent.title, ent.content, tags_json, ent.importance, ent.content[:500]),
            )
            for tag in ent.tags:
                cursor.execute("INSERT INTO tag_index (entity_id, tag) VALUES (?, ?)", (entity_id, tag.strip()))
            entity_id_map[ent.title] = entity_id
            created_count += 1

        for rel in req.relations:
            source_id = entity_id_map.get(rel.source)
            target_id = entity_id_map.get(rel.target)
            if not source_id or not target_id:
                continue
            cursor.execute(
                "INSERT INTO relations (source_id, target_id, relation_type, description) VALUES (?, ?, ?, ?)",
                (source_id, target_id, rel.relation_type, rel.description),
            )
            relation_count += 1

        conn.commit()
        return {"success": True, "created_entities": created_count, "created_relations": relation_count}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"导入失败: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("  世界观数据库管理系统 v1.15.0 中文版")
    print("=" * 60)
    print(f"  启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    print("  [i] API 密钥状态：")
    print(f"  管理员密钥: {ADMIN_KEY[:8]}... (已配置, 长度 {len(ADMIN_KEY)})")
    print(f"  用户密钥:   {API_KEY[:8]}... (已配置, 长度 {len(API_KEY)})")
    print("  [!] 如使用自动生成的密钥，完整密钥保存在 .api_keys.json 文件中")
    print("-" * 60)
    print(f"  [Web] 网页界面: http://localhost:8000")
    print(f"  [DOC] API文档:  http://localhost:8000/docs")
    print("=" * 60)
    
    init_db()
    embedding_provider = MockEmbeddingProvider()
    vector_store = VectorStore(DB_PATH, embedding_provider)
    vector_store.init_db()
    app.state.vector_store = vector_store
    app.state.db_path = DB_PATH
    app.include_router(semantic_router)
    app.include_router(rag_router)
    app.include_router(consistency_router)
    print("  [OK] Vector Store initialized with sqlite-vec")
    print("  [OK] Consistency Checker loaded (4 check types)")
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    finally:
        close_connection()