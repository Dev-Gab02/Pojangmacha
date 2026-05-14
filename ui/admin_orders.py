"""
Orders Management Tab for Admin Panel
"""
import flet as ft
from models.order import Order, OrderItem
from models.user import User
from models.food_item import FoodItem
from models.audit_log import AuditLog
from ui.admin_constants import (
    DESKTOP_COLUMNS,
    GRID_SPACING, GRID_RUN_SPACING
)
import os
import shutil
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

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
    
    # ===================== STATE =====================
    current_view = {"value": "list"}  # "list", "details", or "receipt"
    selected_order = {"value": None}
    receipt_image_path = {"value": ""}
    
    # ===================== CARD BUILDER =====================
    
    def build_order_card(order):
        """Build a single order card - clickable to show details"""
        user = db.query(User).get(order.user_id)
        username = user.full_name if user else "Unknown"
        
        return ft.Container(
            content=ft.Card(
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
                    ], spacing=3),
                    padding=10,
                    bgcolor='white',
                    border_radius=12
                )
            ),
            on_click=lambda e, o=order: show_order_details(o)
        )
    
    # ===================== GRID/LIST CONTAINERS =====================
    
    orders_grid = ft.GridView(
        runs_count=DESKTOP_COLUMNS,  # 3 columns
        max_extent=500,  
        child_aspect_ratio=5.5,  
        spacing=GRID_SPACING,
        run_spacing=GRID_RUN_SPACING,
        expand=True
    )

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
    
    # ===================== ORDER DETAILS VIEW =====================
    
    def show_order_details(order):
        """Show order details with items and paid button, or receipt if already completed"""
        selected_order["value"] = order
        
        # If order is already completed, show receipt view directly
        if order.status == "Completed":
            current_view["value"] = "receipt"
            # Make sure receipt image exists
            receipt_path = os.path.join("assets/receipts", f"receipt_order_{order.id}.png")
            if os.path.exists(receipt_path):
                receipt_image_path["value"] = receipt_path
            else:
                # Regenerate receipt if it doesn't exist
                generate_receipt_image(order)
        else:
            current_view["value"] = "details"
        
        render_content()
    
    def go_back_to_list():
        """Go back to order list"""
        current_view["value"] = "list"
        selected_order["value"] = None
        load_orders()
        render_content()
    
    def mark_as_paid(e):
        """Show receipt before marking as paid"""
        order = selected_order["value"]
        current_view["value"] = "receipt"
        generate_receipt_image(order)
        render_content()
    
    def confirm_payment_and_mark_paid(e):
        """Confirm payment and mark order as completed"""
        order = selected_order["value"]
        order.status = "Completed"
        db.commit()
        
        db.add(AuditLog(user_email=user_data.get("email"), action=f"Marked order #{order.id} as paid"))
        db.commit()
        
        go_back_to_list()
        page.snack_bar = ft.SnackBar(ft.Text(f"Order #{order.id} marked as paid!"), bgcolor=ft.Colors.GREEN, open=True)
        page.update()
    
    def generate_receipt_image(order):
        """Generate receipt as an image"""
        user = db.query(User).get(order.user_id)
        username = user.full_name if user else "Unknown"
        
        # Get order items
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        # Create image (800x600 minimum, expand based on items)
        img_height = 400 + (len(order_items) * 40)
        img = Image.new('RGB', (600, img_height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use a nice font, fall back to default if not available
        try:
            title_font = ImageFont.truetype("arial.ttf", 24)
            header_font = ImageFont.truetype("arial.ttf", 18)
            normal_font = ImageFont.truetype("arial.ttf", 14)
            small_font = ImageFont.truetype("arial.ttf", 12)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        y_position = 20
        
        # Title
        draw.text((50, y_position), "POJANGMACHA", fill='black', font=title_font)
        y_position += 30
        
        # Order number
        draw.text((50, y_position), f"Order #{order.id}", fill='black', font=header_font)
        y_position += 30
        
        # Customer
        draw.text((50, y_position), f"Customer: {username}", fill='black', font=normal_font)
        y_position += 25
        
        # Order date
        date_str = order.created_at.strftime('%Y-%m-%d %H:%M')
        draw.text((50, y_position), f"Date: {date_str}", fill='black', font=normal_font)
        y_position += 30
        
        # Divider line
        draw.line([(50, y_position), (550, y_position)], fill='black', width=1)
        y_position += 20
        
        # Items header
        draw.text((50, y_position), "Item", fill='black', font=normal_font)
        draw.text((350, y_position), "Qty", fill='black', font=normal_font)
        draw.text((450, y_position), "Price", fill='black', font=normal_font)
        y_position += 25
        
        # Divider line
        draw.line([(50, y_position), (550, y_position)], fill='black', width=1)
        y_position += 15
        
        # Items
        total = 0
        for item in order_items:
            food = db.query(FoodItem).get(item.food_id)
            if food:
                draw.text((50, y_position), food.name[:35], fill='black', font=small_font)
                draw.text((350, y_position), str(item.quantity), fill='black', font=small_font)
                draw.text((450, y_position), f"₱{item.subtotal:.2f}", fill='black', font=small_font)
                y_position += 35
                total += item.subtotal
        
        # Divider line
        draw.line([(50, y_position), (550, y_position)], fill='black', width=1)
        y_position += 20
        
        # Total
        draw.text((350, y_position), "TOTAL:", fill='black', font=header_font)
        draw.text((450, y_position), f"₱{total:.2f}", fill='black', font=header_font)
        
        # Save receipt image
        receipt_dir = "assets/receipts"
        os.makedirs(receipt_dir, exist_ok=True)
        receipt_path = os.path.join(receipt_dir, f"receipt_order_{order.id}.png")
        img.save(receipt_path)
        receipt_image_path["value"] = receipt_path
    
    def generate_receipt_pdf(order):
        """Generate receipt as a PDF"""
        user = db.query(User).get(order.user_id)
        username = user.full_name if user else "Unknown"
        
        # Get order items
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        # Create PDF
        receipt_dir = "assets/receipts"
        os.makedirs(receipt_dir, exist_ok=True)
        pdf_path = os.path.join(receipt_dir, f"receipt_order_{order.id}.pdf")
        
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.black,
            spaceAfter=12,
            alignment=1
        )
        elements.append(Paragraph("POJANGMACHA", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Order info
        order_info_style = ParagraphStyle(
            'OrderInfo',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            spaceAfter=6
        )
        elements.append(Paragraph(f"<b>Order #{order.id}</b>", order_info_style))
        elements.append(Paragraph(f"Customer: {username}", order_info_style))
        date_str = order.created_at.strftime('%Y-%m-%d %H:%M')
        elements.append(Paragraph(f"Date: {date_str}", order_info_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Items table
        items_data = [['Item', 'Qty', 'Price']]
        total = 0
        
        for item in order_items:
            food = db.query(FoodItem).get(item.food_id)
            if food:
                items_data.append([
                    food.name[:35],
                    str(item.quantity),
                    f"₱{item.subtotal:.2f}"
                ])
                total += item.subtotal
        
        # Add total row
        items_data.append(['', '', ''])
        items_data.append(['TOTAL', '', f"₱{total:.2f}"])
        
        # Create table
        items_table = Table(items_data, colWidths=[3.5*inch, 1*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -3), colors.beige),
            ('GRID', (0, 0), (-1, -3), 1, colors.black),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -2), (-1, -1), 12),
            ('BACKGROUND', (0, -2), (-1, -1), colors.lightgrey),
            ('TOPPADDING', (0, -2), (-1, -1), 12),
        ]))
        
        elements.append(items_table)
        
        # Build PDF
        doc.build(elements)
        return pdf_path
    
    def build_order_details_view():
        """Build the order details view"""
        order = selected_order["value"]
        user = db.query(User).get(order.user_id)
        username = user.full_name if user else "Unknown"
        
        # Get order items
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        
        items_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        total = 0
        
        for item in order_items:
            food = db.query(FoodItem).get(item.food_id)
            if food:
                items_column.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(food.name, weight="bold", size=13, color="black"),
                                ft.Text(f"Qty: {item.quantity}", size=11, color="grey700"),
                            ], spacing=2, expand=True),
                            ft.Text(f"₱{item.subtotal:.2f}", size=12, weight="bold", color="green"),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=10,
                        bgcolor="grey100",
                        border_radius=8
                    )
                )
                total += item.subtotal
        
        return ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color="black",
                        on_click=lambda e: go_back_to_list()
                    ),
                    ft.Text(f"Order #{order.id}", size=18, weight="bold", color="black"),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(top=15, left=5, right=15, bottom=8)
            ),
            ft.Divider(height=1, color="grey300", thickness=1),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("Order Details", size=14, weight="bold", color="black"),
                    ft.Text(f"Customer: {username}", size=12, color="grey700"),
                    ft.Text(f"Status: {order.status}", size=12, color="grey700"),
                    ft.Text(f"Order Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}", size=12, color="grey700"),
                ], spacing=4),
                padding=15,
                bgcolor="white",
                border_radius=12,
                margin=ft.margin.symmetric(vertical=12, horizontal=16),
                width=float('inf')
            ),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("Items", size=14, weight="bold", color="black"),
                    items_column,
                ], spacing=8),
                padding=15,
                bgcolor="white",
                border_radius=12,
                margin=ft.margin.symmetric(vertical=0, horizontal=16),
                expand=True,
                width=float('inf')
            ),
            
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Total", size=16, weight="bold", color="black"),
                        ft.Text(f"₱{total:.2f}", size=18, weight="bold", color="green"),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.ElevatedButton(
                        "Print Receipt" if order.status == "Completed" else "Paid",
                        on_click=mark_as_paid if order.status != "Completed" else None,
                        style=ft.ButtonStyle(
                            bgcolor="#FEB23F" if order.status != "Completed" else "grey",
                            color="white"
                        ),
                        width=350,
                        height=45,
                        disabled=order.status == "Completed"
                    ),
                ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15,
                border_radius=12,
                bgcolor="white",
                margin=ft.margin.symmetric(vertical=12, horizontal=16),
                width=float('inf')
            )
        ], expand=True, spacing=0)
    
    def build_receipt_view():
        """Build the receipt view"""
        order = selected_order["value"]
        receipt_path = receipt_image_path["value"]
        
        # Determine button layout based on order status
        is_completed = order.status == "Completed"
        
        # Buttons column
        buttons_column = ft.Column([
            ft.ElevatedButton(
                "Download Receipt",
                icon=ft.Icons.DOWNLOAD,
                on_click=lambda e: download_receipt(order),
                style=ft.ButtonStyle(
                    bgcolor="#FEB23F",
                    color="white"
                ),
                width=float('inf'),
                height=50
            ),
            ft.ElevatedButton(
                "Back to Orders" if is_completed else "Confirm Payment",
                on_click=lambda e: go_back_to_list() if is_completed else confirm_payment_and_mark_paid(e),
                style=ft.ButtonStyle(
                    bgcolor="green" if not is_completed else "blue",
                    color="white"
                ),
                width=float('inf'),
                height=50
            ),
        ], spacing=15)
        
        # For desktop: 2-column layout (image + buttons)
        # For mobile: vertical layout
        if is_desktop:
            content_area = ft.Row([
                # Left column: Image (70%)
                ft.Container(
                    content=ft.Image(
                        src=receipt_path,
                        fit=ft.ImageFit.CONTAIN,
                        expand=True,
                    ),
                    expand=True,
                    padding=15,
                ),
                # Right column: Buttons (30%) - fixed height for 2 buttons
                ft.Container(
                    content=buttons_column,
                    width=350,
                    height=150,
                    padding=15,
                    bgcolor="white",
                    border_radius=12,
                    alignment=ft.alignment.bottom_center,
                )
            ], spacing=15, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
        else:
            content_area = ft.Column([
                ft.Container(
                    content=ft.Image(
                        src=receipt_path,
                        fit=ft.ImageFit.CONTAIN,
                        expand=True,
                    ),
                    expand=True,
                    padding=15,
                ),
                ft.Container(
                    content=buttons_column,
                    padding=15,
                    border_radius=12,
                    bgcolor="white",
                )
            ], spacing=15, expand=True)
        
        return ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color="black",
                        on_click=lambda e: back_to_order_details()
                    ),
                    ft.Text(f"Order #{order.id} Receipt", size=18, weight="bold", color="black"),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(top=15, left=5, right=15, bottom=8)
            ),
            ft.Divider(height=1, color="grey300", thickness=1),
            
            ft.Container(
                content=content_area,
                expand=True,
                padding=15,
            )
        ], expand=True, spacing=0)
    
    def download_receipt(order):
        """Download receipt as image to Downloads folder"""
        receipt_path = receipt_image_path["value"]
        if receipt_path and os.path.exists(receipt_path):
            try:
                # Get Downloads folder
                downloads_folder = str(Path.home() / "Downloads")
                filename = f"receipt_order_{order.id}.png"
                destination = os.path.join(downloads_folder, filename)
                
                # Copy file to Downloads
                shutil.copy(receipt_path, destination)
                
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Receipt downloaded to Downloads folder!"),
                    bgcolor=ft.Colors.GREEN,
                    open=True
                )
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Error downloading receipt: {ex}"),
                    bgcolor=ft.Colors.RED,
                    open=True
                )
                page.update()
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("Receipt file not found"),
                bgcolor=ft.Colors.RED,
                open=True
            )
            page.update()
    
    def back_to_order_details():
        """Go back to order details from receipt, or to list if order is completed"""
        order = selected_order["value"]
        # For completed orders, go back to list; for pending orders, go to details
        if order.status == "Completed":
            go_back_to_list()
        else:
            current_view["value"] = "details"
            render_content()
    
    # ===================== RENDER CONTENT =====================
    
    def render_content():
        """Render list, details, or receipt view"""
        if current_view["value"] == "receipt":
            main_content.content = build_receipt_view()
        elif current_view["value"] == "details":
            main_content.content = build_order_details_view()
        else:
            main_content.content = ft.Column([
                ft.Container(
                    content=ft.Text("Manage Orders", size=20, weight="bold", color='black'),
                    padding=10
                ),
                
                ft.Container(
                    content=orders_grid if is_desktop else orders_list,
                    expand=True,
                    padding=10
                )
            ], expand=True, spacing=0)
        page.update()
    
    # ===================== BUILD TAB =====================
    
    # Load initial data
    load_orders()
    
    # Main content container
    main_content = ft.Container(expand=True)
    render_content()
    
    # Return the complete tab
    return ft.Tab(
        text="Orders",
        icon=ft.Icons.SHOPPING_BAG,
        content=main_content
    )