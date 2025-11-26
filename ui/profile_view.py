import os
import flet as ft
from core.db import SessionLocal
from core.profile_service import get_user_by_id, update_profile, change_password
from models.order import Order
from models.user import User
from core.two_fa_service import enable_2fa, disable_2fa

def profile_view_widget(page, on_nav):
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

    # ✅ FIX: Google users have NO phone number (phone is the real indicator)
    has_password_ref = {"value": bool(user.phone and user.phone.strip())}

    # Profile image (use placeholder if none)
    def get_profile_image():
        profile_image_path = user.profile_picture if user.profile_picture and os.path.exists(user.profile_picture) else None
        
        if profile_image_path:
            return ft.Image(
                src=profile_image_path,
                width=80,
                height=80,
                fit=ft.ImageFit.COVER,
                border_radius=40
            )
        else:
            # Placeholder avatar with user's initials
            initials = "".join([name[0].upper() for name in user.full_name.split()[:2]])
            return ft.Container(
                content=ft.Text(initials, size=28, weight="bold", color="white"),
                width=80,
                height=80,
                border_radius=40,
                bgcolor="blue400",
                alignment=ft.alignment.center
            )

    # Profile fields for editing
    full_name_field = ft.TextField(
        label="Full Name", 
        value=user.full_name, 
        width=300, 
        color="black", 
        label_style=ft.TextStyle(color="black")
    )
    
    # ✅ Email as disabled TextField (looks like input with border)
    email_field = ft.TextField(
        label="Email", 
        value=user.email, 
        width=300, 
        disabled=True, 
        color="grey700",
        bgcolor="grey100",
        label_style=ft.TextStyle(color="grey700"),
        border_color="grey400",
        filled=True
    )
    
    phone_field = ft.TextField(
        label="Phone Number", 
        value=user.phone or "", 
        width=300, 
        color="black", 
        label_style=ft.TextStyle(color="black")
    )
    
    message = ft.Text("", color="green")

    # Password change fields (for users with existing password)
    old_pass = ft.TextField(label="Current Password", password=True, can_reveal_password=True, width=300, color="black", label_style=ft.TextStyle(color="black"))
    new_pass = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=300, color="black", label_style=ft.TextStyle(color="black"))
    confirm_pass = ft.TextField(label="Confirm New Password", password=True, can_reveal_password=True, width=300, color="black", label_style=ft.TextStyle(color="black"))
    
    # Set password fields (for Google users without password)
    set_new_pass = ft.TextField(label="New Password", password=True, can_reveal_password=True, width=300, color="black", label_style=ft.TextStyle(color="black"))
    set_confirm_pass = ft.TextField(label="Confirm Password", password=True, can_reveal_password=True, width=300, color="black", label_style=ft.TextStyle(color="black"))
    
    pass_msg = ft.Text("", color="red")

    # Container that will hold the content
    content_container = ft.Container(expand=True)
    
    # Header container that changes based on mode
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
                user.profile_picture = dest
                db.commit()
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Profile picture updated!"),
                    bgcolor=ft.Colors.GREEN
                )
                page.snack_bar.open = True
                build_ui()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Error uploading image"),
                    bgcolor=ft.Colors.RED
                )
                page.snack_bar.open = True
                page.update()

    file_picker = ft.FilePicker(on_result=on_file_pick)
    page.overlay.append(file_picker)

    # Update profile handler
    def handle_update_profile(e):
        ok, msg = update_profile(
            db, user.id, 
            full_name_field.value.strip(), 
            email_field.value.strip(), 
            phone_field.value.strip(), 
            user.profile_picture or ""
        )

        if ok:
            page.session.set("user", {
                "id": user.id,
                "email": email_field.value.strip(),
                "full_name": full_name_field.value.strip(),
                "role": user.role
            })
            edit_mode_ref["value"] = False
            page.session.set("profile_edit_mode", False)
            
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Profile updated successfully!"),
                bgcolor=ft.Colors.GREEN
            )
            page.snack_bar.open = True
            build_ui()
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ {msg}"),
                bgcolor=ft.Colors.RED
            )
            page.snack_bar.open = True
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
            if ok:
                old_pass.value = new_pass.value = confirm_pass.value = ""
                pass_msg.value = ""
                
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Password changed successfully!"),
                    bgcolor=ft.Colors.GREEN
                )
                page.snack_bar.open = True
            else:
                pass_msg.value = msg
                pass_msg.color = "red"
        page.update()

    # ✅ Set password handler (for Google users) - SWITCHES TO CHANGE PASSWORD MODE
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
            from core.auth_service import hash_password
            try:
                # ✅ Set both password AND phone (mark as having password)
                user.password_hash = hash_password(set_new_pass.value)
                
                # ✅ Set phone to a placeholder to mark as "has password"
                if not user.phone or not user.phone.strip():
                    user.phone = "set_via_google"  # Marker that password was set
                
                db.commit()
                
                # ✅ Clear fields and message
                set_new_pass.value = set_confirm_pass.value = ""
                pass_msg.value = ""
                
                # ✅ Update reference to show "Change Password" section
                has_password_ref["value"] = True
                
                # ✅ Show success snackbar
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ Password set! You can now use email/password login."),
                    bgcolor=ft.Colors.GREEN
                )
                page.snack_bar.open = True
                
                # ✅ Rebuild UI to show "Change Password" section
                build_ui()
                
            except Exception as ex:
                print(f"Set password error: {ex}")
                pass_msg.value = "❌ Error setting password."
                pass_msg.color = "red"
                page.update()

    # 2FA Functions
    dialog_ref = {"current": None}
    
    def open_dialog(dlg):
        close_dialog()
        dialog_ref["current"] = dlg
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def close_dialog(e=None):
        if dialog_ref["current"]:
            dialog_ref["current"].open = False
            if dialog_ref["current"] in page.overlay:
                page.overlay.remove(dialog_ref["current"])
            dialog_ref["current"] = None
        page.update()

    def toggle_2fa(e):
        fresh_user = db.query(User).filter(User.id == user.id).first()
        
        if fresh_user.two_fa_enabled:
            confirm_dlg = ft.AlertDialog(
                title=ft.Text("Disable 2FA?", size=16, weight="bold", color="black"),
                content=ft.Container(
                    content=ft.Text(
                        "Are you sure you want to disable two-factor authentication?\n\nThis will make your account less secure.",
                        size=12,
                        color="grey700"
                    ),
                    width=360
                ),
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
            enable_2fa_process()

    def confirm_disable_2fa():
        close_dialog()
        
        if disable_2fa(db, user.id):
            user.two_fa_enabled = False
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Two-Factor Authentication disabled"),
                bgcolor=ft.Colors.ORANGE
            )
            page.snack_bar.open = True
            page.update()
            build_ui()
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Failed to disable 2FA"),
                bgcolor=ft.Colors.RED
            )
            page.snack_bar.open = True
            page.update()

    def enable_2fa_process():
        backup_codes = enable_2fa(db, user.id)
        
        if backup_codes:
            user.two_fa_enabled = True
            
            backup_codes_dlg = ft.AlertDialog(
                title=ft.Text("Save Your Backup Codes", size=16, weight="bold", color="black"),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Save these codes in a safe place. You'll need them if you lose access to your email.", 
                            size=12,
                            color="grey700",
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(height=8),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(
                                    code,
                                    selectable=True,
                                    size=14,
                                    weight="bold",
                                    color="black",
                                    text_align=ft.TextAlign.CENTER
                                ) for code in backup_codes
                            ], 
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5),
                            bgcolor=ft.Colors.GREY_200,
                            padding=15,
                            border_radius=5,
                            border=ft.border.all(2, ft.Colors.BLUE_200),
                            alignment=ft.alignment.center
                        ),
                        ft.Container(height=8),
                        ft.Text(
                            "These codes will only be shown once!", 
                            color="red", 
                            size=12,
                            weight="bold",
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            "Each backup code can only be used once.",
                            size=11,
                            color="grey600",
                            text_align=ft.TextAlign.CENTER
                        )
                    ], 
                    tight=True, 
                    scroll=ft.ScrollMode.AUTO,
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    width=360
                ),
                actions=[
                    ft.Container(
                        content=ft.ElevatedButton(
                            "I've Saved My Codes",
                            on_click=lambda e: finish_enable_2fa(),
                            style=ft.ButtonStyle(bgcolor="green", color="white"),
                            width=200
                        ),
                        alignment=ft.alignment.center
                    )
                ]
            )
            open_dialog(backup_codes_dlg)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Failed to enable 2FA"),
                bgcolor=ft.Colors.RED
            )
            page.snack_bar.open = True
            page.update()

    def finish_enable_2fa():
        close_dialog()
        page.snack_bar = ft.SnackBar(
            ft.Text("✅ Two-Factor Authentication enabled!"),
            bgcolor=ft.Colors.GREEN
        )
        page.snack_bar.open = True
        page.update()
        build_ui()

    def show_2fa_settings(e):
        fresh_user = db.query(User).filter(User.id == user.id).first()
        
        two_fa_status_text = ft.Text(
            f"🟢 Enabled" if fresh_user.two_fa_enabled else "🔴 Disabled",
            size=14,
            weight="bold",
            color="green" if fresh_user.two_fa_enabled else "red"
        )
        
        toggle_btn = ft.Container(
            content=ft.ElevatedButton(
                text="Disable" if fresh_user.two_fa_enabled else "Enable",
                on_click=toggle_2fa,
                style=ft.ButtonStyle(
                    bgcolor="red" if fresh_user.two_fa_enabled else "green",
                    color="white"
                ),
                width=200
            ),
            alignment=ft.alignment.center
        )
        
        two_fa_dlg = ft.AlertDialog(
            title=ft.Text("Two-Factor Authentication", size=16, weight="bold", color="black"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Add an extra layer of security to your account",
                        size=12,
                        color="grey700"
                    ),
                    ft.Divider(),
                    ft.Column([
                        ft.Text("Status:", size=14, weight="bold", color="black"),
                        two_fa_status_text
                    ], spacing=4),
                    ft.Container(height=8),
                    ft.Text(
                        "When enabled, you'll receive a 6-digit code via email each time you log in.",
                        size=12,
                        color="grey600"
                    ),
                    ft.Container(height=8),
                    toggle_btn
                ], tight=True, spacing=8),
                width=360
            ),
            actions=[
                ft.TextButton("Close", on_click=close_dialog)
            ]
        )
        
        open_dialog(two_fa_dlg)

    def toggle_edit(e):
        edit_mode_ref["value"] = not edit_mode_ref["value"]
        page.session.set("profile_edit_mode", edit_mode_ref["value"])
        build_ui()

    def logout_user(e):
        page.session.set("user", None)
        page.snack_bar = ft.SnackBar(ft.Text("You have been logged out."), open=True)
        page.go("/logout")

    def show_coming_soon(feature_name):
        def handler(e):
            page.snack_bar = ft.SnackBar(ft.Text(f"{feature_name} - Coming soon!"), open=True)
            page.update()
        return handler

    # Build UI function
    def build_ui():
        if not edit_mode_ref["value"]:
            # VIEW MODE
            header_container.content = ft.Column([
                ft.Container(
                    content=ft.Text("Profile", size=20, weight="bold", color="black"),
                    padding=ft.padding.only(left=15, right=15, top=15, bottom=8)
                ),
                ft.Divider(height=1, color="grey300", thickness=1)
            ], spacing=0)
            header_container.bgcolor = "grey100"
            header_container.padding = 0
            
            content_container.content = ft.Column(
                [
                    ft.Container(
                        content=ft.Row([
                            get_profile_image(),
                            ft.Container(width=10),
                            ft.Column([
                                ft.Text(
                                    user.full_name[:20] + "..." if len(user.full_name) > 20 else user.full_name,
                                    size=16,
                                    weight="bold",
                                    color="black",
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS
                                ),
                                ft.Text(
                                    user.email[:25] + "..." if len(user.email) > 25 else user.email,
                                    size=12,
                                    color="grey700",
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        "Edit",
                                        size=14,
                                        color="red",
                                        weight="normal"
                                    ),
                                    on_click=toggle_edit,
                                    ink=True,
                                    padding=ft.padding.only(top=2, bottom=0, left=0, right=0)
                                )
                            ], spacing=2, expand=True, horizontal_alignment=ft.CrossAxisAlignment.START),
                        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START),
                        border=ft.border.all(1, "grey300"),
                        border_radius=10,
                        bgcolor="white",
                        padding=15,
                        margin=ft.margin.symmetric(horizontal=15, vertical=10)
                    ),
                    
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text(str(total_orders), size=20, weight="bold", color="black"),
                                        ft.Text("Orders", size=10, color="grey700"),
                                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                                    border=ft.border.all(1, "grey300"),
                                    border_radius=10,
                                    bgcolor="white",
                                    padding=12,
                                    expand=1
                                ),
                                ft.Container(width=8),
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text(f"₱{total_spent:.0f}", size=20, weight="bold", color="black"),
                                        ft.Text("Spent", size=10, color="grey700"),
                                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                                    border=ft.border.all(1, "grey300"),
                                    border_radius=10,
                                    bgcolor="white",
                                    padding=12,
                                    expand=1
                                ),
                                ft.Container(width=8),
                                ft.Container(
                                    content=ft.Column([
                                        ft.Text("5", size=20, weight="bold", color="black"),
                                        ft.Text("Rating", size=10, color="grey700"),
                                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                                    border=ft.border.all(1, "grey300"),
                                    border_radius=10,
                                    bgcolor="white",
                                    padding=12,
                                    expand=1
                                ),
                            ],
                            spacing=0
                        ),
                        margin=ft.margin.symmetric(horizontal=15, vertical=10)
                    ),
                    
                    ft.Container(
                        content=ft.Column([
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.LOCK, color="black", size=24),
                                    ft.Container(width=12),
                                    ft.Column([
                                        ft.Text("Two-Factor Authentication", size=14, weight="w500", color="black"),
                                        ft.Text(
                                            "🟢 Enabled" if user.two_fa_enabled else "🔴 Disabled",
                                            size=11,
                                            color="green" if user.two_fa_enabled else "red"
                                        )
                                    ], spacing=2, expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="black", size=20),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=12,
                                on_click=show_2fa_settings,
                                ink=True
                            ),
                            ft.Container(height=8),
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.LOCATION_ON, color="black", size=24),
                                    ft.Container(width=12),
                                    ft.Text("Delivery Address", size=14, weight="w500", color="black", expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="black", size=20),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=12,
                                on_click=show_coming_soon("Delivery Address"),
                                ink=True
                            ),
                            ft.Container(height=8),
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.PAYMENT, color="black", size=24),
                                    ft.Container(width=12),
                                    ft.Text("Payment Method", size=14, weight="w500", color="black", expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="black", size=20),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=12,
                                on_click=show_coming_soon("Payment Method"),
                                ink=True
                            ),
                            ft.Container(height=8),
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.HELP_OUTLINE, color="black", size=24),
                                    ft.Container(width=12),
                                    ft.Text("Help & Support", size=14, weight="w500", color="black", expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="black", size=20),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=12,
                                on_click=show_coming_soon("Help & Support"),
                                ink=True
                            ),
                            ft.Container(height=8),
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.DESCRIPTION, color="black", size=24),
                                    ft.Container(width=12),
                                    ft.Text("Terms & Policies", size=14, weight="w500", color="black", expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="black", size=20),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=12,
                                on_click=show_coming_soon("Terms & Policies"),
                                ink=True
                            ),
                            ft.Container(height=8),
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.SETTINGS, color="black", size=24),
                                    ft.Container(width=12),
                                    ft.Text("Settings", size=14, weight="w500", color="black", expand=True),
                                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color="black", size=20),
                                ], alignment=ft.MainAxisAlignment.START),
                                border=ft.border.all(1, "grey300"),
                                border_radius=10,
                                bgcolor="white",
                                padding=12,
                                on_click=show_coming_soon("Settings"),
                                ink=True
                            ),
                        ], spacing=0),
                        margin=ft.margin.symmetric(horizontal=15, vertical=10)
                    ),
                    
                    ft.Container(
                        content=ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.LOGOUT, color="red700", size=24),
                                ft.Container(width=12),
                                ft.Text("Log Out", size=14, weight="w500", color="red700", expand=True),
                                ft.Icon(ft.Icons.CHEVRON_RIGHT, color="red700", size=20),
                            ], alignment=ft.MainAxisAlignment.START),
                            border=ft.border.all(1, "red300"),
                            border_radius=10,
                            bgcolor="white",
                            padding=12,
                            on_click=logout_user,
                            ink=True
                        ),
                        margin=ft.margin.only(left=15, right=15, top=15, bottom=10)
                    ),
                    
                    ft.Container(
                        content=ft.Text("Version 1.0", size=12, color="grey600", italic=True),
                        alignment=ft.alignment.center,
                        padding=ft.padding.only(bottom=20)
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO
            )
        else:
            # ✅ EDIT MODE - DYNAMIC PASSWORD SECTION
            header_container.content = ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=toggle_edit, tooltip="Cancel", icon_color="black"),
                        ft.Text("Edit Profile", size=20, weight="bold", color="black"),
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.only(left=5, right=15, top=10, bottom=8)
                ),
                ft.Divider(height=1, color="grey300", thickness=1)
            ], spacing=0)
            header_container.bgcolor = "white"
            header_container.padding = 0
            
            # Dynamic password section based on has_password_ref
            if has_password_ref["value"]:
                # User has password - show "Change Password"
                password_section = ft.Column([
                    ft.Text("Change Password", size=18, weight="bold", color="black"),
                    ft.Text("Update your current password", size=12, color="grey600"),
                    old_pass,
                    new_pass,
                    confirm_pass,
                    ft.ElevatedButton(
                        "Update Password",
                        on_click=handle_change_password,
                        style=ft.ButtonStyle(bgcolor="green700", color="white"),
                        width=200
                    ),
                    pass_msg,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            else:
                # User doesn't have password - show "Set Password"
                password_section = ft.Column([
                    ft.Text("Set Password", size=18, weight="bold", color="black"),
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
                        border_radius=5,
                        width=300
                    ),
                    set_new_pass,
                    set_confirm_pass,
                    ft.ElevatedButton(
                        "Set Password",
                        icon=ft.Icons.LOCK,
                        on_click=handle_set_password,
                        style=ft.ButtonStyle(bgcolor="blue700", color="white"),
                        width=200
                    ),
                    pass_msg,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
            
            content_container.content = ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Container(
                        content=ft.Column([
                            get_profile_image(),
                            ft.ElevatedButton(
                                "Change Profile Picture",
                                icon=ft.Icons.CAMERA_ALT,
                                on_click=lambda e: file_picker.pick_files(
                                    allowed_extensions=["png", "jpg", "jpeg"],
                                    allow_multiple=False
                                )
                            ),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        padding=20
                    ),
                    ft.Divider(),
                    
                    # Account Info Section - Email as disabled TextField
                    ft.Column([
                        ft.Text("Account Info", size=18, weight="bold", color="black"),
                        full_name_field,
                        email_field,  # Now uses TextField with disabled=True
                        phone_field,
                        ft.ElevatedButton(
                            "Save Changes",
                            on_click=handle_update_profile,
                            style=ft.ButtonStyle(bgcolor="blue700", color="white"),
                            width=200
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    
                    ft.Divider(),
                    
                    # Dynamic Password section
                    password_section,
                    
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO, spacing=10)
            )
        
        page.update()

    # Main layout
    build_ui()
    return ft.Container(
    content=ft.Column([
        header_container,
        content_container,
    ], expand=True, spacing=0),
    bgcolor="grey100" 
)