# ui/reset_password_view.py
import flet as ft
from core.db import SessionLocal
from core.auth_service import create_password_reset, reset_password_with_token

def reset_password_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Reset Password - Pojangmacha"

    email_field = ft.TextField(label="Registered Email", width=320)
    token_field = ft.TextField(label="Reset Token (Check console/email)", width=320, visible=False)
    new_password = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=320, visible=False)
    status_text = ft.Text(value="", color="red")
    
    reset_btn = ft.ElevatedButton("Reset with Token", visible=False, width=320)

    def handle_request(e):
        if not email_field.value or "@" not in email_field.value:
            status_text.value = "❌ Please enter a valid email address"
            status_text.color = "red"
            page.update()
            return
            
        token, msg = create_password_reset(db, email_field.value)
        if token:
            status_text.value = f"✅ {msg}\n\n🔑 Your Token: {token}\n\n(Save this token to reset your password)"
            status_text.color = "green"
            token_field.visible = True
            new_password.visible = True
            reset_btn.visible = True
        else:
            status_text.value = f"❌ {msg}"
            status_text.color = "red"
        page.update()

    def handle_reset(e):
        if not token_field.value or not new_password.value:
            status_text.value = "❌ Please enter token and new password"
            status_text.color = "red"
            page.update()
            return
        
        if len(new_password.value) < 6:
            status_text.value = "❌ Password must be at least 6 characters"
            status_text.color = "red"
            page.update()
            return
            
        success, msg = reset_password_with_token(db, token_field.value, new_password.value)
        if success:
            status_text.value = f"✅ {msg}\nRedirecting to login..."
            status_text.color = "green"
            page.update()
            import time
            time.sleep(2)
            page.go("/login")
        else:
            status_text.value = f"❌ {msg}"
            status_text.color = "red"
            page.update()

    reset_btn.on_click = handle_reset

    request_btn = ft.ElevatedButton(
        "Request Reset Token", 
        on_click=handle_request,
        width=320,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.ORANGE_700,
        )
    )

    page.clean()
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(height=30),
                    ft.Icon(ft.Icons.LOCK_RESET, size=50, color=ft.Colors.ORANGE_700),
                    ft.Text("Reset Password", size=26, weight="bold", color=ft.Colors.ORANGE_700),
                    ft.Text("Enter your registered email to receive a reset token", 
                            size=14, color="grey", text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    email_field,
                    request_btn,
                    ft.Container(height=10),
                    status_text,
                    ft.Divider(height=1, thickness=1, visible=False),
                    token_field,
                    new_password,
                    reset_btn,
                    ft.Container(height=10),
                    ft.Divider(height=1, thickness=1),
                    ft.TextButton(
                        "← Back to Login", 
                        on_click=lambda e: page.go("/login")
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
                spacing=10
            ),
            padding=20,
            alignment=ft.alignment.center,
            expand=True
        )
    )