# TeleCup

**Local-first desktop application** to turn Telegram *Saved Messages* into a personal archive manager that feels like Google Drive.

No more scrolling through long chats just to find a PDF, image, code snippet, document, or note you once saved. TeleCup runs entirely on your laptop: no own server, no VPS, no Streamlit, and no mandatory cloud service. The catalog, downloaded files, and configuration are all stored locally.

> **Status:** early development (pre-MVP).

---

## Table of Contents

- [Features](#features)
- [Technology](#technology)
- [Requirements](#requirements)
- [Installation](#installation)
- [Telegram API Configuration](#telegram-api-configuration)
- [Running the App](#running-the-app)
- [Folder Structure](#folder-structure)
- [Database Design](#database-design)
- [Security](#security)
- [Roadmap & MVP Checklist](#roadmap--mvp-checklist)
- [Testing](#testing)
- [Building a Windows App (.exe)](#building-a-windows-app-exe)
- [References](#references)

---

## Features

### Core features

- Sync messages from Saved Messages.
- Download attachments: PDFs, DOCX, ZIP, images, videos, audio, and other files.
- Display files in **grid** or **list view**.
- **Virtual folders** that can be created, renamed, and deleted without modifying the original messages on Telegram.
- Automatic categorization based on file type.
- Search by file name, caption, message text, and tags.
- Favorites and sorting by name, date, size, and type.
- Preview supported files and open them with Windows applications.
- Button to open the source message on Telegram (if the link/reference is available).
- Re-sync without re-downloading files that have already been successfully archived.

### Advanced features

- Filter by date, media type, and category.
- Duplicate file detection using hashing.
- Progress bar, sync log, and handling of dropped connections.
- Export and import catalog for backup.
- Dark and light themes.

---

## Technology

| Component | Purpose |
| --- | --- |
| **PySide6 / Qt** | Native desktop UI: sidebar, file grid, dialogs, right-click menu |
| **Telethon** | Communicates with Telegram via the MTProto API using an authenticated user account |
| **SQLite** | Stores message metadata, files, virtual folders, tags, and search index |
| **Local storage + venv** | Files are saved to Windows disk; Python libraries are isolated with a virtual environment |

> `venv` is neither a UI framework nor a server. The app runs directly as a Python program that opens a desktop window. Telethon still requires an internet connection when accessing Telegram.

---

## Requirements

- Windows 10/11
- Python 3.10 or newer
- An active Telegram account
- Telegram `API ID` and `API hash` (see [Telegram API Configuration](#telegram-api-configuration))

---

## Installation

```powershell
git clone <your-repo-url> TeleCup
cd TeleCup

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If starting from scratch (no `requirements.txt` yet):

```powershell
mkdir TeleCup
cd TeleCup

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install PySide6 telethon
pip freeze > requirements.txt
```

> If PowerShell refuses to run the activation script, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

---

## Telegram API Configuration

1. Open [my.telegram.org](https://my.telegram.org) and log in with your Telegram account.
2. Go to **API development tools** and create a new application.
3. Copy your `api_id` and `api_hash`.
4. Create the file `config/settings.json`:

```json
{
  "api_id": 123456,
  "api_hash": "your_api_hash_here",
  "session_name": "telecup"
}
```

The first time you run the app, you will be prompted to enter your phone number and the login code from Telegram.

---

## Running the App

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

---

## Folder Structure

```
TeleCup/
├── .venv/                  # created by Python, not written manually
├── app.py                  # application entry point
├── requirements.txt
├── .gitignore
├── config/
│   └── settings.json       # secret, do not commit
├── src/
│   ├── __init__.py
│   ├── telegram_client.py  # authentication & Saved Messages access
│   ├── sync_service.py     # message & attachment synchronization
│   ├── database.py         # SQLite operations
│   ├── file_service.py     # storage, duplicate checking, open file
│   ├── search_service.py   # text & metadata search
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py
│       ├── sidebar.py
│       ├── file_grid.py
│       ├── toolbar.py
│       └── dialogs.py
├── storage/                # local archive & database (not committed)
│   ├── files/
│   ├── thumbnails/
│   ├── logs/
│   └── vault.db
└── tests/
    ├── test_database.py
    └── test_file_service.py
```

Keep the UI, Telegram communication, and data management separate so the code doesn't pile up in a single file.

---

## Database Design

SQLite with the following main tables:

| Table | Purpose |
| --- | --- |
| `messages` | Telegram message ID, date, text/caption, and source reference |
| `files` | File name, size, MIME type, hash, and local path |
| `folders` | Virtual folders created by the user |
| `file_tags` | Relationship between files and tags or categories |
| `sync_state` | Last processed message, sync status, and errors |

**Design principle:** Telegram messages, downloaded files, and user-defined groupings are three separate things.

- One message can contain multiple files.
- One file can be referenced by more than one message.
- Do not use **file name** as a unique ID.
- Store the message ID and chat ID as source references.
- To prevent duplication, use the combination of message ID + media identity, then file hash as an additional check if needed.

---

## Security

Since this involves a personal Telegram account, security is part of the design from the start:

- Do not commit Telethon session files, API hash, login codes, or OTPs to Git.
- Make sure `.venv/`, `storage/`, session files, and secret config are in `.gitignore`.
- Store sessions in a private location with restricted access. A leaked session can grant access to the account.
- Use the official Telegram API and respect rate limits. Do not scrape Telegram Web.
- Do not delete original messages when archiving files.
- Back up `vault.db` and archive files regularly.

---

## Roadmap & MVP Checklist

Complete the UI and database first, test Telegram integration with a few messages, then build out full synchronization.

- [ ] App opens a PySide6 desktop window
- [ ] Sidebar and file grid display correctly
- [ ] SQLite can store file metadata
- [ ] Virtual folders and search work correctly
- [ ] Telegram login succeeds
- [ ] Saved Messages can be read
- [ ] Attachments can be downloaded to local storage
- [ ] Re-sync does not duplicate archives
- [ ] Files and database can be backed up

### Implementation steps

1. **Set up the Python environment** — create the project folder, activate `venv`, install dependencies.
2. **Build the UI first** — `app.py` and `main_window.py` with sidebar, toolbar, file area, search box, and status bar using dummy data.
3. **Database & file manager** — SQLite, virtual folders, categories, favorites, sorting, search, and open local files.
4. **Connect Telegram** — log in with your own account via Telethon and read Saved Messages.
5. **Synchronization** — read messages incrementally, record metadata, download to a staging folder, move to archive on success, save state so it can be resumed.
6. **Test & package** — test dropped connections, duplicate files, large files, messages without attachments, and files deleted from disk.

---

## Testing

```powershell
pip install pytest
pytest tests/
```

Scenarios to test: dropped connections, duplicate files, large files, messages without attachments, and files deleted from disk.

---

## Building a Windows App (.exe)

Once the app is stable, package it with PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name TeleCup app.py
```

The output will be in the `dist/` folder.

---

## References

- [Telethon — documentation](https://docs.telethon.dev/en/stable/)
- [Telegram Saved Messages API](https://core.telegram.org/api/saved-messages)
- [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/)
- [Python `venv`](https://docs.python.org/3/library/venv.html)
- [Python `sqlite3`](https://docs.python.org/3/library/sqlite3.html)

---

## License

