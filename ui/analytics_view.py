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

def analytics_view(page: ft.Page):
    db = SessionLocal()
    page.title = "Analytics Dashboard - Pojangmacha"
    
    # Check if user is admin
    user_data = page.session.get("user")
    if not user_data or user_data.get("role") != "admin":
        page.snack_bar = ft.SnackBar(ft.Text("Access denied. Admins only."), open=True)
        page.go("/home")
        return
    
    # Get dashboard data
    summary = get_dashboard_summary(db)
    
    # --- SUMMARY CARDS ---
    summary_cards = ft.Row([
        ft.Container(
            content=ft.Column([
                ft.Text(str(summary["total_orders"]), size=28, weight="bold"),
                ft.Text("Total Orders", size=12, color="grey700"),
                ft.Text(f"Today: {summary['today_orders']}", size=10, color="green")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            padding=12,
            bgcolor="blue50",
            border_radius=8,
            expand=1
        ),
        ft.Container(
            content=ft.Column([
                ft.Text(f"₱{summary['total_revenue']:,.0f}", size=24, weight="bold"),
                ft.Text("Revenue", size=12, color="grey700"),
                ft.Text(f"₱{summary['today_revenue']:,.0f}", size=10, color="green")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            padding=12,
            bgcolor="green50",
            border_radius=8,
            expand=1
        ),
    ], spacing=8)
    
    summary_cards_row2 = ft.Row([
        ft.Container(
            content=ft.Column([
                ft.Text(str(summary["total_customers"]), size=28, weight="bold"),
                ft.Text("Customers", size=12, color="grey700"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            padding=12,
            bgcolor="orange50",
            border_radius=8,
            expand=1
        ),
        ft.Container(
            content=ft.Column([
                ft.Text(str(summary["total_items"]), size=28, weight="bold"),
                ft.Text("Menu Items", size=12, color="grey700"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            padding=12,
            bgcolor="purple50",
            border_radius=8,
            expand=1
        ),
    ], spacing=8)
    
    # --- CHART 1: Sales Trends ---
    def create_sales_trend_chart(period="daily"):
        """Create sales trend line chart"""
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
        
        fig.update_layout(
            title=dict(text=f"Sales Trend ({period.capitalize()})", font=dict(size=14)),
            xaxis_title="Date",
            yaxis_title="Revenue (₱)",
            hovermode='x unified',
            height=250,
            margin=dict(l=40, r=20, t=40, b=40),
            font=dict(size=10)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # Period selector for sales trend
    period_ref = {"value": "daily"}
    sales_chart_container = ft.Container()
    
    def update_sales_chart(e):
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
    
    # --- CHART 2: Best Selling Items ---
    def create_best_sellers_chart():
        """Create horizontal bar chart of best sellers"""
        items = get_best_selling_items(db, limit=8)  # Reduced to 8 for mobile
        
        if not items:
            return ft.Container(
                content=ft.Text("No sales data", size=14, color="grey"),
                alignment=ft.alignment.center,
                padding=30
            )
        
        names = [item["name"][:20] for item in items]  # Truncate long names
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
        
        fig.update_layout(
            title=dict(text="Top Sellers", font=dict(size=14)),
            xaxis_title="Qty Sold",
            yaxis_title="",
            height=280,
            margin=dict(l=120, r=20, t=40, b=40),
            font=dict(size=10)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # --- CHART 3: Revenue by Category ---
    def create_category_revenue_chart():
        """Create pie chart of revenue by category"""
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
        
        fig.update_layout(
            title=dict(text="Revenue by Category", font=dict(size=14)),
            height=280,
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(size=10)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # --- CHART 4: Customer Order Frequency ---
    def create_order_frequency_chart():
        """Create bar chart of customer order frequency"""
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
        
        fig.update_layout(
            title=dict(text="Order Frequency", font=dict(size=14)),
            xaxis_title="Orders",
            yaxis_title="Customers",
            height=220,
            margin=dict(l=40, r=20, t=40, b=40),
            font=dict(size=10)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # --- CHART 5: Hourly Sales Pattern ---
    def create_hourly_pattern_chart():
        """Create heatmap-style bar chart of hourly sales"""
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
        
        fig.update_layout(
            title=dict(text="Hourly Sales", font=dict(size=14)),
            xaxis_title="Hour",
            yaxis_title="Orders",
            height=220,
            margin=dict(l=40, r=20, t=40, b=40),
            font=dict(size=10)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # --- INVENTORY ALERTS TABLE ---
    def create_inventory_alerts():
        """Create inventory alerts table"""
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
        
        for alert in alerts[:5]:  # Limit to 5 for mobile
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
    
    # --- LAYOUT ---
    page.clean()
    page.add(
        ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            tooltip="Back to Admin",
                            on_click=lambda e: page.go("/admin")
                        ),
                        ft.Text("Analytics Dashboard", size=18, weight="bold"),
                    ]),
                    padding=10,
                    bgcolor="black",
                ),
                
                # Content (scrollable)
                ft.Container(
                    content=ft.Column([
                        # Summary Cards
                        ft.Container(
                            content=ft.Column([
                                summary_cards,
                                summary_cards_row2
                            ], spacing=8),
                            padding=ft.padding.symmetric(horizontal=10, vertical=10)
                        ),
                        
                        # Sales Trend Chart
                        ft.Container(
                            content=ft.Column([
                                period_selector,
                                sales_chart_container
                            ], spacing=8),
                            border=ft.border.all(1, "grey300"),
                            border_radius=8,
                            padding=12,
                            bgcolor="white",
                            margin=ft.margin.symmetric(horizontal=10)
                        ),
                        
                        # Best Sellers Chart
                        ft.Container(
                            content=create_best_sellers_chart(),
                            border=ft.border.all(1, "grey300"),
                            border_radius=8,
                            padding=12,
                            bgcolor="white",
                            margin=ft.margin.symmetric(horizontal=10, vertical=8)
                        ),
                        
                        # Category Revenue Chart
                        ft.Container(
                            content=create_category_revenue_chart(),
                            border=ft.border.all(1, "grey300"),
                            border_radius=8,
                            padding=12,
                            bgcolor="white",
                            margin=ft.margin.symmetric(horizontal=10, vertical=8)
                        ),
                        
                        # Order Frequency Chart
                        ft.Container(
                            content=create_order_frequency_chart(),
                            border=ft.border.all(1, "grey300"),
                            border_radius=8,
                            padding=12,
                            bgcolor="white",
                            margin=ft.margin.symmetric(horizontal=10, vertical=8)
                        ),
                        
                        # Hourly Pattern Chart
                        ft.Container(
                            content=create_hourly_pattern_chart(),
                            border=ft.border.all(1, "grey300"),
                            border_radius=8,
                            padding=12,
                            bgcolor="white",
                            margin=ft.margin.symmetric(horizontal=10, vertical=8)
                        ),
                        
                        # Inventory Alerts
                        ft.Container(
                            content=ft.Column([
                                ft.Text("Inventory Alerts", size=16, weight="bold"),
                                ft.Divider(height=1),
                                create_inventory_alerts()
                            ], spacing=8),
                            border=ft.border.all(1, "grey300"),
                            border_radius=8,
                            padding=12,
                            bgcolor="white",
                            margin=ft.margin.symmetric(horizontal=10, vertical=8)
                        ),
                        
                        ft.Container(height=20)  # Bottom padding
                        
                    ], spacing=0, scroll=ft.ScrollMode.AUTO),
                    expand=True,
                    padding=0
                )
            ], expand=True, spacing=0),
            width=400,
            height=700,
            padding=0
        )
    )
    
    page.update()