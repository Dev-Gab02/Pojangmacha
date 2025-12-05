"""
Food Items Management Tab for Admin Panel
"""
import flet as ft
from models.food_item import FoodItem
from models.audit_log import AuditLog
from ui.admin_constants import (
    CATEGORIES, DESKTOP_COLUMNS,
    GRID_SPACING, GRID_RUN_SPACING
)
from ui.admin_utils import close_dialog
import os

def build_food_items_tab(page: ft.Page, db, user_data: dict, is_desktop: bool):
    """
    Build the Food Items management tab
    
    Args:
        page: Flet page object
        db: Database session
        user_data: Current admin user data
        is_desktop: True if desktop layout, False if mobile
    
    Returns:
        ft.Tab: Complete food items tab with all functionality
    """
    
    # ===================== CARD BUILDER =====================
    
    def build_food_card(item):
        """
        Build a single food card
        - SAME DESIGN for both desktop and mobile (horizontal layout)
        - Desktop: 3-column grid
        - Mobile: Single column list
        - 3-dot menu for Edit/Delete actions
        """
        
        # ✅ UNIFIED HORIZONTAL LAYOUT (same for desktop & mobile)
        return ft.Card(
            content=ft.Container(
                content=ft.Row([
                    # Image (left side)
                    ft.Container(
                        content=ft.Image(
                            src=item.image,
                            width=80,
                            height=80,
                            fit=ft.ImageFit.COVER,
                            border_radius=8
                        ) if item.image else ft.Container(
                            width=80,
                            height=80,
                            bgcolor="grey300",
                            border_radius=8,
                            alignment=ft.alignment.center,
                            content=ft.Icon(ft.Icons.RESTAURANT, size=30, color="grey600")
                        ),
                        border=ft.border.all(1, "grey300"),
                        border_radius=8
                    ),
                    
                    # Content (center - expandable)
                    ft.Column([
                        # ✅ Row 1: Name + 3-dot menu (SPACE_BETWEEN alignment)
                        ft.Row([
                            ft.Text(item.name, weight="bold", size=16, color="black", expand=True),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color="black",
                                items=[
                                    ft.PopupMenuItem(
                                        text="Edit",
                                        icon=ft.Icons.EDIT,
                                        on_click=lambda e, i=item: show_edit_food_dialog(i)
                                    ),
                                    ft.PopupMenuItem(
                                        text="Delete",
                                        icon=ft.Icons.DELETE,
                                        on_click=lambda e, i=item: delete_food_item(i)
                                    ),
                                ], 
                                icon_size=20,
                                padding=0,
                                bgcolor='white',
                                menu_position=ft.PopupMenuPosition.OVER,
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=5),
                        
                        # Row 2: Category
                        ft.Text(f"Category: {item.category}", size=12, color="grey700"),
                        
                        # Row 3: Price
                        ft.Text(f"₱{item.price:.2f}", color="green", weight="bold"),
                    ], spacing=5, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),  # ✅ Center alignment
                padding=10,
                bgcolor="white",
                border_radius=12
            )
        )
    
    # ===================== GRID/LIST CONTAINERS =====================
    
    # ✅ Desktop: GridView with 3 columns (horizontal cards)
    food_grid = ft.GridView(
        runs_count=DESKTOP_COLUMNS,  # 3 columns
        max_extent=500,  # ✅ Responsive: allows cards to expand up to 500px
        child_aspect_ratio=4.0,  # ✅ Width/Height = 4:1 (matches mobile proportions)
        spacing=GRID_SPACING,
        run_spacing=GRID_RUN_SPACING,
        expand=True
    )

    # ✅ Mobile: Column (single column list) - UNCHANGED
    food_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    
    # ===================== LOAD DATA =====================
    
    def load_food_items():
        """Load food items into grid/list"""
        if is_desktop:
            food_grid.controls.clear()
            items = db.query(FoodItem).all()
            for item in items:
                food_grid.controls.append(build_food_card(item))
        else:
            food_list.controls.clear()
            items = db.query(FoodItem).all()
            for item in items:
                food_list.controls.append(build_food_card(item))
        page.update()
    
    # ===================== ADD FOOD DIALOG =====================
    
    def show_add_food_dialog(e=None):
        name_field = ft.TextField(label="Food Name", width=300)
        description_field = ft.TextField(label="Description", width=300, multiline=True)
        price_field = ft.TextField(label="Price", width=300, keyboard_type=ft.KeyboardType.NUMBER)
        category_dropdown = ft.Dropdown(
            label="Category",
            width=300,
            options=[ft.dropdown.Option(cat) for cat in CATEGORIES]
        )
        message = ft.Text("", color="red")
        
        uploaded_image_path = {"value": ""}
        
        image_preview = ft.Container(
            content=ft.Text("No image selected", size=12, color="grey"),
            width=300,
            height=120,
            bgcolor="grey200",
            border_radius=8,
            alignment=ft.alignment.center,
            border=ft.border.all(1, "grey300")  # ✅ Add border
        )

        def on_file_pick(e: ft.FilePickerResultEvent):
            if e.files:
                import shutil
                src = e.files[0].path
                upload_dir = "assets/uploads/foods"
                os.makedirs(upload_dir, exist_ok=True)
                filename = os.path.basename(src)
                dest = os.path.join(upload_dir, filename)
                
                try:
                    shutil.copy(src, dest)
                    uploaded_image_path["value"] = dest
                    
                    image_preview.content = ft.Image(
                        src=dest,
                        width=300,
                        height=120,
                        fit=ft.ImageFit.COVER,
                        border_radius=8
                    )
                    
                    # ✅ REMOVED success message
                    page.update()
                except Exception as ex:
                    message.value = f"❌ Error: {ex}"
                    message.color = "red"
                    page.update()

        file_picker = ft.FilePicker(on_result=on_file_pick)
        page.overlay.append(file_picker)
        page.update()

        def save_food(e):
            if not all([name_field.value, price_field.value, category_dropdown.value]):
                message.value = "❌ Please fill all required fields"
                message.color = "red"
                page.update()
                return

            try:
                new_item = FoodItem(
                    name=name_field.value.strip(),
                    description=description_field.value.strip() or "",
                    price=float(price_field.value),
                    category=category_dropdown.value,
                    image=uploaded_image_path["value"]
                )
                db.add(new_item)
                db.commit()
                
                db.add(AuditLog(user_email=user_data.get("email"), action=f"Added food item: {new_item.name}"))
                db.commit()
                
                dialog.open = False
                page.update()
                load_food_items()
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ {new_item.name} added successfully!"), bgcolor=ft.Colors.GREEN, open=True)
                page.update()
            except Exception as ex:
                message.value = f"❌ Error: {ex}"
                message.color = "red"
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Container(
                content=ft.Text(
                    "Add New Food Item",
                    size=16,
                    weight="bold"
                ),
                alignment=ft.alignment.center_left,
                width=320,
                padding=ft.padding.only(left=10)
            ),
            content=ft.Container(
                content=ft.Column([
                    name_field,
                    description_field,
                    price_field,
                    category_dropdown,
                    ft.Divider(),
                    ft.Text("Food Image", size=14, weight="bold"),
                    image_preview,
                    ft.ElevatedButton(
                        "Upload Image",
                        icon=ft.Icons.UPLOAD_FILE,
                        on_click=lambda e: file_picker.pick_files(
                            allowed_extensions=["png", "jpg", "jpeg"],
                            allow_multiple=False
                        ),
                        width=300,
                        bgcolor="#FEB23F",  # ✅ Orange button
                        color="white"
                    ),
                    message
                ], tight=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=320,  # ✅ Fixed width on container
                height=520,
                alignment=ft.alignment.top_center  # ✅ Center content
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(page, dialog)),
                ft.ElevatedButton("Save", on_click=save_food)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    # ===================== EDIT FOOD DIALOG =====================
    
    def show_edit_food_dialog(item):
        name_field = ft.TextField(label="Food Name", value=item.name, width=300)
        description_field = ft.TextField(label="Description", value=item.description or "", width=300, multiline=True)
        price_field = ft.TextField(label="Price", value=str(item.price), width=300, keyboard_type=ft.KeyboardType.NUMBER)
        category_dropdown = ft.Dropdown(
            label="Category",
            value=item.category,
            width=300,
            options=[ft.dropdown.Option(cat) for cat in CATEGORIES]
        )
        message = ft.Text("", color="red")
        
        uploaded_image_path = {"value": item.image or ""}
        
        if item.image and os.path.exists(item.image):
            image_preview = ft.Container(
                content=ft.Image(
                    src=item.image,
                    width=300,
                    height=120,
                    fit=ft.ImageFit.COVER,
                    border_radius=8
                ),
                width=300,
                height=120,
                border_radius=8,
                border=ft.border.all(1, "grey300")  # ✅ Changed to grey300
            )
        else:
            image_preview = ft.Container(
                content=ft.Text("No image", size=12, color="grey"),
                width=300,
                height=120,
                bgcolor="grey200",
                border_radius=8,
                alignment=ft.alignment.center,
                border=ft.border.all(1, "grey300")  # ✅ Changed to grey300
            )

        def on_file_pick(e: ft.FilePickerResultEvent):
            if e.files:
                import shutil
                src = e.files[0].path
                upload_dir = "assets/uploads/foods"
                os.makedirs(upload_dir, exist_ok=True)
                filename = os.path.basename(src)
                dest = os.path.join(upload_dir, filename)
                
                try:
                    shutil.copy(src, dest)
                    uploaded_image_path["value"] = dest
                    
                    image_preview.content = ft.Image(
                        src=dest,
                        width=300,
                        height=120,
                        fit=ft.ImageFit.COVER,
                        border_radius=8
                    )
                    
                    # ✅ REMOVED success message
                    page.update()
                except Exception as ex:
                    message.value = f"❌ Error: {ex}"
                    message.color = "red"
                    page.update()

        file_picker = ft.FilePicker(on_result=on_file_pick)
        page.overlay.append(file_picker)
        page.update()

        def update_food(e):
            if not all([name_field.value, price_field.value, category_dropdown.value]):
                message.value = "❌ Please fill all required fields"
                message.color = "red"
                page.update()
                return

            try:
                item.name = name_field.value.strip()
                item.description = description_field.value.strip()
                item.price = float(price_field.value)
                item.category = category_dropdown.value
                item.image = uploaded_image_path["value"]
                db.commit()
                
                db.add(AuditLog(user_email=user_data.get("email"), action=f"Updated food item: {item.name}"))
                db.commit()
                
                dialog.open = False
                page.update()
                load_food_items()
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ {item.name} updated!"), bgcolor=ft.Colors.GREEN, open=True)
                page.update()
            except Exception as ex:
                message.value = f"❌ Error: {ex}"
                message.color = "red"
                page.update()

        # ✅ Truncate title to 25 characters with ellipsis
        title_text = f"Edit: {item.name[:22]}..." if len(item.name) > 22 else f"Edit: {item.name}"
        
        dialog = ft.AlertDialog(
            title=ft.Container(
                content=ft.Text(
                    title_text,
                    size=16,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1
                ),
                alignment=ft.alignment.center_left,
                width=320,
                padding=ft.padding.only(left=10)
            ),
            content=ft.Container(
                content=ft.Column([
                    name_field,
                    description_field,
                    price_field,
                    category_dropdown,
                    ft.Divider(),
                    ft.Text("Food Image", size=14, weight="bold"),
                    image_preview,
                    ft.ElevatedButton(
                        "Change Image",
                        icon=ft.Icons.UPLOAD_FILE,
                        on_click=lambda e: file_picker.pick_files(
                            allowed_extensions=["png", "jpg", "jpeg"],
                            allow_multiple=False
                        ),
                        width=300,
                        bgcolor="#FEB23F",
                        color='white'
                    ),
                    message
                ], tight=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=320,  # ✅ Fixed width on container
                height=540,
                alignment=ft.alignment.top_center  # ✅ Center content
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(page, dialog)),
                ft.ElevatedButton("Update", on_click=update_food)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    # ===================== DELETE FOOD =====================
    
    def delete_food_item(item):
        def confirm_delete(e):
            db.delete(item)
            db.commit()
            
            db.add(AuditLog(user_email=user_data.get("email"), action=f"Deleted food item: {item.name}"))
            db.commit()
            
            dialog.open = False
            page.update()
            load_food_items()
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ {item.name} deleted"), bgcolor=ft.Colors.ORANGE, open=True)
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete '{item.name}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(page, dialog)),
                ft.ElevatedButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor="red", color="white"))
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    # ===================== BUILD TAB =====================
    
    # Load initial data
    load_food_items()
    
    # Return the complete tab
    return ft.Tab(
        text="Food Items",
        icon=ft.Icons.RESTAURANT_MENU,
        content=ft.Column([
            # ✅ Title Row - TRANSPARENT (gradient shows through)
            ft.Container(
                content=ft.Row([
                    ft.Text("Manage Food Items", size=20, weight="bold", color='black'),
                    ft.ElevatedButton(
                        "Add New Item",
                        icon=ft.Icons.ADD,
                        on_click=show_add_food_dialog,
                        bgcolor="#FEB23F",
                        color="white"
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=10
                # ✅ No bgcolor - gradient from parent shows through
            ),
            
            # ✅ Grid/List with TRANSPARENT background (gradient from parent)
            ft.Container(
                content=food_grid if is_desktop else food_list,
                expand=True,
                padding=10
                # ✅ No gradient here - inherits from parent
            )
        ], expand=True, spacing=0)
    )