"""
ui/login_window.py

The very first window the user sees. Handles three flows:
1. First run -> "Create Admin Account"
2. Normal run -> Login / Register tabs
3. "Forgot password?" recovery dialog

On successful login it closes itself and opens ui.dashboard.Dashboard.
"""

import logging

import customtkinter as ctk

from auth.login import (
    AuthenticationError,
    authenticate_user,
    clear_remembered_username,
    get_security_question,
    load_remembered_username,
    reset_password_with_security_answer,
    save_remembered_username,
)
from auth.register import RegistrationError, has_any_user, register_user
from database.database import Database
from encryption.crypto import CryptoManager

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LoginWindow(ctk.CTk):
    def __init__(self, db: Database, crypto: CryptoManager) -> None:
        super().__init__()
        self.db = db
        self.crypto = crypto

        self.title("Password Manager - Login")
        self.geometry("420x560")
        self.resizable(False, False)

        self._build_layout()

        if has_any_user(self.db):
            self._show_login_register()
        else:
            self._show_first_run()

    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=24, pady=24)

    def _clear_container(self) -> None:
        for widget in self.container.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # First-run: create the admin account
    # ------------------------------------------------------------------
    def _show_first_run(self) -> None:
        self._clear_container()

        ctk.CTkLabel(
            self.container, text="🔐 Welcome", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            self.container,
            text="Create your admin account to get started.",
            text_color="gray70",
        ).pack(pady=(0, 16))

        self.reg_username = self._labeled_entry("Username")
        self.reg_email = self._labeled_entry("Email")
        self.reg_password = self._labeled_entry("Master Password", show="*")
        self.reg_confirm = self._labeled_entry("Confirm Password", show="*")
        self.reg_question = self._labeled_entry("Security Question (e.g. First pet's name?)")
        self.reg_answer = self._labeled_entry("Security Answer", show="*")

        self.first_run_error = ctk.CTkLabel(self.container, text="", text_color="#ff6b6b")
        self.first_run_error.pack(pady=(4, 4))

        ctk.CTkButton(
            self.container, text="Create Admin Account", command=self._handle_create_admin
        ).pack(fill="x", pady=(12, 0))

    def _handle_create_admin(self) -> None:
        try:
            register_user(
                self.db,
                self.reg_username.get(),
                self.reg_email.get(),
                self.reg_password.get(),
                self.reg_confirm.get(),
                self.reg_question.get(),
                self.reg_answer.get(),
            )
        except RegistrationError as exc:
            self.first_run_error.configure(text=str(exc))
            return
        self._show_login_register()

    # ------------------------------------------------------------------
    # Normal Login / Register tabs
    # ------------------------------------------------------------------
    def _show_login_register(self) -> None:
        self._clear_container()

        ctk.CTkLabel(
            self.container, text="🔐 Password Manager", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(pady=(0, 16))

        self.tabs = ctk.CTkTabview(self.container, width=360)
        self.tabs.pack(fill="both", expand=True)
        self.tabs.add("Login")
        self.tabs.add("Register")

        self._build_login_tab(self.tabs.tab("Login"))
        self._build_register_tab(self.tabs.tab("Register"))

    def _build_login_tab(self, parent) -> None:
        self.login_username = self._labeled_entry("Username", parent=parent)
        remembered = load_remembered_username()
        if remembered:
            self.login_username.insert(0, remembered)

        self.login_password = self._labeled_entry("Password", show="*", parent=parent)

        self.remember_me_var = ctk.BooleanVar(value=bool(remembered))
        ctk.CTkCheckBox(parent, text="Remember me", variable=self.remember_me_var).pack(
            anchor="w", pady=(4, 0)
        )

        self.login_error = ctk.CTkLabel(parent, text="", text_color="#ff6b6b")
        self.login_error.pack(pady=(4, 4))

        ctk.CTkButton(parent, text="Login", command=self._handle_login).pack(fill="x", pady=(8, 4))
        ctk.CTkButton(
            parent,
            text="Forgot password?",
            fg_color="transparent",
            text_color="gray60",
            hover=False,
            command=self._open_forgot_password,
        ).pack(pady=(0, 4))

    def _build_register_tab(self, parent) -> None:
        self.reg2_username = self._labeled_entry("Username", parent=parent)
        self.reg2_email = self._labeled_entry("Email", parent=parent)
        self.reg2_password = self._labeled_entry("Password", show="*", parent=parent)
        self.reg2_confirm = self._labeled_entry("Confirm Password", show="*", parent=parent)
        self.reg2_question = self._labeled_entry("Security Question", parent=parent)
        self.reg2_answer = self._labeled_entry("Security Answer", show="*", parent=parent)

        self.register_error = ctk.CTkLabel(parent, text="", text_color="#ff6b6b")
        self.register_error.pack(pady=(4, 4))

        ctk.CTkButton(parent, text="Register", command=self._handle_register).pack(
            fill="x", pady=(8, 4)
        )

    # ------------------------------------------------------------------
    def _handle_login(self) -> None:
        username = self.login_username.get()
        password = self.login_password.get()
        try:
            user_row = authenticate_user(self.db, username, password)
        except AuthenticationError as exc:
            self.login_error.configure(text=str(exc))
            return

        if self.remember_me_var.get():
            save_remembered_username(username.strip())
        else:
            clear_remembered_username()

        self._open_dashboard(user_row)

    def _handle_register(self) -> None:
        try:
            register_user(
                self.db,
                self.reg2_username.get(),
                self.reg2_email.get(),
                self.reg2_password.get(),
                self.reg2_confirm.get(),
                self.reg2_question.get(),
                self.reg2_answer.get(),
            )
        except RegistrationError as exc:
            self.register_error.configure(text=str(exc))
            return
        self.register_error.configure(text_color="#51cf66", text="Account created! You can log in now.")
        self.tabs.set("Login")

    # ------------------------------------------------------------------
    def _open_forgot_password(self) -> None:
        ForgotPasswordDialog(self, self.db)

    def _open_dashboard(self, user_row) -> None:
        from ui.dashboard import Dashboard  # local import avoids a circular import

        self.destroy()
        app = Dashboard(self.db, self.crypto, user_id=user_row["id"], username=user_row["username"])
        app.mainloop()

    # ------------------------------------------------------------------
    # Small helper to keep label+entry creation DRY
    # ------------------------------------------------------------------
    def _labeled_entry(self, label_text: str, show: str | None = None, parent=None) -> ctk.CTkEntry:
        parent = parent or self.container
        ctk.CTkLabel(parent, text=label_text, anchor="w").pack(fill="x", pady=(8, 0))
        entry = ctk.CTkEntry(parent, show=show or "")
        entry.pack(fill="x")
        return entry


class ForgotPasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, db: Database) -> None:
        super().__init__(master)
        self.db = db
        self.title("Reset Password")
        self.geometry("360x420")
        self.grab_set()  # modal

        ctk.CTkLabel(self, text="Reset Password", font=ctk.CTkFont(size=18, weight="bold")).pack(
            pady=(16, 8)
        )

        ctk.CTkLabel(self, text="Username").pack(anchor="w", padx=16)
        self.username_entry = ctk.CTkEntry(self)
        self.username_entry.pack(fill="x", padx=16)

        ctk.CTkButton(self, text="Find Security Question", command=self._load_question).pack(
            pady=8, padx=16, fill="x"
        )

        self.question_label = ctk.CTkLabel(self, text="", wraplength=300, text_color="gray70")
        self.question_label.pack(padx=16, pady=(0, 4))

        self.answer_entry = None
        self.new_password_entry = None
        self.confirm_password_entry = None
        self.submit_button = None

        self.error_label = ctk.CTkLabel(self, text="", text_color="#ff6b6b", wraplength=300)
        self.error_label.pack(padx=16, pady=(4, 4))

    def _load_question(self) -> None:
        username = self.username_entry.get()
        question = get_security_question(self.db, username)
        if not question:
            self.error_label.configure(text="No account found with that username.")
            return

        self.question_label.configure(text=f"Q: {question}")

        if self.answer_entry is None:
            ctk.CTkLabel(self, text="Your Answer").pack(anchor="w", padx=16)
            self.answer_entry = ctk.CTkEntry(self, show="*")
            self.answer_entry.pack(fill="x", padx=16)

            ctk.CTkLabel(self, text="New Password").pack(anchor="w", padx=16, pady=(8, 0))
            self.new_password_entry = ctk.CTkEntry(self, show="*")
            self.new_password_entry.pack(fill="x", padx=16)

            ctk.CTkLabel(self, text="Confirm New Password").pack(anchor="w", padx=16, pady=(8, 0))
            self.confirm_password_entry = ctk.CTkEntry(self, show="*")
            self.confirm_password_entry.pack(fill="x", padx=16)

            self.submit_button = ctk.CTkButton(self, text="Reset Password", command=self._submit)
            self.submit_button.pack(fill="x", padx=16, pady=12)

    def _submit(self) -> None:
        try:
            reset_password_with_security_answer(
                self.db,
                self.username_entry.get(),
                self.answer_entry.get(),
                self.new_password_entry.get(),
                self.confirm_password_entry.get(),
            )
        except AuthenticationError as exc:
            self.error_label.configure(text=str(exc))
            return
        self.error_label.configure(text_color="#51cf66", text="Password reset! You can close this window.")
