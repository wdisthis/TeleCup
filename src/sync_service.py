"""Synchronization service for Telegram Saved Messages and attachment downloads."""

import os
import shutil
import hashlib
import asyncio
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from .database import DatabaseManager
from .telegram_client import TelegramManager

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
FILES_DIR = STORAGE_DIR / "files"
TEMP_DIR = STORAGE_DIR / "temp"


def ensure_storage_dirs():
    """Ensure destination directories exist."""
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def extract_media_info(msg) -> Optional[Dict[str, Any]]:
    """Extract safe file metadata from a Telethon Message object."""
    if not msg.media:
        return None

    filename = None
    ext = ""
    mime_type = ""
    size_bytes = 0

    if msg.file:
        filename = msg.file.name
        ext = (msg.file.ext or "").lstrip(".").lower()
        mime_type = msg.file.mime_type or ""
        size_bytes = msg.file.size or 0

    if not filename:
        if msg.photo:
            ext = "jpg"
            mime_type = "image/jpeg"
            filename = f"photo_{msg.id}.jpg"
        elif msg.video:
            ext = "mp4"
            mime_type = "video/mp4"
            filename = f"video_{msg.id}.mp4"
        elif msg.voice:
            ext = "ogg"
            mime_type = "audio/ogg"
            filename = f"voice_{msg.id}.ogg"
        elif msg.audio:
            ext = "mp3"
            mime_type = "audio/mpeg"
            filename = f"audio_{msg.id}.mp3"
        elif ext:
            filename = f"attachment_{msg.id}.{ext}"
        else:
            ext = "bin"
            filename = f"file_{msg.id}.bin"

    # Sanitize filename for Windows filesystem
    safe_name = "".join(c for c in filename if c not in r'\/:*?"<>|').strip()
    if not safe_name:
        safe_name = f"file_{msg.id}.{ext if ext else 'bin'}"

    clean_ext = ext if ext else (safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else "bin")

    return {
        "filename": safe_name,
        "ext": clean_ext,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
    }


class SyncService:
    """Coordinates reading Saved Messages, downloading attachments, and updating SQLite database."""

    def __init__(self, db: DatabaseManager, tg: TelegramManager):
        self.db = db
        self.tg = tg
        ensure_storage_dirs()

    def sync_saved_messages(
        self,
        progress_callback: Callable[[Dict[str, Any]], None],
        is_cancelled_callback: Callable[[], bool],
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Synchronize Saved Messages and download attachments in the background loop."""

        async def _do_sync():
            if not self.tg.client.is_connected():
                await self.tg.client.connect()
            if not await self.tg.client.is_user_authorized():
                raise RuntimeError("Akun Telegram belum terotentikasi.")

            stats = {
                "scanned_messages": 0,
                "total_files_found": 0,
                "synced_files": 0,
                "skipped_files": 0,
                "errors": 0,
            }

            progress_callback({
                "phase": "scanning",
                "message": "Menghubungi Saved Messages Telegram...",
                "stats": stats,
            })

            # Fetch messages from Saved Messages ("me")
            # We iterate through messages
            max_msg_id = 0

            async for msg in self.tg.client.iter_messages("me", limit=limit):
                if is_cancelled_callback():
                    progress_callback({
                        "phase": "cancelled",
                        "message": "Sinkronisasi dihentikan oleh pengguna.",
                        "stats": stats,
                    })
                    return stats

                stats["scanned_messages"] += 1
                if msg.id > max_msg_id:
                    max_msg_id = msg.id

                # 1. Save Message metadata to database
                date_str = str(msg.date).split("+")[0].strip() if msg.date else ""
                caption = msg.text or ""
                self.db.save_message(
                    msg_id=msg.id,
                    chat_id=None,
                    date_str=date_str,
                    text=caption,
                    sender_name="Saved Messages",
                )

                # 2. Check if message has media/attachment
                media_info = extract_media_info(msg)
                if not media_info:
                    continue

                stats["total_files_found"] += 1
                raw_filename = media_info["filename"]
                ext = media_info["ext"]
                size_bytes = media_info["size_bytes"]
                mime_type = media_info["mime_type"]

                # 3. Check if file already exists in SQLite and on local disk
                existing_file = self.db.get_file_by_msg_id(msg.id)
                if existing_file and existing_file.get("local_path"):
                    local_p = Path(existing_file["local_path"])
                    if local_p.exists() and local_p.stat().st_size > 0:
                        stats["skipped_files"] += 1
                        progress_callback({
                            "phase": "downloading",
                            "message": f"Sudah tersimpan: {raw_filename}",
                            "filename": raw_filename,
                            "current_bytes": size_bytes,
                            "total_bytes": size_bytes,
                            "stats": stats,
                        })
                        continue

                # 4. Prepare local staging file in storage/temp/
                temp_filename = f"dl_{msg.id}_{raw_filename}"
                temp_path = TEMP_DIR / temp_filename

                # Final destination in storage/files/
                dest_filename = f"{msg.id}_{raw_filename}"
                final_path = FILES_DIR / dest_filename

                progress_callback({
                    "phase": "downloading",
                    "message": f"Mengunduh ({stats['synced_files'] + 1}): {raw_filename}",
                    "filename": raw_filename,
                    "current_bytes": 0,
                    "total_bytes": size_bytes,
                    "stats": stats,
                })

                # Progress callback for Telethon download
                def on_download_progress(received_bytes, total):
                    if is_cancelled_callback():
                        raise asyncio.CancelledError("Download aborted by user")
                    progress_callback({
                        "phase": "downloading",
                        "message": f"Mengunduh: {raw_filename}",
                        "filename": raw_filename,
                        "current_bytes": received_bytes,
                        "total_bytes": total or size_bytes,
                        "stats": stats,
                    })

                try:
                    # Download media using Telethon client
                    downloaded_file = await self.tg.client.download_media(
                        msg,
                        file=str(temp_path),
                        progress_callback=on_download_progress,
                    )

                    if is_cancelled_callback():
                        if temp_path.exists():
                            temp_path.unlink(missing_ok=True)
                        progress_callback({
                            "phase": "cancelled",
                            "message": "Sinkronisasi dibatalkan.",
                            "stats": stats,
                        })
                        return stats

                    if downloaded_file and Path(downloaded_file).exists():
                        # Compute SHA-256 checksum
                        file_sha = calculate_sha256(Path(downloaded_file))
                        actual_size = Path(downloaded_file).stat().st_size

                        # Move from temp to final storage
                        shutil.move(downloaded_file, str(final_path))

                        # Save file record into database
                        self.db.add_file(
                            name=raw_filename,
                            ext=ext,
                            size_bytes=actual_size,
                            date_added=date_str,
                            telegram_msg_id=msg.id,
                            mime_type=mime_type,
                            sha256=file_sha,
                            local_path=str(final_path),
                            folder_id=None,
                        )

                        stats["synced_files"] += 1
                        progress_callback({
                            "phase": "downloading",
                            "message": f"Berhasil disimpan: {raw_filename}",
                            "filename": raw_filename,
                            "current_bytes": actual_size,
                            "total_bytes": actual_size,
                            "stats": stats,
                        })
                    else:
                        stats["errors"] += 1

                except asyncio.CancelledError:
                    if temp_path.exists():
                        temp_path.unlink(missing_ok=True)
                    progress_callback({
                        "phase": "cancelled",
                        "message": "Sinkronisasi dibatalkan oleh pengguna.",
                        "stats": stats,
                    })
                    return stats
                except Exception as e:
                    stats["errors"] += 1
                    if temp_path.exists():
                        temp_path.unlink(missing_ok=True)
                    progress_callback({
                        "phase": "warning",
                        "message": f"Gagal mengunduh {raw_filename}: {str(e)}",
                        "filename": raw_filename,
                        "current_bytes": 0,
                        "total_bytes": size_bytes,
                        "stats": stats,
                    })

            # Update last synced message id in SQLite
            if max_msg_id > 0:
                prev_max = self.db.get_last_synced_msg_id()
                if max_msg_id > prev_max:
                    self.db.set_last_synced_msg_id(max_msg_id)

            progress_callback({
                "phase": "completed",
                "message": "Sinkronisasi selesai.",
                "stats": stats,
            })
            return stats

        # Run coroutine inside the dedicated Telethon persistent event loop
        return self.tg.run_async(_do_sync())
