import flet as ft
from core.two_fa_service import enable_2fa, disable_2fa
from models.user import User

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