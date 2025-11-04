# ui/login_view.py
import flet as ft
from core.db import SessionLocal
from core.auth_service import authenticate_user
from core.session_manager import start_session

def login_view(page: ft.Page):
    page.title = "Login - Pojangmacha"
    db = SessionLocal()

    email = ft.TextField(label="Email", width=320)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=320)
    message = ft.Text(value="", color="red")

    def handle_login(e):
        user, status = authenticate_user(db, email.value or "", password.value or "")
        if not user:
            message.value = status
            message.color = "red"
            page.update()
            return

        # store minimal session info in page.session (persisted per Flet session)
        page.session.set("user", {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        })

        # start in-memory session monitor for demo
        start_session(user.email)

        message.value = f"Welcome, {user.full_name}!"
        message.color = "green"
        page.update()

        # redirect based on role
        if user.role == "admin":
            page.go("/admin")
        else:
            page.go("/home")

    login_btn = ft.ElevatedButton("Sign In", on_click=handle_login)
    forgot_btn = ft.TextButton("Forgot Password?", on_click=lambda e: page.go("/reset_password"))
    signup_btn = ft.TextButton("Don't have an account? Sign Up", on_click=lambda e: page.go("/signup"))

    # Render
    page.clean()
    page.add(
        ft.Column(
            [
                ft.Text("Welcome Back", size=26, weight="bold"),
                email,
                password,
                ft.Row([login_btn, forgot_btn], alignment=ft.MainAxisAlignment.CENTER),
                message,
                signup_btn
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO
        )
    )
