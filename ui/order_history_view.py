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

    order_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

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
                        on_click=lambda e: page.go("/home"),
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
                                    ft.Text(food_name, weight="bold", size=13),
                                    ft.Text(f"₱{food_price:.2f} × {i.quantity}", size=11, color="grey700"),
                                ], spacing=2, expand=True),
                                # Subtotal
                                ft.Text(f"₱{i.subtotal:.2f}", size=13, weight="bold", color="green"),
                            ], spacing=8, alignment=ft.MainAxisAlignment.START),
                            padding=ft.padding.symmetric(horizontal=8, vertical=4)
                        )
                    )
                else:
                    # Deleted item fallback
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
                                # Order header
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
                                
                                # Items list
                                ft.Column(item_rows, spacing=4),
                                
                                ft.Divider(height=1),
                                
                                # Total and reorder button
                                ft.Row(
                                    [
                                        ft.Text(f"Total: ₱{order.total_price:.2f}", weight="bold", size=16, color="blue700"),
                                        ft.ElevatedButton(
                                            "Reorder",
                                            icon=ft.Icons.REFRESH,
                                            on_click=lambda e, oid=order.id: reorder_items(page, oid, user_email, db),
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

    # Footer
    footer = ft.Container(
        content=ft.Row([
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.RESTAURANT_MENU,
                    tooltip="Food",
                    on_click=lambda e: page.go("/home"),
                    icon_size=24
                ),
                ft.Text("Food", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.SEARCH,
                    tooltip="Search",
                    on_click=lambda e: page.go("/home"),
                    icon_size=24
                ),
                ft.Text("Search", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.HISTORY,
                    tooltip="Orders",
                    icon_color="blue700",
                    icon_size=24
                ),
                ft.Text("Orders", size=10, text_align=ft.TextAlign.CENTER, color="blue700")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.PERSON,
                    tooltip="Profile",
                    on_click=lambda e: page.go("/profile"),
                    icon_size=24
                ),
                ft.Text("Profile", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        bgcolor="white",
        padding=ft.padding.symmetric(vertical=6, horizontal=0),
        border=ft.border.only(top=ft.BorderSide(1, "grey300")),
        margin=0,
        height=60
    )

    # Main layout
    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda e: page.go("/home")
                        ),
                        ft.Text("Order History", size=18, weight="bold"),
                    ]),
                    padding=10,
                    bgcolor="white"
                ),
                
                # Orders list (scrollable)
                ft.Container(
                    content=order_column,  # ✅ FIXED: was orders_column
                    expand=True,
                    padding=10,
                    bgcolor="grey100"
                ),
                
                # Footer
                footer
            ], expand=True, spacing=0),
            width=400,
            height=700,
            padding=0
        )
    )
    page.update()


def reorder_items(page, order_id, user_email, db):
    """Reorder items from a previous order"""
    from core.cart_service import add_to_cart
    
    user_data = page.session.get("user")
    if not user_data:
        return
    
    user_id = user_data.get("id")
    
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    if not order_items:
        page.snack_bar = ft.SnackBar(ft.Text("No items found for reorder."), open=True)
        page.update()
        return

    added_count = 0
    names = []
    
    for i in order_items:
        food = db.query(FoodItem).get(i.food_id)
        if food:
            # Add to cart
            add_to_cart(db, user_id, food.id, quantity=i.quantity)
            names.append(food.name)
            added_count += 1

    # ✅ Audit log for reorder
    db.add(AuditLog(user_email=user_email, action=f"Reordered order #{order_id} ({added_count} items)"))
    db.commit()

    if added_count > 0:
        msg = f"✅ Added {added_count} items to cart!"
        page.snack_bar = ft.SnackBar(
            ft.Text(msg),
            bgcolor="green700",
            action="View Cart",
            on_action=lambda e: page.go("/home")
        )
    else:
        msg = "⚠️ Items no longer available."
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor="orange")
    
    page.snack_bar.open = True
    page.update()