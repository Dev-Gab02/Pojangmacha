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

def admin_view(page: ft.Page):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
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
                ft.Row(
                    [
                        img_display,
                        ft.Text(f.name, width=150),
                        ft.Text(f.category or "-", width=100),
                        ft.Text(f"₱{f.price:.2f}", width=100),
                        ft.IconButton(icon=ft.Icons.EDIT, on_click=lambda e, fid=f.id: open_edit_food(fid)),
                        ft.IconButton(icon=ft.Icons.DELETE, on_click=lambda e, fid=f.id: open_delete_food(fid)),
                    ]
                )
            )
        page.update()

    def close_dialog(dlg):
        dlg.open = False
        page.dialog = None
        page.update()

    # ===== Add Food =====
    def open_add_food(e):
        name = ft.TextField(label="Name", width=300)
        desc = ft.TextField(label="Description", multiline=True, width=300)
        cat = ft.TextField(label="Category", width=300)
        price = ft.TextField(label="Price", width=300)
        image_preview = ft.Image(src="", width=150, height=150, border_radius=10, fit=ft.ImageFit.CONTAIN)

        # File picker for image upload
        file_picker = ft.FilePicker()
        page.overlay.append(file_picker)

        selected_image_path = {"path": ""}

        def on_file_picked(e):
            if not e.files:
                return
            file = e.files[0]
            filename = os.path.basename(file.path)
            dest = os.path.join(UPLOAD_DIR, filename)
            try:
                with open(file.path, "rb") as src_file, open(dest, "wb") as dest_file:
                    dest_file.write(src_file.read())
                selected_image_path["path"] = dest.replace("\\", "/")
                image_preview.src = selected_image_path["path"]
                image_preview.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error uploading image: {ex}"), open=True)
                page.update()

        file_picker.on_result = on_file_picked

        upload_button = ft.ElevatedButton("Choose Image", on_click=lambda _: file_picker.pick_files(allow_multiple=False))

        def save_food(ev):
            if not name.value or not price.value:
                page.snack_bar = ft.SnackBar(ft.Text("Name and price required."), open=True)
                page.update()
                return

            new_food = FoodItem(
                name=name.value.strip(),
                description=desc.value.strip(),
                category=cat.value.strip(),
                price=float(price.value),
                image=selected_image_path["path"] or "assets/default.png",
            )
            db.add(new_food)
            db.commit()
            db.add(AuditLog(user_email="admin", action=f"Added food: {new_food.name}"))
            db.commit()

            close_dialog(dlg)
            refresh_foods()
            page.snack_bar = ft.SnackBar(ft.Text("Food added successfully."), open=True)
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Add New Food"),
            content=ft.Column([name, desc, cat, price, upload_button, image_preview]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg)),
                ft.ElevatedButton("Save", on_click=save_food),
            ],
            modal=True,
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # ===== Edit Food =====
    def open_edit_food(food_id):
        food = db.query(FoodItem).get(food_id)
        if not food:
            page.snack_bar = ft.SnackBar(ft.Text("Food not found."), open=True)
            page.update()
            return

        name = ft.TextField(label="Name", value=food.name, width=300)
        desc = ft.TextField(label="Description", value=food.description or "", multiline=True, width=300)
        cat = ft.TextField(label="Category", value=food.category or "", width=300)
        price = ft.TextField(label="Price", value=str(food.price), width=300)
        image_preview = ft.Image(src=food.image or "", width=150, height=150, border_radius=10, fit=ft.ImageFit.CONTAIN)

        file_picker = ft.FilePicker()
        page.overlay.append(file_picker)

        selected_image_path = {"path": food.image or ""}

        def on_file_picked(e):
            if not e.files:
                return
            file = e.files[0]
            filename = os.path.basename(file.path)
            dest = os.path.join(UPLOAD_DIR, filename)
            with open(file.path, "rb") as src_file, open(dest, "wb") as dest_file:
                dest_file.write(src_file.read())
            selected_image_path["path"] = dest.replace("\\", "/")
            image_preview.src = selected_image_path["path"]
            image_preview.update()

        file_picker.on_result = on_file_picked
        upload_button = ft.ElevatedButton("Change Image", on_click=lambda _: file_picker.pick_files(allow_multiple=False))

        def update_food(ev):
            food.name = name.value.strip()
            food.description = desc.value.strip()
            food.category = cat.value.strip()
            food.price = float(price.value)
            food.image = selected_image_path["path"] or "assets/default.png"
            db.commit()
            db.add(AuditLog(user_email="admin", action=f"Edited food: {food.name}"))
            db.commit()

            close_dialog(dlg)
            refresh_foods()
            page.snack_bar = ft.SnackBar(ft.Text("Food updated successfully."), open=True)
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Edit Food #{food.id}"),
            content=ft.Column([name, desc, cat, price, upload_button, image_preview]),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg)),
                ft.ElevatedButton("Update", on_click=update_food),
            ],
            modal=True,
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # ===== Delete Food =====
    def open_delete_food(food_id):
        food = db.query(FoodItem).get(food_id)
        if not food:
            page.snack_bar = ft.SnackBar(ft.Text("Food not found."), open=True)
            page.update()
            return

        def confirm_delete(ev):
            db.delete(food)
            db.commit()
            db.add(AuditLog(user_email="admin", action=f"Deleted food: {food.name}"))
            db.commit()
            close_dialog(dlg)
            refresh_foods()
            page.snack_bar = ft.SnackBar(ft.Text("Food deleted."), open=True)
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete '{food.name}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg)),
                ft.ElevatedButton("Delete", on_click=confirm_delete),
            ],
            modal=True,
        )
        page.dialog = dlg
        dlg.open = True
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
        fig = px.bar(
            x=list(data.keys()),
            y=list(data.values()),
            labels={"x": "Date", "y": "Revenue (₱)"},
            title="Daily Revenue Trend"
        )
        return PlotlyChart(fig, expand=True)

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
            ft.Tab(
                text="Food Management",
                content=ft.Column([
                    ft.Row([
                        ft.ElevatedButton("Add Food", on_click=open_add_food),
                    ]),
                    ft.Divider(),
                    food_table
                ])
            ),
            ft.Tab(text="Sales Analytics", content=generate_sales_chart()),
        ],
        expand=1
    )

    # ===== Render Page =====
    page.clean()
    page.add(
        ft.Column([
            ft.Row([ft.Text("Admin Dashboard", size=24, weight="bold"), logout_button],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            tabs
        ])
    )

    refresh_foods()
