"""Modern dark-themed dialogs for Telegram authentication and operations."""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QWidget,
    QMessageBox,
    QProgressBar,
    QFrame,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from telethon.errors import SessionPasswordNeededError
from ..telegram_client import TelegramManager
from ..database import DatabaseManager
from ..sync_service import SyncService


class AsyncAuthWorker(QThread):
    """Background worker thread executing Telegram authentication calls without freezing UI."""

    code_sent = Signal(str)  # phone_code_hash
    login_success = Signal(dict)  # user_info
    password_required = Signal()
    error_occurred = Signal(str)

    def __init__(self, tg: TelegramManager, action: str, **kwargs):
        super().__init__()
        self.tg = tg
        self.action = action
        self.kwargs = kwargs

    def run(self):
        try:
            if self.action == "request_code":
                phone = self.kwargs.get("phone", "")
                code_hash = self.tg.request_code(phone)
                self.code_sent.emit(code_hash)

            elif self.action == "sign_in_code":
                phone = self.kwargs.get("phone", "")
                code = self.kwargs.get("code", "")
                phone_code_hash = self.kwargs.get("phone_code_hash", "")
                try:
                    user_info = self.tg.sign_in_code(phone, code, phone_code_hash)
                    self.login_success.emit(user_info)
                except SessionPasswordNeededError:
                    self.password_required.emit()

            elif self.action == "sign_in_2fa":
                password = self.kwargs.get("password", "")
                user_info = self.tg.sign_in_2fa(password)
                self.login_success.emit(user_info)

        except Exception as e:
            self.error_occurred.emit(str(e))


class TelegramLoginDialog(QDialog):
    """Dialog guiding user through Phone -> OTP -> (optional 2FA) Telegram login."""

    login_successful = Signal(dict)

    def __init__(self, tg_manager: TelegramManager, parent=None):
        super().__init__(parent)
        self.tg = tg_manager
        self.phone_number: str = ""
        self.phone_code_hash: str = ""
        self.worker: Optional[AsyncAuthWorker] = None

        self.setWindowTitle("Telegram Authentication - TeleCup")
        self.setFixedSize(460, 360)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background-color: #18181b;
                color: #e4e4e7;
            }
            QLabel {
                color: #e4e4e7;
            }
            QLineEdit {
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                background-color: #27272a;
                color: #f4f4f5;
            }
            QLineEdit:focus {
                border: 1.5px solid #3b82f6;
            }
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            QPushButton:disabled {
                background-color: #3f3f46;
                color: #71717a;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(14)

        # Header Title
        title_label = QLabel("Connect Telegram Account")
        title_font = QFont("Segoe UI", 14, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff;")
        root_layout.addWidget(title_label)

        # Subtitle
        self.desc_label = QLabel(
            "TeleCup uses official Telegram MTProto API to synchronize your Saved Messages locally."
        )
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #a1a1aa; font-size: 12px; margin-bottom: 6px;")
        root_layout.addWidget(self.desc_label)

        # Stacked Pages
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)

        # ── Page 0: Phone Input ──
        page_phone = QWidget()
        p0_layout = QVBoxLayout(page_phone)
        p0_layout.setContentsMargins(0, 8, 0, 0)
        p0_layout.setSpacing(12)

        lbl_phone = QLabel("Enter your phone number with country code:")
        lbl_phone.setStyleSheet("font-size: 12px; font-weight: 500;")
        p0_layout.addWidget(lbl_phone)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("e.g. +6281234567890")
        p0_layout.addWidget(self.phone_input)

        self.send_code_btn = QPushButton("Send Login Code")
        self.send_code_btn.setCursor(Qt.PointingHandCursor)
        self.send_code_btn.clicked.connect(self._start_request_code)
        p0_layout.addWidget(self.send_code_btn)

        p0_layout.addStretch(1)
        self.stack.addWidget(page_phone)  # Index 0

        # ── Page 1: Verification Code Input ──
        page_code = QWidget()
        p1_layout = QVBoxLayout(page_code)
        p1_layout.setContentsMargins(0, 8, 0, 0)
        p1_layout.setSpacing(12)

        self.lbl_code_info = QLabel("Enter confirmation code sent to your Telegram app:")
        self.lbl_code_info.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.lbl_code_info.setWordWrap(True)
        p1_layout.addWidget(self.lbl_code_info)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. 54321")
        p1_layout.addWidget(self.code_input)

        btn_row = QHBoxLayout()
        self.back_to_phone_btn = QPushButton("Back")
        self.back_to_phone_btn.setStyleSheet(
            "background-color: #27272a; border: 1px solid #3f3f46; color: #e4e4e7;"
        )
        self.back_to_phone_btn.setCursor(Qt.PointingHandCursor)
        self.back_to_phone_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))

        self.verify_code_btn = QPushButton("Verify Code")
        self.verify_code_btn.setCursor(Qt.PointingHandCursor)
        self.verify_code_btn.clicked.connect(self._start_verify_code)

        btn_row.addWidget(self.back_to_phone_btn)
        btn_row.addWidget(self.verify_code_btn, stretch=1)
        p1_layout.addLayout(btn_row)

        p1_layout.addStretch(1)
        self.stack.addWidget(page_code)  # Index 1

        # ── Page 2: 2FA Password Input ──
        page_2fa = QWidget()
        p2_layout = QVBoxLayout(page_2fa)
        p2_layout.setContentsMargins(0, 8, 0, 0)
        p2_layout.setSpacing(12)

        lbl_2fa = QLabel("Two-Step Verification (2FA) is enabled on this account.\nEnter your cloud password:")
        lbl_2fa.setStyleSheet("font-size: 12px; font-weight: 500;")
        lbl_2fa.setWordWrap(True)
        p2_layout.addWidget(lbl_2fa)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Your Telegram cloud password")
        p2_layout.addWidget(self.password_input)

        self.submit_2fa_btn = QPushButton("Submit Password")
        self.submit_2fa_btn.setCursor(Qt.PointingHandCursor)
        self.submit_2fa_btn.clicked.connect(self._start_verify_2fa)
        p2_layout.addWidget(self.submit_2fa_btn)

        p2_layout.addStretch(1)
        self.stack.addWidget(page_2fa)  # Index 2

        # Status & Error Message Label
        self.status_msg_label = QLabel("")
        self.status_msg_label.setWordWrap(True)
        self.status_msg_label.setStyleSheet("font-size: 12px; color: #94a3b8;")
        root_layout.addWidget(self.status_msg_label)

    # ── Step 1: Request Code ──

    def _start_request_code(self):
        phone = self.phone_input.text().strip()
        if not phone or len(phone) < 7:
            self._set_error("Masukkan nomor telepon yang valid beserta kode negara (contoh: +6281234567890).")
            return

        self.phone_number = phone
        self._set_loading("Menghubungi server Telegram & mengirimkan kode login...")
        self.send_code_btn.setEnabled(False)

        self.worker = AsyncAuthWorker(self.tg, "request_code", phone=self.phone_number)
        self.worker.code_sent.connect(self._on_code_sent)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.start()

    def _on_code_sent(self, phone_code_hash: str):
        self.phone_code_hash = phone_code_hash
        self.send_code_btn.setEnabled(True)
        self._clear_status()

        self.lbl_code_info.setText(
            f"Kode login telah dikirimkan ke aplikasi Telegram pada nomor:\n<b>{self.phone_number}</b>"
        )
        self.stack.setCurrentIndex(1)
        self.code_input.setFocus()

    # ── Step 2: Verify OTP Code ──

    def _start_verify_code(self):
        code = self.code_input.text().strip()
        if not code:
            self._set_error("Silakan masukkan kode verifikasi yang Anda terima.")
            return

        self._set_loading("Memverifikasi kode login...")
        self.verify_code_btn.setEnabled(False)

        self.worker = AsyncAuthWorker(
            self.tg,
            "sign_in_code",
            phone=self.phone_number,
            code=code,
            phone_code_hash=self.phone_code_hash,
        )
        self.worker.login_success.connect(self._on_login_success)
        self.worker.password_required.connect(self._on_password_required)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.start()

    def _on_password_required(self):
        self.verify_code_btn.setEnabled(True)
        self._clear_status()
        self.stack.setCurrentIndex(2)
        self.password_input.setFocus()

    # ── Step 3: Verify 2FA Password ──

    def _start_verify_2fa(self):
        pwd = self.password_input.text()
        if not pwd:
            self._set_error("Silakan masukkan kata sandi 2FA Anda.")
            return

        self._set_loading("Memverifikasi kata sandi Two-Step Verification...")
        self.submit_2fa_btn.setEnabled(False)

        self.worker = AsyncAuthWorker(self.tg, "sign_in_2fa", password=pwd)
        self.worker.login_success.connect(self._on_login_success)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.start()

    # ── Success & Error Handlers ──

    def _on_login_success(self, user_info: dict):
        self._clear_status()
        username = f"@{user_info['username']}" if user_info.get("username") else user_info.get("first_name", "User")
        QMessageBox.information(
            self,
            "Login Berhasil",
            f"Selamat datang, {user_info.get('first_name', '')} ({username})!\n"
            "Akun Telegram Anda telah terhubung secara aman dengan TeleCup.",
        )
        self.login_successful.emit(user_info)
        self.accept()

    def _on_worker_error(self, err_msg: str):
        self.send_code_btn.setEnabled(True)
        self.verify_code_btn.setEnabled(True)
        self.submit_2fa_btn.setEnabled(True)
        self._set_error(err_msg)

    def _set_loading(self, msg: str):
        self.status_msg_label.setStyleSheet("font-size: 12px; color: #60a5fa;")
        self.status_msg_label.setText(f"[Loading] {msg}")

    def _set_error(self, err_msg: str):
        self.status_msg_label.setStyleSheet("font-size: 12px; color: #ef4444; font-weight: 500;")
        self.status_msg_label.setText(err_msg)

    def _clear_status(self):
        self.status_msg_label.setText("")


class SyncWorker(QThread):
    """Background worker thread executing incremental Telegram synchronization."""

    progress_updated = Signal(dict)
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self, sync_service: SyncService, limit: Optional[int] = None):
        super().__init__()
        self.sync_service = sync_service
        self.limit = limit
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            stats = self.sync_service.sync_saved_messages(
                progress_callback=self._on_progress,
                is_cancelled_callback=lambda: self._is_cancelled,
                limit=self.limit,
            )
            self.finished_signal.emit(stats)
        except Exception as e:
            self.error_signal.emit(str(e))

    def _on_progress(self, data: dict):
        self.progress_updated.emit(data)


class SyncProgressDialog(QDialog):
    """Modern dark-themed progress dialog for Telegram Saved Messages synchronization."""

    sync_completed = Signal()

    def __init__(self, sync_service: SyncService, parent=None, limit: Optional[int] = None):
        super().__init__(parent)
        self.sync_service = sync_service
        self.limit = limit
        self.worker: Optional[SyncWorker] = None
        self.has_finished: bool = False

        self.setWindowTitle("Sync Saved Messages - TeleCup")
        self.setFixedSize(540, 390)
        self.setModal(True)

        self._init_ui()
        self._start_sync()

    def _init_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background-color: #18181b;
                color: #e4e4e7;
            }
            QLabel {
                color: #e4e4e7;
            }
            QProgressBar {
                background-color: #27272a;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                height: 18px;
                text-align: center;
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 5px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 9px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)

        # 1. Header
        title = QLabel("Synchronizing Saved Messages")
        title_font = QFont("Segoe UI", 14, QFont.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")
        root.addWidget(title)

        desc = QLabel(
            "TeleCup is scanning your Saved Messages, downloading attachments to local disk, "
            "and cataloging metadata in your vault."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a1a1aa; font-size: 12px; margin-bottom: 4px;")
        root.addWidget(desc)

        # 2. Status & Filename
        self.status_label = QLabel("Initializing connection to Telegram MTProto...")
        self.status_label.setStyleSheet("color: #60a5fa; font-weight: 600; font-size: 12px;")
        root.addWidget(self.status_label)

        self.filename_label = QLabel("")
        self.filename_label.setStyleSheet("color: #f4f4f5; font-size: 12px;")
        root.addWidget(self.filename_label)

        # 3. Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        # 4. Metrics Box
        stats_frame = QFrame()
        stats_frame.setStyleSheet(
            """
            QFrame {
                background-color: #202024;
                border: 1px solid #333338;
                border-radius: 8px;
                padding: 10px;
            }
            """
        )
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setContentsMargins(12, 10, 12, 10)
        stats_layout.setHorizontalSpacing(24)
        stats_layout.setVerticalSpacing(8)

        lbl_scanned = QLabel("Messages Scanned:")
        lbl_scanned.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        self.val_scanned = QLabel("0")
        self.val_scanned.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 12px;")

        lbl_detected = QLabel("Files Detected:")
        lbl_detected.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        self.val_detected = QLabel("0")
        self.val_detected.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 12px;")

        lbl_synced = QLabel("Files Downloaded:")
        lbl_synced.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        self.val_synced = QLabel("0")
        self.val_synced.setStyleSheet("color: #3b82f6; font-weight: 600; font-size: 12px;")

        lbl_skipped = QLabel("Already Up-to-Date:")
        lbl_skipped.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        self.val_skipped = QLabel("0")
        self.val_skipped.setStyleSheet("color: #10b981; font-weight: 600; font-size: 12px;")

        stats_layout.addWidget(lbl_scanned, 0, 0)
        stats_layout.addWidget(self.val_scanned, 0, 1)
        stats_layout.addWidget(lbl_detected, 0, 2)
        stats_layout.addWidget(self.val_detected, 0, 3)

        stats_layout.addWidget(lbl_synced, 1, 0)
        stats_layout.addWidget(self.val_synced, 1, 1)
        stats_layout.addWidget(lbl_skipped, 1, 2)
        stats_layout.addWidget(self.val_skipped, 1, 3)

        root.addWidget(stats_frame)
        root.addStretch(1)

        # 5. Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.cancel_btn = QPushButton("Stop Sync")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27272a;
                border: 1px solid #3f3f46;
                color: #ef4444;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #f87171;
            }
            """
        )
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)

        self.close_btn = QPushButton("Done")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setEnabled(False)
        self.close_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #3f3f46;
                color: #71717a;
            }
            """
        )
        self.close_btn.clicked.connect(self.accept)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.close_btn)
        root.addLayout(btn_layout)

    def _start_sync(self):
        self.worker = SyncWorker(self.sync_service, limit=self.limit)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.finished_signal.connect(self._on_sync_finished)
        self.worker.error_signal.connect(self._on_sync_error)
        self.worker.start()

    def _on_progress_updated(self, data: dict):
        phase = data.get("phase", "")
        msg = data.get("message", "")
        self.status_label.setText(msg)

        if "filename" in data:
            self.filename_label.setText(data["filename"])

        if "current_bytes" in data and "total_bytes" in data:
            tot = data["total_bytes"]
            cur = data["current_bytes"]
            if tot > 0:
                pct = int((cur / tot) * 100)
                self.progress_bar.setValue(min(100, max(0, pct)))

        stats = data.get("stats", {})
        if stats:
            self.val_scanned.setText(str(stats.get("scanned_messages", 0)))
            self.val_detected.setText(str(stats.get("total_files_found", 0)))
            self.val_synced.setText(str(stats.get("synced_files", 0)))
            self.val_skipped.setText(str(stats.get("skipped_files", 0)))

        if phase == "completed":
            self._finalize_sync("Sync completed successfully.")
        elif phase == "cancelled":
            self._finalize_sync("Sync stopped by user.")

    def _on_sync_finished(self, stats: dict):
        self._finalize_sync("Sync finished.")

    def _on_sync_error(self, err_msg: str):
        self.status_label.setStyleSheet("color: #ef4444; font-weight: 600; font-size: 12px;")
        self.status_label.setText(f"Sync error: {err_msg}")
        self._finalize_sync("Sync interrupted with error.")

    def _on_cancel_clicked(self):
        if self.worker and self.worker.isRunning():
            self.status_label.setText("Stopping sync...")
            self.cancel_btn.setEnabled(False)
            self.worker.cancel()
        else:
            self.reject()

    def _finalize_sync(self, final_text: str):
        self.has_finished = True
        self.status_label.setText(final_text)
        self.progress_bar.setValue(100)
        self.cancel_btn.setEnabled(False)
        self.close_btn.setEnabled(True)
        self.sync_completed.emit()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1500)
        super().closeEvent(event)
