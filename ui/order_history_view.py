import os
import flet as ft
from core.db import SessionLocal
from models.order import Order, OrderItem
from models.food_item import FoodItem
from models.audit_log import AuditLog

def order_history_widget(page, on_nav):
    db = SessionLocal()
    user_data = page.session.get("user")
    if not user_data:
        return ft.Text("Please log in first.", color="red")

    user_id = user_data.get("id")
    user_email = user_data.get("email")

    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    order_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def reorder_items(order_id):
        from core.cart_service import add_to_cart
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        added_count = 0
        for i in order_items:
            food = db.query(FoodItem).get(i.food_id)
            if food:
                add_to_cart(db, user_id, food.id, quantity=i.quantity)
                added_count += 1
        db.add(AuditLog(user_email=user_email, action=f"Reordered order #{order_id} ({added_count} items)"))
        db.commit()
        page.snack_bar = ft.SnackBar(
            ft.Text(f"✅ Added {added_count} items to cart!"),
            bgcolor="green700",
            action="View Cart",
            on_action=lambda e: on_nav("cart")
        )
        page.snack_bar.open = True
        page.update()

    if not orders:
        order_column.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.RECEIPT_LONG_OUTLINED, size=80, color="grey"),
                    ft.Text("No orders yet", size=18, color="grey", weight="bold"),
                    ft.Text("Start shopping to see your order history", size=12, color="grey"),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "Browse Menu",
                        icon=ft.Icons.RESTAURANT_MENU,
                        on_click=lambda e: on_nav("food"),
                        style=ft.ButtonStyle(bgcolor="blue700", color="white")
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=40,
                alignment=ft.alignment.center
            )
        )
    else:
        for order in orders:
            items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            item_rows = []
            for i in items:
                food = db.query(FoodItem).get(i.food_id)
                if food:
                    food_name = food.name
                    food_image = food.image
                    food_price = food.price
                    item_rows.append(
                        ft.Container(
                            content=ft.Row([
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
                                ft.Column([
                                    ft.Text(food_name, weight="bold", size=13),
                                    ft.Text(f"₱{food_price:.2f} × {i.quantity}", size=11, color="grey700"),
                                ], spacing=2, expand=True),
                                ft.Text(f"₱{i.subtotal:.2f}", size=13, weight="bold", color="green"),
                            ], spacing=8, alignment=ft.MainAxisAlignment.START),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4)
                        )
                    )
                else:
                    item_rows.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Container(width=50, height=50, bgcolor="grey300", border_radius=8),
                                ft.Column([
                                    ft.Text("Deleted item", weight="bold", size=13, color="red"),
                                    ft.Text(f"Quantity: {i.quantity}", size=11, color="grey700"),
                                ], spacing=2, expand=True),
                                ft.Text(f"₱{i.subtotal:.2f}", size=13, weight="bold", color="grey"),
                            ], spacing=8, alignment=ft.MainAxisAlignment.START),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4)
                        )
                    )
            order_column.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row([
                                    ft.Text(f"Order #{order.id}", size=16, weight="bold"),
                                    ft.Container(
                                        content=ft.Text(order.status, color="white", size=11, weight="bold"),
                                        bgcolor="green" if order.status == "Completed" else "orange" if order.status == "Pending" else "red",
                                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                        border_radius=5
                                    )
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Text(f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}", size=11, color="grey700"),
                                ft.Divider(height=1),
                                ft.Column(item_rows, spacing=4),
                                ft.Divider(height=1),
                                ft.Row(
                                    [
                                        ft.Text(f"Total: ₱{order.total_price:.2f}", weight="bold", size=16, color="blue700"),
                                        ft.ElevatedButton(
                                            "Reorder",
                                            icon=ft.Icons.REFRESH,
                                            on_click=lambda e, oid=order.id: reorder_items(oid),
                                            style=ft.ButtonStyle(
                                                bgcolor="blue700",
                                                color="white"
                                            ),
                                            height=36
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                )
                            ],
                            spacing=8
                        ),
                        padding=12
                    )
                )
            )

    # Header (matches profile header style)
    header = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text("Order History", size=20, weight="bold", color="black"),
                padding=ft.padding.only(top=15, left=15, right=15, bottom=8)
            ),
            ft.Divider(height=1, color="grey300", thickness=1)
        ], spacing=0),
        bgcolor="white",
        padding=ft.padding.only(left=0, right=0, top=0, bottom=0)
    )

    return ft.Column([
        header,
        ft.Container(
            content=order_column,
            expand=True,
            padding=10,
            bgcolor="grey100"
        )
    ], expand=True, spacing=0)