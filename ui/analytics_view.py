import flet as ft
from flet.plotly_chart import PlotlyChart
import plotly.graph_objects as go
import plotly.express as px
from core.db import SessionLocal
from core.analytics_service import (
    get_sales_trends,
    get_best_selling_items,
    get_revenue_by_category,
    get_customer_order_frequency,
    get_hourly_sales_pattern,
    get_inventory_alerts,
    get_dashboard_summary
)
import threading
import time

def analytics_view(page: ft.Page):
    page.title = "Analytics Dashboard - Pojangmacha"
    
    # Check if user is admin
    user_data = page.session.get("user")
    if not user_data or user_data.get("role") != "admin":
        page.snack_bar = ft.SnackBar(ft.Text("Access denied. Admins only."), open=True)
        page.go("/home")
        return
    
    # ✅ DETECT DESKTOP MODE - USE ACTUAL WINDOW DIMENSIONS
    BREAKPOINT = 800
    current_width = page.window.width or 400
    is_desktop = current_width >= BREAKPOINT
    
    # ✅ RESPONSIVE DIMENSIONS - Preserve current window size
    container_width = current_width if is_desktop else 400
    container_height = page.window.height or 700
    
    print(f"📊 Analytics - Width: {container_width}px, Height: {container_height}px, Mode: {'Desktop' if is_desktop else 'Mobile'}")
    
    # ✅ Track if component is still active (moved here - before handle_back)
    is_active = {"value": True}
    
    # ✅ OPTIMIZED BACK NAVIGATION - Stop background thread immediately
    def handle_back(e):
        """Fast navigation back to admin - stop all operations"""
        try:
            # ✅ STOP BACKGROUND THREAD IMMEDIATELY
            is_active["value"] = False
            
            # Close any dialogs
            if hasattr(page, 'dialog') and page.dialog:
                page.dialog.open = False
            
            # ✅ SHOW LOADING SCREEN BEFORE NAVIGATION
            main_container.content = ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.ProgressRing(width=50, height=50, stroke_width=4, color="#FEB23F"),
                        ft.Text("Returning to Admin...", size=14, color="grey700")
                    ], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                    ),
                    expand=True,
                    alignment=ft.alignment.center
                )
            ], expand=True, spacing=0)
            page.update()
            
            # Small delay to show loading screen
            time.sleep(0.2)
            
            # Navigate to admin
            page.go("/admin")
            
        except Exception as ex:
            print(f"❌ Back navigation error: {ex}")
            page.go("/admin")
    
    # ✅ CREATE MAIN CONTAINER (will be updated, not replaced)
    main_container = ft.Container(
        content=ft.Column([
            # ✅ LOADING SCREEN HEADER - WHITE WITH DIVIDER
            ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            tooltip="Back to Admin",
                            on_click=handle_back,
                            icon_color="black"
                        ),
                        ft.Text("Analytics Dashboard", size=20, weight="bold", color="black"),
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.only(left=5, right=15, top=10, bottom=8)
                ),
                ft.Divider(height=1, color="grey300", thickness=1)
            ], spacing=0),
            
            # Loading content (CENTERED)
            ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=50, height=50, stroke_width=4, color="#FEB23F"),
                    ft.Text("Loading analytics...", size=14, color="grey700")
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=20
                ),
                expand=True,
                alignment=ft.alignment.center
            )
        ], expand=True, spacing=0),
        width=container_width,
        height=container_height,
        padding=0
    )
    
    # ✅ SHOW LOADING SCREEN FIRST
    page.clean()
    page.add(main_container)
    page.update()
    
    # ✅ LOAD DATA IN BACKGROUND THREAD
    def load_analytics():
        db = SessionLocal()
        
        try:
            # Small delay to ensure loading screen is visible
            time.sleep(0.2)
            
            # ✅ Check if user navigated away
            if not is_active["value"]:
                print("⏹️ Analytics loading cancelled - user navigated away")
                db.close()
                return
            
            # Get dashboard data
            summary = get_dashboard_summary(db)
            
            # ✅ Check again before building charts
            if not is_active["value"]:
                print("⏹️ Analytics cancelled before chart creation")
                db.close()
                return
            
            # --- CHART CREATION FUNCTIONS ---
            def create_sales_trend_chart(period="daily"):
                """Create sales trend line chart"""
                if not is_active["value"]:
                    return ft.Container()
                
                days = 30 if period == "daily" else 90 if period == "weekly" else 180
                data = get_sales_trends(db, period=period, days=days)
                
                if not data["dates"]:
                    return ft.Container(
                        content=ft.Text("No sales data available", size=14, color="grey"),
                        alignment=ft.alignment.center,
                        padding=30
                    )
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=data["dates"],
                    y=data["revenue"],
                    mode='lines+markers',
                    name='Revenue',
                    line=dict(color='#2196F3', width=2),
                    marker=dict(size=6),
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.1)'
                ))
                
                chart_height = 350 if is_desktop else 250
                
                fig.update_layout(
                    title=dict(text=f"Sales Trend ({period.capitalize()})", font=dict(size=14)),
                    xaxis_title="Date",
                    yaxis_title="Revenue (₱)",
                    hovermode='x unified',
                    height=chart_height,
                    margin=dict(l=40, r=20, t=40, b=40),
                    font=dict(size=10)
                )
                
                return PlotlyChart(fig, expand=True)
            
            def create_best_sellers_chart():
                """Create horizontal bar chart of best sellers"""
                if not is_active["value"]:
                    return ft.Container()
                
                items = get_best_selling_items(db, limit=8)
                
                if not items:
                    return ft.Container(
                        content=ft.Text("No sales data", size=14, color="grey"),
                        alignment=ft.alignment.center,
                        padding=30
                    )
                
                names = [item["name"][:20] for item in items]
                quantities = [item["quantity"] for item in items]
                
                fig = go.Figure(go.Bar(
                    x=quantities,
                    y=names,
                    orientation='h',
                    marker=dict(
                        color=quantities,
                        colorscale='Viridis',
                        showscale=False
                    ),
                    text=quantities,
                    textposition='auto',
                ))
                
                chart_height = 320 if is_desktop else 280
                
                fig.update_layout(
                    title=dict(text="Top Sellers", font=dict(size=14)),
                    xaxis_title="Qty Sold",
                    yaxis_title="",
                    height=chart_height,
                    margin=dict(l=120, r=20, t=40, b=40),
                    font=dict(size=10)
                )
                
                return PlotlyChart(fig, expand=True)
            
            def create_category_revenue_chart():
                """Create pie chart of revenue by category"""
                if not is_active["value"]:
                    return ft.Container()
                
                data = get_revenue_by_category(db)
                
                if not data["categories"]:
                    return ft.Container(
                        content=ft.Text("No category data", size=14, color="grey"),
                        alignment=ft.alignment.center,
                        padding=30
                    )
                
                fig = go.Figure(go.Pie(
                    labels=data["categories"],
                    values=data["revenue"],
                    hole=0.4,
                    marker=dict(colors=px.colors.qualitative.Set3),
                    textinfo='label+percent',
                    textposition='auto',
                    textfont=dict(size=10)
                ))
                
                chart_height = 320 if is_desktop else 280
                
                fig.update_layout(
                    title=dict(text="Revenue by Category", font=dict(size=14)),
                    height=chart_height,
                    margin=dict(l=20, r=20, t=40, b=20),
                    font=dict(size=10)
                )
                
                return PlotlyChart(fig, expand=True)
            
            def create_order_frequency_chart():
                """Create bar chart of customer order frequency"""
                if not is_active["value"]:
                    return ft.Container()
                
                data = get_customer_order_frequency(db)
                
                if not data["order_counts"]:
                    return ft.Container(
                        content=ft.Text("No customer data", size=14, color="grey"),
                        alignment=ft.alignment.center,
                        padding=30
                    )
                
                fig = go.Figure(go.Bar(
                    x=[f"{count}" for count in data["order_counts"]],
                    y=data["customer_counts"],
                    marker=dict(color='#FF9800'),
                    text=data["customer_counts"],
                    textposition='auto',
                ))
                
                chart_height = 280 if is_desktop else 220
                
                fig.update_layout(
                    title=dict(text="Order Frequency", font=dict(size=14)),
                    xaxis_title="Orders",
                    yaxis_title="Customers",
                    height=chart_height,
                    margin=dict(l=40, r=20, t=40, b=40),
                    font=dict(size=10)
                )
                
                return PlotlyChart(fig, expand=True)
            
            def create_hourly_pattern_chart():
                """Create heatmap-style bar chart of hourly sales"""
                if not is_active["value"]:
                    return ft.Container()
                
                data = get_hourly_sales_pattern(db)
                
                if not data["hours"]:
                    return ft.Container(
                        content=ft.Text("No hourly data", size=14, color="grey"),
                        alignment=ft.alignment.center,
                        padding=30
                    )
                
                fig = go.Figure(go.Bar(
                    x=[f"{h:02d}:00" for h in data["hours"]],
                    y=data["orders"],
                    marker=dict(
                        color=data["orders"],
                        colorscale='RdYlGn',
                        showscale=False
                    ),
                    text=data["orders"],
                    textposition='auto',
                ))
                
                chart_height = 280 if is_desktop else 220
                
                fig.update_layout(
                    title=dict(text="Hourly Sales", font=dict(size=14)),
                    xaxis_title="Hour",
                    yaxis_title="Orders",
                    height=chart_height,
                    margin=dict(l=40, r=20, t=40, b=40),
                    font=dict(size=10)
                )
                
                return PlotlyChart(fig, expand=True)
            
            def create_inventory_alerts():
                """Create inventory alerts table"""
                if not is_active["value"]:
                    return ft.Container()
                
                alerts = get_inventory_alerts(db)
                
                if not alerts:
                    return ft.Container(
                        content=ft.Column([
                            ft.Text("All inventory OK", size=14, color="green", weight="bold")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        alignment=ft.alignment.center,
                        padding=20
                    )
                
                alert_list = ft.Column(spacing=6)
                
                for alert in alerts[:5]:
                    status_color = "red" if alert["status"] == "High Demand" else "orange"
                    
                    alert_list.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(alert["name"][:25], weight="bold", size=12, expand=True),
                                    ft.Container(
                                        content=ft.Text(alert["status"], size=10, color="white", weight="bold"),
                                        bgcolor=status_color,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                        border_radius=4
                                    )
                                ]),
                                ft.Text(f"Sold: {alert['quantity_sold']} | ₱{alert['revenue']:,.0f}", size=10, color="grey700"),
                            ], spacing=4),
                            border=ft.border.all(1, "grey300"),
                            border_radius=6,
                            padding=10,
                            bgcolor="white"
                        )
                    )
                
                return ft.Container(
                    content=alert_list,
                    padding=5
                )
            
            # --- ✅ EQUAL SIZE SUMMARY CARDS ---
            if is_desktop:
                summary_cards_container = ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(summary["total_orders"]), size=28, weight="bold"),
                            ft.Text("Total Orders", size=12, color="grey700"),
                            ft.Text(f"Today: {summary['today_orders']}", size=10, color="green")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, alignment=ft.MainAxisAlignment.CENTER),
                        padding=12, bgcolor="blue50", border_radius=8, expand=1, height=100
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"₱{summary['total_revenue']:,.0f}", size=28, weight="bold"),
                            ft.Text("Revenue", size=12, color="grey700"),
                            ft.Text(f"₱{summary['today_revenue']:,.0f}", size=10, color="green")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, alignment=ft.MainAxisAlignment.CENTER),
                        padding=12, bgcolor="green50", border_radius=8, expand=1, height=100
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(summary["total_customers"]), size=28, weight="bold"),
                            ft.Text("Customers", size=12, color="grey700"),
                            ft.Text("", size=10)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, alignment=ft.MainAxisAlignment.CENTER),
                        padding=12, bgcolor="orange50", border_radius=8, expand=1, height=100
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(summary["total_items"]), size=28, weight="bold"),
                            ft.Text("Menu Items", size=12, color="grey700"),
                            ft.Text("", size=10)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, alignment=ft.MainAxisAlignment.CENTER),
                        padding=12, bgcolor="purple50", border_radius=8, expand=1, height=100
                    ),
                ], spacing=8)
            else:
                summary_cards_row1 = ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(summary["total_orders"]), size=28, weight="bold"),
                            ft.Text("Total Orders", size=12, color="grey700"),
                            ft.Text(f"Today: {summary['today_orders']}", size=10, color="green")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, alignment=ft.MainAxisAlignment.CENTER),
                        padding=12, bgcolor="blue50", border_radius=8, expand=1, height=100
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"₱{summary['total_revenue']:,.0f}", size=28, weight="bold"),
                            ft.Text("Revenue", size=12, color="grey700"),
                            ft.Text(f"₱{summary['today_revenue']:,.0f}", size=10, color="green")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, alignment=ft.MainAxisAlignment.CENTER),
                        padding=12, bgcolor="green50", border_radius=8, expand=1, height=100
                    ),
                ], spacing=8)
                
                summary_cards_row2 = ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(summary["total_customers"]), size=28, weight="bold"),
                            ft.Text("Customers", size=12, color="grey700"),
                            ft.Text("", size=10)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, alignment=ft.MainAxisAlignment.CENTER),
                        padding=12, bgcolor="orange50", border_radius=8, expand=1, height=100
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(summary["total_items"]), size=28, weight="bold"),
                            ft.Text("Menu Items", size=12, color="grey700"),
                            ft.Text("", size=10)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3, alignment=ft.MainAxisAlignment.CENTER),
                        padding=12, bgcolor="purple50", border_radius=8, expand=1, height=100
                    ),
                ], spacing=8)
                
                summary_cards_container = ft.Column([summary_cards_row1, summary_cards_row2], spacing=8)
            
            # Period selector for sales trend
            period_ref = {"value": "daily"}
            sales_chart_container = ft.Container()
            
            def update_sales_chart(e):
                if not is_active["value"]:
                    return
                period_ref["value"] = e.control.value
                sales_chart_container.content = create_sales_trend_chart(period_ref["value"])
                page.update()
            
            period_selector = ft.RadioGroup(
                content=ft.Row([
                    ft.Radio(value="daily", label="Daily"),
                    ft.Radio(value="weekly", label="Weekly"),
                    ft.Radio(value="monthly", label="Monthly"),
                ], spacing=10),
                value="daily",
                on_change=update_sales_chart
            )
            
            sales_chart_container.content = create_sales_trend_chart("daily")
            
            # ✅ Check one more time before building layout
            if not is_active["value"]:
                print("⏹️ Analytics cancelled before layout creation")
                db.close()
                return
            
            # ✅ DESKTOP: 2-column grid | MOBILE: Single column
            if is_desktop:
                charts_content = ft.Column([
                    ft.Container(content=summary_cards_container, padding=ft.padding.symmetric(horizontal=20, vertical=15)),
                    ft.Container(
                        content=ft.Column([period_selector, sales_chart_container], spacing=8),
                        border=ft.border.all(1, "grey300"), border_radius=8, padding=12, bgcolor="white",
                        margin=ft.margin.symmetric(horizontal=20)
                    ),
                    ft.Row([
                        ft.Container(content=create_best_sellers_chart(), border=ft.border.all(1, "grey300"), 
                                   border_radius=8, padding=12, bgcolor="white", expand=1),
                        ft.Container(content=create_category_revenue_chart(), border=ft.border.all(1, "grey300"),
                                   border_radius=8, padding=12, bgcolor="white", expand=1),
                    ], spacing=12, alignment=ft.MainAxisAlignment.START),
                    ft.Row([
                        ft.Container(content=create_order_frequency_chart(), border=ft.border.all(1, "grey300"),
                                   border_radius=8, padding=12, bgcolor="white", expand=1),
                        ft.Container(content=create_hourly_pattern_chart(), border=ft.border.all(1, "grey300"),
                                   border_radius=8, padding=12, bgcolor="white", expand=1),
                    ], spacing=12, alignment=ft.MainAxisAlignment.START),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Inventory Alerts", size=16, weight="bold"),
                            ft.Divider(height=1),
                            create_inventory_alerts()
                        ], spacing=8),
                        border=ft.border.all(1, "grey300"), border_radius=8, padding=12, bgcolor="white",
                        margin=ft.margin.symmetric(horizontal=20, vertical=8)
                    ),
                    ft.Container(height=20)
                ], spacing=12, scroll=ft.ScrollMode.AUTO)
            else:
                charts_content = ft.Column([
                    ft.Container(content=summary_cards_container, padding=ft.padding.symmetric(horizontal=10, vertical=10)),
                    ft.Container(
                        content=ft.Column([period_selector, sales_chart_container], spacing=8),
                        border=ft.border.all(1, "grey300"), border_radius=8, padding=12, bgcolor="white",
                        margin=ft.margin.symmetric(horizontal=10)
                    ),
                    ft.Container(content=create_best_sellers_chart(), border=ft.border.all(1, "grey300"),
                               border_radius=8, padding=12, bgcolor="white", margin=ft.margin.symmetric(horizontal=10, vertical=8)),
                    ft.Container(content=create_category_revenue_chart(), border=ft.border.all(1, "grey300"),
                               border_radius=8, padding=12, bgcolor="white", margin=ft.margin.symmetric(horizontal=10, vertical=8)),
                    ft.Container(content=create_order_frequency_chart(), border=ft.border.all(1, "grey300"),
                               border_radius=8, padding=12, bgcolor="white", margin=ft.margin.symmetric(horizontal=10, vertical=8)),
                    ft.Container(content=create_hourly_pattern_chart(), border=ft.border.all(1, "grey300"),
                               border_radius=8, padding=12, bgcolor="white", margin=ft.margin.symmetric(horizontal=10, vertical=8)),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Inventory Alerts", size=16, weight="bold"),
                            ft.Divider(height=1),
                            create_inventory_alerts()
                        ], spacing=8),
                        border=ft.border.all(1, "grey300"), border_radius=8, padding=12, bgcolor="white",
                        margin=ft.margin.symmetric(horizontal=10, vertical=8)
                    ),
                    ft.Container(height=20)
                ], spacing=0, scroll=ft.ScrollMode.AUTO)
            
            # ✅ Final check before updating UI
            if not is_active["value"]:
                print("⏹️ Analytics cancelled before final update")
                db.close()
                return
            
            # ✅ UPDATE MAIN CONTAINER CONTENT
            main_container.content = ft.Column([
                ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.ARROW_BACK,
                                tooltip="Back to Admin",
                                on_click=handle_back,
                                icon_color="black"
                            ),
                            ft.Text("Analytics Dashboard", size=20, weight="bold", color="black"),
                        ], alignment=ft.MainAxisAlignment.START),
                        padding=ft.padding.only(left=5, right=15, top=10, bottom=8)
                    ),
                    ft.Divider(height=1, color="grey300", thickness=1)
                ], spacing=0),
                ft.Container(content=charts_content, expand=True, padding=0)
            ], expand=True, spacing=0)
            
            main_container.width = container_width
            main_container.height = container_height
            
            page.update()
            print("✅ Analytics loaded successfully")
            
        except Exception as ex:
            if not is_active["value"]:
                print("⏹️ Analytics error but already cancelled")
                db.close()
                return
                
            main_container.content = ft.Column([
                ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.IconButton(icon=ft.Icons.ARROW_BACK, tooltip="Back to Admin",
                                        on_click=handle_back, icon_color="black"),
                            ft.Text("Analytics Dashboard", size=20, weight="bold", color="black"),
                        ], alignment=ft.MainAxisAlignment.START),
                        padding=ft.padding.only(left=5, right=15, top=10, bottom=8)
                    ),
                    ft.Divider(height=1, color="grey300", thickness=1)
                ], spacing=0),
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, size=60, color="red"),
                        ft.Text(f"Error loading analytics: {str(ex)}", size=14, color="red", text_align=ft.TextAlign.CENTER),
                        ft.ElevatedButton("Try Again", on_click=lambda e: analytics_view(page), bgcolor="#FEB23F", color="white")
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
                    expand=True, alignment=ft.alignment.center, padding=20
                )
            ], expand=True, spacing=0)
            
            page.update()
            print(f"❌ Analytics loading error: {ex}")
        finally:
            db.close()
            print("🔒 Database connection closed")
    
    # ✅ START BACKGROUND THREAD
    thread = threading.Thread(target=load_analytics, daemon=True)
    thread.start()