import os
import flet as ft
from core.db import SessionLocal
from core.profile_service import get_user_by_id, update_profile, change_password
from models.order import Order
from models.user import User
from core.two_fa_service import enable_2fa, disable_2fa

def profile_view(page: ft.Page):
    db = SessionLocal()

    # Check session user
    user_data = page.session.get("user")
    if not user_data:
        page.snack_bar = ft.SnackBar(ft.Text("Please log in first."), open=True)
        page.go("/login")
        return

    user = get_user_by_id(db, user_data["id"])
    if not user:
        page.snack_bar = ft.SnackBar(ft.Text("User not found."), open=True)
        page.go("/login")
        return

    page.title = "Profile - Pojangmacha"

    # Get edit mode from session (persists across route changes)
    edit_mode_ref = {"value": page.session.get("profile_edit_mode") or False}

    # Calculate user statistics
    user_orders = db.query(Order).filter(Order.user_id == user.id).all()
    total_orders = len(user_orders)
    total_spent = sum(order.total_price for order in user_orders)

    # Check if user has password (Google users have no phone number)
    has_password = bool(user.phone)  # Google users don't have phone, so no password set

    # Profile image (use placeholder if none)
    def get_profile_image():
        # FIXED: Changed profile_image to profile_picture
        profile_image_path = user.profile_picture if user.profile_picture and os.path.exists(user.profile_picture) else None
        
        if profile_image_path:
            return ft.Image(
                src=profile_image_path,
                width=120,
                height=120,
                fit=ft.ImageFit.COVER,
                border_radius=60
            )
        else:
            # Placeholder avatar with user's initials
            initials = "".join([name[0].upper() for name in user.full_name.split()[:2]])
            return ft.Container(
                content=ft.Text(initials, size=40, weight="bold", color="white"),
                width=120,
                height=120,
                border_radius=60,
                bgcolor="blue400",
                alignment=ft.alignment.center
            )

    # Profile fields for editing
    full_name_field = ft.TextField(label="Full Name", value=user.full_name, width=300)
    email_field = ft.TextField(label="Email", value=user.email, width=300, disabled=True)
    phone_field = ft.TextField(label="Phone Number", value=user.phone or "", width=300)
    message = ft.Text("", color="green")

    # Password change fields (for users with existing password)
    old_pass = ft.TextField(label="Current Password", password=True, can_reveal_password=True, width=300)
    new_pass = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=300)
    confirm_pass = ft.TextField(label="Confirm New Password", password=True, can_reveal_password=True, width=300)
    
    # Set password fields (for Google users without password)
    set_new_pass = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=300)
    set_confirm_pass = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, width=300)
    
    pass_msg = ft.Text("", color="red")

    # 2FA message
    two_fa_msg = ft.Text("", color="green")

    # Container that will hold the content
    content_container = ft.Container(expand=True)
    
    # Header container that changes based on mode - NO bgcolor
    header_container = ft.Container(padding=10)

    # File picker for profile image
    def on_file_pick(e: ft.FilePickerResultEvent):
        if e.files:
            import shutil
            src = e.files[0].path
            upload_dir = "assets/profile_images"
            os.makedirs(upload_dir, exist_ok=True)
            filename = f"user_{user.id}_{os.path.basename(src)}"
            dest = os.path.join(upload_dir, filename)
            
            try:
                shutil.copy(src, dest)
                # FIXED: Changed profile_image to profile_picture
                user.profile_picture = dest
                db.commit()
                message.value = "✅ Profile picture updated!"
                message.color = "green"
                # Rebuild UI to show new image
                build_ui()
            except Exception as ex:
                message.value = f"❌ Error uploading image: {ex}"
                message.color = "red"
                page.update()

    file_picker = ft.FilePicker(on_result=on_file_pick)
    page.overlay.append(file_picker)

    # Update profile handler
    def handle_update_profile(e):
        # FIXED: Changed profile_image to profile_picture
        ok, msg = update_profile(
            db, user.id, 
            full_name_field.value.strip(), 
            email_field.value.strip(), 
            phone_field.value.strip(), 
            user.profile_picture or ""
        )
        message.value = msg
        message.color = "green" if ok else "red"

        if ok:
            page.session.set("user", {
                "id": user.id,
                "email": email_field.value.strip(),
                "full_name": full_name_field.value.strip(),
                "role": user.role
            })
            edit_mode_ref["value"] = False
            page.session.set("profile_edit_mode", False)
            # Rebuild to show view mode
            build_ui()
        else:
            page.update()

    # Change password handler (for users with existing password)
    def handle_change_password(e):
        if not all([old_pass.value, new_pass.value, confirm_pass.value]):
            pass_msg.value = "All password fields are required."
            pass_msg.color = "red"
        elif new_pass.value != confirm_pass.value:
            pass_msg.value = "New passwords do not match."
            pass_msg.color = "red"
        elif len(new_pass.value) < 6:
            pass_msg.value = "Password too short (min 6 characters)."
            pass_msg.color = "red"
        else:
            ok, msg = change_password(db, user.id, old_pass.value, new_pass.value)
            pass_msg.value = msg
            pass_msg.color = "green" if ok else "red"
            if ok:
                old_pass.value = new_pass.value = confirm_pass.value = ""
        page.update()

    # Set password handler (for Google users)
    def handle_set_password(e):
        if not all([set_new_pass.value, set_confirm_pass.value]):
            pass_msg.value = "All fields are required."
            pass_msg.color = "red"
        elif set_new_pass.value != set_confirm_pass.value:
            pass_msg.value = "Passwords do not match."
            pass_msg.color = "red"
        elif len(set_new_pass.value) < 6:
            pass_msg.value = "Password too short (min 6 characters)."
            pass_msg.color = "red"
        else:
            # Set password directly (no old password verification needed)
            from core.auth_service import hash_password
            try:
                user.password_hash = hash_password(set_new_pass.value)
                db.commit()
                
                pass_msg.value = "✅ Password set successfully! You can now login with email/password."
                pass_msg.color = "green"
                set_new_pass.value = set_confirm_pass.value = ""
                
                # Update has_password flag
                nonlocal has_password
                has_password = True
                
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Password set! You can now use email/password login."),
                    bgcolor=ft.Colors.GREEN
                )
                page.snack_bar.open = True
                
            except Exception as ex:
                print(f"Set password error: {ex}")
                pass_msg.value = "❌ Error setting password."
                pass_msg.color = "red"
        
        page.update()

    # 2FA Functions
    def open_dialog(dlg):
        """Open a dialog"""
        if dlg not in page.overlay:
            page.overlay.append(dlg)
        page.dialog = dlg
        dlg.open = True
        page.update()

    def close_dialog(e=None):
        """Close all dialogs"""
        if page.dialog:
            page.dialog.open = False
            page.dialog = None
        for item in list(page.overlay):
            if hasattr(item, "open") and type(item).__name__ == "AlertDialog":
                try:
                    item.open = False
                    page.overlay.remove(item)
                except:
                    pass
        page.update()

    def toggle_2fa(e):
        """Enable or disable 2FA"""
        # Refresh user data
        fresh_user = db.query(User).filter(User.id == user.id).first()
        
        if fresh_user.two_fa_enabled:
            # Disable 2FA
            confirm_dlg = ft.AlertDialog(
                title=ft.Text("❌ Disable 2FA?"),
                content=ft.Text("Are you sure you want to disable two-factor authentication?\n\nThis will make your account less secure."),
                actions=[
                    ft.TextButton("Cancel", on_click=close_dialog),
                    ft.ElevatedButton(
                        "Disable",
                        on_click=lambda e: confirm_disable_2fa(),
                        style=ft.ButtonStyle(bgcolor="red", color="white")
                    )
                ]
            )
            open_dialog(confirm_dlg)
        else:
            # Enable 2FA
            enable_2fa_process()

    def confirm_disable_2fa():
        """Confirm and disable 2FA"""
        close_dialog()
        
        if disable_2fa(db, user.id):
            user.two_fa_enabled = False
            two_fa_msg.value = "✅ 2FA disabled successfully"
            two_fa_msg.color = "green"
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Two-Factor Authentication disabled"),
                bgcolor=ft.Colors.ORANGE
            )
            page.snack_bar.open = True
            build_ui()  # Rebuild to update UI
        else:
            two_fa_msg.value = "❌ Failed to disable 2FA"
            two_fa_msg.color = "red"
            page.update()

    def enable_2fa_process():
        """Enable 2FA and show backup codes"""
        backup_codes = enable_2fa(db, user.id)
        
        if backup_codes:
            user.two_fa_enabled = True
            
            # Show backup codes
            codes_display = "\n".join(backup_codes)
            
            backup_codes_dlg = ft.AlertDialog(
                title=ft.Text("⚠️ Save Your Backup Codes"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Save these codes in a safe place. You'll need them if you lose access to your email.", 
                            size=14, 
                            color="grey700"
                        ),
                        ft.Container(height=10),
                        ft.Container(
                            content=ft.Text(
                                codes_display, 
                                selectable=True, 
                                size=16, 
                                weight="bold",
                                text_align=ft.TextAlign.CENTER
                            ),
                            bgcolor=ft.Colors.GREY_200,
                            padding=20,
                            border_radius=5,
                            border=ft.border.all(2, ft.Colors.BLUE_200)
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            "⚠️ These codes will only be shown once!", 
                            color="red", 
                            size=14,
                            weight="bold"
                        ),
                        ft.Text(
                            "Each backup code can only be used once.",
                            size=12,
                            color="grey600"
                        )
                    ], 
                    tight=True, 
                    scroll=ft.ScrollMode.AUTO,
                    spacing=5),
                    width=400
                ),
                actions=[
                    ft.ElevatedButton(
                        "I've Saved My Codes",
                        on_click=lambda e: finish_enable_2fa(),
                        style=ft.ButtonStyle(bgcolor="green", color="white")
                    )
                ]
            )
            open_dialog(backup_codes_dlg)
        else:
            two_fa_msg.value = "❌ Failed to enable 2FA"
            two_fa_msg.color = "red"
            page.update()

    def finish_enable_2fa():
        """Finish enabling 2FA"""
        close_dialog()
        two_fa_msg.value = "✅ 2FA enabled successfully!"
        two_fa_msg.color = "green"
        page.snack_bar = ft.SnackBar(
            ft.Text("✅ Two-Factor Authentication enabled!"),
            bgcolor=ft.Colors.GREEN
        )
        page.snack_bar.open = True
        build_ui()  # Rebuild to update UI

    def show_2fa_settings(e):
        """Show 2FA settings page"""
        # Refresh user data
        fresh_user = db.query(User).filter(User.id == user.id).first()
        
        two_fa_status_text = ft.Text(
            f"🟢 Enabled" if fresh_user.two_fa_enabled else "🔴 Disabled",
            size=18,
            weight="bold",
            color="green" if fresh_user.two_fa_enabled else "red"
        )
        
        toggle_btn = ft.ElevatedButton(
            text="Disable 2FA" if fresh_user.two_fa_enabled else "Enable 2FA",
            icon=ft.Icons.LOCK_OPEN if fresh_user.two_fa_enabled else ft.Icons.LOCK,
            on_click=toggle_2fa,
            style=ft.ButtonStyle(
                bgcolor="red" if fresh_user.two_fa_enabled else "green",
                color="white"
            ),
            width=250
        )
        
        # Build 2FA settings dialog
        two_fa_dlg = ft.AlertDialog(
            title=ft.Text("🔐 Two-Factor Authentication"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Add an extra layer of security to your account",
                        size=14,
                        color="grey700"
                    ),
                    ft.Divider(),
                    ft.Row([
                        ft.Text("Status:", size=16, weight="bold"),
                        two_fa_status_text
                    ], spacing=10),
                    ft.Container(height=10),
                    ft.Text(
                        "When enabled, you'll receive a 6-digit code via email each time you log in.",
                        size=12,
                        color="grey600"
                    ),
                    ft.Container(height=10),
                    toggle_btn,
                    two_fa_msg
                ], tight=True, spacing=10),
                width=400
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog)
            ]
        )
        
        open_dialog(two_fa_dlg)

    # Toggle edit mode
    def toggle_edit(e):
        edit_mode_ref["value"] = not edit_mode_ref["value"]
        page.session.set("profile_edit_mode", edit_mode_ref["value"])
        # Rebuild UI instead of navigating
        build_ui()

    def logout_user(e):
        page.session.set("user", None)
        page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
        page.go("/logout")

    # Placeholder click handlers
    def show_coming_soon(feature_name):
        def handler(e):
            page.snack_bar = ft.SnackBar(ft.Text(f"{feature_name} - Coming soon!"), open=True)
            page.update()
        return handler

    # Fixed footer at bottom - NO SPACING, TOUCHES BOTTOM
    footer = ft.Container(
        content=ft.Row([
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.RESTAURANT_MENU,
                    tooltip="Food",
                    on_click=lambda e: page.go("/home")
                ),
                ft.Text("Food", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.SEARCH,
                    tooltip="Search",
                    on_click=lambda e: page.go("/home")
                ),
                ft.Text("Search", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.HISTORY,
                    tooltip="Orders",
                    on_click=lambda e: page.go("/orders")
                ),
                ft.Text("Orders", size=10, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            
            ft.Column([
                ft.IconButton(
                    icon=ft.Icons.PERSON,
                    tooltip="Profile",
                    icon_color="blue700"
                ),
                ft.Text("Profile", size=10, text_align=ft.TextAlign.CENTER, color="blue700")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
        bgcolor="white",
        padding=ft.padding.symmetric(vertical=8, horizontal=0),
        border=ft.border.only(top=ft.BorderSide(1, "grey300")),
        margin=0
    )

    # Build UI function
    def build_ui():
        # Refresh has_password status
        nonlocal has_password
        has_password = bool(user.phone)
        
        if not edit_mode_ref["value"]:
            # View mode - Show "Your Profile" header
            header_container.content = ft.Text("👤 Your Profile", size=24, weight="bold")
            
            # View mode - Show profile card
            content_container.content = ft.Column(
                [
                    # Profile Card (Image, Name, Email, Edit Button)
                    ft.Container(
                        content=ft.Row(
                            [
                                get_profile_image(),
                                ft.Container(width=20),
                                ft.Column(
                                    [
                                        ft.Text(user.full_name, size=18, weight="bold"),
                                        ft.Text(user.email, size=14, color="grey700"),
                                    ],
                                    spacing=5
                                ),
                                ft.Container(expand=True),
                                ft.TextButton(
                                    "Edit",
                                    on_click=toggle_edit,
                                    style=ft.ButtonStyle(
                                        color="blue700"
                                    )
                                )
                            ],
                            alignment=ft.MainAxisAlignment.START
                        ),
                        border=ft.border.all(1, "grey300"),
                        border_radius=10,
                        bgcolor="white",
                        padding=20,
                        margin=ft.margin.symmetric(horizontal=20, vertical=10)
                    ),
                    
                    # Statistics Row (3 separate cards with gaps)
                    ft.Container(
                        content=ft.Row(
                            [
                                # Total Orders Card
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(str(total_orders), size=24, weight="bold"),
                                            ft.Text("Orders", size=12, color="grey700"),
                                        ],
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=2
                                    ),
                                    border=ft.border.all(1, "grey300"),
                                    border_radius=10,
                                    bgcolor="white",
                                    padding=20,
                                    expand=1
                                ),
                                
                                ft.Container(width=10),  # Gap between cards
                                
                                # Total Spent Card
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(f"₱{total_spent:.0f}", size=24, weight="bold"),
                                            ft.Text("Spent", size=12, color="grey700"),
                                        ],
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=2
                                    ),
                                    border=ft.border.all(1, "grey300"),
                                    border_radius=10,
                                    bgcolor="white",
                                    padding=20,
                                    expand=1
                                ),
                                
                                ft.Container(width=10),  # Gap between cards
                                
                                # Rating Card
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text("5", size=24, weight="bold"),
                                            ft.Text("Rating", size=12, color="grey700"),
                                        ],
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=2
                                    ),
                                    border=ft.border.all(1, "grey300"),
                                    border_radius=10,
                                    bgcolor="white",
                                    padding=20,
                                    expand=1
                                ),
                            ],
                            spacing=0
                        ),
                        margin=ft.margin.symmetric(horizontal=20, vertical=10)
                    ),
                    
                    # Profile Options Section (6 clickable items with row gaps) - ADDED 2FA
                    ft.Container(
                        content=ft.Column([
                            # Two-Factor Authentication (NEW)
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.LOCK, color="blue700", size=30),
                                    ft.Container(width=15),
                                    ft.Column([
                                        ft.Text("Two-Factor Authentication", size=16, weight="w500"),
                                        ft.Text(
                                            "🟢 Enabled" if user.two_fa_enabled else "🔴 Disabled",
                                            size=12,
                                            color="green" if user.two_fa_enabled else "red"
                                        )
                                    ], spacing=2),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="grey"),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=15,
                                on_click=show_2fa_settings,
                                ink=True
                            ),
                            
                            ft.Container(height=10),  # Gap between items
                            
                            # Delivery Address
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.LOCATION_ON, color="blue700", size=30),
                                    ft.Container(width=15),
                                    ft.Text("Delivery Address", size=16, weight="w500"),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="grey"),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=15,
                                on_click=show_coming_soon("Delivery Address"),
                                ink=True
                            ),
                            
                            ft.Container(height=10),  # Gap between items
                            
                            # Payment Method
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.PAYMENT, color="blue700", size=30),
                                    ft.Container(width=15),
                                    ft.Text("Payment Method", size=16, weight="w500"),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="grey"),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=15,
                                on_click=show_coming_soon("Payment Method"),
                                ink=True
                            ),
                            
                            ft.Container(height=10),  # Gap between items
                            
                            # Help & Support
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.HELP_OUTLINE, color="blue700", size=30),
                                    ft.Container(width=15),
                                    ft.Text("Help & Support", size=16, weight="w500"),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="grey"),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=15,
                                on_click=show_coming_soon("Help & Support"),
                                ink=True
                            ),
                            
                            ft.Container(height=10),  # Gap between items
                            
                            # Terms & Policies
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.DESCRIPTION, color="blue700", size=30),
                                    ft.Container(width=15),
                                    ft.Text("Terms & Policies", size=16, weight="w500"),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="grey"),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=15,
                                on_click=show_coming_soon("Terms & Policies"),
                                ink=True
                            ),
                            
                            ft.Container(height=10),  # Gap between items
                            
                            # Settings
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.SETTINGS, color="blue700", size=30),
                                    ft.Container(width=15),
                                    ft.Text("Settings", size=16, weight="w500"),
                                    ft.Container(expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="grey"),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=15,
                                on_click=show_coming_soon("Settings"),
                                ink=True
                            ),
                        ], spacing=0),
                        margin=ft.margin.symmetric(horizontal=20, vertical=10)
                    ),
                    
                    # Logout Button (double the gap = 20px margin top)
                    ft.Container(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.LOGOUT, color="red700", size=30),
                                ft.Container(width=15),
                                ft.Text("Log Out", size=16, weight="w500", color="red700"),
                                ft.Container(expand=True),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color="red700"),
                            ], alignment=ft.MainAxisAlignment.START),
                            border=ft.border.all(1, "red300"),
                            border_radius=10,
                            bgcolor="white",
                            padding=15,
                            on_click=logout_user,
                            ink=True
                        ),
                        margin=ft.margin.only(left=20, right=20, top=20, bottom=10)
                    ),
                    
                    # Version Text
                    ft.Container(
                        content=ft.Text("Version 1.0", size=12, color="grey600", italic=True),
                        alignment=ft.alignment.center,
                        padding=ft.padding.only(bottom=20)
                    ),
                    
                    message,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO
            )
        else:
            # Edit mode - Show ONLY "Edit Profile" header with back button
            header_container.content = ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=toggle_edit,
                        tooltip="Cancel"
                    ),
                    ft.Text("Edit Profile", size=24, weight="bold"),
                ],
                alignment=ft.MainAxisAlignment.START
            )
            
            # Build password section based on account type
            if has_password:
                # User has password - show Change Password section
                password_section = ft.Column([
                    ft.Text("Change Password", size=18, weight="bold"),
                    ft.Text("Update your current password", size=12, color="grey600"),
                    old_pass,
                    new_pass,
                    confirm_pass,
                    ft.ElevatedButton(
                        "Update Password",
                        on_click=handle_change_password,
                        style=ft.ButtonStyle(
                            bgcolor="green700",
                            color="white"
                        )
                    ),
                    pass_msg,
                ], spacing=10)
            else:
                # Google user - show Set Password section
                password_section = ft.Column([
                    ft.Text("Set Password", size=18, weight="bold"),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, color="blue", size=20),
                            ft.Text(
                                "You signed up with Google. Set a password to also login with email.",
                                size=12,
                                color="grey600",
                                expand=True
                            )
                        ], spacing=10),
                        bgcolor="blue50",
                        padding=10,
                        border_radius=5
                    ),
                    set_new_pass,
                    set_confirm_pass,
                    ft.ElevatedButton(
                        "Set Password",
                        icon=ft.Icons.LOCK,
                        on_click=handle_set_password,
                        style=ft.ButtonStyle(
                            bgcolor="blue700",
                            color="white"
                        )
                    ),
                    pass_msg,
                ], spacing=10)
            
            # Edit mode - Show edit form
            content_container.content = ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        # Profile Image Section
                        ft.Container(
                            content=ft.Column(
                                [
                                    get_profile_image(),
                                    ft.ElevatedButton(
                                        "Change Profile Picture",
                                        icon=ft.Icons.CAMERA_ALT,
                                        on_click=lambda e: file_picker.pick_files(
                                            allowed_extensions=["png", "jpg", "jpeg"],
                                            allow_multiple=False
                                        )
                                    ),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                spacing=10
                            ),
                            padding=20
                        ),
                        
                        ft.Divider(),
                        
                        # Account Info Section
                        ft.Text("Account Info", size=18, weight="bold"),
                        full_name_field,
                        email_field,
                        phone_field,
                        
                        ft.ElevatedButton(
                            "Save Changes",
                            on_click=handle_update_profile,
                            style=ft.ButtonStyle(
                                bgcolor="blue700",
                                color="white"
                            )
                        ),
                        message,
                        
                        ft.Divider(),
                        
                        # Password Section (dynamic based on account type)
                        password_section,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=10
                )
            )
        
        page.update()

    # Main layout with fixed footer - NO SPACING
    page.clean()
    page.add(
        ft.Column([
            # Header (changes based on mode)
            header_container,
            # Content (scrollable)
            content_container,
            # Footer (fixed) - NO SPACING
            footer
        ], expand=True, spacing=0)
    )
    
    # Initial build
    build_ui()