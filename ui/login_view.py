import flet as ft
from core.db import SessionLocal
from core.session_manager import start_session
from core.auth_service import authenticate_user, create_user_from_google, hash_password
from core.google_auth import get_google_user_info
from core.two_fa_service import send_2fa_code, verify_2fa_code, verify_backup_code
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

def login_view(page: ft.Page):
    page.title = "Login - Pojangmacha"
    db = SessionLocal()
    MOBILE_WIDTH = 350

    email = ft.TextField(label="Email", width=MOBILE_WIDTH)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=MOBILE_WIDTH)
    message = ft.Text(value="", color="red")
    
    # Lockout UI elements
    lockout_message = ft.Text(value="", color="red", size=16, weight="bold")
    countdown_text = ft.Text(value="", color="orange", size=14)
    lockout_info = ft.Text(value="", color="grey", size=12, italic=True)
    lockout_container = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.LOCK, size=60, color="red"),
            lockout_message,
            countdown_text,
            lockout_info
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        visible=False,
        padding=20,
        border=ft.border.all(2, "red"),
        border_radius=10,
        bgcolor="red50"
    )
    
    # 2FA verification fields
    two_fa_code_input = ft.TextField(
        label="Enter 6-digit 2FA code",
        width=300,
        max_length=6,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER
    )
    backup_code_input = ft.TextField(
        label="Or enter backup code (XXXX-XXXX)",
        width=300,
        max_length=9,
        text_align=ft.TextAlign.CENTER
    )
    two_fa_message = ft.Text(value="", color="red")
    
    # Store temp user data
    temp_user = None
    
    # Countdown thread control
    countdown_active = {"value": False}
    
    # Sign up button reference
    signup_btn = ft.TextButton("Don't have an account? Sign Up", on_click=lambda e: page.go("/signup"))

    def start_lockout_countdown(locked_until, locked_email=None):
        """Start live countdown timer"""
        countdown_active["value"] = True
        
        def countdown_thread():
            while countdown_active["value"]:
                from datetime import datetime
                
                # Check if still locked
                remaining_seconds = int((locked_until - datetime.utcnow()).total_seconds())
                
                if remaining_seconds <= 0:
                    # Lockout expired
                    lockout_container.visible = False
                    login_btn.disabled = False
                    forgot_pass_btn.disabled = False
                    google_btn.disabled = False
                    signup_btn.disabled = False  # RE-ENABLE SIGN UP
                    email.disabled = False
                    password.disabled = False
                    countdown_active["value"] = False
                    
                    message.value = "✅ Account unlocked. You can login now."
                    message.color = "green"
                    page.update()
                    break
                
                # Update countdown display
                countdown_text.value = f"⏱️ Time remaining: {format_lockout_time(remaining_seconds)}"
                if locked_email:
                    lockout_info.value = f"Account: {locked_email}"
                page.update()
                
                time.sleep(1)
        
        thread = threading.Thread(target=countdown_thread, daemon=True)
        thread.start()

    def check_lockout_status():
        """Check if account is locked before allowing any action"""
        if not email.value or not email.value.strip():
            return False
        
        locked, locked_until, remaining = is_account_locked(db, email.value.strip())
        
        if locked:
            # Account is locked
            lockout_message.value = "🔒 Account Temporarily Locked"
            lockout_info.value = f"Account: {email.value.strip()}"
            lockout_container.visible = True
            
            login_btn.disabled = True
            forgot_pass_btn.disabled = True
            google_btn.disabled = True
            signup_btn.disabled = True  # DISABLE SIGN UP
            email.disabled = True
            password.disabled = True
            
            # Start countdown
            start_lockout_countdown(locked_until, email.value.strip())
            
            page.update()
            return True
        
        return False

    def check_global_lockout():
        """Check if ANY account is locked on page load (NEW)"""
        has_lockout, locked_email, locked_until, remaining = check_any_active_lockout(db)
        
        if has_lockout:
            # Show lockout UI
            lockout_message.value = "🔒 System Temporarily Locked"
            lockout_info.value = f"Due to security, please wait for the countdown to finish."
            lockout_container.visible = True
            
            login_btn.disabled = True
            forgot_pass_btn.disabled = True
            google_btn.disabled = True
            signup_btn.disabled = True  # DISABLE SIGN UP
            email.disabled = True
            password.disabled = True
            
            # If we have the locked email, populate it
            if locked_email:
                email.value = locked_email
                lockout_info.value = f"Account: {locked_email}"
            
            # Start countdown
            start_lockout_countdown(locked_until, locked_email)
            
            page.update()
            return True
        
        return False

    def handle_login(e):
        nonlocal temp_user
        
        # Check lockout status first
        if check_lockout_status():
            return
        
        if not email.value or not password.value:
            message.value = "Please enter email and password"
            message.color = "red"
            page.update()
            return
        
        try:
            user, status = authenticate_user(db, email.value, password.value)
            
            if not user:
                # Failed login - record attempt
                failed_count, locked_until = record_failed_attempt(db, email.value.strip())
                
                if locked_until:
                    # Account just got locked
                    lockout_message.value = "🔒 Too Many Failed Attempts!"
                    lockout_info.value = f"Account: {email.value.strip()}"
                    message.value = f"❌ Account locked for 15 minutes after {failed_count} failed attempts"
                    message.color = "red"
                    lockout_container.visible = True
                    
                    login_btn.disabled = True
                    forgot_pass_btn.disabled = True
                    google_btn.disabled = True
                    signup_btn.disabled = True  # DISABLE SIGN UP
                    email.disabled = True
                    password.disabled = True
                    
                    # Start countdown
                    start_lockout_countdown(locked_until, email.value.strip())
                else:
                    # Show remaining attempts
                    remaining = get_remaining_attempts(db, email.value.strip())
                    message.value = f"❌ Invalid credentials. {remaining} attempt(s) remaining."
                    message.color = "red"
                
                page.update()
                return

            # Successful authentication - reset attempts
            record_successful_login(db, email.value.strip())
            
            # Check if 2FA is enabled
            if user.two_fa_enabled:
                temp_user = user
                
                # Send 2FA code
                message.value = "📧 Sending 2FA code..."
                message.color = "blue"
                login_btn.disabled = True
                page.update()
                
                def send_2fa_thread():
                    if send_2fa_code(user.email):
                        show_2fa_verification()
                    else:
                        message.value = "❌ Failed to send 2FA code"
                        message.color = "red"
                        login_btn.disabled = False
                        page.update()
                
                thread = threading.Thread(target=send_2fa_thread, daemon=True)
                thread.start()
                return

            # No 2FA - proceed to login
            complete_login(user)

        except Exception as ex:
            print("Login error:", ex)
            message.value = "An error occurred during login."
            message.color = "red"
            page.update()

    def show_2fa_verification():
        """Show 2FA code input screen"""
        two_fa_message.value = f"✅ Code sent to {temp_user.email}"
        two_fa_message.color = "green"
        
        verify_btn = ft.ElevatedButton(
            "Verify & Sign In",
            on_click=verify_2fa,
            width=300
        )
        
        resend_btn = ft.TextButton(
            "Resend Code",
            on_click=resend_2fa_code
        )
        
        back_btn = ft.TextButton(
            "← Back to Login",
            on_click=lambda e: show_login_form()
        )

        page.clean()
        page.add(
            ft.Column([
                ft.Text("🔐 Two-Factor Authentication", size=24, weight="bold"),
                ft.Text("Enter the code sent to your email", size=14, color="grey"),
                two_fa_code_input,
                ft.Text("OR", size=12, color="grey"),
                backup_code_input,
                verify_btn,
                resend_btn,
                two_fa_message,
                back_btn
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER)
        )

    def verify_2fa(e):
        """Verify 2FA code or backup code"""
        code = two_fa_code_input.value
        backup = backup_code_input.value
        
        if not code and not backup:
            two_fa_message.value = "Please enter a code"
            two_fa_message.color = "red"
            page.update()
            return

        # Try 2FA code first
        if code and verify_2fa_code(temp_user.email, code):
            complete_login(temp_user)
            return
        
        # Try backup code
        if backup:
            from models.user import User
            user = db.query(User).filter(User.id == temp_user.id).first()
            if verify_backup_code(user, backup):
                db.commit()
                two_fa_message.value = "⚠️ Backup code used. Generate new codes in your profile."
                two_fa_message.color = "orange"
                page.update()
                complete_login(temp_user)
                return
        
        two_fa_message.value = "❌ Invalid code. Please try again."
        two_fa_message.color = "red"
        page.update()

    def resend_2fa_code(e):
        """Resend 2FA code"""
        two_fa_message.value = "📧 Resending code..."
        two_fa_message.color = "blue"
        page.update()

        def resend_thread():
            if send_2fa_code(temp_user.email):
                two_fa_message.value = "✅ New code sent"
                two_fa_message.color = "green"
            else:
                two_fa_message.value = "❌ Failed to send code"
                two_fa_message.color = "red"
            page.update()
        
        thread = threading.Thread(target=resend_thread, daemon=True)
        thread.start()

    def complete_login(user):
        """Complete login after authentication"""
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

    def show_login_form():
        """Show the login form"""
        # Check for global lockout on load (NEW)
        if not check_global_lockout():
            # No global lockout - check specific email lockout if entered
            if email.value and email.value.strip():
                check_lockout_status()
        
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Container(height=40),  # Top spacing
                    ft.Text("Welcome Back", size=24, weight="bold"),
                    ft.Container(height=10),
                    lockout_container,
                    email, 
                    password,
                    login_btn,
                    forgot_pass_btn,
                    divider_row,
                    google_btn,
                    message,
                    signup_btn
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO),  # Enable scrolling
                width=400,
                height=700,
                padding=ft.padding.symmetric(horizontal=25)
            )
        )

    def handle_google_login(e):
        """Handle Google sign-in with real OAuth"""
        # Check lockout (use generic email for Google login)
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
                
                # Reset any lockout on successful Google login
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
                name = type(item).__name__
                try:
                    if hasattr(item, "open"):
                        item.open = False
                except Exception:
                    pass
                if name in ("AlertDialog", "FilePicker"):
                    try:
                        page.overlay.remove(item)
                    except Exception:
                        pass
            try:
                if hasattr(page, "dialog") and page.dialog:
                    try:
                        page.dialog.open = False
                    except Exception:
                        pass
                    page.dialog = None
            except Exception:
                pass
            page.update()
        except Exception as ex:
            print("close_dialog error:", ex)

    def forgot_password_dialog(e):
        """Show forgot password flow with email verification"""
        # Check lockout before allowing password reset
        if email.value and email.value.strip():
            if check_lockout_status():
                message.value = "❌ Account is locked. Please wait for countdown to finish."
                message.color = "red"
                page.update()
                return
        
        from models.user import User
        
        # Step 1: Email input
        email_input = ft.TextField(label="Enter your email", width=300)
        step1_message = ft.Text("", color="red")
        
        # Step 2: Code verification
        code_input = ft.TextField(
            label="Enter 6-digit code",
            width=300,
            max_length=6,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Step 3: New password
        new_pass = ft.TextField(label="New password", password=True, can_reveal_password=True, width=300)
        confirm_pass = ft.TextField(label="Confirm password", password=True, can_reveal_password=True, width=300)
        
        step2_message = ft.Text("", color="red")
        
        # Step containers
        step1_container = ft.Container()
        step2_container = ft.Container()
        step3_container = ft.Container()
        
        current_step = {"value": 1}
        temp_email = {"value": ""}
        
        def send_reset_code(ev):
            """Send password reset code to email"""
            if not email_input.value or not email_input.value.strip():
                step1_message.value = "Please enter your email"
                step1_message.color = "red"
                page.update()
                return
            
            # Check if account is locked
            locked, locked_until, remaining = is_account_locked(db, email_input.value.strip())
            if locked:
                step1_message.value = f"❌ Account is locked. Wait {format_lockout_time(remaining)} before resetting password."
                step1_message.color = "red"
                page.update()
                return
            
            # Check if email exists
            user = db.query(User).filter(User.email == email_input.value.strip()).first()
            if not user:
                step1_message.value = "Email not found"
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
                    store_password_reset_code(temp_email["value"], code)
                    
                    # Move to step 2
                    current_step["value"] = 2
                    show_step_2()
                else:
                    step1_message.value = "❌ Failed to send email. Please try again."
                    step1_message.color = "red"
                    send_code_btn.disabled = False
                    page.update()
            
            thread = threading.Thread(target=send_email_thread, daemon=True)
            thread.start()
        
        def verify_code_step(ev):
            """Verify the reset code"""
            if not code_input.value or len(code_input.value) != 6:
                step2_message.value = "Please enter the 6-digit code"
                step2_message.color = "red"
                page.update()
                return
            
            if verify_password_reset_code(temp_email["value"], code_input.value):
                # Code valid - move to step 3
                current_step["value"] = 3
                show_step_3()
            else:
                step2_message.value = "❌ Invalid or expired code"
                step2_message.color = "red"
                page.update()
        
        def resend_reset_code(ev):
            """Resend password reset code"""
            step2_message.value = "📧 Resending code..."
            step2_message.color = "blue"
            page.update()
            
            def resend_thread():
                if resend_password_reset_code(temp_email["value"]):
                    step2_message.value = "✅ New code sent to your email"
                    step2_message.color = "green"
                else:
                    step2_message.value = "❌ Failed to send code"
                    step2_message.color = "red"
                page.update()
            
            thread = threading.Thread(target=resend_thread, daemon=True)
            thread.start()
        
        def reset_password_final(ev):
            """Set the new password"""
            if not all([new_pass.value, confirm_pass.value]):
                step2_message.value = "All fields required"
                step2_message.color = "red"
                page.update()
                return
            
            if new_pass.value != confirm_pass.value:
                step2_message.value = "Passwords do not match"
                step2_message.color = "red"
                page.update()
                return
            
            if len(new_pass.value) < 6:
                step2_message.value = "Password too short (min 6 characters)"
                step2_message.color = "red"
                page.update()
                return
            
            # Update password in database
            try:
                user = db.query(User).filter(User.email == temp_email["value"]).first()
                if user:
                    user.password_hash = hash_password(new_pass.value)
                    db.commit()
                    
                    # Clear any lockout on password reset
                    record_successful_login(db, temp_email["value"])
                    
                    step2_message.value = "✅ Password reset successful!"
                    step2_message.color = "green"
                    page.update()
                    
                    # Close dialog and show success
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
            """Show email input step"""
            step1_container.content = ft.Column([
                ft.Text("🔐 Forgot Password", size=20, weight="bold"),
                ft.Text("Enter your email to receive a reset code", size=12, color="grey"),
                email_input,
                send_code_btn,
                step1_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            
            step2_container.visible = False
            step3_container.visible = False
            step1_container.visible = True
            page.update()
        
        def show_step_2():
            """Show code verification step"""
            step2_container.content = ft.Column([
                ft.Text("📧 Check Your Email", size=20, weight="bold"),
                ft.Text(f"Code sent to {temp_email['value']}", size=12, color="grey"),
                code_input,
                verify_code_btn,
                ft.TextButton("Resend Code", on_click=resend_reset_code),
                step2_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            
            step1_container.visible = False
            step3_container.visible = False
            step2_container.visible = True
            page.update()
        
        def show_step_3():
            """Show new password step"""
            step3_container.content = ft.Column([
                ft.Text("✅ Code Verified", size=20, weight="bold"),
                ft.Text("Enter your new password", size=12, color="grey"),
                new_pass,
                confirm_pass,
                reset_password_btn,
                step2_message
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            
            step1_container.visible = False
            step2_container.visible = False
            step3_container.visible = True
            page.update()
        
        # Buttons
        send_code_btn = ft.ElevatedButton("Send Reset Code", on_click=send_reset_code, width=250)
        verify_code_btn = ft.ElevatedButton("Verify Code", on_click=verify_code_step, width=250)
        reset_password_btn = ft.ElevatedButton("Reset Password", on_click=reset_password_final, width=250)
        
        # Build dialog
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
        
        # Show step 1 initially
        show_step_1()
        open_dialog(dlg)

    login_btn = ft.ElevatedButton("Sign In", on_click=handle_login, width=MOBILE_WIDTH)
    forgot_pass_btn = ft.TextButton("Forgot Password?", on_click=forgot_password_dialog)
    
    google_btn = ft.OutlinedButton(
        content=ft.Row([
            ft.Image(
                src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg",
                width=20,
                height=20
            ),
            ft.Text("Continue with Google", size=14)
        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
        width=MOBILE_WIDTH,
        height=45,
        on_click=handle_google_login,
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, "grey400"),
            shape=ft.RoundedRectangleBorder(radius=5)
        )
    )

    divider_row = ft.Row([
        ft.Container(expand=True, height=1, bgcolor="grey400"),
        ft.Text("OR", size=12, color="grey"),
        ft.Container(expand=True, height=1, bgcolor="grey400"),
    ], spacing=10, width=MOBILE_WIDTH)

    show_login_form()