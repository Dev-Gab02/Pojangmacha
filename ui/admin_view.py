# ui/admin_view.py
import os
import flet as ft
from core.db import SessionLocal
from models.user import User
from models.food_item import FoodItem
from models.order import Order
from models.audit_log import AuditLog
from flet.plotly_chart import PlotlyChart
import plotly.express as px
from datetime import datetime

UPLOAD_DIR = "assets/uploads/foods"
PROFILE_UPLOAD_DIR = "assets/uploads/profiles"

def admin_view(page: ft.Page):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(PROFILE_UPLOAD_DIR, exist_ok=True)
    db = SessionLocal()
    page.title = "Admin Dashboard - Pojangmacha"

    # ===== Overview =====
    def refresh_overview():
        total_users = db.query(User).count()
        total_foods = db.query(FoodItem).count()
        total_orders = db.query(Order).count()
        total_revenue = sum(order.total_price for order in db.query(Order).all())
        return ft.Row(
            [
                ft.Container(ft.Column([ft.Text("Users"), ft.Text(str(total_users), size=20, weight="bold")]),
                             padding=10, bgcolor=ft.Colors.BLUE_100, border_radius=10),
                ft.Container(ft.Column([ft.Text("Foods"), ft.Text(str(total_foods), size=20, weight="bold")]),
                             padding=10, bgcolor=ft.Colors.GREEN_100, border_radius=10),
                ft.Container(ft.Column([ft.Text("Orders"), ft.Text(str(total_orders), size=20, weight="bold")]),
                             padding=10, bgcolor=ft.Colors.AMBER_100, border_radius=10),
                ft.Container(ft.Column([ft.Text("Revenue"), ft.Text(f"₱{total_revenue:.2f}", size=20, weight="bold")]),
                             padding=10, bgcolor=ft.Colors.PURPLE_100, border_radius=10),
            ],
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        )

    # ===== USER MANAGEMENT =====
    user_table = ft.Column(scroll=ft.ScrollMode.AUTO)

    def refresh_users():
        user_table.controls.clear()
        users = db.query(User).all()
        if not users:
            user_table.controls.append(ft.Text("No users found.", italic=True))
        else:
            for u in users:
                img = ft.Image(src=u.profile_image or "assets/default-profile.png", width=50, height=50)
                user_table.controls.append(
                    ft.Row([
                        img,
                        ft.Text(u.full_name or "-", width=150),
                        ft.Text(u.email, width=200),
                        ft.Text(u.role, width=100),
                        ft.Text("Active" if u.is_active else "Disabled", width=100),
                        ft.IconButton(icon=ft.Icons.EDIT, on_click=lambda e, uid=u.id: open_edit_user(uid)),
                        ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, uid=u.id: open_delete_user(uid)),
                    ])
                )
        page.update()

    def close_dialog(dlg):
        dlg.open = False
        page.dialog = None
        page.update()

    # --- Add User ---
    def open_add_user(e):
        full_name = ft.TextField(label="Full Name", width=300)
        email = ft.TextField(label="Email", width=300)
        password = ft.TextField(label="Password", width=300, password=True, can_reveal_password=True)
        role = ft.Dropdown(label="Role", options=[
            ft.dropdown.Option("admin"),
            ft.dropdown.Option("customer")
        ], value="customer")

        def save_user(ev):
            if not email.value or not password.value:
                page.snack_bar = ft.SnackBar(ft.Text("Email and password are required."), open=True)
                page.update()
                return

            new_user = User(full_name=full_name.value, email=email.value,
                            password_hash=password.value, role=role.value)
            db.add(new_user)
            db.commit()
            db.add(AuditLog(user_email="admin", action=f"Created user: {email.value}"))
            db.commit()

            close_dialog(dlg)
            refresh_users()
            page.snack_bar = ft.SnackBar(ft.Text("User created successfully."), open=True)
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Add New User"),
            content=ft.Column([full_name, email, password, role]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg)),
                ft.ElevatedButton("Save", on_click=save_user),
            ],
            modal=True,
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # --- Edit User ---
    def open_edit_user(user_id):
        user = db.query(User).get(user_id)
        if not user:
            page.snack_bar = ft.SnackBar(ft.Text("User not found."), open=True)
            page.update()
            return

        full_name = ft.TextField(label="Full Name", value=user.full_name or "", width=300)
        email = ft.TextField(label="Email", value=user.email, width=300)
        role = ft.Dropdown(label="Role", options=[
            ft.dropdown.Option("admin"),
            ft.dropdown.Option("customer")
        ], value=user.role)
        is_active = ft.Switch(label="Active", value=user.is_active)

        def update_user(ev):
            user.full_name = full_name.value
            user.email = email.value
            user.role = role.value
            user.is_active = is_active.value
            db.commit()
            db.add(AuditLog(user_email="admin", action=f"Edited user: {user.email}"))
            db.commit()
            close_dialog(dlg)
            refresh_users()
            page.snack_bar = ft.SnackBar(ft.Text("User updated."), open=True)
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Edit User #{user.id}"),
            content=ft.Column([full_name, email, role, is_active]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg)),
                ft.ElevatedButton("Update", on_click=update_user),
            ],
            modal=True,
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # --- Delete User ---
    def open_delete_user(user_id):
        user = db.query(User).get(user_id)
        if not user:
            page.snack_bar = ft.SnackBar(ft.Text("User not found."), open=True)
            page.update()
            return

        def confirm_delete(ev):
            db.delete(user)
            db.commit()
            db.add(AuditLog(user_email="admin", action=f"Deleted user: {user.email}"))
            db.commit()
            close_dialog(dlg)
            refresh_users()
            page.snack_bar = ft.SnackBar(ft.Text("User deleted."), open=True)
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete '{user.email}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg)),
                ft.ElevatedButton("Delete", on_click=confirm_delete),
            ],
            modal=True,
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # ===== Food Management =====
    food_table = ft.Column(scroll=ft.ScrollMode.AUTO)
    def refresh_foods():
        food_table.controls.clear()
        foods = db.query(FoodItem).all()
        if not foods:
            food_table.controls.append(ft.Text("No food items yet.", italic=True))
        for f in foods:
            img_display = ft.Image(src=f.image, width=50, height=50) if f.image else ft.Icon(ft.Icons.NO_PHOTOGRAPHY)
            food_table.controls.append(
                ft.Row([
                    img_display,
                    ft.Text(f.name, width=150),
                    ft.Text(f.category or "-", width=100),
                    ft.Text(f"₱{f.price:.2f}", width=100),
                ])
            )
        page.update()

    # ===== Sales Analytics =====
    def generate_sales_chart():
        orders = db.query(Order).all()
        if not orders:
            return ft.Text("No order data yet.")
        data = {}
        for o in orders:
            day = o.created_at.strftime("%Y-%m-%d")
            data[day] = data.get(day, 0) + o.total_price
        fig = px.bar(x=list(data.keys()), y=list(data.values()),
                     labels={"x": "Date", "y": "Revenue (₱)"},
                     title="Daily Revenue Trend")
        return PlotlyChart(fig, expand=True)

    # ===== Audit Logs =====
    audit_table = ft.Column(scroll=ft.ScrollMode.AUTO)
    user_filter = ft.TextField(label="Filter by User", width=200)
    action_filter = ft.TextField(label="Action contains", width=200)
    from_date = ft.TextField(label="From (YYYY-MM-DD)", width=150)
    to_date = ft.TextField(label="To (YYYY-MM-DD)", width=150)

    def load_audits():
        audit_table.controls.clear()
        query = db.query(AuditLog)
        if user_filter.value:
            query = query.filter(AuditLog.user_email.like(f"%{user_filter.value}%"))
        if action_filter.value:
            query = query.filter(AuditLog.action.like(f"%{action_filter.value}%"))
        if from_date.value:
            try:
                start = datetime.strptime(from_date.value, "%Y-%m-%d")
                query = query.filter(AuditLog.timestamp >= start)
            except:
                pass
        if to_date.value:
            try:
                end = datetime.strptime(to_date.value, "%Y-%m-%d")
                query = query.filter(AuditLog.timestamp <= end)
            except:
                pass
        logs = query.order_by(AuditLog.timestamp.desc()).all()
        if not logs:
            audit_table.controls.append(ft.Text("No audit logs found.", color="grey"))
        else:
            for log in logs:
                audit_table.controls.append(
                    ft.Row([
                        ft.Text(log.timestamp.strftime("%Y-%m-%d %H:%M:%S"), width=180),
                        ft.Text(log.user_email, width=180),
                        ft.Text(log.action, width=300),
                    ])
                )
        page.update()

    def apply_filters(e): load_audits()
    load_audits()
    audit_tab = ft.Column([
        ft.Row([user_filter, action_filter, from_date, to_date, ft.ElevatedButton("Apply Filters", on_click=apply_filters)]),
        ft.Divider(),
        audit_table,
    ])

    # ===== Logout =====
    def handle_logout(e):
        page.session.set("user", None)
        page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
        page.go("/login")

    logout_button = ft.ElevatedButton("Logout", icon=ft.Icons.LOGOUT,
                                      bgcolor=ft.Colors.RED_200, on_click=handle_logout)

    # ===== Tabs =====
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Overview", content=ft.Column([refresh_overview()])),
            ft.Tab(text="User Management", content=ft.Column([
                ft.Row([ft.ElevatedButton("Add User", on_click=open_add_user)]),
                ft.Divider(),
                user_table
            ])),
            ft.Tab(text="Food Management", content=ft.Column([
                ft.Row([ft.ElevatedButton("Add Food", on_click=open_add_user)]),
                ft.Divider(),
                food_table
            ])),
            ft.Tab(text="Sales Analytics", content=generate_sales_chart()),
            ft.Tab(text="Audit Logs", content=audit_tab),
        ],
        expand=1
    )

    page.clean()
    page.add(
        ft.Column([
            ft.Row([ft.Text("Admin Dashboard", size=24, weight="bold"), logout_button],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            tabs
        ])
    )

    refresh_foods()
    refresh_users()
