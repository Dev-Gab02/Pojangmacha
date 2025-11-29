import os
import threading
import time
from dotenv import load_dotenv
import flet as ft

# Load environment variables
load_dotenv()

# Import all models FIRST to ensure SQLAlchemy relationships are registered
from models.user import User
from models.food_item import FoodItem
from models.order import Order, OrderItem
from models.cart import Cart
from models.audit_log import AuditLog
from models.login_attempt import LoginAttempt

# Import core services
from core.session_manager import start_session, end_session, is_session_active, refresh_session

# Import views
from ui.splash_view import splash_view
from ui.login_view import login_view
from ui.signup_view import signup_view
from ui.home_view import home_view
from ui.admin_view import admin_view
from ui.analytics_view import analytics_view
from ui.order_history_view import order_history_widget as order_history_view
from ui.profile_view import profile_view_widget as profile_view
from ui.reset_password_view import reset_password_view

SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "180"))
SESSION_CHECK_INTERVAL = int(os.getenv("SESSION_CHECK_INTERVAL", "10"))
WARNING_TIME = int(os.getenv("SESSION_WARNING_TIME", "60"))

def main(page: ft.Page):
    page.window.width = 400
    page.window.height = 700
    page.window.resizable = False
    page.padding = 0
    page.spacing = 0
    
    page.title = "Pojangmacha"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    if not page.session.contains_key("user"):
        page.session.set("user", None)

    splash_shown = {"value": False}
    monitor_active = {"value": False}
    warning_dialog_shown = {"value": False}
    last_activity_logged = {"time": time.time()}

    def current_email():
        u = page.session.get("user")
        return u.get("email") if u else None

    def close_warning_dialog():
        try:
            if hasattr(page, "dialog") and page.dialog:
                page.dialog.open = False
                page.dialog = None
            warning_dialog_shown["value"] = False
            page.update()
        except Exception as ex:
            print(f"Warning dialog close error: {ex}")

    def on_user_activity(e=None):
        current_time = time.time()
        if current_time - last_activity_logged["time"] > 1.0:
            print(f"👆 User activity detected!")
            last_activity_logged["time"] = current_time
        
        try:
            if warning_dialog_shown["value"]:
                print("✅ Closing warning due to user activity")
                close_warning_dialog()
        except Exception:
            pass
            
        email = current_email()
        if email:
            try:
                result = refresh_session(email)
                if not result:
                    print(f"⚠️ Failed to refresh session for {email}")
            except Exception as ex:
                print(f"❌ refresh_session error: {ex}")

    try:
        if hasattr(page, "on_keyboard_event"):
            old_keyboard_handler = page.on_keyboard_event
            page.on_keyboard_event = lambda ev: (on_user_activity(ev), old_keyboard_handler(ev) if old_keyboard_handler else None)
            print("✅ Keyboard activity handler attached")
    except Exception as ex:
        print(f"⚠️ Keyboard handler error: {ex}")

    try:
        if hasattr(page, "on_pointer_move"):
            old_pointer_move = page.on_pointer_move
            page.on_pointer_move = lambda ev: (on_user_activity(ev), old_pointer_move(ev) if old_pointer_move else None)
            print("✅ Pointer move handler attached")
    except Exception as ex:
        print(f"⚠️ Pointer move handler error: {ex}")

    try:
        if hasattr(page, "on_pointer_down"):
            old_pointer_down = page.on_pointer_down
            page.on_pointer_down = lambda ev: (on_user_activity(ev), old_pointer_down(ev) if old_pointer_down else None)
            print("✅ Pointer click handler attached")
    except Exception as ex:
        print(f"⚠️ Pointer click handler error: {ex}")

    original_update = page.update
    
    def activity_aware_update(*args, **kwargs):
        email = current_email()
        if email and page.route not in ["/login", "/signup", "/"]:
            on_user_activity()
        return original_update(*args, **kwargs)
    
    page.update = activity_aware_update
    print("✅ Page update interceptor installed")

    def show_warning_dialog(remaining_seconds):
        if warning_dialog_shown["value"]:
            return
        
        print(f"⚠️ Showing warning dialog with {remaining_seconds}s remaining")
        warning_dialog_shown["value"] = True
        
        countdown_text = ft.Text(
            f"{int(remaining_seconds)}s",
            size=40,
            weight="bold",
            color="orange"
        )
        
        def stay_logged_in(e):
            email = current_email()
            if email:
                refresh_session(email)
                print("✅ User chose to stay logged in - session refreshed")
            close_warning_dialog()
        
        def logout_now(e):
            force_logout()
        
        warning_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Text("Session Expiring", size=20, weight="bold")
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        "You've been inactive. Your session will expire soon.",
                        size=14,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=20),
                    countdown_text,
                    ft.Container(height=10),
                    ft.Text(
                        "Move your mouse or click to stay logged in",
                        size=12,
                        color="grey",
                        text_align=ft.TextAlign.CENTER,
                        italic=True
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=300,
                padding=20
            ),
            actions=[
                ft.TextButton(
                    "Logout Now",
                    on_click=logout_now
                ),
                ft.ElevatedButton(
                    "Stay Logged In",
                    on_click=stay_logged_in,
                    style=ft.ButtonStyle(
                        bgcolor="green",
                        color="white"
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        try:
            page.dialog = warning_dlg
            warning_dlg.open = True
            original_update()
            print("✅ Warning dialog displayed")
        except Exception as ex:
            print(f"❌ Error showing warning dialog: {ex}")
            warning_dialog_shown["value"] = False
            return
        
        def update_countdown():
            email = current_email()
            
            while warning_dialog_shown["value"] and email:
                try:
                    active, remaining = is_session_active(email, return_remaining=True)
                    
                    if not active or remaining <= 0:
                        print("⏱️ Countdown ended - session expired")
                        break
                    
                    countdown_text.value = f"{int(remaining)}s"
                    original_update()
                    
                except Exception as ex:
                    print(f"Countdown update error: {ex}")
                    break
                
                time.sleep(1)
            
            print("🛑 Countdown thread ended")
        
        countdown_thread = threading.Thread(target=update_countdown, daemon=True)
        countdown_thread.start()

    def force_logout():
        print("🔴 FORCE LOGOUT INITIATED")
        
        email = current_email()
        if email:
            try:
                end_session(email)
                print(f"🔴 Session ended for {email}")
            except Exception as ex:
                print(f"End session error: {ex}")
        
        monitor_active["value"] = False
        print("🛑 Monitor deactivated")
        
        close_warning_dialog()
        
        page.session.set("user", None)
        print("🧹 User session cleared")
        
        page.go("/login")
        print("🔄 Redirected to login")

    def stop_session_monitor():
        monitor_active["value"] = False
        close_warning_dialog()
        print("🛑 Session monitor stopped")

    def start_session_monitor():
        if monitor_active["value"]:
            stop_session_monitor()
            time.sleep(0.5)
        
        warning_dialog_shown["value"] = False
        monitor_active["value"] = True
        
        def session_monitor():
            print("🚀 Session monitor started")
            
            while monitor_active["value"]:
                email = current_email()
                
                if not email:
                    print("⏸️ No user logged in - monitor sleeping")
                    time.sleep(SESSION_CHECK_INTERVAL)
                    continue
                
                try:
                    res = is_session_active(email, return_remaining=True)
                    if isinstance(res, tuple):
                        active, remaining = res
                    else:
                        active = bool(res)
                        remaining = SESSION_TIMEOUT
                    
                    print(f"🔍 Session check: active={active}, remaining={remaining:.0f}s")
                    
                    if not active or remaining <= 0:
                        print("❌ Session expired - logging out")
                        monitor_active["value"] = False
                        
                        try:
                            end_session(email)
                        except Exception as ex:
                            print(f"End session error: {ex}")
                        
                        force_logout()
                        return
                    
                    if remaining <= WARNING_TIME and remaining > 0:
                        if not warning_dialog_shown["value"]:
                            print(f"⚠️ Showing warning - {remaining:.0f}s remaining")
                            show_warning_dialog(remaining)
                
                except Exception as ex:
                    print(f"Session monitor error: {ex}")
                    import traceback
                    traceback.print_exc()
                
                time.sleep(SESSION_CHECK_INTERVAL)
            
            print("🛑 Session monitor ended")
        
        thread = threading.Thread(target=session_monitor, daemon=True)
        thread.start()
        print("✅ New session monitor thread started")

    def route_change(e):
        if not splash_shown["value"]:
            splash_shown["value"] = True
            
            def on_splash_complete():
                print("✅ Splash screen completed")
                page.go("/login")
            
            splash_view(page, on_splash_complete)
            return
        
        page.clean()
        current_user = page.session.get("user")

        if page.route not in ["/login", "/signup", "/logout", "/", "/reset_password"]:
            if not current_user:
                page.snack_bar = ft.SnackBar(ft.Text("Please log in to continue."), open=True)
                original_update()
                page.go("/login")
                return
            
            email = current_user.get("email")
            if email:
                try:
                    if not is_session_active(email):
                        start_session(email)
                        print(f"✅ Session created for {email}")
                    else:
                        refresh_session(email)
                        print(f"🔄 Session refreshed on route change for {email}")
                    
                    if not monitor_active["value"]:
                        start_session_monitor()
                
                except Exception as ex:
                    print(f"Session initialization error: {ex}")

        if page.route == "/logout":
            cur = page.session.get("user")
            if cur and cur.get("email"):
                try:
                    end_session(cur["email"])
                except Exception:
                    pass
            
            stop_session_monitor()
            
            page.session.set("user", None)
            page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
            original_update()
            page.go("/login")
            return

        if page.route == "/login" or page.route == "/":
            stop_session_monitor()
            login_view(page)
        elif page.route == "/signup":
            stop_session_monitor()
            signup_view(page)
        elif page.route == "/home":
            home_view(page)
        elif page.route == "/admin":
            admin_view(page)
        elif page.route == "/analytics":
            analytics_view(page)
        elif page.route == "/orders":
            order_history_view(page)
        elif page.route == "/profile":
            profile_view(page)
        elif page.route == "/reset_password":
            stop_session_monitor()
            reset_password_view(page)
        else:
            stop_session_monitor()
            page.go("/login")

    page.on_route_change = route_change
    page.go("/")

if __name__ == "__main__":
    ft.app(target=main)