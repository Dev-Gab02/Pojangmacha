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
from ui.profile_view import profile_view_widget
from ui.order_history_view import order_history_widget

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

    # --- MAIN CONTENT RENDERERS ---
    def render_main_content():
        tab = nav_state["tab"]
        if tab == "food":
            render_food()
        elif tab == "cart":
            render_cart()
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
                    ft.Image(
                        src="assets/brand.png",
                        width=180,
                        height=60,
                        fit=ft.ImageFit.CONTAIN
                    ),
                    ft.Text(
                        "Order your favorite food!",
                        size=11,
                        color="grey600",
                        italic=True
                    ),
                    ft.Container(height=12),
                    ft.TextField(
                        label="Search food items...",
                        on_change=lambda e: search_items(e.control.value),
                        prefix_icon=ft.Icons.SEARCH,
                        text_size=13,
                        height=50,
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

    # --- CART TAB ---
    def render_cart():
        update_cart_badge()
        cart_items = get_user_cart(db, user_id)
        cart_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        total = 0
        if not cart_items:
            cart_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, size=80, color="grey"),
                        ft.Text("Your cart is empty", size=16, color="grey"),
                        ft.TextButton(
                            "Start Shopping",
                            on_click=lambda e: switch_tab("food")
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40,
                    alignment=ft.alignment.center
                )
            )
        else:
            for cart_item in cart_items:
                food = db.query(FoodItem).filter(FoodItem.id == cart_item.food_id).first()
                if not food:
                    remove_from_cart(db, cart_item.id)
                    continue
                quantity = cart_item.quantity
                subtotal = food.price * quantity
                total += subtotal
                cart_column.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Row([
                                ft.Image(
                                    src=food.image,
                                    width=60,
                                    height=60,
                                    fit=ft.ImageFit.COVER,
                                    border_radius=8
                                ) if food.image and os.path.exists(food.image) else ft.Container(
                                    width=60,
                                    height=60,
                                    bgcolor="grey300",
                                    border_radius=8
                                ),
                                ft.Column([
                                    ft.Text(food.name, weight="bold", size=14),
                                    ft.Text(f"₱{food.price:.2f} each", size=11, color="grey700"),
                                    ft.Text(f"Subtotal: ₱{subtotal:.2f}", size=12, weight="bold", color="green"),
                                ], spacing=2, expand=True),
                                ft.Column([
                                    ft.Row([
                                        ft.IconButton(
                                            icon=ft.Icons.REMOVE,
                                            icon_size=16,
                                            on_click=lambda e, cid=cart_item.id: update_quantity(cid, -1),
                                            tooltip="Decrease"
                                        ),
                                        ft.Text(str(quantity), size=14, weight="bold"),
                                        ft.IconButton(
                                            icon=ft.Icons.ADD,
                                            icon_size=16,
                                            on_click=lambda e, cid=cart_item.id: update_quantity(cid, 1),
                                            tooltip="Increase"
                                        ),
                                    ], spacing=2),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color="red",
                                        icon_size=18,
                                        tooltip="Remove",
                                        on_click=lambda e, cid=cart_item.id: remove_item(cid)
                                    )
                                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                            ], spacing=8, alignment=ft.MainAxisAlignment.START)
                        )
                    )
                )
        # Header (like profile)
        content_container.content = ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Text("Cart", size=20, weight="bold", color="black"),
                    ft.Divider(height=1, color="grey300", thickness=1)
                ], spacing=0),
                bgcolor="white",
                padding=ft.padding.only(left=15, right=15, top=15, bottom=8)
            ),
            ft.Container(
                content=cart_column,
                expand=True,
                padding=10,
                bgcolor="grey100"
            ),
            ft.Container(
                content=ft.Column([
                    ft.Divider(),
                    ft.Row([
                        ft.Text(f"Items: {len(cart_items)}", size=14),
                        ft.Text(f"Total: ₱{total:.2f}", size=18, weight="bold"),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.ElevatedButton(
                        "Checkout",
                        on_click=lambda e: checkout(),
                        disabled=len(cart_items) == 0,
                        style=ft.ButtonStyle(
                            bgcolor="green700" if len(cart_items) > 0 else "grey",
                            color="white"
                        ),
                        width=350,
                        height=45
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                bgcolor="white",
                padding=12,
                shadow=ft.BoxShadow(blur_radius=10, color="grey300")
            )
        ], expand=True, spacing=0)
        page.update()

    def update_quantity(cart_item_id, change):
        cart_item = db.query(Cart).filter(Cart.id == cart_item_id).first()
        if cart_item:
            new_quantity = cart_item.quantity + change
            if new_quantity <= 0:
                remove_from_cart(db, cart_item_id)
            else:
                update_cart_quantity(db, cart_item_id, new_quantity)
        update_cart_badge()
        render_cart()

    def remove_item(cart_item_id):
        remove_from_cart(db, cart_item_id)
        update_cart_badge()
        render_cart()

    def checkout():
        cart_items = get_user_cart(db, user_id)
        if not cart_items:
            page.snack_bar = ft.SnackBar(ft.Text("Cart is empty!"), open=True)
            page.update()
            return
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            page.snack_bar = ft.SnackBar(ft.Text("User not found"), open=True)
            page.go("/login")
            return
        total = 0
        for cart_item in cart_items:
            food = db.query(FoodItem).filter(FoodItem.id == cart_item.food_id).first()
            if food:
                total += food.price * cart_item.quantity
        new_order = Order(user_id=user.id, total_price=total, status="Pending", created_at=datetime.utcnow())
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        for cart_item in cart_items:
            food = db.query(FoodItem).filter(FoodItem.id == cart_item.food_id).first()
            if food:
                order_item = OrderItem(
                    order_id=new_order.id,
                    food_id=cart_item.food_id,
                    quantity=cart_item.quantity,
                    subtotal=food.price * cart_item.quantity
                )
                db.add(order_item)
        db.commit()
        db.query(Cart).filter(Cart.user_id == user_id).delete()
        db.commit()
        db.add(AuditLog(user_email=user.email, action=f"Placed order #{new_order.id}"))
        db.commit()
        update_cart_badge()
        page.snack_bar = ft.SnackBar(
            ft.Text(f"✅ Order #{new_order.id} placed successfully!"),
            bgcolor=ft.Colors.GREEN,
            open=True
        )
        nav_state["tab"] = "orders"
        render_main_content()

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