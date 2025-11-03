# ui/login_view.py
import flet as ft
from core.db import SessionLocal
from core.auth_service import authenticate_user

def login_view(page: ft.Page):
    page.title = "Login - Pojangmacha"
    db = SessionLocal()

    email = ft.TextField(label="Email", width=300)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)
    message = ft.Text(value="", color="red")

    def handle_login(e):
        user = authenticate_user(db, email.value, password.value)
        if not user:
            message.value = "Invalid email or password!"
            message.color = "red"
            page.update()
            return

        # ✅ Store user info in session
        page.session.set("user", {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        })

        message.value = f"Welcome, {user.full_name}!"
        message.color = "green"
        page.update()

        # Redirect based on role
        if user.role == "admin":
            page.go("/admin")
        else:
            page.go("/home")

    login_btn = ft.ElevatedButton("Sign In", on_click=handle_login)

    page.add(
        ft.Column(
            [
                ft.Text("Welcome Back", size=24, weight="bold"),
                email,
                password,
                login_btn,
                message,
                ft.TextButton("Don't have an account? Sign Up", on_click=lambda e: page.go("/signup"))
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )
    )
