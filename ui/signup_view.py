# ui/signup_view.py
import flet as ft
from core.db import SessionLocal
from core.auth_service import create_user

def signup_view(page: ft.Page):
    page.title = "Sign Up - Pojangmacha"
    db = SessionLocal()

    full_name = ft.TextField(label="Full Name", width=300)
    email = ft.TextField(label="Email", width=300)
    phone = ft.TextField(label="Phone Number", width=300)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)
    confirm_password = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, width=300)
    message = ft.Text(value="", color="red")

    def handle_signup(e):
        if not all([full_name.value, email.value, phone.value, password.value, confirm_password.value]):
            message.value = "All fields are required!"
            page.update()
            return

        if password.value != confirm_password.value:
            message.value = "Passwords do not match!"
            page.update()
            return

        new_user = create_user(db, full_name.value, email.value, phone.value, password.value)
        if new_user:
            page.session.set("user", {
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "role": new_user.role
            })
            message.value = "Account created successfully!"
            message.color = "green"
            page.update()
            page.go("/home")
        else:
            message.value = "Email already exists."
            message.color = "red"
            page.update()

    signup_btn = ft.ElevatedButton("Create Account", on_click=handle_signup)

    page.add(
        ft.Column(
            [
                ft.Text("Create Your Account", size=24, weight="bold"),
                full_name,
                email,
                phone,
                password,
                confirm_password,
                signup_btn,
                message,
                ft.TextButton("Already have an account? Sign In", on_click=lambda e: page.go("/login")),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )
    )
