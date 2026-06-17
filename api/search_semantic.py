import os
from fastapi import APIRouter, Query, Body, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(tags=['semantic_search'])

class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filter_type: Optional[str] = None
    book_id: Optional[str] = None
    use_hybrid: bool = True

@router.post('/api/search/semantic')
async def semantic_search(req: SemanticSearchRequest, request: Request, api_key: str = Query(None)):
    # Dual auth: X-API-Key header or query param
    key = request.headers.get("X-API-Key") or api_key
    expected = os.environ.get("NOVEL_API_KEY") or ""
    if key != expected and expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
    store = request.app.state.vector_store
    if not store:
        raise HTTPException(500, 'Vector store not initialized')
    results = store.search(
        query=req.query,
        top_k=req.top_k,
        filter_type=req.filter_type,
        book_id=req.book_id
    )
    return {
        'results': [
            {
                'entity_id': r.entity_id,
                'title': r.title,
                'type': r.entity_type,
                'importance': r.importance,
                'content_preview': r.chunk_text[:200],
                'score': round(r.score, 4),
                'book_id': r.book_id
            }
            for r in results
        ],
        'total': len(results),
        'search_method': 'hybrid' if req.use_hybrid else 'vector',
        'query': req.query
    }
