"""SQLite Database Manager for TeleCup local archive."""

import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "storage" / "vault.db"

# Category mappings based on file extension
CATEGORY_MAP = {
    "pdf": "documents", "doc": "documents", "docx": "documents",
    "txt": "documents", "xls": "documents", "xlsx": "documents",
    "ppt": "documents", "pptx": "documents", "md": "documents", "csv": "documents",
    
    "png": "images", "jpg": "images", "jpeg": "images",
    "gif": "images", "webp": "images", "svg": "images", "bmp": "images",
    
    "mp3": "media", "mp4": "media", "mkv": "media",
    "wav": "media", "ogg": "media", "m4a": "media", "flac": "media", "mov": "media",
    
    "zip": "archives", "rar": "archives", "7z": "archives", "tar": "archives", "gz": "archives",
}


def infer_category(ext: str) -> str:
    """Infer category from file extension."""
    return CATEGORY_MAP.get(ext.lower().lstrip("."), "documents")


def format_size(size_bytes: int) -> str:
    """Format bytes into readable string (e.g. 2.4 MB, 420 KB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class DatabaseManager:
    """Manages SQLite connection and CRUD operations for TeleCup."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        """Create tables and indexes if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Virtual Folders Table (Hierarchical with parent_id)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    parent_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES folders (id) ON DELETE CASCADE
                );
                """
            )

            # 2. Telegram Messages Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    chat_id INTEGER,
                    date TEXT,
                    text TEXT,
                    sender_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # 3. Files Metadata Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_msg_id INTEGER,
                    name TEXT NOT NULL,
                    ext TEXT NOT NULL,
                    category TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    size_str TEXT NOT NULL,
                    mime_type TEXT,
                    sha256 TEXT,
                    local_path TEXT,
                    folder_id INTEGER DEFAULT NULL,
                    is_fav INTEGER DEFAULT 0,
                    date_added TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_msg_id) REFERENCES messages (id) ON DELETE SET NULL,
                    FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE SET NULL
                );
                """
            )

            # 4. Sync State Key-Value Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Indexes for high performance searches and sorting
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_category ON files (category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_folder ON files (folder_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_fav ON files (is_fav);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files (name);")

            conn.commit()

        # Seed initial starter data if tables are empty
        self._seed_initial_data()

    def _seed_initial_data(self):
        """Populate initial virtual folders and files if database is brand new."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM folders;")
            if cursor.fetchone()["cnt"] == 0:
                cursor.execute("INSERT INTO folders (name, parent_id) VALUES ('Work Projects', NULL);")
                work_id = cursor.lastrowid

                cursor.execute("INSERT INTO folders (name, parent_id) VALUES ('Receipts & Finance', NULL);")
                finance_id = cursor.lastrowid

                cursor.execute("INSERT INTO folders (name, parent_id) VALUES ('Learning & E-books', NULL);")
                learning_id = cursor.lastrowid

                cursor.execute("INSERT INTO folders (name, parent_id) VALUES ('2026', ?);", (work_id,))
                sub_2026_id = cursor.lastrowid

                cursor.execute("INSERT INTO folders (name, parent_id) VALUES ('Q4 Deliverables', ?);", (sub_2026_id,))
                q4_id = cursor.lastrowid

                cursor.execute("INSERT INTO folders (name, parent_id) VALUES ('Client Reviews', ?);", (work_id,))
                reviews_id = cursor.lastrowid

                cursor.execute("INSERT INTO folders (name, parent_id) VALUES ('Tax 2026', ?);", (finance_id,))
                tax_id = cursor.lastrowid

                sample_files = [
                    (1042, "Python_CheatSheet_v2.pdf", "pdf", "documents", 2516582, format_size(2516582), learning_id, 1, "2026-10-28 14:20", "#1042 - Quick Python Guide"),
                    (1039, "Server_Architecture_Diagram.png", "png", "images", 1887436, format_size(1887436), q4_id, 0, "2026-10-27 09:12", "#1039 - Diagram final"),
                    (1025, "Backup_Database_Postgres.zip", "zip", "archives", 15204352, format_size(15204352), sub_2026_id, 0, "2026-10-25 18:00", "#1025 - DB Dump"),
                    (1010, "Meeting_Audio_Transcript.mp3", "mp3", "media", 8598323, format_size(8598323), reviews_id, 1, "2026-10-24 11:30", "#1010 - Voice note recording"),
                    (980, "Receipt_Hosting_AWS_Oct26.pdf", "pdf", "documents", 430080, format_size(430080), tax_id, 0, "2026-10-20 08:45", "#980 - Server invoice"),
                    (964, "App_Demo_Walkthrough.mp4", "mp4", "media", 36805017, format_size(36805017), learning_id, 0, "2026-10-18 20:15", "#964 - Demo testing video"),
                ]

                for msg_id, name, ext, cat, size_b, size_s, f_id, is_fav, date_str, caption in sample_files:
                    cursor.execute(
                        "INSERT OR IGNORE INTO messages (id, date, text) VALUES (?, ?, ?);",
                        (msg_id, date_str, caption)
                    )
                    cursor.execute(
                        """
                        INSERT INTO files (telegram_msg_id, name, ext, category, size_bytes, size_str, folder_id, is_fav, date_added)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (msg_id, name, ext, cat, size_b, size_s, f_id, is_fav, date_str)
                    )

                conn.commit()

    # ── Folder CRUD ──

    def get_all_folders(self) -> List[Dict[str, Any]]:
        """Get all folders sorted by hierarchy."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, parent_id FROM folders ORDER BY parent_id IS NOT NULL, name ASC;")
            return [dict(row) for row in cursor.fetchall()]

    def get_subfolders(self, parent_id: Optional[int]) -> List[Dict[str, Any]]:
        """Get direct child folders of a folder, including item counters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if parent_id is None:
                cursor.execute(
                    """
                    SELECT f.id, f.name, f.parent_id,
                           (SELECT COUNT(*) FROM files WHERE folder_id = f.id) as direct_files,
                           (SELECT COUNT(*) FROM folders WHERE parent_id = f.id) as subfolders_count
                    FROM folders f
                    WHERE f.parent_id IS NULL
                    ORDER BY f.name ASC;
                    """
                )
            else:
                cursor.execute(
                    """
                    SELECT f.id, f.name, f.parent_id,
                           (SELECT COUNT(*) FROM files WHERE folder_id = f.id) as direct_files,
                           (SELECT COUNT(*) FROM folders WHERE parent_id = f.id) as subfolders_count
                    FROM folders f
                    WHERE f.parent_id = ?
                    ORDER BY f.name ASC;
                    """,
                    (parent_id,)
                )
            rows = cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                item["path"] = self.get_folder_path(item["id"])
                result.append(item)
            return result

    def add_folder(self, name: str, parent_id: Optional[int] = None) -> int:
        """Create a new folder or subfolder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO folders (name, parent_id) VALUES (?, ?);",
                (name.strip(), parent_id)
            )
            conn.commit()
            return cursor.lastrowid

    def rename_folder(self, folder_id: int, new_name: str):
        """Rename an existing folder."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE folders SET name = ? WHERE id = ?;", (new_name.strip(), folder_id))
            conn.commit()

    def delete_folder(self, folder_id: int):
        """Delete folder and its nested subfolders (files inside have folder_id set to NULL)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM folders WHERE id = ?;", (folder_id,))
            conn.commit()

    def get_folder_path(self, folder_id: Optional[int]) -> str:
        """Resolve breadcrumb path string (e.g. 'Work Projects / 2026 / Q4 Deliverables')."""
        if not folder_id:
            return ""
        folders = {f["id"]: f for f in self.get_all_folders()}
        parts = []
        curr_id = folder_id
        while curr_id in folders:
            parts.insert(0, folders[curr_id]["name"])
            curr_id = folders[curr_id]["parent_id"]
        return " / ".join(parts)

    def get_descendant_folder_ids(self, folder_id: int) -> List[int]:
        """Get target folder id and all recursive descendant subfolder ids."""
        all_folders = self.get_all_folders()
        result = [folder_id]

        added = True
        while added:
            added = False
            for f in all_folders:
                if f["parent_id"] in result and f["id"] not in result:
                    result.append(f["id"])
                    added = True
        return result

    # ── File CRUD ──

    def get_files(
        self,
        category: Optional[str] = None,
        folder_id: Optional[int] = None,
        search_query: Optional[str] = None,
        sort_key: str = "date_desc"
    ) -> List[Dict[str, Any]]:
        """Query files with filtering, category/folder matching, and sorting."""
        query = """
            SELECT f.id, f.telegram_msg_id, f.name, f.ext, f.category,
                   f.size_bytes, f.size_str, f.mime_type, f.local_path,
                   f.folder_id, f.is_fav, f.date_added,
                   COALESCE(m.text, '') as message,
                   COALESCE(fo.name, '') as folder_name
            FROM files f
            LEFT JOIN messages m ON f.telegram_msg_id = m.id
            LEFT JOIN folders fo ON f.folder_id = fo.id
            WHERE 1=1
        """
        params = []

        # Category filter
        if category and category != "all":
            if category == "favorites":
                query += " AND f.is_fav = 1"
            else:
                query += " AND f.category = ?"
                params.append(category)

        # Folder filter (only files directly in this folder or descendants)
        if folder_id is not None:
            descendants = self.get_descendant_folder_ids(folder_id)
            placeholders = ",".join("?" for _ in descendants)
            query += f" AND f.folder_id IN ({placeholders})"
            params.extend(descendants)

        # Search query (by filename or telegram caption)
        if search_query:
            q = f"%{search_query.strip().lower()}%"
            query += " AND (LOWER(f.name) LIKE ? OR LOWER(m.text) LIKE ?)"
            params.extend([q, q])

        # Sorting
        sort_orders = {
            "date_desc": "f.date_added DESC, f.id DESC",
            "date_asc": "f.date_added ASC, f.id ASC",
            "name_asc": "LOWER(f.name) ASC",
            "size_desc": "f.size_bytes DESC",
        }
        query += f" ORDER BY {sort_orders.get(sort_key, 'f.date_added DESC')}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                item = dict(row)
                item["date"] = item["date_added"]
                item["folder"] = self.get_folder_path(item["folder_id"])
                result.append(item)
            return result

    def toggle_favorite(self, file_id: int) -> bool:
        """Toggle is_fav between 0 and 1. Returns the new state."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_fav FROM files WHERE id = ?;", (file_id,))
            row = cursor.fetchone()
            if not row:
                return False
            new_state = 0 if row["is_fav"] else 1
            cursor.execute("UPDATE files SET is_fav = ? WHERE id = ?;", (new_state, file_id))
            conn.commit()
            return bool(new_state)

    def move_file_to_folder(self, file_id: int, folder_id: Optional[int]):
        """Update file's virtual folder assignment."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE files SET folder_id = ? WHERE id = ?;", (folder_id, file_id))
            conn.commit()

    def delete_file(self, file_id: int):
        """Remove file metadata from vault."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE id = ?;", (file_id,))
            conn.commit()

    def add_file(
        self,
        name: str,
        ext: str,
        size_bytes: int,
        date_added: str,
        telegram_msg_id: Optional[int] = None,
        mime_type: Optional[str] = None,
        sha256: Optional[str] = None,
        local_path: Optional[str] = None,
        folder_id: Optional[int] = None
    ) -> int:
        """Insert a newly synced file metadata into the vault."""
        category = infer_category(ext)
        size_str = format_size(size_bytes)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO files (
                    telegram_msg_id, name, ext, category, size_bytes, size_str,
                    mime_type, sha256, local_path, folder_id, is_fav, date_added
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?);
                """,
                (telegram_msg_id, name, ext.lower(), category, size_bytes, size_str,
                 mime_type, sha256, local_path, folder_id, date_added)
            )
            conn.commit()
            return cursor.lastrowid

    # ── Sync State ──

    def get_sync_state(self, key: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM sync_state WHERE key = ?;", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None

    def set_sync_state(self, key: str, value: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sync_state (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP;",
                (key, value)
            )
            conn.commit()
