"""
Users Management Tab for Admin Panel
"""
import flet as ft
from models.user import User
from models.audit_log import AuditLog
from core.admin_user_service import create_user_by_admin, update_user_by_admin, delete_user_by_admin
from core.email_service import generate_verification_code, send_verification_email, store_verification_code, verify_code, resend_verification_code
from ui.admin_constants import USER_CARD_MIN_HEIGHT, DESKTOP_COLUMNS, GRID_SPACING, GRID_RUN_SPACING
from ui.admin_utils import is_valid_email, close_dialog
import threading

def build_users_tab(page: ft.Page, db, user_data: dict, is_desktop: bool):
    """
    Build the Users management tab
    
    Args:
        page: Flet page object
        db: Database session
        user_data: Current admin user data
        is_desktop: True if desktop layout, False if mobile
    
    Returns:
        ft.Tab: Complete users tab with all functionality
    """
    
    # ===================== CARD BUILDER =====================
    def build_user_card(user):
        """Build a single user card - SAME DESIGN for mobile & desktop with 3-dot menu"""
        role_color = "blue" if user.role == "admin" else "green"
        
        return ft.Card(
            content=ft.Container(
                content=ft.Row([
                    # User info (left - expandable)
                    ft.Column([
                        # ✅ Row 1: Name + 3-dot menu (SPACE_BETWEEN alignment)
                        ft.Row([
                            ft.Text(user.full_name, weight="bold", size=16, color='black', expand=True),
                            ft.PopupMenuButton(
                                icon=ft.Icons.MORE_VERT,
                                icon_color="black",
                                items=[
                                    ft.PopupMenuItem(
                                        text="Edit",
                                        icon=ft.Icons.EDIT,
                                        on_click=lambda e, u=user: show_edit_user_dialog(u)
                                    ),
                                    ft.PopupMenuItem(
                                        text="Delete",
                                        icon=ft.Icons.DELETE,
                                        on_click=lambda e, u=user: delete_user(u)
                                    ),
                                ],
                                icon_size=20,
                                padding=0,
                                bgcolor='white',
                                menu_position=ft.PopupMenuPosition.OVER,
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=5),
                        
                        # Row 2: Email
                        ft.Text(user.email, size=12, color="grey700"),
                        
                        # Row 3: Role badge
                        ft.Container(
                            content=ft.Text(user.role.upper(), color="white", size=10, weight="bold"),
                            bgcolor=role_color,
                            padding=5,
                            border_radius=5
                        )
                    ], spacing=7, expand=True),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=10,
                bgcolor='white',
                border_radius=12,
                # ✅ Min height for grid consistency
                **({'height': USER_CARD_MIN_HEIGHT} if is_desktop else {})
            )
        )
    
    # ===================== GRID/LIST CONTAINERS =====================
    
    # ✅ Desktop: GridView with 3 columns
    users_grid = ft.GridView(
        runs_count=DESKTOP_COLUMNS,
        max_extent=400,
        child_aspect_ratio=2.5,
        spacing=GRID_SPACING,
        run_spacing=GRID_RUN_SPACING,
        expand=True
    )

    # ✅ Mobile: Column (single column list)
    users_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    
    # ===================== LOAD DATA =====================
    
    def load_users():
        """Load users into grid/list"""
        if is_desktop:
            users_grid.controls.clear()
            users = db.query(User).all()
            for user in users:
                users_grid.controls.append(build_user_card(user))
        else:
            users_list.controls.clear()
            users = db.query(User).all()
            for user in users:
                users_list.controls.append(build_user_card(user))
        page.update()
    
    # ===================== CREATE USER DIALOG =====================
    
    def show_create_user_dialog(e=None):
        """Create new user with email verification"""
        
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
        
        verification_code_input = ft.TextField(
            label="Enter 6-digit code",
            width=300,
            max_length=6,
            text_align=ft.TextAlign.CENTER,
            keyboard_type=ft.KeyboardType.NUMBER,
            visible=False
        )
        
        message = ft.Text("", color="red")
        
        temp_data = {}
        step = {"current": 1}
        
        step1_container = ft.Container()
        step2_container = ft.Container()
        
        def send_verification(ev):
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
            
            existing_user = db.query(User).filter(User.email == email_field.value).first()
            if existing_user:
                message.value = "❌ Email already exists!"
                message.color = "red"
                page.update()
                return
            
            temp_data["full_name"] = full_name_field.value.strip()
            temp_data["email"] = email_field.value.strip()
            temp_data["password"] = password_field.value
            temp_data["role"] = role_dropdown.value
            
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
            step1_container.content = ft.Column([
                ft.Text("Create New User", size=18, weight="bold"),
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
        
        send_verify_btn = ft.ElevatedButton(
            "Send Verification Code",
            on_click=send_verification,
            width=300,
            bgcolor="#FEB23F",  # ✅ Orange button
            color="white"
        )
        verify_create_btn = ft.ElevatedButton(
            "Verify & Create User",
            on_click=verify_and_create,
            width=300,
            bgcolor="#FEB23F",  # ✅ Orange button
            color="white"
        )
        
        dialog = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                content=ft.Column([
                    step1_container,
                    step2_container
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=320,
                height=440,
                padding=10,
                alignment=ft.alignment.top_center  # ✅ Center content
            ),
            actions=[ft.TextButton("Cancel", on_click=lambda e: close_dialog(page, dialog))]
        )
        
        show_step_1()
        
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    # ===================== EDIT USER DIALOG =====================
    
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
        
        def update_user_data(e):
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
        
        # ✅ Truncate title to 25 characters with ellipsis
        title_text = f"Edit: {user.full_name[:22]}..." if len(user.full_name) > 22 else f"Edit: {user.full_name}"
        
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
                    full_name_field,
                    email_field,
                    role_dropdown,
                    ft.Divider(),
                    ft.Text("Reset Password (Optional)", size=14, weight="bold"),
                    new_password_field,
                    confirm_password_field,
                    message
                ], tight=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                width=320,
                height=360,
                alignment=ft.alignment.top_center  # ✅ Center content
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(page, dialog)),
                ft.ElevatedButton(
                    "Update User",
                    on_click=update_user_data,
                    bgcolor="white"
                )
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    
    # ===================== DELETE USER =====================
    
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
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete user:\n'{user.full_name}' ({user.email})\nThis action cannot be undone!"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: close_dialog(page, dialog)),
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
    
    # ===================== BUILD TAB =====================
    
    # Load initial data
    load_users()
    
    # Return the complete tab
    return ft.Tab(
        text="Users",
        icon=ft.Icons.PEOPLE,
        content=ft.Column([
            # ✅ Title Row - TRANSPARENT (gradient shows through)
            ft.Container(
                content=ft.Row([
                    ft.Text("Manage Users", size=20, weight="bold", color='black'),
                    ft.ElevatedButton(
                        "Create New User",
                        icon=ft.Icons.PERSON_ADD,
                        on_click=show_create_user_dialog,
                        bgcolor="#FEB23F",
                        color="white"
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=10
                # ✅ No bgcolor - gradient from parent shows through
            ),
            
            # ✅ Grid/List with TRANSPARENT background (gradient from parent)
            ft.Container(
                content=users_grid if is_desktop else users_list,
                expand=True,
                padding=10
                # ✅ No gradient here - inherits from parent
            )
        ], expand=True, spacing=0)
    )