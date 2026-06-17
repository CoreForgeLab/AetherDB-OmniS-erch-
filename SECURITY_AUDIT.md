# 世界观数据库管理系统 - 安全审计报告

**日期**：2026-06-17  |  **项目**：v1.15.0  |  **框架**：FastAPI + SQLite + Jinja2

---

## 1. 漏洞总表

| ID | 漏洞 | 风险等级 |
|---|---|---|
| V-001 | 存储型XSS（innerHTML） | **CRITICAL** |
| V-002 | API Key在URL Query中传输 | **HIGH** |
| V-003 | 管理员Key在HTML源码中明文 | **HIGH** |
| V-004 | update_entity动态SQL拼接 | MEDIUM |
| V-005 | 软删除无级联清理 | MEDIUM |
| V-006 | 前端引用后端缺失接口 | MEDIUM |
| V-007 | novel_world_v3.db孤文件 | MEDIUM |
| V-008 | ID生成TOCTOU竞态 | LOW |
| V-009 | esc()函数转义不完整 | LOW |
| V-010 | 输入校验缺失 | LOW |
| V-011 | 异常信息泄露 | LOW |
| V-012 | CORS全来源放行 | LOW |
---

## 2. V-001 CRITICAL：XSS

All templates use innerHTML without escaping.
---

## 3. V-002 HIGH: API Key in Query Params

Current: all 13 endpoints use api_key: str = Query(None)
Fix: switch to X-API-Key header

## 4. V-003 HIGH: Admin Key in Page Source

Exposed in: admin.html, import.html

Fix: Session-based auth, dont embed key in HTML

## 5. V-004 MEDIUM: SQL Injection Risk

update_entity uses f-string for SET clause.
Fields come from hardcoded dict, but design is fragile.
Fix: whitelist allowed field names

## 6. V-005 MEDIUM: Soft Delete Cascade Missing

Deleting entity leaves orphan tag_index/relations/refs.
Fix: add CASCADE DELETE for related tables

## 7. V-006 MEDIUM: Missing API Endpoints

Frontend calls but backend doesnt implement:
- /api/import
- /api/search/quick
- /api/timeline

Fix: implement missing endpoints

## 8. V-007 MEDIUM: Orphaned Config

novel_world_v3.db (64KB) exists but DB_PATH points to novel_world_zh.db
api_keys.json.txt and .env.txt are stale - code no longer reads them

## 9. LOW Issues (V-008 to V-012)

- V-008: ID generation SELECT MAX()+1 has race condition
- V-009: esc() only escapes " < >, missing backtick and single quote
- V-010: No server-side length/range validation
- V-011: Raw exception details leaked to client
- V-012: CORS allow_origins=["*"]

## 10. Fix Roadmap

| Priority | Task | Est. Time |
|---|---|---|
| P0 | XSS fix (innerHTML to DOM API) | 2-3h |
| P1 | API Key to Header | 2h |
| P1 | Session auth for admin | 3h |
| P1 | Implement missing endpoints | 3h |
| P2 | SQL whitelist + cascade delete | 2h |
| P2 | Clean orphan files | 0.5h |
| P2 | Pydantic model hardening | 1h |
| P3 | esc() upgrade, error handling, CORS | 2.5h |
| P3 | Rate limiting, tests | ongoing |

---
Audit completed 2026-06-17
