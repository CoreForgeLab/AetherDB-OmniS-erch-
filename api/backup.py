"""
Backup API — Data-Centric Backup for Entities and Relations.
Exports all database content (entities, relations, timeline, etc.) as portable JSON.
"""
import os, json, shutil, time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from services.logger import get_logger

router = APIRouter(prefix="/api/backup", tags=["backup"])
BACKUP_DIR = "备份内容"
DB_PATH = "novel_world_zh.db"
LOG = get_logger()
os.makedirs(BACKUP_DIR, exist_ok=True)

# ── Table query definitions ──
TABLES = {
    "entities": "SELECT * FROM entities WHERE is_active = 1 ORDER BY entity_id",
    "relations": "SELECT * FROM relations ORDER BY id",
    "timeline_events": "SELECT * FROM timeline_events ORDER BY year",
    "tag_index": "SELECT * FROM tag_index ORDER BY id",
    "references_map": "SELECT * FROM references_map ORDER BY id",
    "entity_versions": "SELECT * FROM entity_versions ORDER BY id",
}

# ── Helper functions ──

def _export_data(db_path=DB_PATH):
    '''Export all tables to dict of lists. Returns {table_name: [rows]}.'''
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    data = {}
    for table, query in TABLES.items():
        rows = conn.execute(query).fetchall()
        data[table] = [dict(r) for r in rows]
    conn.close()
    return data

def _import_data(data: dict, db_path=DB_PATH):
    '''Import data dict back into database. Returns {table: count}.'''
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    counts = {}
    for table, rows in data.items():
        if not rows:
            counts[table] = 0
            continue
        columns = list(rows[0].keys())
        placeholders = ', '.join(['?' for _ in columns])
        col_names = ', '.join(columns)
        sql = f'INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})'
        for row in rows:
            values = [row.get(col) for col in columns]
            cursor.execute(sql, values)
        conn.commit()
        counts[table] = len(rows)
    conn.close()
    return counts

def create_data_backup(description=""):
    '''Create a timestamped backup of all database content as JSON.'''
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name = f'worldview_data_{timestamp}'
    backup_path = os.path.join(BACKUP_DIR, name)
    os.makedirs(backup_path, exist_ok=True)

    # Export all data to JSON
    data = _export_data()
    json_files = {}
    for table, rows in data.items():
        filepath = os.path.join(backup_path, f'{table}.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        json_files[table] = filepath

    # Copy raw .db file
    db_copy = os.path.join(backup_path, 'database_snapshot.db')
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, db_copy)

    # Write metadata
    total_entities = len(data.get('entities', []))
    total_relations = len(data.get('relations', []))
    import yaml
    with open('config.yaml', encoding='utf-8') as cf:
        cfg = yaml.safe_load(cf)
    workspace_id = cfg.get('app', {}).get('workspace_id', 'default')
    meta = {
        'name': name, 'timestamp': timestamp,
        'version': 'v1.19.1', 'workspace_id': workspace_id, 'description': description or 'Data backup',
        'counts': {t: len(r) for t, r in data.items()},
        'total_entities': total_entities,
        'total_relations': total_relations,
        'has_db_snapshot': os.path.exists(db_copy),
        'files': {t: f'{t}.json' for t in data},
    }
    with open(os.path.join(backup_path, 'backup_metadata.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    LOG.info('Data backup created: %s (%d entities, %d relations)',
             name, total_entities, total_relations)
    return meta

def list_data_backups():
    '''List all data backups sorted by date (newest first).'''
    backups = []
    for entry in sorted(os.listdir(BACKUP_DIR), reverse=True):
        entry_path = os.path.join(BACKUP_DIR, entry)
        if not os.path.isdir(entry_path) or not entry.startswith('worldview_data_'):
            continue
        meta_path = os.path.join(entry_path, 'backup_metadata.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
        else:
            meta = {'name': entry, 'timestamp': entry.replace('worldview_data_', ''),
                    'description': 'No metadata'}
            meta['size_bytes'] = sum(os.path.getsize(os.path.join(dp, f))
                                 for dp, dn, fns in os.walk(entry_path) for f in fns)
            meta['size_human'] = f'{meta["size_bytes"]/1024:.1f} KB'
        backups.append(meta)
    return backups


# ── API Endpoints ──

@router.post('/create')
async def create_backup(
    description: str = Query('', description='Optional backup description')
):
    '''Create a new data backup of all entities and relations.'''
    try:
        meta = create_data_backup(description)
        return {'status': 'ok', 'backup': meta}
    except Exception as e:
        LOG.error('Backup failed: %s', e)
        raise HTTPException(status_code=500, detail=f'Backup failed: {e}')


@router.get('/list')
async def list_backups():
    '''List all available data backups.'''
    return {'backups': list_data_backups()}


@router.get('/stats')
async def backup_stats():
    '''Get backup statistics.'''
    backups = list_data_backups()
    total_size = sum(b.get('size_bytes', 0) for b in backups)
    latest = backups[0] if backups else None
    return {
        'total_backups': len(backups),
        'total_size_bytes': total_size,
        'total_size_human': f'{total_size/1024/1024:.1f} MB' if total_size > 0 else '0 B',
        'total_entities': latest['total_entities'] if latest else 0,
        'total_relations': latest['total_relations'] if latest else 0,
        'last_backup': latest,
    }


@router.post('/restore/{backup_name}')
async def restore_backup(backup_name: str):
    '''Restore data from a backup. Overwrites current database content.'''
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    if not os.path.exists(backup_path) or not os.path.isdir(backup_path):
        raise HTTPException(status_code=404, detail='Backup not found')
    meta_path = os.path.join(backup_path, 'backup_metadata.json')
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=400, detail='Backup metadata not found')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    try:
        data = {}
        for table in TABLES:
            filepath = os.path.join(backup_path, f'{table}.json')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data[table] = json.load(f)
            else:
                data[table] = []
        counts = _import_data(data)
        LOG.info('Restored from backup: %s (%d entities)',
                 backup_name, counts.get('entities', 0))
        return {'status': 'ok', 'restored': counts, 'backup': meta}
    except Exception as e:
        LOG.error('Restore failed: %s', e)
        raise HTTPException(status_code=500, detail=f'Restore failed: {e}')


@router.post('/cleanup')
async def cleanup_backups(keep: int = Query(10, description='Number to keep')):
    '''Remove old backups, keeping only the N most recent.'''
    backups = list_data_backups()
    if len(backups) <= keep:
        return {'status': 'ok', 'removed': 0, 'message': 'No cleanup needed'}
    to_remove = backups[keep:]
    for b in to_remove:
        path = os.path.join(BACKUP_DIR, b['name'])
        if os.path.exists(path):
            shutil.rmtree(path)
    LOG.info('Cleaned up %d old backups, kept %d', len(to_remove), keep)
    return {'status': 'ok', 'removed': len(to_remove), 'kept': keep}

# ── Auto-backup Toggle ──

@router.get('/auto-backup')
async def get_auto_backup():
    '''Check whether auto-backup on startup is enabled.'''
    import yaml
    with open('config.yaml', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    enabled = cfg.get('backup', {}).get('auto_backup_on_startup', True)
    return {'auto_backup_on_startup': enabled}


@router.post('/auto-backup')
async def set_auto_backup(enabled: bool = Query(..., description='true=enable, false=disable')):
    '''Enable or disable auto-backup on server startup.'''
    import yaml
    with open('config.yaml', 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    if 'backup' not in cfg:
        cfg['backup'] = {}
    cfg['backup']['auto_backup_on_startup'] = enabled
    with open('config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
    status = 'enabled' if enabled else 'disabled'
    LOG.info('Auto-backup %s', status)
    return {'auto_backup_on_startup': enabled, 'status': 'updated'}
