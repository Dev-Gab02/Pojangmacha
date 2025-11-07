# ui/login_view.py
import flet as ft
from core.db import SessionLocal
from core.auth_service import authenticate_user
from core.session_manager import start_session

def login_view(page: ft.Page):
    page.title = "Login - Pojangmacha"
    db = SessionLocal()

    email = ft.TextField(label="Email", width=300)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)
    message = ft.Text(value="", color="red")

    def handle_login(e):
        user, status = authenticate_user(db, email.value, password.value)
        message.value = status
        message.color = "red" if not user else "green"
        page.update()

        if user:
            page.session.set("user", {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            })
            start_session(user.email)
            if user.role == "admin":
                page.go("/admin")
            else:
                page.go("/home")

    login_btn = ft.ElevatedButton("Sign In", on_click=handle_login)
    signup_btn = ft.TextButton("Don't have an account? Sign Up", on_click=lambda e: page.go("/signup"))
    forgot_password_btn = ft.TextButton("Forgot Password?", on_click=lambda e: page.go("/reset_password"))

    page.clean()
    page.add(
        ft.Column(
            [
                ft.Text("Welcome Back", size=24, weight="bold"),
                email,
                password,
                login_btn,
                message,
                forgot_password_btn,
                signup_btn
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )
    )