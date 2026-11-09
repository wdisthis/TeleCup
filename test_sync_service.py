"""
Standalone sync test: run SyncService directly without the Qt UI.
Run: .\.venv\Scripts\python.exe test_sync_service.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import DatabaseManager
from src.telegram_client import TelegramManager
from src.sync_service import SyncService

print("=" * 60)
print("Standalone Sync Service Test")
print("=" * 60)

# 1. Init
print("\n[1] Initializing database...")
db = DatabaseManager()
print("    DB OK")

print("[2] Initializing Telegram client...")
tg = TelegramManager()
print("    TG OK")

print("[3] Checking authorization...")
is_auth = tg.is_authorized()
print(f"    Authorized: {is_auth}")
if not is_auth:
    print("    ERROR: Not authorized. Please run app.py and log in first.")
    sys.exit(1)

me = tg.get_me_info()
print(f"    Logged in as: {me.get('first_name')} (@{me.get('username')})")

# 2. Run sync (limit=10 messages to keep it fast for testing)
print("\n[4] Running sync (limit=10 messages, downloads skipped for speed)...")
print("-" * 60)

sync = SyncService(db, tg)

def on_progress(data):
    phase = data.get("phase", "")
    msg   = data.get("message", "")
    stats = data.get("stats", {})
    print(f"  [{phase.upper():10s}] {msg}")
    if stats:
        s = stats
        print(f"             scanned={s.get('scanned_messages',0)} "
              f"found={s.get('total_files_found',0)} "
              f"synced={s.get('synced_files',0)} "
              f"skipped={s.get('skipped_files',0)} "
              f"errors={s.get('errors',0)}")

def is_cancelled():
    return False

try:
    # Only scan metadata, do NOT download (limit=5 messages, quick test)
    # To test download set limit=5
    result = sync.sync_saved_messages(
        progress_callback=on_progress,
        is_cancelled_callback=is_cancelled,
        limit=5,
    )
    print("-" * 60)
    print(f"\n[5] Sync result: {result}")
except Exception as e:
    import traceback
    print(f"\n[ERROR] Sync failed with exception:")
    traceback.print_exc()
    sys.exit(1)

# 3. Check DB after sync
print("\n[6] Database after sync:")
from src.database import DatabaseManager as DB2
db2 = DB2()
files = db2.get_files()
msgs_count = len(files)
print(f"    Files in vault: {msgs_count}")
for f in files[:5]:
    print(f"    - {f['name']} | {f['size_str']} | local_path={f.get('local_path')}")

print("\nDone.")

