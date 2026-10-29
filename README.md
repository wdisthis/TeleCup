# TeleCup

**Local-first desktop application** untuk mengubah Telegram *Saved Messages* menjadi pengelola arsip pribadi yang terasa seperti Google Drive.

Tidak perlu lagi menggulir chat panjang hanya untuk menemukan PDF, gambar, kode, dokumen, atau catatan yang pernah kamu simpan. TeleCup berjalan sepenuhnya di laptop kamu: tanpa server sendiri, tanpa VPS, tanpa Streamlit, dan tanpa layanan cloud wajib. Katalog, file hasil unduhan, dan konfigurasi semuanya disimpan secara lokal.

> **Status:** dalam pengembangan awal (pra-MVP).

---

## Daftar Isi

- [Fitur](#fitur)
- [Teknologi](#teknologi)
- [Persyaratan](#persyaratan)
- [Instalasi](#instalasi)
- [Konfigurasi Telegram API](#konfigurasi-telegram-api)
- [Menjalankan Aplikasi](#menjalankan-aplikasi)
- [Struktur Folder](#struktur-folder)
- [Desain Database](#desain-database)
- [Keamanan](#keamanan)
- [Roadmap & Checklist MVP](#roadmap--checklist-mvp)
- [Pengujian](#pengujian)
- [Membuat Aplikasi Windows (.exe)](#membuat-aplikasi-windows-exe)
- [Referensi](#referensi)

---

## Fitur

### Fitur inti

- Sinkronisasi pesan dari Saved Messages.
- Mengunduh lampiran: PDF, DOCX, ZIP, gambar, video, audio, dan file lainnya.
- Tampilan file dalam **grid** atau **list view**.
- **Folder virtual** yang dapat dibuat, diganti nama, dan dihapus tanpa mengubah pesan asli di Telegram.
- Kategori otomatis berdasarkan jenis file.
- Pencarian berdasarkan nama file, caption, teks pesan, dan tag.
- Favorit serta pengurutan berdasarkan nama, tanggal, ukuran, dan jenis.
- Preview file yang didukung dan tombol buka file dengan aplikasi Windows.
- Tombol untuk membuka pesan sumber di Telegram (jika tautan/referensinya tersedia).
- Sinkronisasi ulang tanpa mengunduh ulang file yang sudah berhasil diarsipkan.

### Fitur lanjutan

- Filter berdasarkan tanggal, jenis media, dan kategori.
- Deteksi file duplikat menggunakan hash.
- Progress bar, log sinkronisasi, dan penanganan koneksi terputus.
- Ekspor dan impor katalog untuk pencadangan.
- Tema gelap dan terang.

---

## Teknologi

| Komponen | Fungsi |
| --- | --- |
| **PySide6 / Qt** | UI desktop native: sidebar, grid file, dialog, menu klik kanan |
| **Telethon** | Berkomunikasi dengan Telegram lewat MTProto API menggunakan akun pengguna yang terautentikasi |
| **SQLite** | Menyimpan metadata pesan, file, folder virtual, tag, dan indeks pencarian |
| **Penyimpanan lokal + venv** | File tersimpan di disk Windows; library Python diisolasi dengan virtual environment |

> `venv` bukan framework UI ataupun server. Aplikasi dijalankan langsung sebagai program Python yang membuka jendela desktop. Telethon tetap memerlukan koneksi internet saat mengakses Telegram.

---

## Persyaratan

- Windows 10/11
- Python 3.10 atau lebih baru
- Akun Telegram aktif
- Telegram `API ID` dan `API hash` (lihat [Konfigurasi Telegram API](#konfigurasi-telegram-api))

---

## Instalasi

```powershell
git clone <url-repo-kamu> TeleCup
cd TeleCup

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

Jika memulai dari nol (belum ada `requirements.txt`):

```powershell
mkdir TeleCup
cd TeleCup

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install PySide6 telethon
pip freeze > requirements.txt
```

> Jika PowerShell menolak menjalankan skrip aktivasi, jalankan sekali:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

---

## Konfigurasi Telegram API

1. Buka [my.telegram.org](https://my.telegram.org) dan login dengan akun Telegram kamu.
2. Masuk ke **API development tools** dan buat aplikasi baru.
3. Salin `api_id` dan `api_hash`.
4. Buat file `config/settings.json`:

```json
{
  "api_id": 123456,
  "api_hash": "isi_api_hash_kamu",
  "session_name": "telecup"
}
```

Saat pertama kali dijalankan, kamu akan diminta memasukkan nomor telepon dan kode login dari Telegram.

---

## Menjalankan Aplikasi

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

---

## Struktur Folder

```
TeleCup/
├── .venv/                  # dibuat oleh Python, bukan ditulis manual
├── app.py                  # titik masuk aplikasi
├── requirements.txt
├── .gitignore
├── config/
│   └── settings.json       # rahasia, jangan di-commit
├── src/
│   ├── __init__.py
│   ├── telegram_client.py  # autentikasi & akses Saved Messages
│   ├── sync_service.py     # sinkronisasi pesan & lampiran
│   ├── database.py         # operasi SQLite
│   ├── file_service.py     # penyimpanan, cek duplikasi, buka file
│   ├── search_service.py   # pencarian teks & metadata
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py
│       ├── sidebar.py
│       ├── file_grid.py
│       ├── toolbar.py
│       └── dialogs.py
├── storage/                # arsip lokal & basis data (tidak di-commit)
│   ├── files/
│   ├── thumbnails/
│   ├── logs/
│   └── vault.db
└── tests/
    ├── test_database.py
    └── test_file_service.py
```

Pisahkan tampilan, komunikasi Telegram, dan pengelolaan data agar kode tidak menumpuk di satu file.

---

## Desain Database

SQLite dengan tabel utama berikut:

| Tabel | Fungsi |
| --- | --- |
| `messages` | ID pesan Telegram, tanggal, teks/caption, dan referensi sumber |
| `files` | Nama file, ukuran, MIME type, hash, dan lokasi lokal |
| `folders` | Folder virtual yang dibuat pengguna |
| `file_tags` | Hubungan file dengan tag atau kategori |
| `sync_state` | Pesan terakhir yang diproses, status sinkronisasi, dan error |

**Prinsip desain:** pesan Telegram, file yang diunduh, dan pengelompokan buatan pengguna adalah tiga hal berbeda.

- Satu pesan dapat berisi beberapa file.
- Satu file dapat direferensikan oleh lebih dari satu pesan.
- Jangan menjadikan **nama file** sebagai ID unik.
- Simpan ID pesan dan ID chat sebagai referensi sumber.
- Untuk mencegah duplikasi, gunakan kombinasi ID pesan + identitas media, lalu hash file sebagai pemeriksaan tambahan bila perlu.

---

## Keamanan

Karena menyangkut akun Telegram pribadi, keamanan adalah bagian dari desain sejak awal:

- Jangan commit file session Telethon, API hash, kode login, atau OTP ke Git.
- Pastikan `.venv/`, `storage/`, file session, dan konfigurasi rahasia ada di `.gitignore`.
- Simpan session di lokasi privat dengan akses terbatas. Session yang bocor dapat memberikan akses ke akun.
- Gunakan API Telegram resmi dan patuhi batas permintaan (rate limit). Jangan scraping Telegram Web.
- Jangan menghapus pesan asli saat mengarsipkan file.
- Buat cadangan `vault.db` dan file arsip secara berkala.

---

## Roadmap & Checklist MVP

Selesaikan UI dan database terlebih dahulu, uji integrasi Telegram dengan sedikit pesan, baru kembangkan sinkronisasi penuh.

- [ ] Aplikasi membuka jendela desktop PySide6
- [ ] Sidebar dan grid file tampil dengan rapi
- [ ] SQLite dapat menyimpan metadata file
- [ ] Folder virtual dan pencarian berfungsi
- [ ] Login Telegram berhasil
- [ ] Pesan Saved Messages dapat dibaca
- [ ] Lampiran dapat diunduh ke penyimpanan lokal
- [ ] Sinkronisasi ulang tidak menggandakan arsip
- [ ] File dan database dapat dicadangkan

### Langkah implementasi

1. **Siapkan lingkungan Python** — buat folder project, aktifkan `venv`, pasang dependensi.
2. **Bangun UI dulu** — `app.py` dan `main_window.py` dengan sidebar, toolbar, area file, kotak pencarian, dan status bar memakai data dummy.
3. **Database & file manager** — SQLite, folder virtual, kategori, favorit, sortir, pencarian, dan buka file lokal.
4. **Hubungkan Telegram** — login dengan akun sendiri via Telethon dan baca Saved Messages.
5. **Sinkronisasi** — baca pesan bertahap, catat metadata, unduh ke folder staging, pindahkan ke arsip setelah berhasil, simpan status agar bisa dilanjutkan.
6. **Uji & kemas** — uji koneksi terputus, file duplikat, file besar, pesan tanpa lampiran, dan file yang terhapus dari disk.

---

## Pengujian

```powershell
pip install pytest
pytest tests/
```

Skenario yang perlu diuji: koneksi terputus, file duplikat, file berukuran besar, pesan tanpa lampiran, dan file yang dihapus dari disk.

---

## Membuat Aplikasi Windows (.exe)

Setelah aplikasi stabil, kemas dengan PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name TeleCup app.py
```

Hasilnya ada di folder `dist/`.

---

## Referensi

- [Telethon — dokumentasi](https://docs.telethon.dev/en/stable/)
- [Telegram Saved Messages API](https://core.telegram.org/api/saved-messages)
- [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/)
- [Python `venv`](https://docs.python.org/3/library/venv.html)
- [Python `sqlite3`](https://docs.python.org/3/library/sqlite3.html)

---

## Lisensi

