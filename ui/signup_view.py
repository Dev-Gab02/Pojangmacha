# ui/signup_view.py
import flet as ft
from core.db import SessionLocal
from core.auth_service import create_user
from core.session_manager import start_session

def signup_view(page: ft.Page):
    page.title = "Sign Up - Pojangmacha"
    db = SessionLocal()

    full_name = ft.TextField(label="Full Name", width=320)
    email = ft.TextField(label="Email", width=320)
    phone = ft.TextField(label="Phone Number", width=320)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=320)
    confirm_password = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, width=320)
    message = ft.Text(value="", color="red")

    def handle_signup(e):
        # basic validation
        if not all([full_name.value, email.value, phone.value, password.value, confirm_password.value]):
            message.value = "All fields are required!"
            message.color = "red"
            page.update()
            return
        if password.value != confirm_password.value:
            message.value = "Passwords do not match!"
            message.color = "red"
            page.update()
            return

        user, status = create_user(db, full_name.value, email.value, phone.value, password.value)
        if not user:
            message.value = status
            message.color = "red"
            page.update()
            return

        # store in session and start in-memory session
        page.session.set("user", {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role})
        start_session(user.email)

        message.value = "Account created successfully!"
        message.color = "green"
        page.update()
        page.go("/home")

    signup_btn = ft.ElevatedButton("Create Account", on_click=handle_signup)
    back_btn = ft.TextButton("Already have an account? Sign In", on_click=lambda e: page.go("/login"))

    page.clean()
    page.add(
        ft.Column(
            [
                ft.Text("Create Your Account", size=26, weight="bold"),
                full_name, email, phone, password, confirm_password,
                signup_btn,
                message,
                back_btn
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO
        )
    )