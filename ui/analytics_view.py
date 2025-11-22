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
                ft.Icon(ft.Icons.SHOPPING_BAG, size=40, color="blue700"),
                ft.Text(str(summary["total_orders"]), size=32, weight="bold"),
                ft.Text("Total Orders", size=14, color="grey700"),
                ft.Text(f"Today: {summary['today_orders']}", size=12, color="green")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=20,
            bgcolor="blue50",
            border_radius=10,
            expand=1
        ),
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ATTACH_MONEY, size=40, color="green700"),
                ft.Text(f"₱{summary['total_revenue']:,.0f}", size=28, weight="bold"),
                ft.Text("Total Revenue", size=14, color="grey700"),
                ft.Text(f"Today: ₱{summary['today_revenue']:,.0f}", size=12, color="green")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=20,
            bgcolor="green50",
            border_radius=10,
            expand=1
        ),
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.PEOPLE, size=40, color="orange700"),
                ft.Text(str(summary["total_customers"]), size=32, weight="bold"),
                ft.Text("Customers", size=14, color="grey700"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=20,
            bgcolor="orange50",
            border_radius=10,
            expand=1
        ),
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.RESTAURANT_MENU, size=40, color="purple700"),
                ft.Text(str(summary["total_items"]), size=32, weight="bold"),
                ft.Text("Menu Items", size=14, color="grey700"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            padding=20,
            bgcolor="purple50",
            border_radius=10,
            expand=1
        ),
    ], spacing=10)
    
    # --- CHART 1: Sales Trends ---
    def create_sales_trend_chart(period="daily"):
        """Create sales trend line chart"""
        days = 30 if period == "daily" else 90 if period == "weekly" else 180
        data = get_sales_trends(db, period=period, days=days)
        
        if not data["dates"]:
            return ft.Container(
                content=ft.Text("No sales data available", size=16, color="grey"),
                alignment=ft.alignment.center,
                padding=40
            )
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data["dates"],
            y=data["revenue"],
            mode='lines+markers',
            name='Revenue',
            line=dict(color='#2196F3', width=3),
            marker=dict(size=8),
            fill='tozeroy',
            fillcolor='rgba(33, 150, 243, 0.1)'
        ))
        
        fig.update_layout(
            title=f"Sales Trend ({period.capitalize()})",
            xaxis_title="Date",
            yaxis_title="Revenue (₱)",
            hovermode='x unified',
            height=350,
            margin=dict(l=40, r=40, t=60, b=40)
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
        ], spacing=20),
        value="daily",
        on_change=update_sales_chart
    )
    
    sales_chart_container.content = create_sales_trend_chart("daily")
    
    # --- CHART 2: Best Selling Items ---
    def create_best_sellers_chart():
        """Create horizontal bar chart of best sellers"""
        items = get_best_selling_items(db, limit=10)
        
        if not items:
            return ft.Container(
                content=ft.Text("No sales data available", size=16, color="grey"),
                alignment=ft.alignment.center,
                padding=40
            )
        
        names = [item["name"] for item in items]
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
            title="Top 10 Best-Selling Items",
            xaxis_title="Quantity Sold",
            yaxis_title="",
            height=400,
            margin=dict(l=150, r=40, t=60, b=40)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # --- CHART 3: Revenue by Category ---
    def create_category_revenue_chart():
        """Create pie chart of revenue by category"""
        data = get_revenue_by_category(db)
        
        if not data["categories"]:
            return ft.Container(
                content=ft.Text("No category data available", size=16, color="grey"),
                alignment=ft.alignment.center,
                padding=40
            )
        
        fig = go.Figure(go.Pie(
            labels=data["categories"],
            values=data["revenue"],
            hole=0.4,
            marker=dict(colors=px.colors.qualitative.Set3),
            textinfo='label+percent',
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Revenue by Category",
            height=350,
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # --- CHART 4: Customer Order Frequency ---
    def create_order_frequency_chart():
        """Create bar chart of customer order frequency"""
        data = get_customer_order_frequency(db)
        
        if not data["order_counts"]:
            return ft.Container(
                content=ft.Text("No customer data available", size=16, color="grey"),
                alignment=ft.alignment.center,
                padding=40
            )
        
        fig = go.Figure(go.Bar(
            x=[f"{count} order{'s' if count != 1 else ''}" for count in data["order_counts"]],
            y=data["customer_counts"],
            marker=dict(color='#FF9800'),
            text=data["customer_counts"],
            textposition='auto',
        ))
        
        fig.update_layout(
            title="Customer Order Frequency",
            xaxis_title="Number of Orders",
            yaxis_title="Number of Customers",
            height=300,
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # --- CHART 5: Hourly Sales Pattern ---
    def create_hourly_pattern_chart():
        """Create heatmap-style bar chart of hourly sales"""
        data = get_hourly_sales_pattern(db)
        
        if not data["hours"]:
            return ft.Container(
                content=ft.Text("No hourly data available", size=16, color="grey"),
                alignment=ft.alignment.center,
                padding=40
            )
        
        fig = go.Figure(go.Bar(
            x=[f"{h:02d}:00" for h in data["hours"]],
            y=data["orders"],
            marker=dict(
                color=data["orders"],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Orders")
            ),
            text=data["orders"],
            textposition='auto',
        ))
        
        fig.update_layout(
            title="Sales Pattern by Hour",
            xaxis_title="Hour of Day",
            yaxis_title="Number of Orders",
            height=300,
            margin=dict(l=40, r=40, t=60, b=40)
        )
        
        return PlotlyChart(fig, expand=True)
    
    # --- INVENTORY ALERTS TABLE ---
    def create_inventory_alerts():
        """Create inventory alerts table"""
        alerts = get_inventory_alerts(db)
        
        if not alerts:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=60, color="green"),
                    ft.Text("All inventory levels are healthy", size=16, color="grey")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.alignment.center,
                padding=40
            )
        
        alert_list = ft.Column(spacing=8)
        
        for alert in alerts:
            status_color = "red" if alert["status"] == "High Demand" else "orange"
            
            alert_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(
                            ft.Icons.WARNING_AMBER if alert["status"] == "High Demand" else ft.Icons.INFO,
                            color=status_color,
                            size=24
                        ),
                        ft.Column([
                            ft.Text(alert["name"], weight="bold", size=14),
                            ft.Text(f"Sold: {alert['quantity_sold']} units | Revenue: ₱{alert['revenue']:,.0f}", size=12, color="grey700"),
                        ], spacing=2, expand=True),
                        ft.Container(
                            content=ft.Text(alert["status"], size=12, color="white", weight="bold"),
                            bgcolor=status_color,
                            padding=ft.padding.symmetric(horizontal=12, vertical=6),
                            border_radius=5
                        )
                    ], alignment=ft.MainAxisAlignment.START),
                    border=ft.border.all(1, "grey300"),
                    border_radius=8,
                    padding=12,
                    bgcolor="white"
                )
            )
        
        return ft.Container(
            content=alert_list,
            padding=10
        )
    
    # --- LAYOUT ---
    page.clean()
    page.add(
        ft.Column([
            # Header
            ft.Container(
                content=ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        tooltip="Back to Admin Panel",
                        on_click=lambda e: page.go("/admin")
                    ),
                    ft.Text("📊 Analytics Dashboard", size=24, weight="bold"),
                ]),
                padding=10
            ),
            
            # Summary Cards
            ft.Container(content=summary_cards, padding=ft.padding.symmetric(horizontal=10)),
            
            # Charts Grid
            ft.Container(
                content=ft.Column([
                    # Row 1: Sales Trend (full width)
                    ft.Container(
                        content=ft.Column([
                            period_selector,
                            sales_chart_container
                        ], spacing=10),
                        border=ft.border.all(1, "grey300"),
                        border_radius=10,
                        padding=15,
                        bgcolor="white"
                    ),
                    
                    # Row 2: Best Sellers + Category Revenue
                    ft.Row([
                        ft.Container(
                            content=create_best_sellers_chart(),
                            border=ft.border.all(1, "grey300"),
                            border_radius=10,
                            padding=15,
                            bgcolor="white",
                            expand=1
                        ),
                        ft.Container(
                            content=create_category_revenue_chart(),
                            border=ft.border.all(1, "grey300"),
                            border_radius=10,
                            padding=15,
                            bgcolor="white",
                            expand=1
                        ),
                    ], spacing=10),
                    
                    # Row 3: Order Frequency + Hourly Pattern
                    ft.Row([
                        ft.Container(
                            content=create_order_frequency_chart(),
                            border=ft.border.all(1, "grey300"),
                            border_radius=10,
                            padding=15,
                            bgcolor="white",
                            expand=1
                        ),
                        ft.Container(
                            content=create_hourly_pattern_chart(),
                            border=ft.border.all(1, "grey300"),
                            border_radius=10,
                            padding=15,
                            bgcolor="white",
                            expand=1
                        ),
                    ], spacing=10),
                    
                    # Row 4: Inventory Alerts
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🚨 Inventory Alerts", size=18, weight="bold"),
                            ft.Divider(height=1),
                            create_inventory_alerts()
                        ], spacing=10),
                        border=ft.border.all(1, "grey300"),
                        border_radius=10,
                        padding=15,
                        bgcolor="white"
                    ),
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                padding=10,
                expand=True
            ),
        ], expand=True, spacing=0)
    )
    
    page.update()