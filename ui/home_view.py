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
from ui.cart_view import cart_view  # <-- Import your new cart view

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
    items_column = ft.Column(spacing=10)
    cart_count_text = ft.Text("", color="white", size=10, weight="bold")
    cart_badge_container = ft.Container(
        content=cart_count_text,
        bgcolor="red",
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=6, vertical=3),
        right=5,
        top=5,
        visible=False
    )
    content_container = ft.Container(expand=True)

    # --- SKELETON LOADER ---
    def create_skeleton_card():
        return ft.Card(
            content=ft.Container(
                padding=10,
                content=ft.Row([
                    ft.Container(width=80, height=80, bgcolor="grey300", border_radius=8),
                    ft.Column([
                        ft.Container(width=150, height=16, bgcolor="grey300", border_radius=4),
                        ft.Container(width=120, height=12, bgcolor="grey300", border_radius=4),
                        ft.Container(width=80, height=14, bgcolor="grey300", border_radius=4),
                    ], spacing=6, expand=True)
                ], spacing=8)
            )
        )
    def show_skeleton_loader(container):
        container.controls.clear()
        for _ in range(5):
            container.controls.append(create_skeleton_card())
        page.update()

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

    # --- LOAD ITEMS ---
    def load_items(category="All"):
        show_skeleton_loader(items_column)
        time.sleep(0.1)
        items_column.controls.clear()
        query = db.query(FoodItem)
        if category != "All":
            query = query.filter(FoodItem.category == category)
        items = query.all()
        for item in items:
            item_card = ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Image(
                            src=item.image,
                            width=80,
                            height=80,
                            fit=ft.ImageFit.COVER,
                            border_radius=8
                        ) if item.image and os.path.exists(item.image) else ft.Container(
                            width=80,
                            height=80,
                            bgcolor="grey300",
                            border_radius=8
                        ),
                        ft.Column([
                            ft.Text(item.name, weight="bold", size=14),
                            ft.Text(item.description[:30] + "..." if len(item.description) > 30 else item.description, size=10, color="grey700"),
                            ft.Text(f"₱{item.price:.2f}", color="green", size=14, weight="bold"),
                            ft.ElevatedButton(
                                "Add",
                                icon=ft.Icons.ADD_SHOPPING_CART,
                                on_click=lambda e, it=item: add_to_cart_directly(it),
                                style=ft.ButtonStyle(bgcolor="blue700", color="white"),
                                height=35
                            )
                        ], spacing=3, expand=True)
                    ], spacing=8)
                )
            )
            items_column.controls.append(item_card)
        if not items_column.controls:
            items_column.controls.append(
                ft.Container(
                    content=ft.Text("No items in this category yet.", size=14, color="grey", italic=True),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        page.update()

    def add_to_cart_directly(item):
        add_to_cart(db, user_id, item.id, quantity=1)
        update_cart_badge()
        page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color="white"),
                ft.Text(f"✅ {item.name} added to cart!", color="white", weight="bold")
            ]),
            bgcolor="green700",
            duration=2000
        )
        page.snack_bar.open = True
        page.update()

    # --- SEARCH ---
    def search_items(keyword):
        show_skeleton_loader(items_column)
        time.sleep(0.1)
        items_column.controls.clear()
        if not keyword.strip():
            load_items()
            return
        results = db.query(FoodItem).filter(FoodItem.name.ilike(f"%{keyword}%")).all()
        if not results:
            items_column.controls.append(
                ft.Container(
                    content=ft.Text("No items found", size=14, color="grey"),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for item in results:
                item_card = ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Row([
                            ft.Image(
                                src=item.image,
                                width=80,
                                height=80,
                                fit=ft.ImageFit.COVER,
                                border_radius=8
                            ) if item.image and os.path.exists(item.image) else ft.Container(
                                width=80,
                                height=80,
                                bgcolor="grey300",
                                border_radius=8
                            ),
                            ft.Column([
                                ft.Text(item.name, weight="bold", size=14),
                                ft.Text(item.description[:30] + "...", size=10, color="grey700"),
                                ft.Text(f"₱{item.price:.2f}", color="green", size=14, weight="bold"),
                                ft.ElevatedButton(
                                    "Add",
                                    icon=ft.Icons.ADD_SHOPPING_CART,
                                    on_click=lambda e, it=item: add_to_cart_directly(it),
                                    style=ft.ButtonStyle(bgcolor="blue700", color="white"),
                                    height=35
                                )
                            ], spacing=3, expand=True)
                        ], spacing=8)
                    )
                )
                items_column.controls.append(item_card)
        page.update()

    # --- CATEGORY ROW ---
    categories = ["All", "Noodles", "K-Food", "Korean Bowls", "Combo", "Toppings", "Drinks"]
    category_row = ft.Row(
        [
            ft.ElevatedButton(
                cat,
                on_click=lambda e, c=cat: load_items(c),
                style=ft.ButtonStyle(
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    shape=ft.RoundedRectangleBorder(radius=20),
                    bgcolor="blue700",
                    color="white"
                )
            ) for cat in categories
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO
    )

    # --- FOOTER NAVIGATION ---
    def nav_icon(icon, label, tab, on_click, active_tab):
        return ft.Column([
            ft.IconButton(
                icon=icon,
                tooltip=label,
                icon_color="blue700" if tab == active_tab else "black",
                on_click=on_click
            ),
            ft.Text(label, size=10, text_align=ft.TextAlign.CENTER, color="blue700" if tab == active_tab else "black")
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)

    def switch_tab(tab):
        nav_state["tab"] = tab
        show_checkout["value"] = False
        render_main_content()
        page.update()

    footer = ft.Container(
        content=ft.Row([
            nav_icon(ft.Icons.RESTAURANT_MENU, "Food", "food", lambda e: switch_tab("food"), lambda: nav_state["tab"]),
            ft.Stack([
                nav_icon(ft.Icons.SHOPPING_CART, "Cart", "cart", lambda e: switch_tab("cart"), lambda: nav_state["tab"]),
                cart_badge_container
            ], width=50, height=50),
            nav_icon(ft.Icons.HISTORY, "Orders", "orders", lambda e: switch_tab("orders"), lambda: nav_state["tab"]),
            nav_icon(ft.Icons.PERSON, "Profile", "profile", lambda e: switch_tab("profile"), lambda: nav_state["tab"]),
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
            # Use the new cart_view
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

    # --- FOOD TAB ---
    def render_food():
        update_cart_badge()
        content_container.content = ft.Column([
            # Header
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Image(
                            src="assets/brand.png",
                            width=160,
                            height=40,
                            fit=ft.ImageFit
                        ),
                        padding=0,
                        margin=0
                    ),
                    ft.Container(
                        content=ft.Text(
                            "Order your favorite food!",
                            size=11,
                            color="grey600",
                            italic=True
                        ),
                        padding=0,
                        margin=0
                    ),
                    ft.Container(height=20),
                    ft.TextField(
                        label="Search food items...",
                        on_change=lambda e: search_items(e.control.value),
                        prefix_icon=ft.Icons.SEARCH,
                        text_size=13,
                        height=40,
                        border_radius=8
                    )
                ], spacing=0),
                padding=ft.padding.only(left=10, right=10, top=8),
                bgcolor="white"
            ),
            ft.Container(
                content=category_row,
                padding=10,
                bgcolor="white",
                height=60
            ),
            ft.Container(
                content=ft.Column([items_column], scroll=ft.ScrollMode.AUTO),
                expand=True,
                padding=10,
                bgcolor="grey100"
            ),
        ], expand=True, spacing=0)
        load_items()
        page.update()

    # --- ORDER HISTORY TAB ---
    def render_orders():
        update_cart_badge()
        content_container.content = order_history_widget(page, switch_tab)
        page.update()

    # --- PROFILE TAB ---
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
            height=700,
            padding=0,
            bgcolor="white"
        )
    )
    render_main_content()
    update_cart_badge()