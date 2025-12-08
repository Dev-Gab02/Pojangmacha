import os
import flet as ft
import threading
import time
from datetime import datetime

from core.db import SessionLocal
from core.session_manager import start_session
from core.auth_service import authenticate_user, create_user_from_google, hash_password
from core.google_auth import get_google_user_info
from core.two_fa_ui_service import show_login_2fa_dialog
from core.email_service import generate_verification_code, send_password_reset_email, store_password_reset_code, verify_password_reset_code, resend_password_reset_code

from core.lockout_service import (
    get_global_failed_attempts,
    set_global_lockout,
    get_global_lockout,
    clear_global_lockout,
    record_login_attempt,
    MAX_FAILED_ATTEMPTS,

)

# ===== BRAND COLORS =====
ORANGE = "#FF6B35"
LIGHT_GRAY = "#D9D9D9"
DARK_GRAY = "#cdbcbc"
WHITE = "#FFFFFF"

def show_lockout_dialog(page, locked_until, message):
    timer_display = ft.Text(value="", size=18, weight="bold", color="#E50914", text_align="center")
    status_message = ft.Text("Please wait for the countdown to finish..", size=14, color="red", text_align="center")
    cancel_button = ft.TextButton("Cancel", disabled=True, style=ft.ButtonStyle(color="black"))

    def close_dialog(e):
        dlg.open = False,
        message.value = "" 
        page.update()

    cancel_button.on_click = close_dialog

    dlg = ft.AlertDialog(
        modal=True,
        content=ft.Container(
            alignment=ft.alignment.center,
            width=330,
            height=140,
            content=ft.Column([
                ft.Text("Temporarily Locked", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                status_message,
                timer_display
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            padding=20
        ),
        actions=[cancel_button],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor='white'
    )

    page.overlay.append(dlg)
    dlg.open = True
    page.update()

    def countdown():
        while True:
            now = datetime.utcnow()
            remaining = int((locked_until - now).total_seconds())
            if remaining > 0:
                minutes = remaining // 60
                seconds = remaining % 60
                timer_display.value = f"Locked for: {minutes:02d}:{seconds:02d}"
                page.update()
                time.sleep(1)
            else:
                timer_display.value = "Locked for: 00:00"
                status_message.value = "You can try logging in again."
                status_message.color = "green"
                cancel_button.disabled = False
                clear_global_lockout(db)
                page.update()
                break

    threading.Thread(target=countdown, daemon=True).start()

def login_view(page: ft.Page):
    page.title = "Login - Pojangmacha"
    global db
    db = SessionLocal()
    MOBILE_WIDTH = 350

    # ===== INPUT FIELDS (NEW DESIGN) =====
    email = ft.TextField(
        label="Email Address",
        label_style=ft.TextStyle(color="#000000"),
        hint_text="Enter your Email",
        hint_style=ft.TextStyle(color="#000000"), 
        color="#000000",
        width=MOBILE_WIDTH,
        border_radius=12,
        filled=True,
        bgcolor=LIGHT_GRAY,
        border_color="transparent",
        focused_border_color=ORANGE,
        prefix_icon=ft.Icons.EMAIL_OUTLINED,
        text_size=14,
        height=55
    )
    
    password = ft.TextField(
        label="Password",
        label_style=ft.TextStyle(color="#000000"),
        hint_text="Create a Password",
        hint_style=ft.TextStyle(color="#000000"), 
        color="#000000",
        password=True,
        can_reveal_password=True,
        width=MOBILE_WIDTH,
        border_radius=12,
        filled=True,
        bgcolor=LIGHT_GRAY,
        border_color="transparent",
        focused_border_color=ORANGE,
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        text_size=14,
        height=55
    )

    message = ft.Text(value="", color="red", size=12, text_align=ft.TextAlign.CENTER)

    def complete_login(user):
        page.session.set("user", {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        })
        try:
            start_session(user.email)
        except Exception as ex:
            print("start_session error:", ex)
        page.snack_bar = ft.SnackBar(
            ft.Text(f"Welcome, {user.full_name}!"),
            bgcolor=ft.Colors.GREEN
        )
        page.snack_bar.open = True
        page.update()
        if user.role == "admin":
            page.go("/admin")
        else:
            page.go("/home")

    def handle_login(e):
        email_val = email.value.strip()
        pwd_val = password.value.strip()

        locked_until = get_global_lockout(db)
        if locked_until:
            show_lockout_dialog(page, locked_until, message)
            return

        if not email_val or not pwd_val:
            message.value = "Please enter email and password"
            message.color = "red"
            page.update()
            return
        try:
            user, status = authenticate_user(db, email_val, pwd_val)
            if not user:
                record_login_attempt(db, email_val, False)
                failed_count = get_global_failed_attempts(db)
                if failed_count >= MAX_FAILED_ATTEMPTS:
                    set_global_lockout(db)
                    locked_until = get_global_lockout(db)
                    show_lockout_dialog(page, locked_until, message)
                    return
                attempts_left = MAX_FAILED_ATTEMPTS - failed_count
                message.value = f"Invalid credentials. {attempts_left} attempt(s) remaining."
                message.color = "red"
                page.update()
                return
            record_login_attempt(db, email_val, True)
            if user.two_fa_enabled:
                message.value = "Sending 2FA code..."
                message.color = "blue"
                page.update()
                def send_2fa_thread():
                    from core.two_fa_service import send_2fa_code
                    if send_2fa_code(user.email):
                        def on_cancel():
                            message.value = ""
                            page.update()
                        show_login_2fa_dialog(page, db, user, complete_login, on_cancel)
                    else:
                        message.value = "Failed to send 2FA code"
                        message.color = "red"
                        page.update()
                thread = threading.Thread(target=send_2fa_thread, daemon=True)
                thread.start()
                return
            complete_login(user)
        except Exception as ex:
            print("Login error:", ex)
            message.value = "An error occurred during login."
            message.color = "red"
            page.update()

    def handle_google_login(e):
        message.value = "Opening Google Sign-In..."
        message.color = "blue"
        google_btn.disabled = True
        page.update()
        def google_auth_thread():
            try:
                user_info = get_google_user_info(force_new_login=True)
                if not user_info or not user_info.get('email'):
                    message.value = "Google Sign-In failed or was cancelled"
                    message.color = "red"
                    google_btn.disabled = False
                    page.update()
                    return
                user = create_user_from_google(
                    db,
                    email=user_info['email'],
                    full_name=user_info.get('name', 'Google User'),
                    picture=user_info.get('picture')
                )
                record_login_attempt(db, user.email, True)
                complete_login(user)
            except Exception as ex:
                print(f"Google OAuth error: {ex}")
                message.value = f"Error: {str(ex)}"
                message.color = "red"
                google_btn.disabled = False
                page.update()
        thread = threading.Thread(target=google_auth_thread, daemon=True)
        thread.start()

    # ===== FORGOT PASSWORD DIALOG =====
    def forgot_password_dialog(e):
        from models.user import User
        email_input = ft.TextField(
            label="Email",
            width=300,
            border_radius=12,
            filled=True,
            bgcolor=LIGHT_GRAY,
            border_color="transparent",
            focused_border_color=ORANGE,
            prefix_icon=ft.Icons.EMAIL_OUTLINED,
            height=55
        )
        step1_message = ft.Text("", color="red", size=12, text_align=ft.TextAlign.CENTER)
        code_input = ft.TextField(
            label="Enter 6-digit code",
            width=300,
            max_length=6,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=12,
            filled=True,
            bgcolor=LIGHT_GRAY,
            border_color="transparent",
            focused_border_color=ORANGE,
            text_size=18,
            height=55
        )
        step2_message = ft.Text("", color="red", size=12, text_align=ft.TextAlign.CENTER)
        new_pass = ft.TextField(
            label="New Password",
            password=True,
            can_reveal_password=True,
            width=300,
            border_radius=12,
            filled=True,
            bgcolor=LIGHT_GRAY,
            border_color="transparent",
            focused_border_color=ORANGE,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            height=55
        )
        confirm_pass = ft.TextField(
            label="Confirm New Password",
            password=True,
            can_reveal_password=True,
            width=300,
            border_radius=12,
            filled=True,
            bgcolor=LIGHT_GRAY,
            border_color="transparent",
            focused_border_color=ORANGE,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            height=55
        )
        step3_message = ft.Text("", color="red", size=12, text_align=ft.TextAlign.CENTER)
        step1_container = ft.Container()
        step2_container = ft.Container(visible=False)
        step3_container = ft.Container(visible=False)
        temp_email = {"value": ""}
        code_sent = {"value": False}

        def show_step_1():
            step1_container.visible = True
            step2_container.visible = False
            step3_container.visible = False
            step1_container.content = ft.Column([
                ft.Container(
                    content=ft.Text("Forgot Password", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                    padding=ft.padding.only(top=30)
                ),
                ft.Text("Enter your email to receive a reset code.", size=12, color='black', text_align=ft.TextAlign.CENTER),
                email_input,
                ft.Container(
                    content=ft.ElevatedButton("Send Reset Code", color='black', bgcolor="#FEB23F", width=300, on_click=send_reset_code),
                    alignment=ft.alignment.center,
                ),
                step1_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
            page.update()

        def show_step_2():
            step1_container.visible = False
            step2_container.visible = True
            step3_container.visible = False
            step2_container.content = ft.Column([
                ft.Container(
                    content=ft.Text("Forgot Password", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                    padding=ft.padding.only(top=30)
                ),
                ft.Text("Enter the code sent to your email.", size=12, text_align=ft.TextAlign.CENTER),
                code_input,
                ft.Container(
                    content=ft.ElevatedButton("Verify", color='black', bgcolor="#FEB23F", width=300, on_click=verify_code),
                    alignment=ft.alignment.center
                ),
                ft.Container(
                    content=ft.TextButton(
                        "Resend Code",
                        on_click=resend_code,
                        style=ft.ButtonStyle(color="blue500", bgcolor="transparent", shape=ft.RoundedRectangleBorder(radius=12))
                    ),
                    alignment=ft.alignment.center
                ),
                step2_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6)
            page.update()

        def show_step_3():
            step1_container.visible = False
            step2_container.visible = False
            step3_container.visible = True
            step3_container.content = ft.Column([
                ft.Text("Forgot Password", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Text("Enter your new password.", size=12, text_align=ft.TextAlign.CENTER),
                new_pass,
                confirm_pass,
                ft.Container(
                    content=ft.ElevatedButton("Reset Password", color='black', bgcolor="#FEB23F", width=300, on_click=reset_password),
                    alignment=ft.alignment.center
                ),
                step3_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)
            page.update()

        def send_reset_code(ev):
            if not email_input.value or not email_input.value.strip():
                step1_message.value = "Please enter your email"
                step1_message.color = "red"
                page.update()
                return
            user = db.query(User).filter(User.email == email_input.value.strip()).first()
            if not user:
                step1_message.value = "Email not found"
                step1_message.color = "red"
                page.update()
                return
            temp_email["value"] = email_input.value.strip()
            step1_message.value = "Sending reset code..."
            step1_message.color = "blue"
            page.update()
            def send_email_thread():
                code = generate_verification_code()
                if send_password_reset_email(temp_email["value"], code):
                    store_password_reset_code(temp_email["value"], code)
                    code_sent["value"] = True
                    show_step_2()
                else:
                    step1_message.value = "Failed to send email"
                    step1_message.color = "red"
                    page.update()
            threading.Thread(target=send_email_thread, daemon=True).start()

        def resend_code(ev):
            step2_message.value = "Resending code..."
            step2_message.color = "blue"
            page.update()
            def resend_thread():
                if resend_password_reset_code(temp_email["value"]):
                    step2_message.value = "New code sent"
                    step2_message.color = "green"
                else:
                    step2_message.value = "Failed to send code"
                    step2_message.color = "red"
                page.update()
            threading.Thread(target=resend_thread, daemon=True).start()

        def verify_code(ev):
            if not code_input.value or len(code_input.value) != 6:
                step2_message.value = "Please enter the 6-digit code"
                step2_message.color = "red"
                page.update()
                return
            if verify_password_reset_code(temp_email["value"], code_input.value):
                show_step_3()
            else:
                step2_message.value = "Invalid or expired code"
                step2_message.color = "red"
                page.update()

        def reset_password(ev):
            if not new_pass.value or not confirm_pass.value:
                step3_message.value = "All fields required"
                step3_message.color = "red"
                page.update()
                return
            if new_pass.value != confirm_pass.value:
                step3_message.value = "Passwords do not match"
                step3_message.color = "red"
                page.update()
                return
            if len(new_pass.value) < 6:
                step3_message.value = "Password too short (min 6 characters)"
                step3_message.color = "red"
                page.update()
                return
            user = db.query(User).filter(User.email == temp_email["value"]).first()
            if user:
                user.password_hash = hash_password(new_pass.value)
                db.commit()
                step3_message.value = "Password reset successful!"
                step3_message.color = "green"
                page.update()
                close_dialog()
                page.snack_bar = ft.SnackBar(
                    ft.Text("Password reset successful! Please log in."),
                    bgcolor=ft.Colors.GREEN
                )
                page.snack_bar.open = True
                page.update()
            else:
                step3_message.value = "User not found"
                step3_message.color = "red"
                page.update()

        dlg = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                alignment=ft.alignment.center,  
                width=350,    
                height=250,                  
                content=ft.Column([
                    step1_container,
                    step2_container,
                    step3_container
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=10
            ),
            actions=[
                ft.TextButton(
                    "Cancel",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(color="black")
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor='white'
        )

        show_step_1()
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ===== GLOBAL close_dialog FUNCTION =====
    def close_dialog(e=None):
        try:
            for item in list(page.overlay):
                if hasattr(item, "open") and getattr(item, "open"):
                    item.open = False
            page.update()
        except Exception as ex:
            print("close_dialog error:", ex)

    # ===== UI COMPONENTS (NEW DESIGN) =====
    brand_logo = ft.Image(
        src="assets/Brand.png",
        width=300,
        height=50,
        fit=ft.ImageFit.CONTAIN
    )
    welcome_text = ft.Text(
        "Welcome back!!!",
        size=22,
        weight="bold",
        color="#000000"
    )
    subtitle_text = ft.Text(
        "Sign in to your Account",
        size=12,
        color=DARK_GRAY
    )
    login_btn = ft.Container(
        content=ft.Text("Sign In", size=18, weight="bold", color=WHITE),
        width=MOBILE_WIDTH,
        height=50,
        bgcolor="#FEB23F",  
        border_radius=12,
        alignment=ft.alignment.center,
        on_click=handle_login,
        ink=True,
        animate=ft.Animation(200, "easeOut")
    )
    forgot_pass_btn = ft.Container(
        content=ft.Text("Forgot Password?", size=12, color=ORANGE, weight="bold"),
        on_click=forgot_password_dialog,
        ink=True
    )
    divider_row = ft.Row([
        ft.Container(expand=True, height=1, bgcolor="#E0E0E0"),
        ft.Text("OR", size=12, color=DARK_GRAY, weight="bold"),
        ft.Container(expand=True, height=1, bgcolor="#E0E0E0"),
    ], spacing=10, width=MOBILE_WIDTH)
    google_btn = ft.Container(
        content=ft.Row([
            ft.Image(
                src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg",
                width=24,
                height=24
            ),
            ft.Text("Continue with Google", size=14, color="#000000", weight="w500")
        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
        width=MOBILE_WIDTH,
        height=50,
        bgcolor=LIGHT_GRAY,
        border=ft.border.all(1, "#E0E0E0"),
        border_radius=12,
        on_click=handle_google_login,
        ink=True,
        animate=ft.Animation(200, "easeOut")
    )
    signup_row = ft.Row([
        ft.Text("Don't have an account?", size=13, color=DARK_GRAY),
        ft.Container(
            content=ft.Text("Sign Up", size=13, color=ORANGE, weight="bold"),
            on_click=lambda e: page.go("/signup"),
            ink=True
        )
    ], spacing=5, alignment=ft.MainAxisAlignment.CENTER)

    def show_login_form():
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Container(height=8),
                    welcome_text,
                    subtitle_text,
                    ft.Container(height=6),
                    brand_logo,
                    ft.Container(height=25),
                    email,
                    ft.Container(height=8),
                    password,
                    ft.Container(
                        content=forgot_pass_btn,
                        alignment=ft.alignment.center_right,
                        width=MOBILE_WIDTH,
                        margin=ft.margin.only(top=1)
                    ),
                    ft.Container(height=20),
                    login_btn,
                    ft.Container(height=4),
                    message,
                    ft.Container(height=10),
                    divider_row,
                    ft.Container(height=30),
                    google_btn,
                    ft.Container(height=8),
                    signup_row,
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,
                spacing=0
                ),
                width=400,
                expand=True,
                padding=ft.padding.symmetric(horizontal=25),
                bgcolor=WHITE,
                alignment=ft.alignment.center
            )
        )
        page.update()

    show_login_form()