import os

SQ = chr(39)  # single quote

# ── Update api/backup.py ──
f = open('api/backup.py', 'r', encoding='utf-8-sig').read()

# 1. Insert workspace_id reading before meta block
ins = '    import yaml\n    with open(' + SQ + 'config.yaml' + SQ + ', encoding=' + SQ + 'utf-8' + SQ + ') as cf:\n        cfg = yaml.safe_load(cf)\n    workspace_id = cfg.get(' + SQ + 'app' + SQ + ', {}).get(' + SQ + 'workspace_id' + SQ + ', ' + SQ + 'default' + SQ + ')\n'
f = f.replace('    meta = {', ins + '    meta = {')

# 2. Add workspace_id to metadata dict
old_meta = SQ + 'version' + SQ + ': ' + SQ + 'v1.18.0' + SQ + ', ' + SQ + 'description' + SQ + ': description or ' + SQ + 'Data backup' + SQ
new_meta = SQ + 'version' + SQ + ': ' + SQ + 'v1.18.0' + SQ + ', ' + SQ + 'workspace_id' + SQ + ': workspace_id, ' + SQ + 'description' + SQ + ': description or ' + SQ + 'Data backup' + SQ
f = f.replace(old_meta, new_meta)

# Also update CLI variant
old_meta2 = SQ + 'version' + SQ + ': ' + SQ + 'v1.18.0' + SQ + ', ' + SQ + 'description' + SQ + ': description or ' + SQ + 'CLI data backup' + SQ
new_meta2 = SQ + 'version' + SQ + ': ' + SQ + 'v1.18.0' + SQ + ', ' + SQ + 'workspace_id' + SQ + ': workspace_id, ' + SQ + 'description' + SQ + ': description or ' + SQ + 'CLI data backup' + SQ
f = f.replace(old_meta2, new_meta2)

open('api/backup.py', 'w', encoding='utf-8').write(f)
print('api/backup.py updated')


# ── Update scripts/backup.py ──
f = open('scripts/backup.py', 'r', encoding='utf-8-sig').read()

# Same insertion before meta block
f = f.replace('    meta = {', ins + '    meta = {')

# Same metadata update for CLI
old_meta3 = SQ + 'version' + SQ + ': ' + SQ + 'v1.18.0' + SQ + ', ' + SQ + 'description' + SQ + ': description or ' + SQ + 'CLI data backup' + SQ
new_meta3 = SQ + 'version' + SQ + ': ' + SQ + 'v1.18.0' + SQ + ', ' + SQ + 'workspace_id' + SQ + ': workspace_id, ' + SQ + 'description' + SQ + ': description or ' + SQ + 'CLI data backup' + SQ
f = f.replace(old_meta3, new_meta3)

open('scripts/backup.py', 'w', encoding='utf-8').write(f)
print('scripts/backup.py updated')
