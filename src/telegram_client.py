"""Telegram MTProto Client wrapper using Telethon with a dedicated persistent asyncio loop."""

import json
import asyncio
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    FloodWaitError,
)
from telethon.tl.types import User

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.json"
STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"


def load_settings() -> Dict[str, Any]:
    """Load api_id and api_hash from config/settings.json."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TelegramManager:
    """Manages Telethon MTProto client with a single dedicated background asyncio loop."""

    def __init__(self):
        settings = load_settings()
        self.api_id = int(settings.get("api_id", 0))
        self.api_hash = str(settings.get("api_hash", "")).strip()
        self.session_name = str(settings.get("session_name", "telecup")).strip()

        if not self.api_id or not self.api_hash:
            raise ValueError("api_id and api_hash must be configured in config/settings.json")

        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.session_file = str(STORAGE_DIR / self.session_name)

        # ── Start a single dedicated background thread with its own persistent loop ──
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Initialize Telethon Client permanently inside this dedicated loop
        future = asyncio.run_coroutine_threadsafe(self._init_client(), self.loop)
        future.result()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _init_client(self):
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash, loop=self.loop)

    def run_async(self, coro):
        """Schedule coroutine on the dedicated Telethon loop and wait for result."""
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    # ── Connection & Authentication APIs ──

    def is_authorized(self) -> bool:
        """Check if user has an active, valid login session."""
        async def _do():
            if not self.client.is_connected():
                await self.client.connect()
            return await self.client.is_user_authorized()

        return self.run_async(_do())

    def get_me_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user info."""
        async def _do():
            if not self.client.is_connected():
                await self.client.connect()
            if not await self.client.is_user_authorized():
                return None
            me = await self.client.get_me()
            if isinstance(me, User):
                return {
                    "id": me.id,
                    "first_name": me.first_name or "",
                    "last_name": me.last_name or "",
                    "username": me.username or "",
                    "phone": me.phone or "",
                }
            return None

        return self.run_async(_do())

    def request_code(self, phone: str) -> str:
        """Send login code to user's Telegram app/phone. Returns phone_code_hash."""
        async def _do():
            if not self.client.is_connected():
                await self.client.connect()
            try:
                res = await self.client.send_code_request(phone.strip())
                return res.phone_code_hash
            except PhoneNumberInvalidError:
                raise ValueError("Nomor telepon tidak valid. Pastikan gunakan format internasional (+62...).")
            except FloodWaitError as e:
                raise RuntimeError(f"Terlalu banyak permintaan login. Harap tunggu {e.seconds} detik.")

        return self.run_async(_do())

    def sign_in_code(self, phone: str, code: str, phone_code_hash: str) -> Dict[str, Any]:
        """Verify OTP login code."""
        async def _do():
            if not self.client.is_connected():
                await self.client.connect()
            try:
                await self.client.sign_in(
                    phone=phone.strip(),
                    code=code.strip(),
                    phone_code_hash=phone_code_hash.strip(),
                )
                me = await self.client.get_me()
                return {
                    "id": me.id,
                    "first_name": me.first_name or "",
                    "last_name": me.last_name or "",
                    "username": me.username or "",
                    "phone": me.phone or "",
                }
            except SessionPasswordNeededError:
                raise SessionPasswordNeededError("Akun ini dilindungi Two-Step Verification (2FA). Masukkan kata sandi Anda.")
            except PhoneCodeInvalidError:
                raise ValueError("Kode verifikasi salah. Silakan periksa kembali pesan resmi dari Telegram.")
            except PhoneCodeExpiredError:
                raise ValueError("Kode verifikasi telah kedaluwarsa. Silakan minta kode baru.")

        return self.run_async(_do())

    def sign_in_2fa(self, password: str) -> Dict[str, Any]:
        """Sign in with 2FA password."""
        async def _do():
            if not self.client.is_connected():
                await self.client.connect()
            try:
                await self.client.sign_in(password=password.strip())
                me = await self.client.get_me()
                return {
                    "id": me.id,
                    "first_name": me.first_name or "",
                    "last_name": me.last_name or "",
                    "username": me.username or "",
                    "phone": me.phone or "",
                }
            except Exception as e:
                raise ValueError(f"Gagal verifikasi kata sandi 2FA: {e}")

        return self.run_async(_do())

    def fetch_saved_messages_sample(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Read recent messages from Telegram Saved Messages ('me')."""
        async def _do():
            if not self.client.is_connected():
                await self.client.connect()
            if not await self.client.is_user_authorized():
                raise RuntimeError("Klien belum terautentikasi.")

            messages = []
            async for msg in self.client.iter_messages("me", limit=limit):
                has_media = bool(msg.media)
                file_name = None
                if msg.file and msg.file.name:
                    file_name = msg.file.name

                messages.append({
                    "id": msg.id,
                    "date": str(msg.date),
                    "text": msg.text or "",
                    "has_media": has_media,
                    "file_name": file_name,
                    "size_bytes": msg.file.size if msg.file else 0,
                })
            return messages

        return self.run_async(_do())

    def disconnect(self):
        """Disconnect client safely."""
        async def _do():
            if self.client.is_connected():
                await self.client.disconnect()

        self.run_async(_do())
