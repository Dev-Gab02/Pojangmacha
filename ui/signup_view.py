import flet as ft
import re
from core.db import SessionLocal
from core.auth_service import create_user, create_user_from_google
from core.session_manager import start_session
from core.google_auth import get_google_user_info
from core.email_service import generate_verification_code, send_verification_email, store_verification_code, verify_code, resend_verification_code
import threading

def signup_view(page: ft.Page):
    page.title = "Sign Up - Pojangmacha"
    db = SessionLocal()

    # Step 1: Registration form
    full_name = ft.TextField(label="Full Name", width=300)
    email = ft.TextField(label="Email", width=300)
    phone = ft.TextField(label="Phone Number", width=300)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)
    confirm_password = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, width=300)
    message = ft.Text(value="", color="red")

    # Step 2: Email verification
    verification_code_input = ft.TextField(
        label="Enter 6-digit code",
        width=300,
        max_length=6,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER
    )
    verification_message = ft.Text(value="", color="red")
    
    # Store user data temporarily
    temp_user_data = {}

    def is_valid_email(email_str: str) -> bool:
        """Check if email format is valid"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email_str) is not None

    def send_verification(e):
        """Send verification code to email"""
        if not all([full_name.value, email.value, phone.value, password.value, confirm_password.value]):
            message.value = "All fields are required!"
            message.color = "red"
            page.update()
            return
        
        if not is_valid_email(email.value):
            message.value = "Please enter a valid email address!"
            message.color = "red"
            page.update()
            return
        
        if password.value != confirm_password.value:
            message.value = "Passwords do not match!"
            message.color = "red"
            page.update()
            return
        
        # Check if email already exists
        from models.user import User
        existing_user = db.query(User).filter(User.email == email.value).first()
        if existing_user:
            message.value = "Email already exists."
            message.color = "red"
            page.update()
            return

        # Store user data temporarily
        temp_user_data["full_name"] = full_name.value
        temp_user_data["email"] = email.value
        temp_user_data["phone"] = phone.value
        temp_user_data["password"] = password.value

        # Generate and send verification code
        message.value = "📧 Sending verification code..."
        message.color = "blue"
        signup_btn.disabled = True
        page.update()

        # Send email in background thread
        def send_email_thread():
            code = generate_verification_code()
            success = send_verification_email(email.value, code)
            
            if success:
                store_verification_code(email.value, code)
                
                # Show verification step
                def show_verification_ui():
                    message.value = ""
                    show_verification_step()
                page.update()
                show_verification_ui()
            else:
                message.value = "❌ Failed to send verification email. Please check your email and try again."
                message.color = "red"
                signup_btn.disabled = False
                page.update()
        
        thread = threading.Thread(target=send_email_thread, daemon=True)
        thread.start()

    def show_verification_step():
        """Show email verification UI"""
        verification_message.value = f"✅ Verification code sent to {temp_user_data['email']}"
        verification_message.color = "green"
        
        verify_btn = ft.ElevatedButton(
            "Verify & Create Account",
            on_click=verify_and_create_account,
            width=300
        )
        
        resend_btn = ft.TextButton(
            "Resend Code",
            on_click=resend_code
        )
        
        back_btn = ft.TextButton(
            "← Back to Form",
            on_click=lambda e: show_signup_form()
        )

        page.clean()
        page.add(
            ft.Column([
                ft.Text("Verify Your Email", size=24, weight="bold"),
                ft.Text("We've sent a 6-digit code to your email", size=14, color="grey"),
                verification_code_input,
                verify_btn,
                resend_btn,
                verification_message,
                back_btn
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER)
        )

    def verify_and_create_account(e):
        """Verify code and create user account"""
        if not verification_code_input.value or len(verification_code_input.value) != 6:
            verification_message.value = "Please enter the 6-digit code"
            verification_message.color = "red"
            page.update()
            return

        if verify_code(temp_user_data["email"], verification_code_input.value):
            # Code is valid - create account
            new_user = create_user(
                db,
                temp_user_data["full_name"],
                temp_user_data["email"],
                temp_user_data["phone"],
                temp_user_data["password"]
            )
            
            if new_user:
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Account created successfully! Please log in."),
                    open=True,
                    bgcolor=ft.Colors.GREEN
                )
                page.update()
                page.go("/login")
            else:
                verification_message.value = "❌ Error creating account. Please try again."
                verification_message.color = "red"
                page.update()
        else:
            verification_message.value = "❌ Invalid or expired code. Please try again."
            verification_message.color = "red"
            page.update()

    def resend_code(e):
        """Resend verification code"""
        verification_message.value = "📧 Resending code..."
        verification_message.color = "blue"
        page.update()

        def resend_thread():
            if resend_verification_code(temp_user_data["email"]):
                verification_message.value = "✅ New code sent to your email"
                verification_message.color = "green"
            else:
                verification_message.value = "❌ Failed to send code. Please try again."
                verification_message.color = "red"
            page.update()
        
        thread = threading.Thread(target=resend_thread, daemon=True)
        thread.start()

    def show_signup_form():
        """Show the signup form"""
        page.clean()
        page.add(
            ft.Column([
                ft.Text("Create Your Account", size=24, weight="bold"),
                full_name,
                email,
                phone,
                password,
                confirm_password,
                signup_btn,
                divider_row,
                google_btn,
                message,
                ft.TextButton("Already have an account? Sign In", on_click=lambda e: page.go("/login"))
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER)
        )

    def handle_google_signup(e):
        """Handle Google sign-up with real OAuth"""
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
                
                message.value = f"✅ Welcome, {user.full_name}!"
                message.color = "green"
                page.update()
                page.go("/home")
                
            except Exception as ex:
                print(f"Google OAuth error: {ex}")
                message.value = f"❌ Error: {str(ex)}"
                message.color = "red"
                google_btn.disabled = False
                page.update()
        
        thread = threading.Thread(target=google_auth_thread, daemon=True)
        thread.start()

    signup_btn = ft.ElevatedButton("Send Verification Code", on_click=send_verification, width=300)
    
    google_btn = ft.OutlinedButton(
        content=ft.Row([
            ft.Image(
                src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg",
                width=20,
                height=20
            ),
            ft.Text("Sign up with Google", size=14)
        ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
        width=300,
        height=45,
        on_click=handle_google_signup,
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, "grey400"),
            shape=ft.RoundedRectangleBorder(radius=5)
        )
    )

    divider_row = ft.Row([
        ft.Container(expand=True, height=1, bgcolor="grey400"),
        ft.Text("OR", size=12, color="grey"),
        ft.Container(expand=True, height=1, bgcolor="grey400"),
    ], spacing=10, width=300)

    show_signup_form()