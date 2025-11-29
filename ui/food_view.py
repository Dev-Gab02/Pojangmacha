import os
import flet as ft
from models.food_item import FoodItem

def food_view(
    db,
    user_id,
    update_cart_badge,
    add_to_cart,
    page,
):
    items_column = ft.Column(spacing=10)

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

    def load_items(category="All"):
        show_skeleton_loader(items_column)
        import time
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
                        ], spacing=3, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE,
                            icon_color="blue700",
                            icon_size=28,
                            tooltip="Add to cart",
                            on_click=lambda e, it=item: add_to_cart_directly(it)
                        )
                    ], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
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

    def search_items(keyword):
        show_skeleton_loader(items_column)
        import time
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
                            ], spacing=3, expand=True),
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE,
                                icon_color="blue700",
                                icon_size=28,
                                tooltip="Add to cart",
                                on_click=lambda e, it=item: add_to_cart_directly(it)
                            )
                        ], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )
                items_column.controls.append(item_card)
        page.update()

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

    # --- UI Layout ---
    food_column = ft.Column([
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
                ft.Container(height=8),
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

    load_items()  # Initial load

    return food_column