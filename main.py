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
from ui.login_view import login_view
from ui.signup_view import signup_view
from ui.home_view import home_view
from ui.admin_view import admin_view
from ui.order_history_view import order_history_view
from ui.profile_view import profile_view
from ui.reset_password_view import reset_password_view

SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "180"))  # 3 minutes
SESSION_CHECK_INTERVAL = int(os.getenv("SESSION_CHECK_INTERVAL", "10"))  # Check every 10s
WARNING_TIME = int(os.getenv("SESSION_WARNING_TIME", "60"))  # Warn 1 minute before

def main(page: ft.Page):
    page.title = "Pojangmacha"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    if not page.session.contains_key("user"):
        page.session.set("user", None)

    # Session monitor control
    monitor_active = {"value": False}
    warning_dialog_shown = {"value": False}
    last_activity_logged = {"time": time.time()}

    # helper to get current user email
    def current_email():
        u = page.session.get("user")
        return u.get("email") if u else None

    def close_warning_dialog():
        """Close the warning dialog (thread-safe)"""
        try:
            if hasattr(page, "dialog") and page.dialog:
                page.dialog.open = False
                page.dialog = None
            
            warning_dialog_shown["value"] = False
            page.update()
                
        except Exception as ex:
            print(f"Warning dialog close error: {ex}")

    # call this on any user activity to refresh server-side session timestamp
    def on_user_activity(e=None):
        """Handle any user activity - refresh session"""
        # Throttle logging (only log once per second to avoid spam)
        current_time = time.time()
        if current_time - last_activity_logged["time"] > 1.0:
            print(f"👆 User activity detected!")
            last_activity_logged["time"] = current_time
        
        try:
            # If warning is shown, close it on activity
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

    # Attach activity handlers to page
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

    # Store original page.update to intercept all updates as activity
    original_update = page.update
    
    def activity_aware_update(*args, **kwargs):
        """Intercept page updates as user activity"""
        email = current_email()
        if email and page.route not in ["/login", "/signup", "/"]:
            on_user_activity()
        return original_update(*args, **kwargs)
    
    page.update = activity_aware_update
    print("✅ Page update interceptor installed")

    def show_warning_dialog(remaining_seconds):
        """Show enhanced warning dialog with countdown"""
        if warning_dialog_shown["value"]:
            return  # Already shown
        
        print(f"⚠️ Showing warning dialog with {remaining_seconds}s remaining")
        warning_dialog_shown["value"] = True
        
        countdown_text = ft.Text(
            f"⏱️ {int(remaining_seconds)}s",
            size=40,
            weight="bold",
            color="orange"
        )
        
        def stay_logged_in(e):
            """User clicked to stay logged in"""
            email = current_email()
            if email:
                refresh_session(email)
                print("✅ User chose to stay logged in - session refreshed")
            close_warning_dialog()
        
        def logout_now(e):
            """User chose to logout"""
            force_logout()
        
        warning_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER, color="orange", size=30),
                ft.Text("⚠️ Session Expiring", size=20, weight="bold")
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
            original_update()  # Use original update to avoid recursion
            print("✅ Warning dialog displayed")
        except Exception as ex:
            print(f"❌ Error showing warning dialog: {ex}")
            warning_dialog_shown["value"] = False
            return
        
        # Update countdown every second
        def update_countdown():
            email = current_email()
            
            while warning_dialog_shown["value"] and email:
                try:
                    active, remaining = is_session_active(email, return_remaining=True)
                    
                    if not active or remaining <= 0:
                        print("⏱️ Countdown ended - session expired")
                        break
                    
                    countdown_text.value = f"⏱️ {int(remaining)}s"
                    original_update()  # Use original update
                    
                except Exception as ex:
                    print(f"Countdown update error: {ex}")
                    break
                
                time.sleep(1)
            
            print("🛑 Countdown thread ended")
        
        countdown_thread = threading.Thread(target=update_countdown, daemon=True)
        countdown_thread.start()

    def force_logout():
        """Force logout immediately"""
        print("🔴 FORCE LOGOUT INITIATED")
        
        email = current_email()
        if email:
            try:
                end_session(email)
                print(f"🔴 Session ended for {email}")
            except Exception as ex:
                print(f"End session error: {ex}")
        
        # Stop the monitor FIRST
        monitor_active["value"] = False
        print("🛑 Monitor deactivated")
        
        close_warning_dialog()
        
        # Clear session
        page.session.set("user", None)
        print("🧹 User session cleared")
        
        # Navigate to login
        page.go("/login")
        print("🔄 Redirected to login")

    def stop_session_monitor():
        """Stop the session monitor thread"""
        monitor_active["value"] = False
        close_warning_dialog()
        print("🛑 Session monitor stopped")

    def start_session_monitor():
        """Start or restart the session monitor thread"""
        # Stop existing monitor if running
        if monitor_active["value"]:
            stop_session_monitor()
            time.sleep(0.5)  # Wait for thread to stop
        
        # Reset warning dialog state
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
                    # Check session status
                    res = is_session_active(email, return_remaining=True)
                    if isinstance(res, tuple):
                        active, remaining = res
                    else:
                        active = bool(res)
                        remaining = SESSION_TIMEOUT
                    
                    print(f"🔍 Session check: active={active}, remaining={remaining:.0f}s")
                    
                    if not active or remaining <= 0:
                        # Session expired - STOP MONITOR IMMEDIATELY
                        print("❌ Session expired - logging out")
                        monitor_active["value"] = False  # CRITICAL: Stop loop immediately
                        
                        try:
                            end_session(email)
                        except Exception as ex:
                            print(f"End session error: {ex}")
                        
                        # Force logout on main thread
                        force_logout()
                        return  # EXIT THREAD
                    
                    # Show warning if time is running out
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
        
        # Start new monitor thread
        thread = threading.Thread(target=session_monitor, daemon=True)
        thread.start()
        print("✅ New session monitor thread started")

    # route change handler
    def route_change(e):
        page.clean()
        current_user = page.session.get("user")

        # Handle authenticated routes
        if page.route not in ["/login", "/signup", "/logout", "/", "/reset_password"]:
            if not current_user:
                page.snack_bar = ft.SnackBar(ft.Text("Please log in to continue."), open=True)
                original_update()
                page.go("/login")
                return
            
            # User is authenticated - ensure session exists and start monitor
            email = current_user.get("email")
            if email:
                try:
                    # Check if session exists, if not create it
                    if not is_session_active(email):
                        start_session(email)
                        print(f"✅ Session created for {email}")
                    else:
                        # Refresh on route change
                        refresh_session(email)
                        print(f"🔄 Session refreshed on route change for {email}")
                    
                    # Start session monitor if not already running
                    if not monitor_active["value"]:
                        start_session_monitor()
                
                except Exception as ex:
                    print(f"Session initialization error: {ex}")

        # Handle logout
        if page.route == "/logout":
            cur = page.session.get("user")
            if cur and cur.get("email"):
                try:
                    end_session(cur["email"])
                except Exception:
                    pass
            
            # Stop monitor
            stop_session_monitor()
            
            page.session.set("user", None)
            page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
            original_update()
            page.go("/login")
            return

        # Routing
        if page.route == "/login" or page.route == "/":
            # Stop monitor when on login page
            stop_session_monitor()
            login_view(page)
        elif page.route == "/signup":
            stop_session_monitor()
            signup_view(page)
        elif page.route == "/home":
            home_view(page)
        elif page.route == "/admin":
            admin_view(page)
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
    page.go("/login")

if __name__ == "__main__":
    ft.app(target=main)