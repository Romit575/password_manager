"""
ui/dashboard.py

The main application window shown after a successful login.
Sidebar navigation switches between:
- Home (stats overview)
- Vault (search + list + show/copy/edit/delete)
- Generator (password generator with copy button)
- Settings (opens ui.settings.SettingsWindow)
- Logout (returns to the login screen)

Also wires up the inactivity-based auto-logout timer.
"""

import logging
from tkinter import messagebox

import customtkinter as ctk
import pyperclip

from auth.security import AUTO_LOGOUT_MS, InactivityMonitor
from database.database import Database
from encryption.crypto import CryptoManager
from models.password_model import PasswordEntry
from services.generator import estimate_strength, generate_password, GeneratorError
from services.password_service import PasswordService, PasswordServiceError
from database.schema import DEFAULT_CATEGORIES

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Dashboard(ctk.CTk):
    def __init__(self, db: Database, crypto: CryptoManager, user_id: int, username: str) -> None:
        super().__init__()
        self.db = db
        self.crypto = crypto
        self.user_id = user_id
        self.username = username
        self.password_service = PasswordService(db, crypto)

        self.title("Password Manager - Dashboard")
        self.geometry("1000x640")
        self.minsize(860, 560)

        self._build_sidebar()
        self._build_content_area()
        self.show_home()

        self.inactivity_monitor = InactivityMonitor(self, on_timeout=self._auto_logout, timeout_ms=AUTO_LOGOUT_MS)
        self.inactivity_monitor.start()

    # ------------------------------------------------------------------
    # Layout scaffolding
    # ------------------------------------------------------------------
    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar, text="🔐 Vault", font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(24, 4))
        ctk.CTkLabel(self.sidebar, text=f"Hi, {self.username}", text_color="gray70").pack(
            pady=(0, 24)
        )

        nav_buttons = [
            ("🏠  Home", self.show_home),
            ("🔑  Vault", self.show_vault),
            ("🎲  Generator", self.show_generator),
            ("⚙️  Settings", self.show_settings),
        ]
        for text, command in nav_buttons:
            ctk.CTkButton(
                self.sidebar, text=text, anchor="w", command=command, fg_color="transparent"
            ).pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            self.sidebar, text="🚪  Logout", fg_color="#c0392b", hover_color="#992d22",
            command=self._logout,
        ).pack(side="bottom", fill="x", padx=12, pady=16)

    def _build_content_area(self) -> None:
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True, padx=20, pady=20)

    def _clear_content(self) -> None:
        for widget in self.content.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # HOME
    # ------------------------------------------------------------------
    def show_home(self) -> None:
        self._clear_content()
        stats = self.password_service.get_stats(self.user_id)

        ctk.CTkLabel(self.content, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold")).pack(
            anchor="w", pady=(0, 16)
        )

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x")
        self._stat_card(cards, "Total Passwords", stats["total_passwords"]).pack(
            side="left", padx=(0, 12), fill="both", expand=True
        )
        self._stat_card(cards, "Categories", stats["total_categories"]).pack(
            side="left", padx=(0, 12), fill="both", expand=True
        )

        ctk.CTkLabel(
            self.content, text="Recent Entries", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", pady=(24, 8))

        recent_frame = ctk.CTkFrame(self.content)
        recent_frame.pack(fill="x")
        if stats["recent"]:
            for website in stats["recent"]:
                ctk.CTkLabel(recent_frame, text=f"• {website}", anchor="w").pack(
                    fill="x", padx=12, pady=4
                )
        else:
            ctk.CTkLabel(recent_frame, text="No entries yet. Add your first password in the Vault tab.").pack(
                padx=12, pady=12
            )

    def _stat_card(self, parent, title: str, value) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=12)
        ctk.CTkLabel(card, text=str(value), font=ctk.CTkFont(size=28, weight="bold")).pack(
            pady=(16, 0)
        )
        ctk.CTkLabel(card, text=title, text_color="gray70").pack(pady=(0, 16))
        return card

    # ------------------------------------------------------------------
    # VAULT
    # ------------------------------------------------------------------
    def show_vault(self) -> None:
        self._clear_content()

        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text="Vault", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Add Password", command=self._open_add_password).pack(
            side="right"
        )
        ctk.CTkButton(header, text="Export", command=self._open_export_dialog, fg_color="gray30").pack(
            side="right", padx=8
        )
        ctk.CTkButton(header, text="Import", command=self._open_import_dialog, fg_color="gray30").pack(
            side="right"
        )

        search_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        search_frame.pack(fill="x", pady=(12, 12))
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by website, username, or category...")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda e: self._refresh_vault_list())

        self.vault_scroll = ctk.CTkScrollableFrame(self.content)
        self.vault_scroll.pack(fill="both", expand=True)

        self._refresh_vault_list()

    def _refresh_vault_list(self) -> None:
        for widget in self.vault_scroll.winfo_children():
            widget.destroy()

        query = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""
        if query:
            entries = self.password_service.search_passwords(self.user_id, query)
        else:
            entries = self.password_service.get_all_passwords(self.user_id)

        if not entries:
            ctk.CTkLabel(self.vault_scroll, text="No entries found.").pack(pady=20)
            return

        for entry in entries:
            self._build_vault_row(entry)

    def _build_vault_row(self, entry: PasswordEntry) -> None:
        row = ctk.CTkFrame(self.vault_scroll, corner_radius=10)
        row.pack(fill="x", pady=6, padx=2)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        ctk.CTkLabel(
            info, text=entry.website, font=ctk.CTkFont(size=15, weight="bold"), anchor="w"
        ).pack(fill="x")
        ctk.CTkLabel(
            info, text=f"{entry.username or entry.email or '—'}  •  {entry.category}",
            text_color="gray70", anchor="w",
        ).pack(fill="x")

        password_var = ctk.StringVar(value="•" * 10)
        password_label = ctk.CTkLabel(info, textvariable=password_var, text_color="gray50", anchor="w")
        password_label.pack(fill="x")

        state = {"revealed": False}

        def toggle_show():
            state["revealed"] = not state["revealed"]
            password_var.set(entry.password if state["revealed"] else "•" * 10)
            show_btn.configure(text="Hide" if state["revealed"] else "Show")

        def copy_password():
            pyperclip.copy(entry.password)
            messagebox.showinfo("Copied", "Password copied to clipboard.")

        def edit_entry():
            self._open_add_password(existing=entry)

        def delete_entry():
            confirmed = messagebox.askyesno(
                "Confirm Delete", f"Delete the entry for '{entry.website}'? This cannot be undone."
            )
            if confirmed:
                self.password_service.delete_password(entry.id, self.user_id)
                self._refresh_vault_list()

        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="right", padx=12)

        show_btn = ctk.CTkButton(actions, text="Show", width=70, command=toggle_show)
        show_btn.pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Copy", width=70, command=copy_password).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Edit", width=70, command=edit_entry, fg_color="gray30").pack(
            side="left", padx=4
        )
        ctk.CTkButton(
            actions, text="Delete", width=70, command=delete_entry, fg_color="#c0392b",
            hover_color="#992d22",
        ).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    def _open_add_password(self, existing: PasswordEntry | None = None) -> None:
        from ui.add_password import AddPasswordWindow

        AddPasswordWindow(
            self, self.password_service, self.user_id, on_saved=self._refresh_vault_list, existing=existing
        )

    def _open_export_dialog(self) -> None:
        from ui.settings import ExportDialog

        ExportDialog(self, self.password_service, self.crypto, self.user_id)

    def _open_import_dialog(self) -> None:
        from ui.settings import ImportDialog

        ImportDialog(self, self.password_service, self.crypto, self.user_id, on_done=self._refresh_vault_list)

    # ------------------------------------------------------------------
    # GENERATOR
    # ------------------------------------------------------------------
    def show_generator(self) -> None:
        self._clear_content()

        ctk.CTkLabel(self.content, text="Password Generator", font=ctk.CTkFont(size=24, weight="bold")).pack(
            anchor="w", pady=(0, 16)
        )

        panel = ctk.CTkFrame(self.content)
        panel.pack(fill="x")

        self.gen_result_var = ctk.StringVar(value="Click 'Generate' to create a password")
        result_entry = ctk.CTkEntry(panel, textvariable=self.gen_result_var, font=ctk.CTkFont(size=16))
        result_entry.pack(fill="x", padx=16, pady=(16, 4))

        self.strength_label = ctk.CTkLabel(panel, text="", text_color="gray70")
        self.strength_label.pack(anchor="w", padx=16, pady=(0, 12))

        length_frame = ctk.CTkFrame(panel, fg_color="transparent")
        length_frame.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(length_frame, text="Length:").pack(side="left")
        self.length_var = ctk.IntVar(value=16)
        length_slider = ctk.CTkSlider(
            length_frame, from_=4, to=64, number_of_steps=60, variable=self.length_var,
            command=lambda v: length_value_label.configure(text=str(int(v))),
        )
        length_slider.pack(side="left", fill="x", expand=True, padx=8)
        length_value_label = ctk.CTkLabel(length_frame, text="16", width=30)
        length_value_label.pack(side="left")

        self.upper_var = ctk.BooleanVar(value=True)
        self.lower_var = ctk.BooleanVar(value=True)
        self.digits_var = ctk.BooleanVar(value=True)
        self.symbols_var = ctk.BooleanVar(value=True)

        checks = ctk.CTkFrame(panel, fg_color="transparent")
        checks.pack(fill="x", padx=16, pady=8)
        ctk.CTkCheckBox(checks, text="Uppercase (A-Z)", variable=self.upper_var).pack(anchor="w")
        ctk.CTkCheckBox(checks, text="Lowercase (a-z)", variable=self.lower_var).pack(anchor="w")
        ctk.CTkCheckBox(checks, text="Numbers (0-9)", variable=self.digits_var).pack(anchor="w")
        ctk.CTkCheckBox(checks, text="Symbols (!@#$...)", variable=self.symbols_var).pack(anchor="w")

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(buttons, text="Generate", command=self._handle_generate).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ctk.CTkButton(
            buttons, text="Copy", fg_color="gray30", command=self._handle_copy_generated
        ).pack(side="left", fill="x", expand=True)

    def _handle_generate(self) -> None:
        try:
            password = generate_password(
                length=int(self.length_var.get()),
                use_upper=self.upper_var.get(),
                use_lower=self.lower_var.get(),
                use_digits=self.digits_var.get(),
                use_symbols=self.symbols_var.get(),
            )
        except GeneratorError as exc:
            messagebox.showerror("Generator Error", str(exc))
            return
        self.gen_result_var.set(password)
        self.strength_label.configure(text=f"Strength: {estimate_strength(password)}")

    def _handle_copy_generated(self) -> None:
        value = self.gen_result_var.get()
        if value and "Click" not in value:
            pyperclip.copy(value)
            messagebox.showinfo("Copied", "Generated password copied to clipboard.")

    # ------------------------------------------------------------------
    # SETTINGS
    # ------------------------------------------------------------------
    def show_settings(self) -> None:
        self._clear_content()
        from ui.settings import SettingsPanel

        SettingsPanel(self.content, self.db, self.user_id).pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # LOGOUT / AUTO LOGOUT
    # ------------------------------------------------------------------
    def _logout(self) -> None:
        self.inactivity_monitor.stop()
        self.destroy()
        self._reopen_login()

    def _auto_logout(self) -> None:
        self.inactivity_monitor.stop()
        self.destroy()
        messagebox.showinfo("Session Expired", "You were logged out due to inactivity.")
        self._reopen_login()

    def _reopen_login(self) -> None:
        from ui.login_window import LoginWindow

        login = LoginWindow(self.db, self.crypto)
        login.mainloop()
