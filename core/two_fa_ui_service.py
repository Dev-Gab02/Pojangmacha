import flet as ft
import threading
from core.two_fa_service import enable_2fa, disable_2fa, send_2fa_code, verify_2fa_code, verify_backup_code
from core.email_service import verify_code, resend_verification_code
from core.auth_service import create_user
from models.user import User

# ===== PROFILE 2FA DIALOGS =====

def show_2fa_settings_dialog(page, db, user, on_change_callback):
    """Show 2FA settings dialog with enable/disable toggle"""
    fresh_user = db.query(User).filter(User.id == user.id).first()
    
    # Status in one row: "Status: 🟢 Enabled" with white "Status:" text
    status_row = ft.Row([
        ft.Text("Status:", size=14, weight="bold", color="white"),
        ft.Text(
            f"🟢 Enabled" if fresh_user.two_fa_enabled else "🔴 Disabled",
            size=14,
            weight="bold",
            color="green" if fresh_user.two_fa_enabled else "red"
        )
    ], spacing=8, alignment=ft.MainAxisAlignment.CENTER)
    
    def toggle_2fa_handler(e):
        """Handle enable/disable toggle"""
        if fresh_user.two_fa_enabled:
            show_disable_2fa_dialog(page, db, user, on_change_callback)
        else:
            show_enable_2fa_dialog(page, db, user, on_change_callback)
        dialog.open = False
        page.update()
    
    toggle_btn = ft.Container(
        content=ft.ElevatedButton(
            text="Disable" if fresh_user.two_fa_enabled else "Enable",
            on_click=toggle_2fa_handler,
            style=ft.ButtonStyle(
                bgcolor="red" if fresh_user.two_fa_enabled else "green",
                color="white"
            ),
            width=200
        ),
        alignment=ft.alignment.center,
        padding=ft.padding.only(top=15)
    )
    
    def close_2fa_settings(ev):
        dialog.open = False
        page.update()
    
    # 2FA SETTINGS DIALOG - Optimized spacing
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Text("Two-Factor Authentication", size=16, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center
        ),
        title_padding=ft.padding.only(left=20, right=20, top=20, bottom=0),
        content=ft.Container(
            content=ft.Column([
                ft.Text(
                    "Add an extra layer of security to your account",
                    size=12,
                    color="white",
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=2),
                status_row,
                ft.Container(height=4),
                ft.Text(
                    "When enabled, you'll receive a 6-digit code via email each time you log in.",
                    size=12,
                    color="white",
                    text_align=ft.TextAlign.CENTER
                ),
                toggle_btn
            ], tight=True, spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=260,
            padding=ft.padding.only(left=20, right=20, top=0, bottom=0)
        ),
        actions=[
            ft.TextButton("Close", on_click=close_2fa_settings)
        ],
        actions_padding=ft.padding.only(left=20, right=20, bottom=20, top=0)
    )
    
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


def show_enable_2fa_dialog(page, db, user, on_success_callback):
    """Show backup codes after enabling 2FA"""
    backup_codes = enable_2fa(db, user.id)
    
    if backup_codes:
        user.two_fa_enabled = True
        
        def finish_enable(ev):
            dialog.open = False
            page.update()
            
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Two-Factor Authentication enabled!"),
                bgcolor=ft.Colors.GREEN
            )
            page.snack_bar.open = True
            page.update()
            
            # Trigger callback to rebuild UI
            if on_success_callback:
                on_success_callback()
        
        # BACKUP CODES DIALOG - Optimized spacing
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Container(
                content=ft.Text("Save Your Backup Codes", size=16, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                alignment=ft.alignment.center
            ),
            title_padding=ft.padding.only(left=20, right=20, top=20, bottom=0),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Save these codes in a safe place. You'll need them if you lose access to your email.", 
                        size=12,
                        color="white",
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=4),
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
                        spacing=4),
                        bgcolor=ft.Colors.GREY_200,
                        padding=ft.padding.only(left=12, right=12, top=0, bottom=12),
                        border_radius=5,
                        border=ft.border.all(2, ft.Colors.BLUE_200),
                        alignment=ft.alignment.center
                    ),
                    ft.Container(height=4),
                    ft.Text(
                        "These codes will only be shown once!", 
                        color="red", 
                        size=12,
                        weight="bold",
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=2),
                    ft.Text(
                        "Each backup code can only be used once.",
                        size=11,
                        color="white",
                        text_align=ft.TextAlign.CENTER
                    )
                ], 
                tight=True, 
                scroll=ft.ScrollMode.AUTO,
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=260,
                padding=ft.padding.only(left=20, right=20, top=0, bottom=0)
            ),
            actions=[
                ft.Container(
                    content=ft.ElevatedButton(
                        "I've Saved My Codes",
                        on_click=finish_enable,
                        style=ft.ButtonStyle(bgcolor="green", color="white"),
                        width=200
                    ),
                    alignment=ft.alignment.center
                )
            ],
            actions_padding=ft.padding.only(left=20, right=20, bottom=20, top=0)
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()
    else:
        page.snack_bar = ft.SnackBar(
            ft.Text("❌ Failed to enable 2FA"),
            bgcolor=ft.Colors.RED
        )
        page.snack_bar.open = True
        page.update()


def show_disable_2fa_dialog(page, db, user, on_success_callback):
    """Show confirmation dialog for disabling 2FA"""
    
    def cancel_disable(ev):
        dialog.open = False
        page.update()
    
    def confirm_disable(ev):
        dialog.open = False
        page.update()
        
        if disable_2fa(db, user.id):
            user.two_fa_enabled = False
            page.snack_bar = ft.SnackBar(
                ft.Text("✅ Two-Factor Authentication disabled"),
                bgcolor=ft.Colors.ORANGE
            )
            page.snack_bar.open = True
            page.update()
            
            # Trigger callback to rebuild UI
            if on_success_callback:
                on_success_callback()
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Failed to disable 2FA"),
                bgcolor=ft.Colors.RED
            )
            page.snack_bar.open = True
            page.update()
    
    # DISABLE 2FA DIALOG - Optimized spacing
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Disable 2FA?", size=16, weight="bold", color="white"),
        title_padding=ft.padding.only(left=24, right=20, top=20, bottom=0),
        content=ft.Container(
            content=ft.Text(
                "Are you sure you want to disable two-factor authentication?\n\nThis will make your account less secure.",
                size=12,
                color="white"
            ),
            width=260,
            padding=ft.padding.only(left=0, right=20, top=0, bottom=0)
        ),
        actions=[
            ft.TextButton("Cancel", on_click=cancel_disable),
            ft.ElevatedButton(
                "Disable",
                on_click=confirm_disable,
                style=ft.ButtonStyle(bgcolor="red", color="white")
            )
        ],
        actions_padding=ft.padding.only(left=20, right=20, bottom=20, top=0)
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


# ===== LOGIN 2FA DIALOG =====

def show_login_2fa_dialog(page, db, user, on_success_callback, on_cancel_callback=None):
    """Show 2FA verification dialog for login
    
    Args:
        page: Flet page object
        db: Database session
        user: User object
        on_success_callback: Function to call on successful verification
        on_cancel_callback: Optional function to call when user cancels (for UI cleanup)
    """
    
    # Single input for both 2FA code and backup code
    code_input = ft.TextField(
        label="Enter 6-digit or backup code",
        label_style=ft.TextStyle(color="white"),
        color="white",
        width=300,
        max_length=9,
        text_align=ft.TextAlign.CENTER,
        border_radius=12,
        filled=True,
        bgcolor="transparent",
        border_color="white",
        focused_border_color="orange",
        text_size=16,
        height=55
    )
    
    dialog_message = ft.Text(
        f"Code sent to {user.email}",
        size=12,
        color="white",
        text_align=ft.TextAlign.CENTER
    )
    
    def verify_code_input(ev):
        """Auto-detect and verify 2FA code or backup code"""
        code = code_input.value
        
        if not code or not code.strip():
            dialog_message.value = "❌ Please enter a code"
            dialog_message.color = "red"
            page.update()
            return
        
        code = code.strip()
        
        # Auto-detect: 6 digits = 2FA code, XXXX-XXXX format = backup code
        if len(code) == 6 and code.isdigit():
            # Verify as 2FA code
            if verify_2fa_code(user.email, code):
                close_2fa_dialog()
                on_success_callback(user)
                return
            else:
                dialog_message.value = "❌ Invalid 2FA code"
                dialog_message.color = "red"
                page.update()
        
        elif len(code) == 9 and code[4] == '-':
            # Verify as backup code
            fresh_user = db.query(User).filter(User.id == user.id).first()
            if verify_backup_code(fresh_user, code):
                db.commit()
                close_2fa_dialog()
                
                page.snack_bar = ft.SnackBar(
                    ft.Text("⚠️ Backup code used. Generate new codes in your profile."),
                    bgcolor=ft.Colors.ORANGE
                )
                page.snack_bar.open = True
                
                on_success_callback(user)
                return
            else:
                dialog_message.value = "❌ Invalid backup code"
                dialog_message.color = "red"
                page.update()
        
        else:
            dialog_message.value = "❌ Invalid format. Enter 6 digits or XXXX-XXXX"
            dialog_message.color = "red"
            page.update()
    
    def resend_code_action(ev):
        """Resend 2FA code"""
        dialog_message.value = "Resending code..."
        dialog_message.color = "blue700"
        page.update()
        
        def resend_thread():
            if send_2fa_code(user.email):
                dialog_message.value = f"Code sent to {user.email}"
                dialog_message.color = "white"
            else:
                dialog_message.value = "❌ Failed to send code"
                dialog_message.color = "red"
            page.update()
        
        thread = threading.Thread(target=resend_thread, daemon=True)
        thread.start()

    def cancel_2fa(ev):
        """Cancel 2FA verification"""
        close_2fa_dialog()
        # ✅ ADDED: Call cancel callback to reset login UI
        if on_cancel_callback:
            on_cancel_callback()
    
    def close_2fa_dialog():
        """Close the 2FA dialog"""
        try:
            two_fa_dialog.open = False
            page.update()
        except Exception as ex:
            print(f"Close 2FA dialog error: {ex}")
    
    # Resend button (centered text button)
    resend_btn = ft.Container(
        content=ft.TextButton(
            "Resend Code",
            on_click=resend_code_action
        ),
        alignment=ft.alignment.center
    )
    
    # 2FA Dialog
    two_fa_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Text(
                "Two-Factor Authentication",
                size=16,
                weight="bold",
                color="white",
                text_align=ft.TextAlign.CENTER
            ),
            alignment=ft.alignment.center
        ),
        title_padding=ft.padding.only(left=20, right=20, top=20, bottom=0),
        content=ft.Container(
            content=ft.Column([
                ft.Text(
                    "Enter the code sent to your email",
                    size=12,
                    color="white",
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=10),
                code_input,
                ft.Container(height=10),
                resend_btn,
                ft.Container(height=5),
                dialog_message
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            width=300,
            padding=ft.padding.only(left=20, right=20, top=0, bottom=0)
        ),
        actions=[
            ft.TextButton("Cancel", on_click=cancel_2fa),
            ft.ElevatedButton(
                "Verify",
                on_click=verify_code_input,
                style=ft.ButtonStyle(bgcolor="green", color="white")
            )
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        actions_padding=ft.padding.only(left=20, right=20, bottom=20, top=0)
    )
    
    page.overlay.append(two_fa_dialog)
    two_fa_dialog.open = True
    page.update()


# ===== SIGNUP EMAIL VERIFICATION DIALOG =====

def show_signup_verification_dialog(page, db, temp_user_data, on_success_callback, on_cancel_callback=None):
    """Show email verification dialog for signup
    
    Args:
        page: Flet page object
        db: Database session
        temp_user_data: Dict with {full_name, email, phone, password}
        on_success_callback: Function to call after successful account creation
        on_cancel_callback: Optional function to reset signup UI
    """
    
    # Single input for 6-digit code
    verification_code_input = ft.TextField(
        label="Enter 6-digit code",
        label_style=ft.TextStyle(color="white"),
        color="white",
        width=300,
        max_length=6,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        filled=True,
        bgcolor="transparent",
        border_color="white",
        focused_border_color="orange",
        text_size=16,
        height=55
    )
    
    dialog_message = ft.Text(
        f"Code sent to {temp_user_data['email']}",
        size=12,
        color="white",
        text_align=ft.TextAlign.CENTER
    )
    
    def verify_code_action(ev):
        """Verify code and create account"""
        if not verification_code_input.value or len(verification_code_input.value) != 6:
            dialog_message.value = "❌ Please enter the 6-digit code"
            dialog_message.color = "red"
            page.update()
            return
        
        if verify_code(temp_user_data["email"], verification_code_input.value):
            # Code is valid - create account
            new_user = create_user(
                db,
                temp_user_data["full_name"],
                temp_user_data["email"],
                temp_user_data["phone"],
                temp_user_data["password"]
            )
            
            if new_user:
                # ✅ Close dialog and call success callback
                close_verification_dialog()
                on_success_callback()
            else:
                dialog_message.value = "❌ Error creating account"
                dialog_message.color = "red"
                page.update()
        else:
            dialog_message.value = "❌ Invalid or expired code"
            dialog_message.color = "red"
            page.update()
    
    def resend_code_action(ev):
        """Resend verification code"""
        dialog_message.value = "Resending..."
        dialog_message.color = "white"
        page.update()
        
        def resend_thread():
            if resend_verification_code(temp_user_data["email"]):
                dialog_message.value = f"Code sent to {temp_user_data['email']}"
                dialog_message.color = "white"
            else:
                dialog_message.value = "❌ Failed to send code"
                dialog_message.color = "red"
            page.update()
        
        thread = threading.Thread(target=resend_thread, daemon=True)
        thread.start()
    
    def cancel_verification(ev):
        """Cancel verification and return to signup form"""
        close_verification_dialog()
        # ✅ Call cancel callback to reset signup UI
        if on_cancel_callback:
            on_cancel_callback()
    
    def close_verification_dialog():
        """Close the verification dialog"""
        try:
            verification_dialog.open = False
            page.update()
        except Exception as ex:
            print(f"Close verification dialog error: {ex}")
    
    # Resend button (centered text button)
    resend_btn = ft.Container(
        content=ft.TextButton(
            "Resend Code",
            on_click=resend_code_action
        ),
        alignment=ft.alignment.center
    )
    
    # Verification Dialog (EXACTLY MATCHING LOGIN 2FA)
    verification_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Container(
            content=ft.Text(
                "Verify Your Email",
                size=16,
                weight="bold",
                color="white",
                text_align=ft.TextAlign.CENTER
            ),
            alignment=ft.alignment.center
        ),
        title_padding=ft.padding.only(left=20, right=20, top=20, bottom=0),
        content=ft.Container(
            content=ft.Column([
                ft.Text(
                    "Enter the code sent to your email",
                    size=12,
                    color="white",
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=10),
                verification_code_input,
                ft.Container(height=10),
                resend_btn,
                ft.Container(height=5),
                dialog_message
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            width=300,
            padding=ft.padding.only(left=20, right=20, top=0, bottom=0)
        ),
        actions=[
            ft.TextButton("Cancel", on_click=cancel_verification),
            ft.ElevatedButton(
                "Verify",
                on_click=verify_code_action,
                style=ft.ButtonStyle(bgcolor="green", color="white")
            )
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        actions_padding=ft.padding.only(left=20, right=20, bottom=20, top=0)
    )
    
    # ✅ EXACTLY MATCHING LOGIN (no page.dialog assignment)
    page.overlay.append(verification_dialog)
    verification_dialog.open = True
    page.update()