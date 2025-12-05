import os
import flet as ft
from core.db import SessionLocal
from core.session_manager import start_session
from core.auth_service import authenticate_user, create_user_from_google, hash_password
from core.google_auth import get_google_user_info
from core.two_fa_ui_service import show_login_2fa_dialog
from core.email_service import generate_verification_code, send_password_reset_email, store_password_reset_code, verify_password_reset_code, resend_password_reset_code
from core.lockout_service import (
    record_failed_attempt,
    record_successful_login,
    is_account_locked,
    get_remaining_attempts,
    format_lockout_time,
    check_any_active_lockout
)
import threading
import time

# ===== BRAND COLORS =====
ORANGE = "#FF6B35"
LIGHT_GRAY = "#D9D9D9"
DARK_GRAY = "#cdbcbc"
WHITE = "#FFFFFF"

def login_view(page: ft.Page):
    page.title = "Login - Pojangmacha"
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
    
    # ===== LOCKOUT UI (ENHANCED) =====
    lockout_message = ft.Text(value="", color="red", size=14, weight="bold")
    countdown_text = ft.Text(value="", color="orange", size=13)
    lockout_info = ft.Text(value="", color=DARK_GRAY, size=11, italic=True)
    lockout_container = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.LOCK_CLOCK, size=50, color="orange"),
            lockout_message,
            countdown_text,
            lockout_info
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        visible=False,
        padding=15,
        border=ft.border.all(2, "#FFA726"),
        border_radius=12,
        bgcolor="#FFF3E0",
        margin=ft.margin.only(bottom=10)
    )
    
    # Countdown thread control
    countdown_active = {"value": False}

    # ===== LOCKOUT COUNTDOWN =====
    def start_lockout_countdown(locked_until, locked_email=None):
        """Start live countdown timer"""
        countdown_active["value"] = True
        
        def countdown_thread():
            while countdown_active["value"]:
                from datetime import datetime
                
                remaining_seconds = int((locked_until - datetime.utcnow()).total_seconds())
                
                if remaining_seconds <= 0:
                    lockout_container.visible = False
                    login_btn.disabled = False
                    forgot_pass_btn.disabled = False
                    google_btn.disabled = False
                    signup_row.disabled = False
                    email.disabled = False
                    password.disabled = False
                    countdown_active["value"] = False
                    
                    message.value = "✅ Account unlocked. You can login now."
                    message.color = "green"
                    page.update()
                    break
                
                countdown_text.value = f"⏱️ Time remaining: {format_lockout_time(remaining_seconds)}"
                if locked_email:
                    lockout_info.value = f"Account: {locked_email}"
                page.update()
                
                time.sleep(1)
        
        thread = threading.Thread(target=countdown_thread, daemon=True)
        thread.start()

    def check_lockout_status():
        """Check if account is locked"""
        if not email.value or not email.value.strip():
            return False
        
        locked, locked_until, remaining = is_account_locked(db, email.value.strip())
        
        if locked:
            lockout_message.value = "🔒 Account Temporarily Locked"
            lockout_info.value = f"Account: {email.value.strip()}"
            lockout_container.visible = True
            
            login_btn.disabled = True
            forgot_pass_btn.disabled = True
            google_btn.disabled = True
            email.disabled = True
            password.disabled = True
            
            start_lockout_countdown(locked_until, email.value.strip())
            page.update()
            return True
        
        return False

    def check_global_lockout():
        """Check if ANY account is locked on page load"""
        has_lockout, locked_email, locked_until, remaining = check_any_active_lockout(db)
        
        if has_lockout:
            lockout_message.value = "🔒 System Temporarily Locked"
            lockout_info.value = "Please wait for the countdown to finish."
            lockout_container.visible = True
            
            login_btn.disabled = True
            forgot_pass_btn.disabled = True
            google_btn.disabled = True
            email.disabled = True
            password.disabled = True
            
            if locked_email:
                email.value = locked_email
                lockout_info.value = f"Account: {locked_email}"
            
            start_lockout_countdown(locked_until, locked_email)
            page.update()
            return True
        
        return False

    # ===== COMPLETE LOGIN =====
    def complete_login(user):
        """Complete login after authentication (callback for 2FA)"""
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
            ft.Text(f"✅ Welcome, {user.full_name}!"),
            bgcolor=ft.Colors.GREEN
        )
        page.snack_bar.open = True
        page.update()

        if user.role == "admin":
            page.go("/admin")
        else:
            page.go("/home")

    # ===== LOGIN HANDLER =====
    def handle_login(e):
        if check_lockout_status():
            return
        
        if not email.value or not password.value:
            message.value = "❌ Please enter email and password"
            message.color = "red"
            page.update()
            return
        
        try:
            user, status = authenticate_user(db, email.value, password.value)
            
            if not user:
                failed_count, locked_until = record_failed_attempt(db, email.value.strip())
                
                if locked_until:
                    lockout_message.value = "🔒 Too Many Failed Attempts!"
                    lockout_info.value = f"Account: {email.value.strip()}"
                    message.value = f"❌ Account locked for 15 minutes after {failed_count} failed attempts"
                    message.color = "red"
                    lockout_container.visible = True
                    
                    login_btn.disabled = True
                    forgot_pass_btn.disabled = True
                    google_btn.disabled = True
                    email.disabled = True
                    password.disabled = True
                    
                    start_lockout_countdown(locked_until, email.value.strip())
                else:
                    remaining = get_remaining_attempts(db, email.value.strip())
                    message.value = f"❌ Invalid credentials. {remaining} attempt(s) remaining."
                    message.color = "red"
                
                page.update()
                return

            record_successful_login(db, email.value.strip())
            
            # ✅ CHANGE: Use show_login_2fa_dialog from two_fa_ui_service
            if user.two_fa_enabled:
                message.value = "📧 Sending 2FA code..."
                message.color = "blue"
                login_btn.disabled = True
                page.update()
                
                def send_2fa_thread():
                    from core.two_fa_service import send_2fa_code
                    if send_2fa_code(user.email):
                        # ✅ ADDED: Define cancel callback to reset UI
                        def on_cancel():
                            message.value = ""
                            login_btn.disabled = False
                            page.update()
                        
                        # ✅ CHANGED: Pass cancel callback
                        show_login_2fa_dialog(page, db, user, complete_login, on_cancel)
                    else:
                        message.value = "❌ Failed to send 2FA code"
                        message.color = "red"
                        login_btn.disabled = False
                        page.update()
                
                thread = threading.Thread(target=send_2fa_thread, daemon=True)
                thread.start()
                return

            complete_login(user)

        except Exception as ex:
            print("Login error:", ex)
            message.value = "❌ An error occurred during login."
            message.color = "red"
            page.update()

    # ===== GOOGLE LOGIN =====
    def handle_google_login(e):
        """Handle Google sign-in"""
        if email.value and email.value.strip():
            if check_lockout_status():
                return
        
        message.value = "🔄 Opening Google Sign-In..."
        message.color = "blue"
        google_btn.disabled = True
        page.update()
        
        def google_auth_thread():
            try:
                user_info = get_google_user_info(force_new_login=True)
                
                if not user_info or not user_info.get('email'):
                    message.value = "❌ Google Sign-In failed or was cancelled"
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
                
                record_successful_login(db, user.email)
                complete_login(user)
                
            except Exception as ex:
                print(f"Google OAuth error: {ex}")
                message.value = f"❌ Error: {str(ex)}"
                message.color = "red"
                google_btn.disabled = False
                page.update()
        
        thread = threading.Thread(target=google_auth_thread, daemon=True)
        thread.start()

    # ===== FORGOT PASSWORD DIALOG =====
    def forgot_password_dialog(e):
        """Show forgot password flow"""
        if email.value and email.value.strip():
            if check_lockout_status():
                message.value = "❌ Account is locked. Please wait."
                message.color = "red"
                page.update()
                return
        
        from models.user import User
        
        email_input = ft.TextField(
            label="Enter your email",
            label_style=ft.TextStyle(color="#000000"), 
            color="#000000",
            width=300,
            border_radius=12,
            filled=True,
            bgcolor=LIGHT_GRAY,
            border_color="transparent",
            focused_border_color=ORANGE,
            prefix_icon=ft.Icons.EMAIL_OUTLINED,
            height=55
        )
        step1_message = ft.Text("", color="red", size=12)
        
        code_input = ft.TextField(
            label="Enter 6-digit code",
            label_style=ft.TextStyle(color="#000000"), 
            color="#000000",
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
        
        new_pass = ft.TextField(
            label="New password",
            label_style=ft.TextStyle(color="#000000"),
            color="#000000",
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
            label="Confirm password",
            label_style=ft.TextStyle(color="#000000"),
            color="#000000",
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
        
        step2_message = ft.Text("", color="red", size=12)
        
        step1_container = ft.Container()
        step2_container = ft.Container()
        step3_container = ft.Container()
        
        current_step = {"value": 1}
        temp_email = {"value": ""}
        
        def send_reset_code(ev):
            if not email_input.value or not email_input.value.strip():
                step1_message.value = "❌ Please enter your email"
                step1_message.color = "red"
                page.update()
                return
            
            locked, locked_until, remaining = is_account_locked(db, email_input.value.strip())
            if locked:
                step1_message.value = f"❌ Account locked. Wait {format_lockout_time(remaining)}"
                step1_message.color = "red"
                page.update()
                return
            
            user = db.query(User).filter(User.email == email_input.value.strip()).first()
            if not user:
                step1_message.value = "❌ Email not found"
                step1_message.color = "red"
                page.update()
                return
            
            temp_email["value"] = email_input.value.strip()
            step1_message.value = "📧 Sending reset code..."
            step1_message.color = "blue"
            send_code_btn.disabled = True
            page.update()
            
            def send_email_thread():
                code = generate_verification_code()
                if send_password_reset_email(temp_email["value"], code):
                    store_password_reset_code(db, temp_email["value"], code)
                    current_step["value"] = 2
                    show_step_2()
                else:
                    step1_message.value = "❌ Failed to send email"
                    step1_message.color = "red"
                    send_code_btn.disabled = False
                    page.update()
            
            thread = threading.Thread(target=send_email_thread, daemon=True)
            thread.start()
        
        def verify_code_step(ev):
            if not code_input.value or len(code_input.value) != 6:
                step2_message.value = "❌ Please enter the 6-digit code"
                step2_message.color = "red"
                page.update()
                return
            
            if verify_password_reset_code(db, temp_email["value"], code_input.value):
                current_step["value"] = 3
                show_step_3()
            else:
                step2_message.value = "❌ Invalid or expired code"
                step2_message.color = "red"
                page.update()
        
        def resend_reset_code(ev):
            step2_message.value = "📧 Resending code..."
            step2_message.color = "blue"
            page.update()
            
            def resend_thread():
                if resend_password_reset_code(db, temp_email["value"]):
                    step2_message.value = "✅ New code sent"
                    step2_message.color = "green"
                else:
                    step2_message.value = "❌ Failed to send code"
                    step2_message.color = "red"
                page.update()
            
            thread = threading.Thread(target=resend_thread, daemon=True)
            thread.start()
        
        def reset_password_final(ev):
            if not all([new_pass.value, confirm_pass.value]):
                step2_message.value = "❌ All fields required"
                step2_message.color = "red"
                page.update()
                return
            
            if new_pass.value != confirm_pass.value:
                step2_message.value = "❌ Passwords do not match"
                step2_message.color = "red"
                page.update()
                return
            
            if len(new_pass.value) < 6:
                step2_message.value = "❌ Password too short (min 6 characters)"
                step2_message.color = "red"
                page.update()
                return
            
            try:
                user = db.query(User).filter(User.email == temp_email["value"]).first()
                if user:
                    user.password_hash = hash_password(new_pass.value)
                    db.commit()
                    
                    record_successful_login(db, temp_email["value"])
                    
                    step2_message.value = "✅ Password reset successful!"
                    step2_message.color = "green"
                    page.update()
                    
                    close_dialog()
                    page.snack_bar = ft.SnackBar(
                        ft.Text("✅ Password reset successful! Please log in."),
                        bgcolor=ft.Colors.GREEN
                    )
                    page.snack_bar.open = True
                    page.update()
                else:
                    step2_message.value = "❌ User not found"
                    step2_message.color = "red"
                    page.update()
            except Exception as ex:
                print(f"Reset password error: {ex}")
                step2_message.value = "❌ Error resetting password"
                step2_message.color = "red"
                page.update()
        
        def show_step_1():
            step1_container.content = ft.Column([
                ft.Text("🔐 Forgot Password", size=20, weight="bold"),
                ft.Text("Enter your email to receive a reset code", size=12, color=DARK_GRAY),
                ft.Container(height=10),
                email_input,
                ft.Container(height=10),
                send_code_btn,
                step1_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            
            step2_container.visible = False
            step3_container.visible = False
            step1_container.visible = True
            page.update()
        
        def show_step_2():
            step2_container.content = ft.Column([
                ft.Text("📧 Check Your Email", size=20, weight="bold"),
                ft.Text(f"Code sent to {temp_email['value']}", size=12, color=DARK_GRAY),
                ft.Container(height=10),
                code_input,
                ft.Container(height=10),
                verify_code_btn,
                ft.TextButton("Resend Code", on_click=resend_reset_code),
                step2_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            
            step1_container.visible = False
            step3_container.visible = False
            step2_container.visible = True
            page.update()
        
        def show_step_3():
            step3_container.content = ft.Column([
                ft.Text("✅ Code Verified", size=20, weight="bold"),
                ft.Text("Enter your new password", size=12, color=DARK_GRAY),
                ft.Container(height=10),
                new_pass,
                ft.Container(height=10),
                confirm_pass,
                ft.Container(height=10),
                reset_password_btn,
                step2_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            
            step1_container.visible = False
            step2_container.visible = False
            step3_container.visible = True
            page.update()
        
        send_code_btn = ft.Container(
            content=ft.Text("Send Reset Code", size=14, weight="bold", color=WHITE),
            width=280,
            height=45,
            bgcolor=ORANGE,
            border_radius=25,
            alignment=ft.alignment.center,
            on_click=send_reset_code,
            ink=True
        )
        
        verify_code_btn = ft.Container(
            content=ft.Text("Verify Code", size=14, weight="bold", color=WHITE),
            width=280,
            height=45,
            bgcolor=ORANGE,
            border_radius=25,
            alignment=ft.alignment.center,
            on_click=verify_code_step,
            ink=True
        )
        
        reset_password_btn = ft.Container(
            content=ft.Text("Reset Password", size=14, weight="bold", color=WHITE),
            width=280,
            height=45,
            bgcolor=ORANGE,
            border_radius=25,
            alignment=ft.alignment.center,
            on_click=reset_password_final,
            ink=True
        )
        
        dlg = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                content=ft.Column([
                    step1_container,
                    step2_container,
                    step3_container
                ], width=350),
                padding=10
            ),
            actions=[ft.TextButton("Cancel", on_click=lambda ev: close_dialog())]
        )
        
        show_step_1()
        open_dialog(dlg)

    def open_dialog(dlg: ft.AlertDialog):
        try:
            if dlg not in page.overlay:
                page.overlay.append(dlg)
            page.dialog = dlg
            page.update()
            dlg.open = True
            page.update()
        except Exception as ex:
            print("open_dialog error:", ex)

    def close_dialog(e=None):
        try:
            for item in list(page.overlay):
                try:
                    if hasattr(item, "open"):
                        item.open = False
                except Exception:
                    pass
                if type(item).__name__ in ("AlertDialog", "FilePicker"):
                    try:
                        page.overlay.remove(item)
                    except Exception:
                        pass
            if hasattr(page, "dialog") and page.dialog:
                try:
                    page.dialog.open = False
                except Exception:
                    pass
                page.dialog = None
            page.update()
        except Exception as ex:
            print("close_dialog error:", ex)

    # ===== UI COMPONENTS (NEW DESIGN) =====
    
    # Brand Logo (BIGGER - 250x100)
    brand_logo = ft.Image(
        src="assets/Brand.png",
        width=300,
        height=50,
        fit=ft.ImageFit.CONTAIN
    )

    # Welcome Text
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

    # Sign In Button
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

    # Forgot Password Link
    forgot_pass_btn = ft.Container(
        content=ft.Text("Forgot Password?", size=12, color=ORANGE, weight="bold"),
        on_click=forgot_password_dialog,
        ink=True
    )

    # OR Divider
    divider_row = ft.Row([
        ft.Container(expand=True, height=1, bgcolor="#E0E0E0"),
        ft.Text("OR", size=12, color=DARK_GRAY, weight="bold"),
        ft.Container(expand=True, height=1, bgcolor="#E0E0E0"),
    ], spacing=10, width=MOBILE_WIDTH)

    # Google Button
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

    # Sign Up Link
    signup_row = ft.Row([
        ft.Text("Don't have an account?", size=13, color=DARK_GRAY),
        ft.Container(
            content=ft.Text("Sign Up", size=13, color=ORANGE, weight="bold"),
            on_click=lambda e: page.go("/signup"),
            ink=True
        )
    ], spacing=5, alignment=ft.MainAxisAlignment.CENTER)

    # ===== MAIN LOGIN FORM (REDUCED SPACING) =====
    def show_login_form():
        """Show the login form"""
        if not check_global_lockout():
            if email.value and email.value.strip():
                check_lockout_status()
        
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
                    lockout_container,
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
                height=700,
                padding=ft.padding.symmetric(horizontal=25),
                bgcolor=WHITE
            )
        )
        page.update()

    show_login_form()