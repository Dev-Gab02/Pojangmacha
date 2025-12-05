"""
Admin Panel - Main Orchestrator
Imports and coordinates all admin tabs
"""
import flet as ft
from core.db import SessionLocal
from ui.admin_constants import BREAKPOINT
from ui.admin_food_items import build_food_items_tab
from ui.admin_orders import build_orders_tab
from ui.admin_users import build_users_tab

def admin_view(page: ft.Page):
    """
    Main admin panel view - orchestrates all tabs
    """
    db = SessionLocal()
    page.title = "Admin Panel"

    # Check if user is admin
    user_data = page.session.get("user")
    if not user_data or user_data.get("role") != "admin":
        page.snack_bar = ft.SnackBar(ft.Text("Access denied. Admins only."), open=True)
        page.go("/home")
        return

    # ✅ Detect layout mode based on window width
    is_desktop = page.window.width > BREAKPOINT
    
    print(f"📐 Admin view - Width: {page.window.width}px, Mode: {'Desktop' if is_desktop else 'Mobile'}")

    # ===================== BUILD TABS =====================
    
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            build_food_items_tab(page, db, user_data, is_desktop),
            build_orders_tab(page, db, user_data, is_desktop),
            build_users_tab(page, db, user_data, is_desktop)
        ],
        expand=True,
        # ✅ Custom tab styling
        label_color="#E9190A",  # Active tab text & icon color (red)
        unselected_label_color="black",  # Inactive tab text & icon color (black)
        indicator_color="#E9190A",  # Active tab indicator line (red)
        indicator_border_radius=0,  # Square indicator
        divider_color="grey300"  # Divider line below tabs
    )

    # ===================== HEADER & LOGOUT =====================
    
    def logout_user(e):
        page.session.set("user", None)
        page.snack_bar = ft.SnackBar(ft.Text("Logged out successfully."), open=True)
        page.go("/logout")

    # ===================== BUILD UI =====================
    
    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                # ✅ Header - WHITE background (NO gradient)
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Row([
                                ft.Text("Admin Panel", size=20, weight="bold", color="black"),
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.Icons.ANALYTICS,
                                        icon_color="black",
                                        tooltip="Analytics",
                                        on_click=lambda e: page.go("/analytics")
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.LOGOUT,
                                        icon_color="black",
                                        tooltip="Logout",
                                        on_click=logout_user
                                    )
                                ], spacing=5)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=ft.padding.only(top=15, left=15, right=15, bottom=8)
                        ),
                        ft.Divider(height=1, color="grey300", thickness=1)
                    ], spacing=0),
                    bgcolor="white",
                    padding=0
                ),
                
                # ✅ Tabs with GRADIENT background (entire remaining area)
                ft.Container(
                    content=tabs,
                    expand=True,
                    gradient=ft.LinearGradient(
                        begin=ft.alignment.top_center,
                        end=ft.alignment.bottom_center,
                        colors=["#FFF6F6", "#F7C171", "#D49535"]
                    )
                )
            ], expand=True, spacing=0),
            # ✅ Responsive container size
            width=page.window.width if is_desktop else 400,
            height=page.window.height if is_desktop else 700,
            padding=0
        )
    )
    page.update()