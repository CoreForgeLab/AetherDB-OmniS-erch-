import urllib.request, json, sys

try:
    req = urllib.request.Request('http://localhost:8000/entries/', method='GET')
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = resp.read().decode()
        print(f"RUNNING - Status: {resp.status}")
        entries = json.loads(data)
        print(f"Entries count: {len(entries) if isinstance(entries, list) else 'N/A'}")
except urllib.error.URLError as e:
    print(f"NOT_RUNNING - {e.reason}")
except Exception as e:
    print(f"ERROR - {e}")
