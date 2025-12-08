import os
import flet as ft
from core.db import SessionLocal
from models.food_item import FoodItem
from models.user import User
from models.order import Order, OrderItem
from models.cart import Cart
from models.audit_log import AuditLog
from core.cart_service import get_user_cart, add_to_cart, update_cart_quantity, remove_from_cart, get_cart_count
from core.profile_service import get_user_by_id
from datetime import datetime
import time
from ui.checkout_view import checkout_view
from ui.profile_view import profile_view_widget
from ui.order_history_view import order_history_widget
from ui.cart_view import cart_view
from ui.food_view import food_view  # <-- Import your new food view

def home_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Pojangmacha"

    # Get logged-in user
    user_data = page.session.get("user")
    if not user_data:
        page.snack_bar = ft.SnackBar(ft.Text("Please log in first."), open=True)
        page.go("/login")
        return

    user_id = user_data.get("id")
    user = get_user_by_id(db, user_id)

    # State
    nav_state = {"tab": "food"}  # "food", "cart", "orders", "profile"
    show_checkout = {"value": False}
    cart_count_text = ft.Text("", color="white", size=10, weight="bold")
    cart_badge_container = ft.Container(
        content=cart_count_text,
        bgcolor="#E9190A",
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=6, vertical=3),
        right=5,
        top=5,
        visible=False
    )
    content_container = ft.Container(expand=True)

    # --- CART BADGE ---
    def update_cart_badge():
        total_items = get_cart_count(db, user_id)
        if total_items > 0:
            cart_count_text.value = str(total_items)
            cart_badge_container.visible = True
        else:
            cart_count_text.value = ""
            cart_badge_container.visible = False
        page.update()

    # --- FOOTER NAVIGATION ---
    def nav_icon(icon, label, tab, on_click, active_tab):
        is_active = tab == active_tab
        return ft.Column([
            ft.IconButton(
                icon=icon,
                tooltip=label,
                icon_color="#E9190A" if is_active else "black",
                on_click=on_click
            ),
            ft.Text(label, size=8, text_align=ft.TextAlign.CENTER, color="black")
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)

    def switch_tab(tab):
        nav_state["tab"] = tab
        show_checkout["value"] = False
        render_main_content()
        update_footer()
        page.update()

    def update_footer():
        footer.content = ft.Row([
            nav_icon(ft.Icons.RESTAURANT_MENU, "Food", "food", lambda e: switch_tab("food"), nav_state["tab"]),
            ft.Stack([
                nav_icon(ft.Icons.SHOPPING_CART, "Cart", "cart", lambda e: switch_tab("cart"), nav_state["tab"]),
                cart_badge_container
            ], width=50, height=50),
            nav_icon(ft.Icons.HISTORY, "Orders", "orders", lambda e: switch_tab("orders"), nav_state["tab"]),
            nav_icon(ft.Icons.PERSON, "Profile", "profile", lambda e: switch_tab("profile"), nav_state["tab"]),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
        page.update()

    footer = ft.Container(
        content=ft.Row([
            nav_icon(ft.Icons.RESTAURANT_MENU, "Food", "food", lambda e: switch_tab("food"), nav_state["tab"]),
            ft.Stack([
                nav_icon(ft.Icons.SHOPPING_CART, "Cart", "cart", lambda e: switch_tab("cart"), nav_state["tab"]),
                cart_badge_container
            ], width=50, height=50),
            nav_icon(ft.Icons.HISTORY, "Orders", "orders", lambda e: switch_tab("orders"), nav_state["tab"]),
            nav_icon(ft.Icons.PERSON, "Profile", "profile", lambda e: switch_tab("profile"), nav_state["tab"]),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        bgcolor="white",
        padding=ft.padding.symmetric(vertical=6),
        border=ft.border.only(top=ft.BorderSide(1, "grey300")),
        margin=0,
        height=60
    )

    def handle_checkout(e=None):
        cart_items = show_checkout.get("cart_items", [])
        total = show_checkout.get("total", 0)
        if not cart_items:
            page.snack_bar = ft.SnackBar(ft.Text("No items to checkout."), open=True)
            page.update()
            return

        # Create new order
        new_order = Order(user_id=user_id, total_price=total, status="Pending", created_at=datetime.now())
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Add order items
        for item in cart_items:
            food = db.query(FoodItem).filter(FoodItem.name == item["name"]).first()
            if food:
                db.add(OrderItem(order_id=new_order.id, food_id=food.id, quantity=item["quantity"], subtotal=item["subtotal"]))
        db.commit()

        # Clear cart
        for cart_item in get_user_cart(db, user_id):
            remove_from_cart(db, cart_item.id)
        update_cart_badge()

        # Show confirmation and go to orders tab
        show_checkout["value"] = False
        nav_state["tab"] = "orders"
        render_main_content()
        page.snack_bar = ft.SnackBar(ft.Text("Order placed!"), open=True)
        page.update()

    def refresh_cart():
        render_main_content()

    # --- MAIN CONTENT RENDERERS ---
    def render_main_content():
        if show_checkout["value"]:
            content_container.content = checkout_view(
                page,
                on_back=lambda e: switch_tab("cart"),
                total=show_checkout.get("total", 0),
                cart_items=show_checkout.get("cart_items", []),
                on_checkout=handle_checkout
            )
            page.update()
            return
        tab = nav_state["tab"]
        if tab == "food":
            render_food()
        elif tab == "cart":
            content_container.content = cart_view(
                db=db,
                user_id=user_id,
                get_user_cart=get_user_cart,
                remove_from_cart=remove_from_cart,
                update_cart_quantity=update_cart_quantity,
                update_cart_badge=update_cart_badge,
                switch_tab=switch_tab,
                show_checkout_page=show_checkout_page,
                refresh_cart=refresh_cart
            )
            page.update()
        elif tab == "orders":
            render_orders()
        elif tab == "profile":
            render_profile()

    def render_food():
        update_cart_badge()
        content_container.content = food_view(
            db=db,
            user_id=user_id,
            update_cart_badge=update_cart_badge,
            add_to_cart=add_to_cart,
            page=page
        )
        page.update()

    def render_orders():
        update_cart_badge()
        content_container.content = order_history_widget(page, switch_tab, update_cart_badge)
        page.update()

    def render_profile():
        content_container.content = profile_view_widget(page, switch_tab)
        update_cart_badge()
        page.update()

    def show_checkout_page():
        # Build cart_items and total for checkout
        cart_items_list = []
        total = 0
        for cart_item in get_user_cart(db, user_id):
            food = db.query(FoodItem).filter(FoodItem.id == cart_item.food_id).first()
            if not food:
                continue
            quantity = cart_item.quantity
            subtotal = food.price * quantity
            total += subtotal
            cart_items_list.append({
                "quantity": quantity,
                "name": food.name,
                "subtotal": subtotal
            })
        show_checkout["value"] = True
        show_checkout["cart_items"] = cart_items_list
        show_checkout["total"] = total
        render_main_content()

    # --- INITIAL RENDER ---
    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                content_container,
                footer
            ], expand=True, spacing=0),
            width=400,
            expand=True,
            padding=0,
            bgcolor="white"
        )
    )
    render_main_content()
    update_cart_badge()