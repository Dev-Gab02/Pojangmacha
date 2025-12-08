import flet as ft
import re
from core.db import SessionLocal
from core.auth_service import create_user_from_google
from core.session_manager import start_session
from core.google_auth import get_google_user_info
from core.email_service import generate_verification_code, send_verification_email, store_verification_code
from core.two_fa_ui_service import show_signup_verification_dialog
import threading

# ===== BRAND COLORS (SAME AS LOGIN) =====
ORANGE = "#FF6B35"
LIGHT_GRAY = "#D9D9D9"
DARK_GRAY = "#cdbcbc"
WHITE = "#FFFFFF"
BUTTON_COLOR = "#FEB23F"

def signup_view(page: ft.Page):
    page.title = "Sign Up - Pojangmacha"
    db = SessionLocal()
    MOBILE_WIDTH = 350

    # ===== INPUT FIELDS (MATCHING LOGIN DESIGN) =====
    full_name = ft.TextField(
        label="Full Name",
        label_style=ft.TextStyle(color="#000000"),
        hint_text="Enter your Full Name",
        hint_style=ft.TextStyle(color="#000000"),
        color="#000000",
        width=MOBILE_WIDTH,
        border_radius=12,
        filled=True,
        bgcolor=LIGHT_GRAY,
        border_color="transparent",
        focused_border_color=ORANGE,
        prefix_icon=ft.Icons.PERSON_OUTLINE,
        text_size=14,
        height=55
    )
    
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
    
    phone = ft.TextField(
        label="Phone Number",
        label_style=ft.TextStyle(color="#000000"),
        hint_text="Enter your Phone Number",
        hint_style=ft.TextStyle(color="#000000"),
        color="#000000",
        width=MOBILE_WIDTH,
        border_radius=12,
        filled=True,
        bgcolor=LIGHT_GRAY,
        border_color="transparent",
        focused_border_color=ORANGE,
        prefix_icon=ft.Icons.PHONE_OUTLINED,
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
    
    confirm_password = ft.TextField(
        label="Confirm Password",
        label_style=ft.TextStyle(color="#000000"),
        hint_text="Confirm your Password",
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
    
    # Store user data temporarily
    temp_user_data = {}

    def is_valid_email(email_str: str) -> bool:
        """Check if email format is valid"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email_str) is not None

    # ===== SEND VERIFICATION CODE =====
    def send_verification(e):
        """Validate form and send verification code"""
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
        
        if len(password.value) < 6:
            message.value = "Password must be at least 6 characters!"
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
        message.value = "Sending verification code..."
        message.color = "blue"
        signup_btn.disabled = True
        page.update()

        # Send email in background thread
        def send_email_thread():
            code = generate_verification_code()
            success = send_verification_email(email.value, code)
            
            if success:
                store_verification_code(email.value, code)
                
                def on_cancel():
                    message.value = ""
                    signup_btn.disabled = False
                    page.update()
                
                def on_success():
                    page.go("/login")
                
                show_signup_verification_dialog(page, db, temp_user_data, on_success, on_cancel)
            else:
                message.value = "Failed to send verification email"
                message.color = "red"
                signup_btn.disabled = False
                page.update()
        
        thread = threading.Thread(target=send_email_thread, daemon=True)
        thread.start()

    # ===== GOOGLE SIGNUP =====
    def handle_google_signup(e):
        """Handle Google sign-up with real OAuth"""
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
                page.go("/home")
                
            except Exception as ex:
                print(f"Google OAuth error: {ex}")
                message.value = f"Error: {str(ex)}"
                message.color = "red"
                google_btn.disabled = False
                page.update()
        
        thread = threading.Thread(target=google_auth_thread, daemon=True)
        thread.start()

    # ===== UI COMPONENTS (MATCHING LOGIN DESIGN) =====
    
    # Brand Logo (300×50 - same as login)
    brand_logo = ft.Image(
        src="assets/Brand.png",
        width=300,
        height=50,
        fit=ft.ImageFit.CONTAIN
    )

    # Welcome Text
    welcome_text = ft.Text(
        "Welcome to",
        size=22,
        weight="bold",
        color="#000000"
    )
    
    subtitle_text = ft.Text(
        "Create your Account",
        size=12,
        color=DARK_GRAY
    )

    # Sign Up Button
    signup_btn = ft.Container(
        content=ft.Text("Create Account", size=16, weight="bold", color=WHITE),
        width=MOBILE_WIDTH,
        height=50,
        bgcolor=BUTTON_COLOR,
        border_radius=12,
        alignment=ft.alignment.center,
        on_click=send_verification,
        ink=True,
        animate=ft.Animation(200, "easeOut")
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
        on_click=handle_google_signup,
        ink=True,
        animate=ft.Animation(200, "easeOut")
    )

    # Sign In Link
    signin_row = ft.Row([
        ft.Text("Already have an account?", size=13, color=DARK_GRAY),
        ft.Container(
            content=ft.Text("Sign In", size=13, color=ORANGE, weight="bold"),
            on_click=lambda e: page.go("/login"),
            ink=True
        )
    ], spacing=5, alignment=ft.MainAxisAlignment.CENTER)

    # ===== MAIN SIGNUP FORM =====
    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Container(height=8),
                welcome_text,
                ft.Container(height=8),
                brand_logo,
                subtitle_text,
                ft.Container(height=20),
                full_name,
                ft.Container(height=8),
                email,
                ft.Container(height=8),
                phone,
                ft.Container(height=8),
                password,
                ft.Container(height=8),
                confirm_password,
                ft.Container(height=8),
                signup_btn,
                ft.Container(height=2),
                message,
                ft.Container(height=10),
                divider_row,
                ft.Container(height=15),
                google_btn,
                ft.Container(height=8),
                signin_row
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            spacing=0),
            width=400,
            expand=True,
            padding=ft.padding.symmetric(horizontal=25),
            bgcolor=WHITE,
            alignment=ft.alignment.center
        )
    )
    page.update()