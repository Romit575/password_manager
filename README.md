# 🔐 Password Manager (Desktop App)

A secure, offline-first desktop Password Manager built with Python and CustomTkinter.
Every stored password is encrypted at rest (Fernet/AES) and account logins are protected
with bcrypt hashing. Designed to be run and developed inside Visual Studio Code.

---

## ✨ Features

- **Login System** — first-run admin account creation, register, login, logout,
  "remember me", forgot password (security question), change password.
- **Password Vault** — add/edit/delete entries with website, URL, username, email,
  password, notes, and category.
- **Encryption** — all vault passwords are encrypted with Fernet (AES-128 in CBC mode
  with HMAC authentication) before touching the database; decrypted only on demand.
- **Password Generator** — configurable length and character sets (upper/lower/digits/
  symbols), with a one-click copy button and a strength indicator.
- **Instant Search** — filter the vault by website, username, or category as you type.
- **Password Viewer** — hidden-by-default passwords with Show / Copy / Edit / Delete
  actions per entry.
- **Dashboard** — total passwords, total categories, and recent entries at a glance.
- **Security** — auto logout after 5 minutes of inactivity, delete confirmations,
  parameterized SQL queries (no SQL injection), form validation.
- **Export** — plain-text CSV or app-native Encrypted JSON.
- **Import** — from CSV or Encrypted JSON.
- **Settings** — Dark/Light/System theme, database backup and restore.
- **Modern UI** — CustomTkinter sidebar navigation, rounded buttons, dark theme by default.

---

## 🧱 Tech Stack

| Purpose            | Library         |
|---------------------|-----------------|
| GUI                 | customtkinter   |
| Password hashing    | bcrypt          |
| Vault encryption     | cryptography (Fernet) |
| Database             | sqlite3 (standard library) |
| Clipboard            | pyperclip       |
| Images/icons          | pillow          |

---

## 📁 Folder Structure

```
password_manager/
│
├── main.py                   # Application entry point
├── requirements.txt
├── README.md
│
├── database/
│   ├── database.py           # SQLite connection + safe query helpers
│   └── schema.py              # CREATE TABLE statements, category list
│
├── auth/
│   ├── login.py               # authenticate, forgot/change password, remember-me
│   ├── register.py            # account creation + first-run admin flow
│   └── security.py            # bcrypt hashing, validation, auto-logout timer
│
├── encryption/
│   ├── crypto.py               # Fernet encrypt/decrypt wrapper
│   └── key_manager.py          # generates & stores the local encryption key
│
├── models/
│   └── password_model.py       # PasswordEntry dataclass
│
├── services/
│   ├── password_service.py     # vault CRUD + search + stats
│   ├── generator.py            # secure password generation
│   ├── export_service.py       # CSV / encrypted JSON export
│   └── import_service.py       # CSV / encrypted JSON import
│
├── ui/
│   ├── login_window.py         # login / register / forgot password screens
│   ├── dashboard.py             # sidebar + home + vault + generator + settings
│   ├── add_password.py          # add/edit entry modal
│   └── settings.py              # theme, backup/restore, change password, export/import dialogs
│
├── assets/
│   ├── icons/
│   └── images/
│
├── backups/                     # created automatically when you back up the DB
└── vault.db                     # created automatically on first run
```

---

## 🚀 Installation & Running (VS Code)

1. **Open the folder in VS Code**
   `File > Open Folder... > password_manager`

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate it**
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

   In VS Code, select this environment as your Python interpreter
   (`Ctrl+Shift+P` → *Python: Select Interpreter*).

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the app**
   ```bash
   python main.py
   ```

On first launch, you'll be asked to create an admin account. After that, the
normal Login/Register screen appears every time you start the app.

> **Linux note:** Tkinter ships with Python but some distros split it into a
> separate OS package. If the app fails to import `tkinter`, run:
> `sudo apt install python3-tk` (Debian/Ubuntu) or the equivalent for your distro.

---

## 🔒 Security Model (please read)

This is a **local, single-user-per-machine** vault:

- Login passwords are hashed with **bcrypt** (salted, one-way) — never stored or
  compared in plain text.
- Vault passwords are encrypted with **Fernet** before being written to `vault.db`.
  The encryption key lives in `encryption/secret.key`, generated automatically on
  first run and permission-restricted to the current OS user (where supported).
- Decryption only happens in memory, only when you click "Show" or "Copy", or when
  exporting.
- Because the key and database both live on your machine, the vault's real
  protection boundary is your **OS user account / disk encryption** — the same
  trust model used by most local password managers and browser vaults.
- CSV export is explicitly **unencrypted** (a plain-text file) — the app warns you
  before writing one. Prefer "Encrypted JSON" when moving data between machines.

---

## 🗄️ Database Tables

**users**
`id, username, email, password_hash, security_question, security_answer_hash, created_at`

**passwords**
`id, user_id, website, url, username, email, encrypted_password, notes, category, created_at, updated_at`

---

## 🖼️ Screenshots

_(Add screenshots here after running the app — e.g. `assets/images/screenshot_login.png`,
`assets/images/screenshot_dashboard.png`, `assets/images/screenshot_vault.png`.)_

---

## 🛣️ Future Improvements

- Multi-factor authentication (TOTP)
- Cloud sync / cross-device support
- Password breach checking (Have I Been Pwned API)
- Per-entry password history
- Tagging in addition to single categories
- Biometric unlock on supported OSes

---

## 📝 License

This project is provided as-is for personal/educational use.
