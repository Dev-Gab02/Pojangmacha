import flet as ft
import os
from models.food_item import FoodItem
from models.cart import Cart

def cart_view(
    db,
    user_id,
    get_user_cart,
    remove_from_cart,
    update_cart_quantity,
    update_cart_badge,
    switch_tab,
    show_checkout_page,
    refresh_cart
):
    cart_items = get_user_cart(db, user_id)
    cart_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    total = 0

    def update_quantity(cart_item_id, change):
        cart_item = db.query(Cart).filter(Cart.id == cart_item_id).first()
        if cart_item:
            new_quantity = cart_item.quantity + change
            if new_quantity <= 0:
                remove_from_cart(db, cart_item_id)
            else:
                update_cart_quantity(db, cart_item_id, new_quantity)
        update_cart_badge()
        refresh_cart()
        # You may want to trigger a re-render from home_view

    def remove_item(cart_item_id):
        remove_from_cart(db, cart_item_id)
        update_cart_badge()
        refresh_cart()
        # You may want to trigger a re-render from home_view

    if not cart_items:
        cart_column.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SHOPPING_CART, size=80, color="grey"),
                    ft.Text("Hungry?", size=28, weight="bold", color="black"),
                    ft.Text("You haven't added anything to your cart!", size=14, color="grey700"),
                    ft.Container(height=2),
                    ft.ElevatedButton(
                        "Browse",
                        on_click=lambda e: switch_tab("food"),
                        style=ft.ButtonStyle(
                            bgcolor="#FEB23F",
                            color="white"
                        ),
                        width=120,
                        height=35
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10),
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

            # --- BUTTONS LOGIC ---
            if quantity == 1:
                button_row = ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.DELETE,
                        icon_color="red",
                        icon_size=18,
                        tooltip="Remove",
                        on_click=lambda e, cid=cart_item.id: remove_item(cid)
                    ),
                    ft.Text(str(quantity), size=14, weight="bold"),
                    ft.IconButton(
                        icon=ft.Icons.ADD,
                        icon_size=16,
                        on_click=lambda e, cid=cart_item.id: update_quantity(cid, 1),
                        tooltip="Increase"
                    ),
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
            else:
                button_row = ft.Row([
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
                ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)

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
                            button_row
                        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
                    )
                )
            )

        # Add "Add more items" button only once, after all cart items
        cart_column.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.ADD, color="black", size=20),
                    ft.Text("Add more items", size=14, weight="bold", color="black"),
                ], spacing=6, alignment=ft.MainAxisAlignment.START),
                padding=ft.padding.only(left=4, top=0, bottom=0),
                on_click=lambda e: switch_tab("food"),
                ink=True
            )
        )

    return ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("Cart", size=20, weight="bold", color="black"),
                    padding=ft.padding.only(top=15, left=15, right=15, bottom=8)
                ),
                ft.Divider(height=1, color="grey300", thickness=1)
            ], spacing=0),
            bgcolor="white",
            padding=ft.padding.only(left=0, right=0, top=0, bottom=0)
        ),
        ft.Container(
            content=cart_column,
            expand=True,
            padding=10,
            bgcolor="grey100"
        ),
        ft.Container(
            content=ft.Column([
                ft.Divider(height=1, color="grey300", thickness=1),
                ft.ElevatedButton(
                    "Review Payment",
                    on_click=lambda e: show_checkout_page(),
                    disabled=len(cart_items) == 0,
                    style=ft.ButtonStyle(
                        bgcolor="#FEB23F" if len(cart_items) > 0 else "grey",
                        color="white"
                    ),
                    width=350,
                    height=45
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            bgcolor="white",
            padding=ft.padding.only(left=0, right=0, top=0, bottom=12),
            shadow=ft.BoxShadow(blur_radius=10, color="grey300")
        )
    ], expand=True, spacing=0)