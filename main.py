# main.py
import flet as ft
from ui.login_view import login_view
from ui.signup_view import signup_view

def main(page: ft.Page):
    def route_change(e):
        page.clean()
        if page.route == "/login":
            login_view(page)
        elif page.route == "/signup":
            signup_view(page)
        else:
            page.go("/login")

    page.on_route_change = route_change
    page.go("/login")

ft.app(target=main)
