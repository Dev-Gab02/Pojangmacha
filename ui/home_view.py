# ui/home_view.py
import flet as ft
from core.db import SessionLocal
from models.food_item import FoodItem

def home_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Pojangmacha - Home"

    # Header
    header = ft.Row(
        [
            ft.Text("Pojangmacha Home", size=24, weight="bold"),
            ft.ElevatedButton("View Orders", on_click=lambda e: show_orders_snackbar(e, page))
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    # Items list
    items_column = ft.Column(scroll=ft.ScrollMode.AUTO)
    for item in db.query(FoodItem).all():
        items_column.controls.append(
            ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Image(src=item.image, width=100, height=100),
                        ft.Column([
                            ft.Text(item.name, weight="bold", size=18),
                            ft.Text(item.description or ""),
                            ft.Text(f"₱{item.price:.2f}", color="green"),
                            ft.ElevatedButton("Add to Cart", on_click=lambda e, it=item: show_cart_added(e, page, it))
                        ])
                    ])
                )
            )
        )

    page.clean()
    page.add(
        ft.Column([
            header,
            ft.Divider(),
            items_column
        ])
    )

def show_orders_snackbar(e, page):
    """Snackbar shown when View Orders button clicked."""
    page.snack_bar = ft.SnackBar(ft.Text("Orders page not implemented"), open=True)
    page.update()

def show_cart_added(e, page, item):
    """Snackbar for adding item to cart."""
    page.snack_bar = ft.SnackBar(ft.Text(f"{item.name} added to cart"), open=True)
    page.update()