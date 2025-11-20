import os
import flet as ft
from core.db import SessionLocal
from models.order import Order, OrderItem
from models.food_item import FoodItem
from models.audit_log import AuditLog
from datetime import datetime

def order_history_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Order History"

    # ✅ Ensure user is logged in
    user_data = page.session.get("user")
    if not user_data:
        page.snack_bar = ft.SnackBar(ft.Text("Please log in first."), open=True)
        page.go("/login")
        return

    user_id = user_data.get("id")
    user_email = user_data.get("email")

    # ✅ Query only current user's orders
    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    order_column = ft.Column(spacing=10)

    if not orders:
        order_column.controls.append(
            ft.Container(
                content=ft.Text("You have no past orders yet.", italic=True, size=16, color="grey"),
                padding=20,
                alignment=ft.alignment.center
            )
        )
    else:
        for order in orders:
            items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            item_rows = []
            
            # Build item rows with images, names, prices, and quantities
            for i in items:
                food = db.query(FoodItem).get(i.food_id)
                
                if food:
                    food_name = food.name
                    food_image = food.image
                    food_price = food.price
                    
                    # Create a row for each food item
                    item_rows.append(
                        ft.Container(
                            content=ft.Row([
                                # Food image
                                ft.Image(
                                    src=food_image,
                                    width=50,
                                    height=50,
                                    fit=ft.ImageFit.COVER,
                                    border_radius=8
                                ) if food_image and os.path.exists(food_image) else ft.Container(
                                    width=50,
                                    height=50,
                                    bgcolor="grey300",
                                    border_radius=8
                                ),
                                # Food details
                                ft.Column([
                                    ft.Text(food_name, weight="bold", size=14),
                                    ft.Text(f"₱{food_price:.2f} × {i.quantity}", size=12, color="grey700"),
                                ], spacing=2, expand=True),
                                # Subtotal
                                ft.Text(f"₱{i.subtotal:.2f}", size=14, weight="bold", color="green"),
                            ], spacing=10, alignment=ft.MainAxisAlignment.START),
                            padding=ft.padding.only(left=10, right=10, top=5, bottom=5)
                        )
                    )
                else:
                    # Deleted item fallback
                    item_rows.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Container(width=50, height=50, bgcolor="grey300", border_radius=8),
                                ft.Column([
                                    ft.Text("❌ Deleted item", weight="bold", size=14, color="red"),
                                    ft.Text(f"Quantity: {i.quantity}", size=12, color="grey700"),
                                ], spacing=2, expand=True),
                                ft.Text(f"₱{i.subtotal:.2f}", size=14, weight="bold", color="grey"),
                            ], spacing=10, alignment=ft.MainAxisAlignment.START),
                            padding=ft.padding.only(left=10, right=10, top=5, bottom=5)
                        )
                    )

            order_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                # Order header
                                ft.Row([
                                    ft.Text(f"Order #{order.id}", size=18, weight="bold"),
                                    ft.Container(
                                        content=ft.Text(order.status, color="white", size=12),
                                        bgcolor="green" if order.status == "Completed" else "orange" if order.status == "Pending" else "red",
                                        padding=5,
                                        border_radius=5
                                    )
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}", size=12, color="grey700"),
                                
                                ft.Divider(height=1),
                                
                                # Items list
                                ft.Column(item_rows, spacing=5),
                                
                                ft.Divider(height=1),
                                
                                # Total and reorder button
                                ft.Row(
                                    [
                                        ft.Text(f"Total: ₱{order.total_price:.2f}", weight="bold", size=18, color="blue700"),
                                        ft.ElevatedButton(
                                            "Reorder",
                                            icon=ft.Icons.REFRESH,
                                            on_click=lambda e, oid=order.id: reorder_items(page, oid, user_email, db),
                                            style=ft.ButtonStyle(
                                                bgcolor="blue700",
                                                color="white"
                                            )
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                )
                            ],
                            spacing=10
                        ),
                        padding=15
                    )
                )
            )

    # Updated footer - NO SPACING, TOUCHES BOTTOM
    footer = ft.Container(
        content=ft.Row([
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.RESTAURANT_MENU,
                    tooltip="Food",
                    on_click=lambda e: page.go("/home")
                ),
                ft.Text("Food", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.SEARCH,
                    tooltip="Search",
                    on_click=lambda e: page.go("/home")
                ),
                ft.Text("Search", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.HISTORY,
                    tooltip="Orders",
                    icon_color="blue700"
                ),
                ft.Text("Orders", size=10, text_align=ft.TextAlign.CENTER, color="blue700")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.PERSON,
                    tooltip="Profile",
                    on_click=lambda e: page.go("/profile")
                ),
                ft.Text("Profile", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        bgcolor="white",
        padding=ft.padding.symmetric(vertical=8, horizontal=0),
        border=ft.border.only(top=ft.BorderSide(1, "grey300")),
        margin=0
    )

    # Main layout - NO SPACING
    page.clean()
    page.add(
        ft.Column([
            # Header
            ft.Container(
                content=ft.Text("🧾 Order History", size=24, weight="bold"),
                padding=10
            ),
            # Orders (scrollable)
            ft.Container(
                content=ft.Column([order_column], scroll=ft.ScrollMode.AUTO),
                expand=True,
                padding=10
            ),
            # Footer (fixed) - NO SPACING
            footer
        ], expand=True, spacing=0)
    )
    page.update()


def reorder_items(page, order_id, user_email, db):
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    if not order_items:
        page.snack_bar = ft.SnackBar(ft.Text("No items found for reorder."), open=True)
        page.update()
        return

    names = []
    for i in order_items:
        f = db.query(FoodItem).get(i.food_id)
        if f:
            names.append(f.name)

    # ✅ Audit log for reorder
    db.add(AuditLog(user_email=user_email, action=f"Reordered order #{order_id}"))
    db.commit()

    if names:
        msg = f"✅ Reordered items: {', '.join(names)}"
    else:
        msg = "⚠️ Some items no longer exist."
    page.snack_bar = ft.SnackBar(ft.Text(msg), open=True)
    page.update()