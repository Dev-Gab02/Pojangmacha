# main.py
import flet as ft
from ui.login_view import login_view
from ui.signup_view import signup_view
from ui.home_view import home_view
from ui.admin_view import admin_view
# from ui.order_history_view import order_history_view
# from ui.profile_view import profile_view
# optionally include reset_password_view if implemented:
# from ui.reset_password_view import reset_password_view

def main(page: ft.Page):
    page.title = "Pojangmacha"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    # ensure session key exists
    if not page.session.contains_key("user"):
        page.session.set("user", None)

    def route_change(e):
        page.clean()
        current_user = page.session.get("user")

        # Redirect unauthorized users to login
        if page.route not in ["/login", "/signup", "/reset_password"] and not current_user:
            page.snack_bar = ft.SnackBar(ft.Text("Please log in to continue."), open=True)
            page.update()
            page.go("/login")
            return

        if page.route == "/login":
            login_view(page)
        elif page.route == "/signup":
            signup_view(page)
        elif page.route == "/home":
            # allow only customers here
            if current_user and current_user.get("role") == "customer":
                home_view(page)
            else:
                page.go("/admin")
        elif page.route == "/admin":
            if current_user and current_user.get("role") == "admin":
                admin_view(page)
            else:
                page.go("/home")
        elif page.route == "/orders":
            order_history_view(page)
        elif page.route == "/profile":
            profile_view(page)
        # elif page.route == "/reset_password":
        #     reset_password_view(page)
        else:
            page.go("/login")

    page.on_route_change = route_change
    page.go("/login")

if __name__ == "__main__":
    ft.app(target=main)
