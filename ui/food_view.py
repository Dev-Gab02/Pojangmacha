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
    items_column = ft.Column(spacing=3)
    
    # Filter state
    filter_state = {
        "sort_by": None,  # "price_low", "price_high", "name_az"
        "price_range": None,  # "all", "0-50", "51-100", "101-150", "151+"
        "active_count": 0
    }
    
    # Filter badge
    filter_badge = ft.Container(
        content=ft.Text("0", color="white", size=10, weight="bold"),
        bgcolor="#E9190A",
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=6, vertical=3),
        right=-5,
        top=-5,
        visible=False
    )
    
    # Active filters display
    active_filters_row = ft.Row(
        spacing=8,
        wrap=True,
        visible=False
    )

    def add_to_cart_directly(item):
        add_to_cart(db, user_id, item.id, quantity=1)
        update_cart_badge()
        page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color="white"),
                ft.Text(f"{item.name} added to cart!", color="white", weight="bold")
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
                    ft.Container(
                        width=80, 
                        height=80, 
                        bgcolor="grey300",
                        border_radius=8,
                        border=ft.border.all(1, "grey300")
                    ),
                    ft.Column([
                        ft.Container(width=150, height=16, bgcolor="grey300", border_radius=4),
                        ft.Container(width=120, height=12, bgcolor="grey400", border_radius=4),
                        ft.Container(width=80, height=14, bgcolor="grey300", border_radius=4),
                    ], spacing=6, expand=True),
                    ft.Container(width=28, height=28, bgcolor="grey300", border_radius=14)
                ], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                bgcolor='white', 
                border_radius=12
            )
        )

    def show_skeleton_loader(container):
        container.controls.clear()
        for _ in range(5):
            container.controls.append(create_skeleton_card())
        page.update()

    def update_filter_badge():
        count = 0
        if filter_state["sort_by"]:
            count += 1
        if filter_state["price_range"] and filter_state["price_range"] != "all":
            count += 1
        
        filter_state["active_count"] = count
        filter_badge.content.value = str(count)
        filter_badge.visible = count > 0
        page.update()

    def update_active_filters_display():
        active_filters_row.controls.clear()
        
        if filter_state["sort_by"]:
            sort_label = {
                "price_low": "Price: Low to High",
                "price_high": "Price: High to Low",
                "name_az": "Name: A-Z"
            }.get(filter_state["sort_by"], "")
            
            active_filters_row.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(sort_label, size=11, color="white"),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_size=14,
                            icon_color="white",
                            on_click=lambda e: clear_sort_filter(),
                            padding=0,
                            width=18,
                            height=18
                        )
                    ], spacing=4),
                    bgcolor="#FEB23F",
                    border_radius=15,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4)
                )
            )
        
        if filter_state["price_range"] and filter_state["price_range"] != "all":
            price_label = {
                "0-50": "₱0 - ₱50",
                "51-100": "₱51 - ₱100",
                "101-150": "₱101 - ₱150",
                "151+": "₱151+"
            }.get(filter_state["price_range"], "")
            
            active_filters_row.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(price_label, size=11, color="white"),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_size=14,
                            icon_color="white",
                            on_click=lambda e: clear_price_filter(),
                            padding=0,
                            width=18,
                            height=18
                        )
                    ], spacing=4),
                    bgcolor="#FEB23F",
                    border_radius=15,
                    padding=ft.padding.symmetric(horizontal=10, vertical=4)
                )
            )
        
        active_filters_row.visible = len(active_filters_row.controls) > 0
        page.update()

    def clear_sort_filter():
        filter_state["sort_by"] = None
        update_filter_badge()
        update_active_filters_display()
        load_items()

    def clear_price_filter():
        filter_state["price_range"] = None
        update_filter_badge()
        update_active_filters_display()
        load_items()

    def apply_filters_and_sort(items):
        # Apply price range filter
        if filter_state["price_range"] and filter_state["price_range"] != "all":
            if filter_state["price_range"] == "0-50":
                items = [item for item in items if item.price <= 50]
            elif filter_state["price_range"] == "51-100":
                items = [item for item in items if 51 <= item.price <= 100]
            elif filter_state["price_range"] == "101-150":
                items = [item for item in items if 101 <= item.price <= 150]
            elif filter_state["price_range"] == "151+":
                items = [item for item in items if item.price >= 151]
        
        # Apply sorting
        if filter_state["sort_by"] == "price_low":
            items = sorted(items, key=lambda x: x.price)
        elif filter_state["sort_by"] == "price_high":
            items = sorted(items, key=lambda x: x.price, reverse=True)
        elif filter_state["sort_by"] == "name_az":
            items = sorted(items, key=lambda x: x.name.lower())
        
        return items

    def load_items(category="All"):
        show_skeleton_loader(items_column)
        import time
        time.sleep(0.1)
        items_column.controls.clear()
        query = db.query(FoodItem)
        if category != "All":
            query = query.filter(FoodItem.category == category)
        items = query.all()
        
        # Apply filters and sorting
        items = apply_filters_and_sort(items)
        
        for item in items:
            item_card = ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Row([
                        ft.Container(
                            content=ft.Image(
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
                            border=ft.border.all(1, "grey300"),
                            border_radius=8
                        ),
                        ft.Column([
                            ft.Text(item.name, weight="bold", size=14, color="black"),
                            ft.Text(item.description[:30] + "..." if len(item.description) > 30 else item.description, size=10, color="grey700"),
                            # Show stock and price row
                            ft.Row([
                                ft.Text(f"Stock: {item.stock}", size=12, color="blue", weight="bold"),
                                ft.Text(f"₱{item.price:.2f}", color="green", size=14, weight="bold"),
                            ], spacing=12) if item.stock > 0 else ft.Text("Sold Out", color="red", size=13, weight="bold")
                        ], spacing=3, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE,
                            icon_color="#FEB23F" if item.stock > 0 else "grey400",
                            icon_size=28,
                            tooltip="Add to cart" if item.stock > 0 else "Out of stock",
                            on_click=lambda e, it=item: add_to_cart_directly(it) if it.stock > 0 else None,
                            disabled=item.stock <= 0
                        )
                    ], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    bgcolor='white',
                    border_radius=12
                )
            )
            items_column.controls.append(
                ft.Container(
                    content=item_card,
                    padding=ft.padding.symmetric(horizontal=10)
                )
            )
        if not items_column.controls:
            items_column.controls.append(
                ft.Container(
                    content=ft.Text("No items found.", size=14, color="grey", italic=True),
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
        
        # Apply filters and sorting
        results = apply_filters_and_sort(results)
        
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
                            ft.Container(
                                content=ft.Image(
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
                                border=ft.border.all(1, "grey300"),
                                border_radius=8
                            ),
                            ft.Column([
                                ft.Text(item.name, weight="bold", size=14, color="black"),
                                ft.Text(item.description[:30] + "..." if len(item.description) > 30 else item.description, size=10, color="grey700"),
                                # Show stock and price row
                                ft.Row([
                                    ft.Text(f"Stock: {item.stock}", size=12, color="blue", weight="bold"),
                                    ft.Text(f"₱{item.price:.2f}", color="green", size=14, weight="bold"),
                                ], spacing=12) if item.stock > 0 else ft.Text("Sold Out", color="red", size=13, weight="bold")
                            ], spacing=3, expand=True),
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE,
                                icon_color="#FEB23F" if item.stock > 0 else "grey400",
                                icon_size=28,
                                tooltip="Add to cart" if item.stock > 0 else "Out of stock",
                                on_click=lambda e, it=item: add_to_cart_directly(it) if it.stock > 0 else None,
                                disabled=item.stock <= 0
                            )
                        ], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        bgcolor='white',
                        border_radius=12
                    )
                )
                items_column.controls.append(
                    ft.Container(
                        content=item_card,
                        padding=ft.padding.symmetric(horizontal=10)
                    )
                )
        page.update()

    def open_filter_dialog():
        # State for selected buttons
        selected_sort = {"value": filter_state["sort_by"]}
        selected_price = {"value": filter_state["price_range"] if filter_state["price_range"] else "all"}
        
        # Sort by buttons (not scrollable, fixed row)
        def create_sort_button(label, value):
            def on_click(e):
                selected_sort["value"] = value
                # Update all sort buttons
                for ctrl in sort_buttons_row.controls:
                    if hasattr(ctrl, 'data') and ctrl.data == value:
                        ctrl.bgcolor = "#FEB23F"
                        ctrl.content.color = "black"
                    else:
                        ctrl.bgcolor = "#CCCCCC"
                        ctrl.content.color = "black"
                page.update()
            
            is_selected = selected_sort["value"] == value
            return ft.Container(
                content=ft.Text(label, size=12, weight="w500", color="black", text_align=ft.TextAlign.CENTER),
                bgcolor="#FEB23F" if is_selected else "#CCCCCC",
                border_radius=8,
                padding=ft.padding.symmetric(vertical=12),
                on_click=on_click,
                data=value,
                ink=True,
                expand=True,
                alignment=ft.alignment.center
            )
        
        sort_buttons_row = ft.Row([
            create_sort_button("Low to High", "price_low"),
            create_sort_button("High to Low", "price_high"),
            create_sort_button("A-Z", "name_az"),
        ], spacing=8)
        
        # Price range buttons (scrollable)
        def create_price_button(label, value):
            def on_click(e):
                selected_price["value"] = value
                # Update all price buttons
                for ctrl in price_buttons_row.controls:
                    if hasattr(ctrl, 'data') and ctrl.data == value:
                        ctrl.bgcolor = "#FEB23F"
                        ctrl.content.color = "black"
                    else:
                        ctrl.bgcolor = "#CCCCCC"
                        ctrl.content.color = "black"
                page.update()
            
            is_selected = selected_price["value"] == value
            return ft.Container(
                content=ft.Text(label, size=13, weight="w500", color="black"),
                bgcolor="#FEB23F" if is_selected else "#CCCCCC",
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                on_click=on_click,
                data=value,
                ink=True,
                alignment=ft.alignment.center
            )
        
        price_buttons_row = ft.Row([
            create_price_button("0-50", "0-50"),
            create_price_button("51-100", "51-100"),
            create_price_button("101-150", "101-150"),
            create_price_button("151+", "151+"),
            create_price_button("All Prices", "all"),
        ], spacing=8, scroll=ft.ScrollMode.AUTO)
        
        def apply_filters(e):
            filter_state["sort_by"] = selected_sort["value"]
            filter_state["price_range"] = selected_price["value"]
            update_filter_badge()
            update_active_filters_display()
            load_items()
            dialog.open = False
            page.update()
        
        def reset_filters(e):
            filter_state["sort_by"] = None
            filter_state["price_range"] = None
            update_filter_badge()
            update_active_filters_display()
            load_items()
            dialog.open = False
            page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                content=ft.Column([
                    # Sort By Section
                    ft.Text("Sort By:", weight="w600", size=14, color="black"),
                    ft.Container(height=8),
                    sort_buttons_row,
                    ft.Container(height=20),
                    
                    # Price Range Section
                    ft.Text("Price Range:", weight="w600", size=14, color="black"),
                    ft.Container(height=8),
                    price_buttons_row,
                ], spacing=0, tight=True),
                width=320,
                padding=ft.padding.symmetric(vertical=10)
            ),
            actions=[
                ft.Container(
                    content=ft.Text("RESET", size=13, weight="w600", color="black"),
                    border=ft.border.all(1, "black"),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=40, vertical=14),
                    on_click=reset_filters,
                    ink=True
                ),
                ft.Container(
                    content=ft.Text("APPLY", size=13, weight="w600", color="black"),
                    bgcolor="#FEB23F",
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=40, vertical=14),
                    on_click=apply_filters,
                    ink=True
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            actions_padding=ft.padding.only(left=20, right=20, bottom=10, top=0),
            bgcolor="#E8E8E8",
            shape=ft.RoundedRectangleBorder(radius=15) 
        )
        
        page.overlay.append(dialog)
        dialog.open = True
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
                    bgcolor="#FEB23F",
                    color="black"
                )
            ) for cat in categories
        ],
        spacing=8,
        scroll=ft.ScrollMode.AUTO
    )

    search_field = ft.TextField(
        label="Search food items...",
        on_change=lambda e: search_items(e.control.value),
        prefix_icon=ft.Icons.SEARCH,
        text_size=13,
        height=40,
        border_radius=8,
        expand=True
    )

    filter_button = ft.Stack([
        ft.IconButton(
            icon=ft.Icons.FILTER_LIST,
            icon_color="#FEB23F",
            icon_size=24,
            tooltip="Filter & Sort",
            on_click=lambda e: open_filter_dialog(),
        ),
        filter_badge
    ])

    # --- UI Layout ---
    food_column = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Image(
                        src="assets/brand.png",
                        width=220,
                        height=50,
                        fit=ft.ImageFit.CONTAIN
                    ),
                    padding=0,
                    margin=0
                ),
                ft.Container(height=8),
                ft.Row([
                    search_field,
                    filter_button
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=0),
            padding=ft.padding.only(left=10, right=10, top=8),
            bgcolor="white"
        ),
        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=category_row,
                    padding=10,
                    height=60
                ),
                ft.Column([items_column], scroll=ft.ScrollMode.AUTO, expand=True),
            ], spacing=0, expand=True),
            expand=True,
            padding=ft.padding.only(bottom=10),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=["#FFF6F6", "#F7C171", "#D49535"]
            )
        ),
    ], expand=True, spacing=0)

    load_items()  # Initial load

    return food_column