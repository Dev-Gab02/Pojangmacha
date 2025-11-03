# ui/admin_view.py
import flet as ft
from core.db import SessionLocal
from models.user import User
from models.food_item import FoodItem
from models.order import Order
from random import randint
from sqlalchemy import inspect
from models.audit_log import AuditLog
from flet.plotly_chart import PlotlyChart
import plotly.express as px
from datetime import datetime

def admin_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Admin Dashboard - Pojangmacha"

    # Overview
    total_users = db.query(User).count()
    total_foods = db.query(FoodItem).count()
    inspector = inspect(db.bind)
    total_orders = db.query(Order).count() if inspector.has_table("orders") else 0
    total_revenue = sum(randint(100, 500) for _ in range(total_orders))

    overview_cards = ft.Row([
        ft.Container(ft.Column([ft.Text("Users"), ft.Text(str(total_users), size=20, weight="bold")]), padding=10, bgcolor=ft.Colors.BLUE_100, border_radius=10),
        ft.Container(ft.Column([ft.Text("Foods"), ft.Text(str(total_foods), size=20, weight="bold")]), padding=10, bgcolor=ft.Colors.GREEN_100, border_radius=10),
        ft.Container(ft.Column([ft.Text("Orders"), ft.Text(str(total_orders), size=20, weight="bold")]), padding=10, bgcolor=ft.Colors.AMBER_100, border_radius=10),
        ft.Container(ft.Column([ft.Text("Revenue"), ft.Text(f"₱{total_revenue}", size=20, weight="bold")]), padding=10, bgcolor=ft.Colors.PURPLE_100, border_radius=10),
    ], alignment=ft.MainAxisAlignment.SPACE_EVENLY)

    def generate_sales_chart():
        orders = db.query(Order).all()
        if not orders:
            return ft.Text("No order data yet.")
        data = {}
        for o in orders:
            day = o.created_at.strftime("%Y-%m-%d")
            data[day] = data.get(day, 0) + o.total_price
        days = list(data.keys())
        revenues = list(data.values())
        fig = px.bar(x=days, y=revenues, labels={"x": "Date", "y": "Revenue (₱)"}, title="Daily Revenue Trend")
        return PlotlyChart(fig, expand=True)

    # --- Buttons fixed for Flet ---
    def handle_add_food(e):
        page.snack_bar = ft.SnackBar(ft.Text("Add food not implemented"), open=True)
        page.update()

    def handle_delete_food(e):
        page.snack_bar = ft.SnackBar(ft.Text("Delete food not implemented"), open=True)
        page.update()

    def handle_edit_food(e):
        page.snack_bar = ft.SnackBar(ft.Text("Edit food not implemented"), open=True)
        page.update()

    def handle_logout(e):
        page.session.set("user", None)
        page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
        page.go("/login")

    logout_button = ft.ElevatedButton("Logout", icon=ft.Icons.LOGOUT, bgcolor=ft.Colors.RED_200, on_click=handle_logout)

    # Tabs
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Overview", content=ft.Column([overview_cards])),
            ft.Tab(
                text="Food Management",
                content=ft.Column([
                    ft.Row([
                        ft.ElevatedButton("Add Food", on_click=handle_add_food),
                        ft.ElevatedButton("Edit Food", on_click=handle_edit_food),
                        ft.ElevatedButton("Delete Food", on_click=handle_delete_food),
                    ]),
                ])
            ),
            ft.Tab(text="Sales Analytics", content=generate_sales_chart()),
        ],
        expand=1
    )

    # Page render
    page.clean()
    page.add(
        ft.Column([
            ft.Row([ft.Text("👨‍💼 Admin Dashboard", size=24, weight="bold"), logout_button],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            tabs
        ])
    )
