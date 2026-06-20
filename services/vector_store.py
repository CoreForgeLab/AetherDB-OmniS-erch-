import math, sqlite3, json, time, struct
from typing import List, Optional
from dataclasses import dataclass
from services.embedding import EmbeddingProvider

VECTOR_DIMS = 1024  # bge-m3
CHUNK_SIZE = 512
CHUNK_OVERLAP = 128

@dataclass
class SearchResult:
    entity_id: str
    title: str
    entity_type: str
    importance: int
    chunk_text: str
    score: float
    book_id: str
    translated_title: str = ""
    translated_content: str = ""

class VectorStore:
    def __init__(self, db_path, embedding_provider):
        self.db_path = db_path
        self.embedding = embedding_provider

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(conn)
        conn.row_factory = sqlite3.Row
        return conn
    def init_db(self):
        conn = self._get_conn()
        sql = '''CREATE TABLE IF NOT EXISTS vector_chunks (
            chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            chunk_type TEXT NOT NULL,
            chunk_index INTEGER DEFAULT 0,
            chunk_text TEXT NOT NULL,
            embedding BLOB,
            token_count INTEGER DEFAULT 0,
            book_id TEXT DEFAULT 'default',
            entity_type TEXT DEFAULT '',
            importance INTEGER DEFAULT 5
        );
        CREATE INDEX IF NOT EXISTS idx_vc_entity ON vector_chunks(entity_id);
        CREATE INDEX IF NOT EXISTS idx_vc_book ON vector_chunks(book_id);'''
        conn.executescript(sql)
        conn.close()
    def _chunk_text(self, text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:])
                break
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def add_entity(self, entity_id, title, content, full_content, ai_summary, entity_type, importance, tags, book_id='default'):
        chunks = []
        # Title chunk
        chunks.append(('title', title))
        # Summary chunk
        if ai_summary:
            chunks.append(('summary', ai_summary[:500]))
        # Content chunks
        source = full_content or content
        if source:
            for i, c in enumerate(self._chunk_text(source)):
                chunks.append(('content', c, i))
        # Tag chunks
        for tag in tags[:10]:
            chunks.append(('tag', tag))
        # Generate embeddings
        texts = [c[1] for c in chunks]
        embeddings = self.embedding.embed_batch(texts)
        # Store
        conn = self._get_conn()
        try:
            for idx, ci in enumerate(chunks):
                ctype = ci[0]
                ctext = ci[1]
                cindex = ci[2] if len(ci) > 2 else 0
                emb_blob = sqlite3.Binary(bytes())
                if idx < len(embeddings):
                    vec = embeddings[idx]
                    emb_blob = sqlite3.Binary(struct.pack('%df' % len(vec), *vec))
                conn.execute(
                    'INSERT INTO vector_chunks '
                    '(entity_id, chunk_type, chunk_index, chunk_text, '
                    'embedding, token_count, book_id, entity_type, importance) '
                    'VALUES (?,?,?,?,?,?,?,?,?)',
                    (entity_id, ctype, cindex, ctext, emb_blob,
                     len(ctext.split()), book_id, entity_type, importance)
                )
            conn.commit()
        finally:
            conn.close()
    def delete_entity(self, entity_id):
        conn = self._get_conn()
        conn.execute('DELETE FROM vector_chunks WHERE entity_id = ?', (entity_id,))
        conn.commit()
        conn.close()

    def update_entity(self, entity_id, title=None, content=None, full_content=None,
                      ai_summary=None, entity_type=None, importance=None,
                      tags=None, book_id=None):
        self.delete_entity(entity_id)
        self.add_entity(
            entity_id,
            title or '',
            content or '',
            full_content or '',
            ai_summary or '',
            entity_type or '',
            importance or 5,
            tags or [],
            book_id or 'default'
        )

    def search(self, query, top_k=10, filter_type=None, book_id=None, lang=None):
        query_vec = self.embedding.embed(query)
        vec_results = self._vector_search(query_vec, top_k * 2, filter_type, book_id)
        kw_results = self._keyword_search(query, top_k * 2, filter_type, book_id)
        results = self._rrf_merge([vec_results, kw_results], top_k)
        if lang:
            results = self._enrich_with_translations(results, lang)
        return results

    def _vector_search(self, query_vec, top_k, filter_type=None, book_id=None):
        conn = self._get_conn()
        try:
            blob = struct.pack('%df' % len(query_vec), *query_vec)
            sql = 'SELECT chunk_id, entity_id, chunk_text, book_id, entity_type, importance FROM vector_chunks WHERE 1=1'
            params = []
            if filter_type:
                sql += ' AND entity_type = ?'
                params.append(filter_type)
            if book_id:
                sql += ' AND book_id = ?'
                params.append(book_id)
            if filter_type or book_id:
                sql += ' AND embedding IS NOT NULL ORDER BY embedding MATCH ? LIMIT ?'
            else:
                sql += ' ORDER BY embedding MATCH ? LIMIT ?'
            params.append(blob)
            params.append(top_k)
            rows = conn.execute(sql, params).fetchall()
            results = []
            for row in rows:
                results.append(SearchResult(
                    entity_id=row['entity_id'],
                    title='',
                    entity_type=row['entity_type'],
                    importance=row['importance'],
                    chunk_text=row['chunk_text'][:200],
                    score=0.5,
                    book_id=row['book_id']
                ))
            return results
        except Exception as e:
            print('Vector search error:', e)
            return []
        finally:
            conn.close()

    def _keyword_search(self, query, top_k, filter_type=None, book_id=None):
        conn = self._get_conn()
        try:
            kw = '%%%s%%' % query
            sql = 'SELECT chunk_id, entity_id, chunk_text, book_id, entity_type, importance FROM vector_chunks WHERE chunk_text LIKE ?'
            params = [kw]
            if filter_type:
                sql += ' AND entity_type = ?'
                params.append(filter_type)
            if book_id:
                sql += ' AND book_id = ?'
                params.append(book_id)
            sql += ' LIMIT ?'
            params.append(top_k)
            rows = conn.execute(sql, params).fetchall()
            results = []
            for row in rows:
                results.append(SearchResult(
                    entity_id=row['entity_id'],
                    title='',
                    entity_type=row['entity_type'],
                    importance=row['importance'],
                    chunk_text=row['chunk_text'][:200],
                    score=0.3,
                    book_id=row['book_id']
                ))
            return results
        except Exception as e:
            print('Keyword search error:', e)
            return []
        finally:
            conn.close()

    
    def _enrich_with_translations(self, results, lang):
        conn = self._get_conn()
        try:
            for r in results:
                c = conn.cursor()
                c.execute("SELECT title, content FROM entity_translations WHERE entity_id=? AND language=?", (r.entity_id, lang))
                trans = c.fetchone()
                if trans:
                    r.translated_title = trans["title"]
                    r.translated_content = trans["content"] or ""
        except:
            pass
        finally:
            conn.close()
        return results

    def _rrf_merge(self, results_lists, top_k, k=60):
        scores = {}
        data = {}
        for rank, results in enumerate(results_lists):
            for i, r in enumerate(results):
                if r.entity_id not in scores:
                    scores[r.entity_id] = 0
                    data[r.entity_id] = r
                scores[r.entity_id] += 1.0 / (k + i + 1)
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
        for eid in sorted_ids:
            data[eid].score = scores[eid]
        return [data[eid] for eid in sorted_ids]
