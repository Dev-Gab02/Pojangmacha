# main.py
import flet as ft, threading, time
from core.session_manager import start_session, is_session_active, refresh_session, end_session
from ui.login_view import login_view
from ui.signup_view import signup_view
from ui.home_view import home_view
from ui.admin_view import admin_view
from ui.reset_password_view import reset_password_view

SESSION_CHECK_INTERVAL = 5  # seconds between checks
WARNING_THRESHOLD = 30      # show alert 30 s before logout

def main(page: ft.Page):
    page.title = "Pojangmacha"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    if not page.session.contains_key("user"):
        page.session.set("user", None)

    # --- Auto-logout monitor thread ---
    def session_monitor():
        while True:
            time.sleep(SESSION_CHECK_INTERVAL)
            user = page.session.get("user")
            if not user:
                continue
            email = user["email"]
            active, remaining = is_session_active(email)
            if not active:
                page.run_on_main_thread(lambda: auto_logout(page))
            elif remaining <= WARNING_THRESHOLD:
                page.run_on_main_thread(lambda: show_warning(page, remaining))

    def auto_logout(pg: ft.Page):
        u = pg.session.get("user")
        if u:
            end_session(u["email"])
            pg.session.set("user", None)
            pg.dialog = ft.AlertDialog(title=ft.Text("Session Expired"),
                                       content=ft.Text("You were logged out due to inactivity."),
                                       actions=[ft.TextButton("OK", on_click=lambda e: pg.go("/login"))],
                                       open=True)
            pg.update()

    def show_warning(pg: ft.Page, remaining):
        pg.snack_bar = ft.SnackBar(ft.Text(f"⚠️ Auto-logout in {remaining}s due to inactivity."), open=True)
        pg.update()

    threading.Thread(target=session_monitor, daemon=True).start()

    # Reset session on any interaction
    def refresh_activity(e):
        u = page.session.get("user")
        if u:
            refresh_session(u["email"])
    page.on_pointer_move = refresh_activity
    page.on_keyboard_event = refresh_activity

    # --- Routing ---
    def route_change(e):
        page.clean()
        user = page.session.get("user")
        if page.route not in ["/login", "/signup"] and not user:
            page.go("/login")
            return
        if page.route == "/login": login_view(page)
        elif page.route == "/signup": signup_view(page)
        elif page.route == "/home": home_view(page)
        elif page.route == "/admin": admin_view(page)
        elif page.route == "/reset_password": reset_password_view(page)
        else: page.go("/login")

    page.on_route_change = route_change
    page.go("/login")

if __name__ == "__main__":
    ft.app(target=main)
