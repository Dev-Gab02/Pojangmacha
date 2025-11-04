# main.py
import flet as ft
from ui.login_view import login_view
from ui.signup_view import signup_view
from ui.home_view import home_view
from ui.admin_view import admin_view
#from ui.order_history_view import order_history_view
#from ui.profile_view import profile_view
#from ui.reset_password_view import reset_password_view


def main(page: ft.Page):
    # --- Page Config ---
    page.title = "Pojangmacha"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    # Initialize user session storage
    if not page.session.contains_key("user"):
        page.session.set("user", None)

    # --- Route Logic ---
    def route_change(e):
        page.clean()
        current_user = page.session.get("user")

        # Enforce authentication for restricted routes
        if page.route not in ["/login", "/signup", "/reset_password"] and not current_user:
            page.snack_bar = ft.SnackBar(ft.Text("Please log in to continue."), open=True)
            page.update()
            page.go("/login")
            return

        # Route handling
        if page.route == "/login":
            login_view(page)

        elif page.route == "/signup":
            signup_view(page)

        elif page.route == "/home":
            # Customer home only
            if current_user and current_user.get("role") == "customer":
                home_view(page)
            else:
                page.go("/admin")

        elif page.route == "/admin":
            # Admin-only access
            if current_user and current_user.get("role") == "admin":
                admin_view(page)
            else:
                page.go("/home")

        elif page.route == "/logout":
            # Universal logout path
            page.session.set("user", None)
            page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
            page.update()
            page.go("/login")

        else:
            page.go("/login")

    # Assign routing handler
    page.on_route_change = route_change
    page.go("/login")


if __name__ == "__main__":
    ft.app(target=main)
