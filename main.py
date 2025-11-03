# main.py
import flet as ft
from ui.login_view import login_view
from ui.signup_view import signup_view
from ui.home_view import home_view
from ui.admin_view import admin_view

def main(page: ft.Page):
    page.title = "Pojangmacha App"

    # Default session
    if not page.session.contains_key("user"):
        page.session.set("user", None)

    def route_change(e):
        page.clean()
        current_user = page.session.get("user")

        # Redirect if not logged in
        if page.route not in ["/login", "/signup"] and not current_user:
            page.snack_bar = ft.SnackBar(ft.Text("Please log in to continue."), open=True)
            page.update()
            page.go("/login")
            return

        # Routes
        if page.route == "/login":
            login_view(page)
        elif page.route == "/signup":
            signup_view(page)
        elif page.route == "/home":
            if current_user and current_user.get("role") == "customer":
                home_view(page)
            else:
                page.go("/admin")
        elif page.route == "/admin":
            if current_user and current_user.get("role") == "admin":
                admin_view(page)
            else:
                page.go("/home")
        else:
            page.go("/login")

    page.on_route_change = route_change
    page.go("/login")

if __name__ == "__main__":
    ft.app(target=main)
