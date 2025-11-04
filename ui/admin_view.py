# ui/admin_view.py
import flet as ft
from core.db import SessionLocal
from models.user import User
from models.food_item import FoodItem
from models.order import Order
from models.audit_log import AuditLog
from core.logger import log_action
from sqlalchemy import inspect
from datetime import datetime
from random import randint
from flet.plotly_chart import PlotlyChart
import plotly.express as px


def admin_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Admin Dashboard - Pojangmacha"

    # --- Overview Summary ---
    total_users = db.query(User).count()
    total_foods = db.query(FoodItem).count()
    inspector = inspect(db.bind)
    total_orders = db.query(Order).count() if inspector.has_table("orders") else 0
    total_revenue = sum(randint(100, 500) for _ in range(total_orders))

    overview_cards = ft.Row([
        ft.Container(ft.Column([
            ft.Text("Users"),
            ft.Text(str(total_users), size=20, weight="bold")
        ]), padding=10, bgcolor=ft.Colors.BLUE_100, border_radius=10),

        ft.Container(ft.Column([
            ft.Text("Foods"),
            ft.Text(str(total_foods), size=20, weight="bold")
        ]), padding=10, bgcolor=ft.Colors.GREEN_100, border_radius=10),

        ft.Container(ft.Column([
            ft.Text("Orders"),
            ft.Text(str(total_orders), size=20, weight="bold")
        ]), padding=10, bgcolor=ft.Colors.AMBER_100, border_radius=10),

        ft.Container(ft.Column([
            ft.Text("Revenue"),
            ft.Text(f"₱{total_revenue}", size=20, weight="bold")
        ]), padding=10, bgcolor=ft.Colors.PURPLE_100, border_radius=10),
    ], alignment=ft.MainAxisAlignment.SPACE_EVENLY)

    # --- Sales Chart ---
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
        fig = px.bar(x=days, y=revenues,
                     labels={"x": "Date", "y": "Revenue (₱)"},
                     title="Daily Revenue Trend")
        return PlotlyChart(fig, expand=True)

    # --- User Management ---
    user_table = ft.Column()

    def load_users():
        user_table.controls.clear()
        for u in db.query(User).filter(User.role != "admin").all():
            user_table.controls.append(
                ft.Row([
                    ft.Text(u.full_name, width=150),
                    ft.Text(u.email, width=200),
                    ft.IconButton(icon=ft.Icons.DELETE,
                                  on_click=lambda e, uid=u.id: delete_user(uid))
                ])
            )
        page.update()

    def delete_user(u_id):
        session = SessionLocal()
        u = session.query(User).get(u_id)
        if u and u.role != "admin":
            session.delete(u)
            session.commit()
            log_action("admin@gmail.com", f"Deleted user {u.full_name}")
        session.close()
        load_users()
        page.snack_bar = ft.SnackBar(ft.Text("User deleted."), open=True)
        page.update()

    load_users()

    # --- Food Management ---
    food_table = ft.Column()

    def load_foods():
        food_table.controls.clear()
        for f in db.query(FoodItem).all():
            food_table.controls.append(
                ft.Row([
                    ft.Text(f.name, width=150),
                    ft.Text(f.category, width=100),
                    ft.Text(f"₱{f.price:.2f}", width=80),
                    ft.IconButton(icon=ft.Icons.DELETE,
                                  on_click=lambda e, fid=f.id: delete_food(fid))
                ])
            )
        page.update()

    def delete_food(f_id):
        session = SessionLocal()
        f = session.query(FoodItem).get(f_id)
        if f:
            session.delete(f)
            session.commit()
            log_action("admin@gmail.com", f"Deleted food {f.name}")
        session.close()
        load_foods()
        page.snack_bar = ft.SnackBar(ft.Text("Food deleted."), open=True)
        page.update()

    load_foods()

    def handle_add_food(e):
        page.snack_bar = ft.SnackBar(ft.Text("Add food not implemented"), open=True)
        page.update()

    def handle_edit_food(e):
        page.snack_bar = ft.SnackBar(ft.Text("Edit food not implemented"), open=True)
        page.update()

    # --- Orders Management ---
    order_table = ft.Column()

    def load_orders():
        order_table.controls.clear()
        for o in db.query(Order).all():
            order_table.controls.append(
                ft.Row([
                    ft.Text(f"Order #{o.id}", width=100),
                    ft.Text(o.status, width=120),
                    ft.Text(f"₱{o.total_price:.2f}", width=100),
                    ft.ElevatedButton("Pending", on_click=lambda e, oid=o.id: update_status(oid, "Pending")),
                    ft.ElevatedButton("Preparing", on_click=lambda e, oid=o.id: update_status(oid, "Preparing")),
                    ft.ElevatedButton("Completed", on_click=lambda e, oid=o.id: update_status(oid, "Completed"))
                ])
            )
        page.update()

    def update_status(order_id, new_status):
        session = SessionLocal()
        try:
            order = session.query(Order).get(order_id)
            if order:
                order.status = new_status
                order.updated_at = datetime.utcnow()
                session.commit()
                log_action("admin@gmail.com", f"Updated Order #{order.id} to {new_status}")
        except Exception as e:
            session.rollback()
            print("Error updating order:", e)
        finally:
            session.close()
        load_orders()
        page.snack_bar = ft.SnackBar(ft.Text(f"Order updated."), open=True)
        page.update()

    load_orders()

    # --- Audit Logs ---
    audit_table = ft.Column()

    def load_audits():
        audit_table.controls.clear()
        for log in db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(20).all():
            audit_table.controls.append(
                ft.Row([
                    ft.Text(log.timestamp.strftime("%Y-%m-%d %H:%M:%S"), width=180),
                    ft.Text(log.user_email, width=200),
                    ft.Text(log.action, width=300)
                ])
            )
        page.update()

    load_audits()

    # --- Logout ---
    def handle_logout(e):
        page.session.set("user", None)
        page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
        page.update()
        page.go("/login")

    logout_button = ft.ElevatedButton("Logout", icon=ft.Icons.LOGOUT,
                                      bgcolor=ft.Colors.RED_200,
                                      on_click=handle_logout)

    # --- Tabs ---
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Overview", content=ft.Column([overview_cards])),
            ft.Tab(text="Users", content=user_table),
            ft.Tab(
                text="Food Management",
                content=ft.Column([
                    ft.Row([
                        ft.ElevatedButton("Add Food", on_click=handle_add_food),
                        ft.ElevatedButton("Edit Food", on_click=handle_edit_food)
                    ]),
                    food_table
                ])
            ),
            ft.Tab(text="Orders", content=order_table),
            ft.Tab(text="Sales Analytics", content=generate_sales_chart()),
            ft.Tab(text="Audit Logs", content=audit_table),
        ],
        expand=1
    )

    # --- Page Render ---
    page.clean()
    page.add(
        ft.Column([
            ft.Row([
                ft.Text("👨‍💼 Admin Dashboard", size=24, weight="bold"),
                logout_button
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            tabs
        ])
    )
