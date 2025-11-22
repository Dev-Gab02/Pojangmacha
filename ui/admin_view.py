import flet as ft
from core.db import SessionLocal
from models.food_item import FoodItem
from models.order import Order
from models.user import User
from models.audit_log import AuditLog
from core.admin_user_service import create_user_by_admin, update_user_by_admin, delete_user_by_admin
from core.email_service import generate_verification_code, send_verification_email, store_verification_code, verify_code, resend_verification_code
import os
import threading
import re

def admin_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Admin Panel"

    # Check if user is admin
    user_data = page.session.get("user")
    if not user_data or user_data.get("role") != "admin":
        page.snack_bar = ft.SnackBar(ft.Text("Access denied. Admins only."), open=True)
        page.go("/home")
        return

    # Category options
    CATEGORIES = ["Noodles", "K-Food", "Korean Bowls", "Combo", "Toppings", "Drinks"]

    # ===================== FOOD ITEMS MANAGEMENT =====================
    
    def load_food_items():
        food_list.controls.clear()
        items = db.query(FoodItem).all()
        for item in items:
            food_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Image(src=item.image, width=80, height=80, fit=ft.ImageFit.COVER, border_radius=8) if item.image else ft.Container(width=80, height=80, bgcolor="grey300"),
                            ft.Column([
                                ft.Text(item.name, weight="bold", size=16),
                                ft.Text(f"Category: {item.category}", size=12, color="grey700"),
                                ft.Text(f"₱{item.price:.2f}", color="green", weight="bold"),
                            ], spacing=5, expand=True),
                            ft.Column([
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Edit",
                                    on_click=lambda e, i=item: show_edit_food_dialog(i)
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_color="red",
                                    tooltip="Delete",
                                    on_click=lambda e, i=item: delete_food_item(i)
                                )
                            ])
                        ], spacing=10),
                        padding=10
                    )
                )
            )
        page.update()

    food_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

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
        
        # Store uploaded image path
        uploaded_image_path = {"value": ""}
        
        # Image preview
        image_preview = ft.Container(
            content=ft.Text("No image selected", size=12, color="grey"),
            width=300,
            height=120,
            bgcolor="grey200",
            border_radius=8,
            alignment=ft.alignment.center
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
                    
                    # Update preview
                    image_preview.content = ft.Image(
                        src=dest,
                        width=300,
                        height=120,
                        fit=ft.ImageFit.COVER,
                        border_radius=8
                    )
                    
                    message.value = "✅ Image uploaded successfully!"
                    message.color = "green"
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
            title=ft.Text("Add New Food Item"),
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
                    width=300
                ),
                message
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=520),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dialog)),
                ft.ElevatedButton("Save", on_click=save_food)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

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
        
        # Store uploaded image path (use existing if not changed)
        uploaded_image_path = {"value": item.image or ""}
        
        # Image preview (show current image or placeholder)
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
                border_radius=8
            )
        else:
            image_preview = ft.Container(
                content=ft.Text("No image", size=12, color="grey"),
                width=300,
                height=120,
                bgcolor="grey200",
                border_radius=8,
                alignment=ft.alignment.center
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
                    
                    # Update preview
                    image_preview.content = ft.Image(
                        src=dest,
                        width=300,
                        height=120,
                        fit=ft.ImageFit.COVER,
                        border_radius=8
                    )
                    
                    message.value = "✅ Image updated!"
                    message.color = "green"
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

        dialog = ft.AlertDialog(
            title=ft.Text(f"Edit: {item.name}"),
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
                    width=300
                ),
                message
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=540),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dialog)),
                ft.ElevatedButton("Update", on_click=update_food)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

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
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=confirm_delete, style=ft.ButtonStyle(bgcolor="red", color="white"))
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # ===================== ORDERS MANAGEMENT =====================
    
    def load_orders():
        orders_list.controls.clear()
        orders = db.query(Order).order_by(Order.created_at.desc()).all()
        for order in orders:
            user = db.query(User).get(order.user_id)
            username = user.full_name if user else "Unknown"
            
            orders_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Order #{order.id}", weight="bold"),
                                ft.Text(f"by {username}", size=12, color="grey700"),
                                ft.Container(
                                    content=ft.Text(order.status, color="white", size=12),
                                    bgcolor="green" if order.status == "Completed" else "orange" if order.status == "Pending" else "red",
                                    padding=5,
                                    border_radius=5
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(f"Total: ₱{order.total_price:.2f}", size=14),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Mark Completed",
                                    on_click=lambda e, o=order: update_order_status(o, "Completed"),
                                    disabled=order.status == "Completed"
                                ),
                                ft.ElevatedButton(
                                    "Mark Cancelled",
                                    on_click=lambda e, o=order: update_order_status(o, "Cancelled"),
                                    disabled=order.status == "Cancelled"
                                )
                            ])
                        ]),
                        padding=10
                    )
                )
            )
        page.update()

    def update_order_status(order, status):
        order.status = status
        db.commit()
        
        db.add(AuditLog(user_email=user_data.get("email"), action=f"Updated order #{order.id} to {status}"))
        db.commit()
        
        load_orders()
        page.snack_bar = ft.SnackBar(ft.Text(f"✅ Order #{order.id} → {status}"), bgcolor=ft.Colors.GREEN, open=True)
        page.update()

    orders_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    # ===================== USERS MANAGEMENT =====================
    
    def load_users():
        users_list.controls.clear()
        users = db.query(User).all()
        for user in users:
            # Role badge color
            role_color = "blue" if user.role == "admin" else "green"
            
            users_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(user.full_name, weight="bold", size=16),
                                ft.Text(user.email, size=12, color="grey700"),
                                ft.Container(
                                    content=ft.Text(user.role.upper(), color="white", size=10, weight="bold"),
                                    bgcolor=role_color,
                                    padding=5,
                                    border_radius=5
                                )
                            ], spacing=5, expand=True),
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Edit User",
                                    on_click=lambda e, u=user: show_edit_user_dialog(u)
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE,
                                    icon_color="red",
                                    tooltip="Delete User",
                                    on_click=lambda e, u=user: delete_user(u)
                                )
                            ])
                        ], spacing=10),
                        padding=10
                    )
                )
            )
        page.update()

    users_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    def is_valid_email(email_str: str) -> bool:
        """Check if email format is valid"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email_str) is not None

    def show_create_user_dialog(e=None):
        """Create new user with email verification"""
        
        # Form fields
        full_name_field = ft.TextField(label="Full Name", width=300)
        email_field = ft.TextField(label="Email", width=300)
        password_field = ft.TextField(label="Password", password=True, can_reveal_password=True, width=300)
        confirm_password_field = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, width=300)
        role_dropdown = ft.Dropdown(
            label="Role",
            width=300,
            value="customer",
            options=[
                ft.dropdown.Option("customer", "Customer"),
                ft.dropdown.Option("admin", "Admin")
            ]
        )
        
        # Verification code field
        verification_code_input = ft.TextField(
            label="Enter 6-digit code",
            width=300,
            max_length=6,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            visible=False
        )
        
        message = ft.Text("", color="red")
        
        # Store temp data
        temp_data = {}
        step = {"current": 1}
        
        # Step containers
        step1_container = ft.Container()
        step2_container = ft.Container()
        
        def send_verification(ev):
            """Validate and send verification code"""
            if not all([full_name_field.value, email_field.value, password_field.value, confirm_password_field.value]):
                message.value = "❌ All fields are required!"
                message.color = "red"
                page.update()
                return
            
            if not is_valid_email(email_field.value):
                message.value = "❌ Invalid email format!"
                message.color = "red"
                page.update()
                return
            
            if password_field.value != confirm_password_field.value:
                message.value = "❌ Passwords do not match!"
                message.color = "red"
                page.update()
                return
            
            if len(password_field.value) < 6:
                message.value = "❌ Password too short (min 6 characters)!"
                message.color = "red"
                page.update()
                return
            
            # Check if email already exists
            existing_user = db.query(User).filter(User.email == email_field.value).first()
            if existing_user:
                message.value = "❌ Email already exists!"
                message.color = "red"
                page.update()
                return
            
            # Store temp data
            temp_data["full_name"] = full_name_field.value.strip()
            temp_data["email"] = email_field.value.strip()
            temp_data["password"] = password_field.value
            temp_data["role"] = role_dropdown.value
            
            # Send verification code
            message.value = "📧 Sending verification code..."
            message.color = "blue"
            send_verify_btn.disabled = True
            page.update()
            
            def send_email_thread():
                code = generate_verification_code()
                success = send_verification_email(temp_data["email"], code)
                
                if success:
                    store_verification_code(temp_data["email"], code)
                    step["current"] = 2
                    show_step_2()
                else:
                    message.value = "❌ Failed to send verification email"
                    message.color = "red"
                    send_verify_btn.disabled = False
                    page.update()
            
            thread = threading.Thread(target=send_email_thread, daemon=True)
            thread.start()
        
        def verify_and_create(ev):
            """Verify code and create user"""
            if not verification_code_input.value or len(verification_code_input.value) != 6:
                message.value = "❌ Please enter the 6-digit code"
                message.color = "red"
                page.update()
                return
            
            if verify_code(temp_data["email"], verification_code_input.value):
                try:
                    new_user = create_user_by_admin(
                        db,
                        full_name=temp_data["full_name"],
                        email=temp_data["email"],
                        password=temp_data["password"],
                        role=temp_data["role"]
                    )
                    
                    db.add(AuditLog(
                        user_email=user_data.get("email"),
                        action=f"Created user: {new_user.email} (Role: {new_user.role})"
                    ))
                    db.commit()
                    
                    dialog.open = False
                    page.update()
                    load_users()
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"✅ User {new_user.email} created successfully!"),
                        bgcolor=ft.Colors.GREEN,
                        open=True
                    )
                    page.update()
                
                except Exception as ex:
                    message.value = f"❌ Error creating user: {ex}"
                    message.color = "red"
                    page.update()
            else:
                message.value = "❌ Invalid or expired code"
                message.color = "red"
                page.update()
        
        def resend_code(ev):
            """Resend verification code"""
            message.value = "📧 Resending code..."
            message.color = "blue"
            page.update()
            
            def resend_thread():
                if resend_verification_code(temp_data["email"]):
                    message.value = "✅ New code sent to email"
                    message.color = "green"
                else:
                    message.value = "❌ Failed to send code"
                    message.color = "red"
                page.update()
            
            thread = threading.Thread(target=resend_thread, daemon=True)
            thread.start()
        
        def show_step_1():
            """Show form step"""
            step1_container.content = ft.Column([
                ft.Text("👤 Create New User", size=18, weight="bold"),
                ft.Text("Fill in the details below", size=12, color="grey"),
                full_name_field,
                email_field,
                password_field,
                confirm_password_field,
                role_dropdown,
                send_verify_btn,
                message
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            step1_container.visible = True
            step2_container.visible = False
            page.update()
        
        def show_step_2():
            """Show verification step"""
            step2_container.content = ft.Column([
                ft.Text("📧 Verify Email", size=18, weight="bold"),
                ft.Text(f"Code sent to {temp_data['email']}", size=12, color="grey"),
                verification_code_input,
                verify_create_btn,
                ft.TextButton("Resend Code", on_click=resend_code),
                ft.TextButton("← Back", on_click=lambda e: show_step_1()),
                message
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            
            verification_code_input.visible = True
            step1_container.visible = False
            step2_container.visible = True
            page.update()
        
        # Buttons
        send_verify_btn = ft.ElevatedButton("Send Verification Code", on_click=send_verification, width=250)
        verify_create_btn = ft.ElevatedButton("Verify & Create User", on_click=verify_and_create, width=250)
        
        # Dialog
        dialog = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                content=ft.Column([
                    step1_container,
                    step2_container
                ], width=350),
                padding=10
            ),
            actions=[ft.TextButton("Cancel", on_click=lambda e: close_dialog(dialog))]
        )
        
        show_step_1()
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def show_edit_user_dialog(user):
        """Edit existing user"""
        full_name_field = ft.TextField(label="Full Name", value=user.full_name, width=300)
        email_field = ft.TextField(label="Email", value=user.email, width=300)
        role_dropdown = ft.Dropdown(
            label="Role",
            width=300,
            value=user.role,
            options=[
                ft.dropdown.Option("customer", "Customer"),
                ft.dropdown.Option("admin", "Admin")
            ]
        )
        
        # Password reset section
        new_password_field = ft.TextField(
            label="New Password (leave blank to keep current)",
            password=True,
            can_reveal_password=True,
            width=300
        )
        confirm_password_field = ft.TextField(
            label="Confirm New Password",
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        message = ft.Text("", color="red")
        
        def update_user(e):
            if not all([full_name_field.value, email_field.value]):
                message.value = "❌ Name and email are required!"
                message.color = "red"
                page.update()
                return
            
            if not is_valid_email(email_field.value):
                message.value = "❌ Invalid email format!"
                message.color = "red"
                page.update()
                return
            
            # Password validation if provided
            new_password = None
            if new_password_field.value:
                if new_password_field.value != confirm_password_field.value:
                    message.value = "❌ Passwords do not match!"
                    message.color = "red"
                    page.update()
                    return
                if len(new_password_field.value) < 6:
                    message.value = "❌ Password too short (min 6 characters)!"
                    message.color = "red"
                    page.update()
                    return
                new_password = new_password_field.value
            
            # Update user
            success, msg = update_user_by_admin(
                db,
                user_id=user.id,
                full_name=full_name_field.value.strip(),
                email=email_field.value.strip(),
                role=role_dropdown.value,
                new_password=new_password
            )
            
            if success:
                db.add(AuditLog(
                    user_email=user_data.get("email"),
                    action=f"Updated user: {email_field.value} (Role: {role_dropdown.value})"
                ))
                db.commit()
                
                dialog.open = False
                page.update()
                load_users()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✅ {msg}"),
                    bgcolor=ft.Colors.GREEN,
                    open=True
                )
                page.update()
            else:
                message.value = f"❌ {msg}"
                message.color = "red"
                page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Edit User: {user.full_name}"),
            content=ft.Column([
                full_name_field,
                email_field,
                role_dropdown,
                ft.Divider(),
                ft.Text("Reset Password (Optional)", size=14, weight="bold"),
                new_password_field,
                confirm_password_field,
                message
            ], tight=True, scroll=ft.ScrollMode.AUTO, height=450, spacing=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dialog)),
                ft.ElevatedButton("Update User", on_click=update_user)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def delete_user(user):
        """Delete user with confirmation"""
        def confirm_delete(e):
            success, msg = delete_user_by_admin(db, user.id)
            
            if success:
                db.add(AuditLog(
                    user_email=user_data.get("email"),
                    action=f"Deleted user: {user.email}"
                ))
                db.commit()
                
                dialog.open = False
                page.update()
                load_users()
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"✅ {msg}"),
                    bgcolor=ft.Colors.ORANGE,
                    open=True
                )
                page.update()
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ {msg}"),
                    bgcolor=ft.Colors.RED,
                    open=True
                )
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("⚠️ Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete user:\n\n'{user.full_name}' ({user.email})\n\nThis action cannot be undone!"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(dialog)),
                ft.ElevatedButton(
                    "Delete User",
                    on_click=confirm_delete,
                    style=ft.ButtonStyle(bgcolor="red", color="white")
                )
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def close_dialog(dialog):
        dialog.open = False
        page.update()

    # ===================== MAIN UI =====================
    
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="Food Items",
                icon=ft.Icons.RESTAURANT_MENU,
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Manage Food Items", size=20, weight="bold"),
                            ft.ElevatedButton(
                                "Add New Item",
                                icon=ft.Icons.ADD,
                                on_click=show_add_food_dialog
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(content=food_list, expand=True)
                    ], expand=True),
                    padding=10
                )
            ),
            ft.Tab(
                text="Orders",
                icon=ft.Icons.SHOPPING_BAG,
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("Manage Orders", size=20, weight="bold"),
                        ft.Container(content=orders_list, expand=True)
                    ], expand=True),
                    padding=10
                )
            ),
            ft.Tab(
                text="Users",
                icon=ft.Icons.PEOPLE,
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Manage Users", size=20, weight="bold"),
                            ft.ElevatedButton(
                                "Create New User",
                                icon=ft.Icons.PERSON_ADD,
                                on_click=show_create_user_dialog
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(content=users_list, expand=True)
                    ], expand=True),
                    padding=10
                )
            )
        ],
        expand=True
    )

    # Load initial data
    load_food_items()
    load_orders()
    load_users()

    # Navigation buttons
    def goto_analytics(e):
        page.go("/analytics")
    
    def logout_user(e):
        page.session.set("user", None)
        page.snack_bar = ft.SnackBar(ft.Text("Logged out successfully."), open=True)
        page.go("/logout")

    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                # Header - BLACK background
                ft.Container(
                    content=ft.Row([
                        ft.Text("Admin Panel", size=18, weight="bold", color="white"),
                        ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.ANALYTICS,
                                icon_color="white",
                                tooltip="Analytics",
                                on_click=lambda e: page.go("/analytics")
                            ),
                            ft.IconButton(
                                icon=ft.Icons.LOGOUT,
                                icon_color="white",
                                tooltip="Logout",
                                on_click=logout_user
                            )
                        ], spacing=5)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10,
                    bgcolor="black",
                ),
                
                # Tabs (scrollable content)
                ft.Container(
                    content=tabs,
                    expand=True
                )
            ], expand=True, spacing=0),
            width=400,
            height=700,
            padding=0
        )
    )
    page.update()