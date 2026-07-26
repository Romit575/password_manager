"""
ui/settings.py

Contains:
- SettingsPanel: embedded in the dashboard's content area. Theme
  toggle, database backup/restore, and change-password form.
- ExportDialog / ImportDialog: modal windows used from the Vault
  screen to move data in/out of the app.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from auth.login import AuthenticationError, change_password
from database.database import Database
from encryption.crypto import CryptoManager
from services.export_service import export_to_csv, export_to_encrypted_json
from services.import_service import ImportError_, import_from_csv, import_from_encrypted_json
from services.password_service import PasswordService, PasswordServiceError

logger = logging.getLogger(__name__)

BACKUPS_DIR = Path(__file__).resolve().parent.parent / "backups"


class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, db: Database, user_id: int) -> None:
        super().__init__(master, fg_color="transparent")
        self.db = db
        self.user_id = user_id

        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=24, weight="bold")).pack(
            anchor="w", pady=(0, 16)
        )

        self._build_theme_section()
        self._build_backup_section()
        self._build_change_password_section()

    # ------------------------------------------------------------------
    def _section_frame(self, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=15, weight="bold")).pack(
            anchor="w", padx=16, pady=(12, 4)
        )
        return frame

    def _build_theme_section(self) -> None:
        frame = self._section_frame("Appearance")
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(row, text="Theme:").pack(side="left")
        ctk.CTkOptionMenu(
            row, values=["Dark", "Light", "System"], command=self._change_theme
        ).pack(side="left", padx=8)

    def _change_theme(self, choice: str) -> None:
        ctk.set_appearance_mode(choice.lower())

    def _build_backup_section(self) -> None:
        frame = self._section_frame("Database Backup")
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(row, text="Backup Now", command=self._backup_database).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(row, text="Restore From Backup", fg_color="gray30", command=self._restore_database).pack(
            side="left"
        )

    def _backup_database(self) -> None:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = BACKUPS_DIR / f"vault_backup_{timestamp}.db"
        try:
            shutil.copy2(self.db.db_path, destination)
        except OSError as exc:
            messagebox.showerror("Backup Failed", str(exc))
            return
        messagebox.showinfo("Backup Complete", f"Database backed up to:\n{destination}")

    def _restore_database(self) -> None:
        filepath = filedialog.askopenfilename(
            initialdir=BACKUPS_DIR, title="Select a backup file", filetypes=[("SQLite DB", "*.db")]
        )
        if not filepath:
            return
        confirmed = messagebox.askyesno(
            "Confirm Restore",
            "This will overwrite your current vault with the selected backup. Continue?",
        )
        if not confirmed:
            return
        try:
            self.db.close()
            shutil.copy2(filepath, self.db.db_path)
            self.db.connect()
        except OSError as exc:
            messagebox.showerror("Restore Failed", str(exc))
            return
        messagebox.showinfo(
            "Restore Complete", "Database restored. Please restart the application."
        )

    def _build_change_password_section(self) -> None:
        frame = self._section_frame("Change Master Password")

        self.current_pw = self._pw_field(frame, "Current Password")
        self.new_pw = self._pw_field(frame, "New Password")
        self.confirm_pw = self._pw_field(frame, "Confirm New Password")

        self.change_pw_error = ctk.CTkLabel(frame, text="", text_color="#ff6b6b")
        self.change_pw_error.pack(anchor="w", padx=16)

        ctk.CTkButton(frame, text="Update Password", command=self._handle_change_password).pack(
            anchor="w", padx=16, pady=(4, 16)
        )

    def _pw_field(self, parent, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=16, pady=(4, 0))
        entry = ctk.CTkEntry(parent, show="*")
        entry.pack(fill="x", padx=16)
        return entry

    def _handle_change_password(self) -> None:
        try:
            change_password(
                self.db,
                self.user_id,
                self.current_pw.get(),
                self.new_pw.get(),
                self.confirm_pw.get(),
            )
        except AuthenticationError as exc:
            self.change_pw_error.configure(text=str(exc))
            return
        self.change_pw_error.configure(text_color="#51cf66", text="Password updated successfully.")


class ExportDialog(ctk.CTkToplevel):
    def __init__(self, master, password_service: PasswordService, crypto: CryptoManager, user_id: int) -> None:
        super().__init__(master)
        self.password_service = password_service
        self.crypto = crypto
        self.user_id = user_id

        self.title("Export Vault")
        self.geometry("380x220")
        self.grab_set()

        ctk.CTkLabel(self, text="Export Vault", font=ctk.CTkFont(size=18, weight="bold")).pack(
            pady=(16, 8)
        )
        ctk.CTkLabel(
            self,
            text="⚠ CSV export stores passwords in PLAIN TEXT.\nEncrypted JSON keeps them protected.",
            text_color="#f1c40f",
            wraplength=320,
            justify="left",
        ).pack(padx=16, pady=(0, 16))

        ctk.CTkButton(self, text="Export as CSV (plain text)", command=self._export_csv).pack(
            fill="x", padx=16, pady=4
        )
        ctk.CTkButton(self, text="Export as Encrypted JSON", command=self._export_json).pack(
            fill="x", padx=16, pady=4
        )

    def _export_csv(self) -> None:
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not filepath:
            return
        confirmed = messagebox.askyesno(
            "Confirm", "This file will contain your passwords in plain text. Continue?"
        )
        if not confirmed:
            return
        entries = self.password_service.get_all_passwords(self.user_id)
        export_to_csv(entries, Path(filepath))
        messagebox.showinfo("Export Complete", f"Exported {len(entries)} entries.")
        self.destroy()

    def _export_json(self) -> None:
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not filepath:
            return
        entries = self.password_service.get_all_passwords(self.user_id)
        export_to_encrypted_json(entries, Path(filepath), self.crypto)
        messagebox.showinfo("Export Complete", f"Exported {len(entries)} entries.")
        self.destroy()


class ImportDialog(ctk.CTkToplevel):
    def __init__(self, master, password_service: PasswordService, crypto: CryptoManager, user_id: int, on_done) -> None:
        super().__init__(master)
        self.password_service = password_service
        self.crypto = crypto
        self.user_id = user_id
        self.on_done = on_done

        self.title("Import Vault")
        self.geometry("340x180")
        self.grab_set()

        ctk.CTkLabel(self, text="Import Vault", font=ctk.CTkFont(size=18, weight="bold")).pack(
            pady=(16, 8)
        )
        ctk.CTkButton(self, text="Import from CSV", command=self._import_csv).pack(
            fill="x", padx=16, pady=4
        )
        ctk.CTkButton(self, text="Import from Encrypted JSON", command=self._import_json).pack(
            fill="x", padx=16, pady=4
        )

    def _import_csv(self) -> None:
        filepath = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not filepath:
            return
        try:
            entries = import_from_csv(Path(filepath))
        except ImportError_ as exc:
            messagebox.showerror("Import Failed", str(exc))
            return
        self._save_entries(entries)

    def _import_json(self) -> None:
        filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not filepath:
            return
        try:
            entries = import_from_encrypted_json(Path(filepath), self.crypto)
        except ImportError_ as exc:
            messagebox.showerror("Import Failed", str(exc))
            return
        self._save_entries(entries)

    def _save_entries(self, entries) -> None:
        saved = 0
        for entry in entries:
            try:
                self.password_service.add_password(self.user_id, entry)
                saved += 1
            except PasswordServiceError:
                logger.warning("Skipped invalid entry during import: %s", entry.website)
        messagebox.showinfo("Import Complete", f"Imported {saved} of {len(entries)} entries.")
        self.on_done()
        self.destroy()
