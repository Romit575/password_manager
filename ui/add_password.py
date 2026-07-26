"""
ui/add_password.py

A modal dialog used both to ADD a new vault entry and to EDIT an
existing one (the caller passes `existing=` for edit mode).
"""

from tkinter import messagebox

import customtkinter as ctk
import pyperclip

from database.schema import DEFAULT_CATEGORIES
from models.password_model import PasswordEntry
from services.generator import generate_password
from services.password_service import PasswordService, PasswordServiceError


class AddPasswordWindow(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        password_service: PasswordService,
        user_id: int,
        on_saved,
        existing: PasswordEntry | None = None,
    ) -> None:
        super().__init__(master)
        self.password_service = password_service
        self.user_id = user_id
        self.on_saved = on_saved
        self.existing = existing

        self.title("Edit Password" if existing else "Add Password")
        self.geometry("420x620")
        self.grab_set()  # modal

        ctk.CTkLabel(
            self, text="Edit Password" if existing else "Add New Password",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(16, 8))

        self.website_entry = self._field("Website *")
        self.url_entry = self._field("URL")
        self.username_entry = self._field("Username")
        self.email_entry = self._field("Email")

        ctk.CTkLabel(self, text="Password *").pack(anchor="w", padx=16, pady=(8, 0))
        pw_row = ctk.CTkFrame(self, fg_color="transparent")
        pw_row.pack(fill="x", padx=16)
        self.password_entry = ctk.CTkEntry(pw_row, show="*")
        self.password_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(pw_row, text="🎲", width=36, command=self._generate_inline).pack(
            side="left", padx=(4, 0)
        )
        ctk.CTkButton(pw_row, text="👁", width=36, command=self._toggle_reveal).pack(
            side="left", padx=(4, 0)
        )

        ctk.CTkLabel(self, text="Category").pack(anchor="w", padx=16, pady=(8, 0))
        self.category_var = ctk.StringVar(value=DEFAULT_CATEGORIES[-1])
        self.category_menu = ctk.CTkOptionMenu(self, values=DEFAULT_CATEGORIES, variable=self.category_var)
        self.category_menu.pack(fill="x", padx=16)

        ctk.CTkLabel(self, text="Notes").pack(anchor="w", padx=16, pady=(8, 0))
        self.notes_box = ctk.CTkTextbox(self, height=80)
        self.notes_box.pack(fill="x", padx=16)

        self.error_label = ctk.CTkLabel(self, text="", text_color="#ff6b6b", wraplength=380)
        self.error_label.pack(padx=16, pady=(8, 0))

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(button_row, text="Cancel", fg_color="gray30", command=self.destroy).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ctk.CTkButton(button_row, text="Save", command=self._save).pack(
            side="left", fill="x", expand=True
        )

        if existing:
            self._prefill(existing)

    # ------------------------------------------------------------------
    def _field(self, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(self, text=label).pack(anchor="w", padx=16, pady=(8, 0))
        entry = ctk.CTkEntry(self)
        entry.pack(fill="x", padx=16)
        return entry

    def _prefill(self, entry: PasswordEntry) -> None:
        self.website_entry.insert(0, entry.website)
        self.url_entry.insert(0, entry.url)
        self.username_entry.insert(0, entry.username)
        self.email_entry.insert(0, entry.email)
        self.password_entry.insert(0, entry.password)
        self.category_var.set(entry.category if entry.category in DEFAULT_CATEGORIES else DEFAULT_CATEGORIES[-1])
        self.notes_box.insert("1.0", entry.notes)

    def _generate_inline(self) -> None:
        password = generate_password()
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, password)
        pyperclip.copy(password)

    def _toggle_reveal(self) -> None:
        current = self.password_entry.cget("show")
        self.password_entry.configure(show="" if current == "*" else "*")

    def _save(self) -> None:
        entry = PasswordEntry(
            website=self.website_entry.get(),
            url=self.url_entry.get(),
            username=self.username_entry.get(),
            email=self.email_entry.get(),
            password=self.password_entry.get(),
            notes=self.notes_box.get("1.0", "end").strip(),
            category=self.category_var.get(),
        )
        try:
            if self.existing:
                self.password_service.update_password(self.existing.id, self.user_id, entry)
            else:
                self.password_service.add_password(self.user_id, entry)
        except PasswordServiceError as exc:
            self.error_label.configure(text=str(exc))
            return

        self.on_saved()
        self.destroy()
