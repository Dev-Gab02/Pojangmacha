import os
import flet as ft
from core.db import SessionLocal
from models.food_item import FoodItem
from models.user import User
from models.order import Order, OrderItem
from models.cart import Cart
from models.audit_log import AuditLog
from core.cart_service import get_user_cart, add_to_cart, update_cart_quantity, remove_from_cart, get_cart_count
from datetime import datetime

def home_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Pojangmacha - Home"

    # Get logged-in user
    user_data = page.session.get("user")
    if not user_data:
        page.snack_bar = ft.SnackBar(ft.Text("Please log in first."), open=True)
        page.go("/login")
        return
    
    user_id = user_data.get("id")

    items_column = ft.Column(spacing=10)
    
    if not page.session.contains_key("recent_searches"):
        page.session.set("recent_searches", [])

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

    def update_cart_badge():
        """Update cart badge from database"""
        total_items = get_cart_count(db, user_id)
        print(f"DEBUG: Updating badge. Total items: {total_items}")
        if total_items > 0:
            cart_count_text.value = str(total_items)
            cart_badge_container.visible = True
        else:
            cart_count_text.value = ""
            cart_badge_container.visible = False
        page.update()

    def add_to_cart_directly(item):
        """Add item to cart (stored in database)"""
        print(f"✅ DEBUG: Adding {item.name} to cart")
        
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

    def load_items(category="All"):
        print(f"DEBUG: Loading items for category: {category}")
        items_column.controls.clear()
        query = db.query(FoodItem)
        if category != "All":
            query = query.filter(FoodItem.category == category)
        items = query.all()
        print(f"DEBUG: Found {len(items)} items")
        
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
                                style=ft.ButtonStyle(
                                    bgcolor="blue700",
                                    color="white"
                                ),
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

    def update_quantity(cart_item_id, change):
        """Update cart item quantity in database"""
        cart_item = db.query(Cart).filter(Cart.id == cart_item_id).first()
        if cart_item:
            new_quantity = cart_item.quantity + change
            if new_quantity <= 0:
                remove_from_cart(db, cart_item_id)
            else:
                update_cart_quantity(db, cart_item_id, new_quantity)
        
        update_cart_badge()
        show_cart_view()

    def remove_item(cart_item_id):
        """Remove item from cart"""
        remove_from_cart(db, cart_item_id)
        update_cart_badge()
        show_cart_view()

    def checkout():
        """Checkout cart items"""
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
        page.go("/orders")

    def show_cart_view():
        """Show cart with items from database"""
        cart_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        cart_items = get_user_cart(db, user_id)
        
        total = 0
        
        if not cart_items:
            cart_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SHOPPING_CART_OUTLINED, size=80, color="grey"),
                        ft.Text("Your cart is empty", size=16, color="grey"),
                        ft.TextButton(
                            "Start Shopping",
                            on_click=lambda e: home_view(page)
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
        
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: home_view(page)),
                            ft.Text("Your Cart", size=20, weight="bold"),
                        ]),
                        padding=10,
                        bgcolor="white"
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
                ], expand=True, spacing=0),
                width=400,
                height=700,
                padding=0
            )
        )
        page.update()

    def search_items(keyword):
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
                                    style=ft.ButtonStyle(
                                        bgcolor="blue700",
                                        color="white"
                                    ),
                                    height=35
                                )
                            ], spacing=3, expand=True)
                        ], spacing=8)
                    )
                )
                items_column.controls.append(item_card)
        page.update()

    def show_search_view():
        search_field = ft.TextField(
            label="Search food items...",
            width=350,
            autofocus=True,
            prefix_icon=ft.Icons.SEARCH,
            on_submit=lambda e: perform_search(e.control.value)
        )
        
        recent_searches = page.session.get("recent_searches") or []
        recent_column = ft.Column(spacing=6)
        recent_container = ft.Container()
        
        def remove_recent_search(search_term):
            recent = page.session.get("recent_searches") or []
            if search_term in recent:
                recent.remove(search_term)
                page.session.set("recent_searches", recent)
            show_search_view()
        
        def rebuild_recent_searches():
            recent_column.controls.clear()
            recent_searches = page.session.get("recent_searches") or []
            
            if recent_searches:
                for search_term in recent_searches[:5]:
                    recent_column.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.HISTORY, size=18, color="grey"),
                                ft.Text(search_term, size=13, expand=True),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=18,
                                    icon_color="grey",
                                    tooltip="Remove",
                                    on_click=lambda e, term=search_term: remove_recent_search(term)
                                ),
                            ], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=8,
                            on_click=lambda e, term=search_term: perform_search(term),
                            ink=True,
                            border_radius=8,
                            bgcolor="grey100"
                        )
                    )
        
        rebuild_recent_searches()
        
        search_results_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        
        def perform_search(keyword):
            if keyword and keyword.strip():
                recent = page.session.get("recent_searches") or []
                if keyword not in recent:
                    recent.insert(0, keyword)
                    recent = recent[:10]
                    page.session.set("recent_searches", recent)
                
                search_field.value = keyword
                search_results_column.controls.clear()
                
                results = db.query(FoodItem).filter(FoodItem.name.ilike(f"%{keyword}%")).all()
                if not results:
                    search_results_column.controls.append(
                        ft.Container(
                            content=ft.Text("No items found", size=14, color="grey"),
                            padding=20,
                            alignment=ft.alignment.center
                        )
                    )
                else:
                    for item in results:
                        search_results_column.controls.append(
                            ft.Card(
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
                        )
                
                recent_container.visible = False
                page.update()
        
        footer = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.IconButton(icon=ft.Icons.RESTAURANT_MENU, tooltip="Food", on_click=lambda e: home_view(page)),
                    ft.Text("Food", size=10, text_align=ft.TextAlign.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                
                ft.Column([
                    ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Search", icon_color="blue700"),
                    ft.Text("Search", size=10, text_align=ft.TextAlign.CENTER, color="blue700")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                
                ft.Column([
                    ft.IconButton(icon=ft.Icons.HISTORY, tooltip="Orders", on_click=lambda e: page.go("/orders")),
                    ft.Text("Orders", size=10, text_align=ft.TextAlign.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                
                ft.Column([
                    ft.IconButton(icon=ft.Icons.PERSON, tooltip="Profile", on_click=lambda e: page.go("/profile")),
                    ft.Text("Profile", size=10, text_align=ft.TextAlign.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
            bgcolor="white",
            padding=ft.padding.symmetric(vertical=6),
            border=ft.border.only(top=ft.BorderSide(1, "grey300")),
            margin=0,
            height=60
        )
        
        recent_container.content = ft.Column([
            ft.Text("Recent Searches", size=14, weight="bold") if len(recent_searches) > 0 else ft.Container(),
            recent_column
        ], spacing=8)
        recent_container.padding = 10
        recent_container.visible = len(recent_searches) > 0
        
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: home_view(page)),
                            search_field,
                        ], spacing=8),
                        padding=10,
                        bgcolor="white"
                    ),
                    recent_container,
                    ft.Container(
                        content=search_results_column,
                        expand=True,
                        padding=10,
                        bgcolor="grey100"
                    ),
                    footer
                ], expand=True, spacing=0),
                width=400,
                height=700,
                padding=0
            )
        )
        page.update()

    # Categories - DEFINE BEFORE USE
    categories = ["All", "Noodles", "K-Food", "Korean Bowls", "Combo", "Toppings", "Drinks"]
    category_row = ft.Row(
        [
            ft.ElevatedButton(
                cat,
                on_click=lambda e, c=cat: load_items(c),
                style=ft.ButtonStyle(padding=8)
            ) for cat in categories
        ],
        wrap=True,
        spacing=6
    )

    # Footer
    footer = ft.Container(
        content=ft.Row([
            ft.Column([
                ft.IconButton(icon=ft.Icons.RESTAURANT_MENU, tooltip="Food", icon_color="blue700"),
                ft.Text("Food", size=10, text_align=ft.TextAlign.CENTER, color="blue700")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Search", on_click=lambda e: show_search_view()),
                ft.Text("Search", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(icon=ft.Icons.HISTORY, tooltip="Orders", on_click=lambda e: page.go("/orders")),
                ft.Text("Orders", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(icon=ft.Icons.PERSON, tooltip="Profile", on_click=lambda e: page.go("/profile")),
                ft.Text("Profile", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        bgcolor="white",
        padding=ft.padding.symmetric(vertical=6),
        border=ft.border.only(top=ft.BorderSide(1, "grey300")),
        margin=0,
        height=60
    )

    # Cart button
    cart_button = ft.Stack([
        ft.IconButton(
            icon=ft.Icons.SHOPPING_CART,
            tooltip="View Cart",
            on_click=lambda e: show_cart_view()
        ),
        cart_badge_container
    ], width=50, height=50)

    # Main layout
    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.TextField(
                            label="Search...",
                            width=260,
                            on_change=lambda e: search_items(e.control.value),
                            prefix_icon=ft.Icons.SEARCH,
                            text_size=13,
                            height=45
                        ),
                        cart_button
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10,
                    bgcolor="white"
                ),
                
                # Categories
                ft.Container(
                    content=ft.Column([
                        ft.Text("Categories", size=14, weight="bold"),
                        category_row
                    ], spacing=8),
                    padding=10,
                    bgcolor="white"
                ),
                
                # Items list (scrollable)
                ft.Container(
                    content=ft.Column([items_column], scroll=ft.ScrollMode.AUTO),
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

    # Load items and update badge
    load_items()
    update_cart_badge()