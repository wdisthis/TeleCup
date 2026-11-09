"""
Test script: Connect to Telegram and peek at Saved Messages directly.
Run: .\.venv\Scripts\python.exe test_sync.py
"""

import asyncio
import json
from pathlib import Path

CONFIG_PATH = Path("config/settings.json")
STORAGE_DIR = Path("storage")

with open(CONFIG_PATH, "r") as f:
    settings = json.load(f)

api_id = int(settings["api_id"])
api_hash = settings["api_hash"].strip()
session_file = str(STORAGE_DIR / settings.get("session_name", "telecup"))

from telethon import TelegramClient
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

async def main():
    print("Connecting to Telegram...")
    async with TelegramClient(session_file, api_id, api_hash) as client:
        me = await client.get_me()
        print(f"Logged in as: {me.first_name} (@{me.username}) | ID: {me.id}")
        print()

        print("Fetching last 20 messages from Saved Messages ('me')...")
        print("-" * 60)
        count = 0
        files_found = 0
        async for msg in client.iter_messages("me", limit=20):
            count += 1
            has_media = bool(msg.media)
            has_file = bool(msg.file)
            fname = msg.file.name if msg.file else None
            fsize = msg.file.size if msg.file else 0
            fext  = (msg.file.ext or "").lstrip(".") if msg.file else ""
            text_preview = (msg.text or "")[:50].replace("\n", " ")

            if has_media:
                files_found += 1
                print(f"  MSG #{msg.id} | has_file={has_file} | name={fname} | ext={fext} | size={fsize}B | text: {text_preview}")
            else:
                print(f"  MSG #{msg.id} | text only: {text_preview}")

        print("-" * 60)
        print(f"Scanned: {count} messages | Files detected: {files_found}")

        if files_found == 0:
            print()
            print("NOTE: No media/attachments found in the last 20 Saved Messages.")
            print("  - Make sure you have forwarded/saved files to your Saved Messages chat in Telegram.")
            print("  - Open Telegram -> click your own name at top -> forward a PDF/image/video there to test.")

asyncio.run(main())

