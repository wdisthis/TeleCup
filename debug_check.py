"""Quick diagnostic script to inspect vault database and test sync flow."""

import sys
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "storage" / "vault.db"

print("=" * 60)
print("TeleCup Diagnostic Check")
print("=" * 60)

if not DB_PATH.exists():
    print(f"[ERROR] vault.db not found at: {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Count tables
print("\n--- TABLE COUNTS ---")
for table in ["folders", "files", "messages", "sync_state"]:
    cur.execute(f"SELECT COUNT(*) as cnt FROM {table};")
    print(f"  {table}: {cur.fetchone()['cnt']} rows")

# 2. Show all files
print("\n--- FILES IN VAULT (all) ---")
cur.execute("""
    SELECT f.id, f.name, f.ext, f.category, f.size_str,
           f.folder_id, f.is_fav, f.local_path, f.date_added
    FROM files f
    ORDER BY f.id DESC
    LIMIT 20;
""")
rows = cur.fetchall()
if not rows:
    print("  (none)")
else:
    for r in rows:
        lp = r["local_path"] or "(no path)"
        print(f"  ID={r['id']} | {r['name']} | {r['size_str']} | folder_id={r['folder_id']} | local_path={lp[:60]}")

# 3. Show folders
print("\n--- VIRTUAL FOLDERS ---")
cur.execute("SELECT id, name, parent_id FROM folders ORDER BY parent_id IS NOT NULL, name;")
for r in cur.fetchall():
    indent = "  " if r["parent_id"] is None else "    └─ "
    print(f"{indent}ID={r['id']} | {r['name']} (parent={r['parent_id']})")

# 4. Sync state
print("\n--- SYNC STATE ---")
cur.execute("SELECT key, value, updated_at FROM sync_state;")
rows = cur.fetchall()
if not rows:
    print("  (empty - sync has never run successfully)")
else:
    for r in rows:
        print(f"  {r['key']} = {r['value']}  (updated: {r['updated_at']})")

# 5. Check storage/files/ directory
FILES_DIR = Path(__file__).parent / "storage" / "files"
print(f"\n--- storage/files/ DIRECTORY ---")
if not FILES_DIR.exists():
    print("  (directory does not exist - sync has not downloaded anything yet)")
else:
    files = list(FILES_DIR.iterdir())
    print(f"  {len(files)} file(s) on disk")
    for f in files[:10]:
        print(f"    {f.name}  ({f.stat().st_size} bytes)")
    if len(files) > 10:
        print(f"    ... and {len(files) - 10} more")

# 6. Test get_files() query manually
print("\n--- SIMULATING get_files(category='all', folder_id=None) ---")
query = """
    SELECT f.id, f.name, f.ext, f.category, f.folder_id
    FROM files f
    LEFT JOIN messages m ON f.telegram_msg_id = m.id
    LEFT JOIN folders fo ON f.folder_id = fo.id
    WHERE 1=1
    ORDER BY f.date_added DESC, f.id DESC
"""
cur.execute(query)
rows = cur.fetchall()
print(f"  Result: {len(rows)} file(s) returned")
for r in rows[:5]:
    print(f"    id={r['id']} | {r['name']} | category={r['category']} | folder_id={r['folder_id']}")

conn.close()
print("\n" + "=" * 60)
print("Diagnosis complete.")

