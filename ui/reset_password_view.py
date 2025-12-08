# ui/reset_password_view.py
import flet as ft
from core.db import SessionLocal
from core.auth_service import generate_reset_token, verify_reset_token

def reset_password_view(page: ft.Page):
    page.title = "Reset Password - Pojangmacha"
    db = SessionLocal()

    email = ft.TextField(label="Email", width=300)
    token = ft.TextField(label="Reset Token", width=300)
    new_password = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=300)
    confirm_password = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, width=300)
    message = ft.Text("", color="red")

    # Step 1: Request reset token
    def request_token(e):
        if not email.value.strip():
            message.value = "Please enter your email."
            message.color = "red"
        else:
            token_value = generate_reset_token(email.value.strip())
            message.value = f"Reset token sent (check console): {token_value}"
            message.color = "green"
        page.update()

    # Step 2: Confirm password reset
    def reset_password(e):
        if not all([email.value, token.value, new_password.value, confirm_password.value]):
            message.value = "All fields are required."
            message.color = "red"
        elif new_password.value != confirm_password.value:
            message.value = "Passwords do not match."
            message.color = "red"
        elif len(new_password.value) < 6:
            message.value = "Password must be at least 6 characters."
            message.color = "red"
        else:
            ok = verify_reset_token(db, email.value.strip(), token.value.strip(), new_password.value)
            if ok:
                message.value = "Password reset successfully! You can now log in."
                message.color = "green"
            else:
                message.value = "Invalid or expired token."
                message.color = "red"
        page.update()

    page.clean()
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=40),
                    ft.Text("Reset Password", size=24, weight="bold"),
                    email,
                    ft.Row([ft.ElevatedButton("Request Token", on_click=request_token)]),
                    token,
                    new_password,
                    confirm_password,
                    ft.Row([ft.ElevatedButton("Reset Password", on_click=reset_password)]),
                    message,
                    ft.TextButton("Back to Login", on_click=lambda e: page.go("/login"))
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO
            ),
            width=400,
            height=700,
            padding=ft.padding.symmetric(horizontal=25)
        )
    )
