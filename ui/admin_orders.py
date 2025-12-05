"""
Orders Management Tab for Admin Panel
"""
import flet as ft
from models.order import Order
from models.user import User
from models.audit_log import AuditLog
from ui.admin_constants import (
    DESKTOP_COLUMNS,
    GRID_SPACING, GRID_RUN_SPACING
)

def build_orders_tab(page: ft.Page, db, user_data: dict, is_desktop: bool):
    """
    Build the Orders management tab
    
    Args:
        page: Flet page object
        db: Database session
        user_data: Current admin user data
        is_desktop: True if desktop layout, False if mobile
    
    Returns:
        ft.Tab: Complete orders tab with all functionality
    """
    
    # ===================== CARD BUILDER =====================
    
    def build_order_card(order):
        """Build a single order card - SAME DESIGN for mobile & desktop"""
        user = db.query(User).get(order.user_id)
        username = user.full_name if user else "Unknown"
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"Order #{order.id}", weight="bold", size=14, color='black'),
                        ft.Container(
                            content=ft.Text(order.status, color="white", size=12),
                            bgcolor="green" if order.status == "Completed" else "orange" if order.status == "Pending" else "red",
                            padding=5,
                            border_radius=5
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"by {username}", size=12, color="grey700"),
                    # ✅ Price and Buttons in same row
                    ft.Row([
                        ft.Text(f"Total: ₱{order.total_price:.2f}", size=14, weight="bold", color="green"),
                        ft.Row([
                            ft.ElevatedButton(
                                "Cancel",
                                on_click=lambda e, o=order: update_order_status(o, "Cancelled"),
                                disabled=order.status == "Cancelled",
                                style=ft.ButtonStyle(padding=8, color='blue700', bgcolor='grey200'),
                                height=35
                            ),
                            ft.ElevatedButton(
                                "Done",
                                on_click=lambda e, o=order: update_order_status(o, "Completed"),
                                disabled=order.status == "Completed",
                                style=ft.ButtonStyle(padding=8, color='green500', bgcolor='grey200'),
                                height=35
                            ),
                        ], spacing=5)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=3),
                padding=10,
                bgcolor='white',
                border_radius=12
            )
        )
    
    # ===================== GRID/LIST CONTAINERS =====================
    
    # ✅ Desktop: GridView with 3 columns (exact mobile card layout)
    orders_grid = ft.GridView(
        runs_count=DESKTOP_COLUMNS,  # 3 columns
        max_extent=500,  # ✅ Responsive: allows cards to expand up to 500px
        child_aspect_ratio=3.8,  # ✅ Width/Height = 3:1 (matches mobile proportions)
        spacing=GRID_SPACING,
        run_spacing=GRID_RUN_SPACING,
        expand=True
    )

    # ✅ Mobile: Column (single column list) - UNCHANGED
    orders_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    
    # ===================== LOAD DATA =====================
    
    def load_orders():
        """Load orders into grid/list"""
        if is_desktop:
            orders_grid.controls.clear()
            orders = db.query(Order).order_by(Order.created_at.desc()).all()
            for order in orders:
                orders_grid.controls.append(build_order_card(order))
        else:
            orders_list.controls.clear()
            orders = db.query(Order).order_by(Order.created_at.desc()).all()
            for order in orders:
                orders_list.controls.append(build_order_card(order))
        page.update()
    
    # ===================== UPDATE ORDER STATUS =====================
    
    def update_order_status(order, status):
        order.status = status
        db.commit()
        
        db.add(AuditLog(user_email=user_data.get("email"), action=f"Updated order #{order.id} to {status}"))
        db.commit()
        
        load_orders()
        page.snack_bar = ft.SnackBar(ft.Text(f"✅ Order #{order.id} → {status}"), bgcolor=ft.Colors.GREEN, open=True)
        page.update()
    
    # ===================== BUILD TAB =====================
    
    # Load initial data
    load_orders()
    
    # Return the complete tab
    return ft.Tab(
        text="Orders",
        icon=ft.Icons.SHOPPING_BAG,
        content=ft.Column([
            # ✅ Title Row - TRANSPARENT (gradient shows through)
            ft.Container(
                content=ft.Text("Manage Orders", size=20, weight="bold", color='black'),
                padding=10
                # ✅ No bgcolor - gradient from parent shows through
            ),
            
            # ✅ Grid/List with TRANSPARENT background (gradient from parent)
            ft.Container(
                content=orders_grid if is_desktop else orders_list,
                expand=True,
                padding=10
                # ✅ No gradient here - inherits from parent
            )
        ], expand=True, spacing=0)
    )