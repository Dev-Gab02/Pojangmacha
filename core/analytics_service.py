from sqlalchemy.orm import Session
from models.order import Order, OrderItem
from models.food_item import FoodItem
from models.user import User
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

def get_sales_trends(db: Session, period="daily", days=30):
    """
    Get sales trends for specified period
    Returns: dict with dates and revenue
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    orders = db.query(Order).filter(
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()
    
    # Group by date
    sales_data = defaultdict(float)
    
    for order in orders:
        if period == "daily":
            date_key = order.created_at.strftime("%Y-%m-%d")
        elif period == "weekly":
            date_key = order.created_at.strftime("%Y-W%U")  # Year-Week
        else:  # monthly
            date_key = order.created_at.strftime("%Y-%m")
        
        sales_data[date_key] += order.total_price
    
    # Sort by date
    sorted_data = dict(sorted(sales_data.items()))
    
    return {
        "dates": list(sorted_data.keys()),
        "revenue": list(sorted_data.values())
    }

def get_best_selling_items(db: Session, limit=10):
    """
    Get top selling food items
    Returns: list of dicts with item name, quantity sold, revenue
    """
    # Query all order items
    order_items = db.query(OrderItem).all()
    
    # Aggregate by food item
    item_stats = defaultdict(lambda: {"quantity": 0, "revenue": 0.0})
    
    for oi in order_items:
        food = db.query(FoodItem).filter(FoodItem.id == oi.food_id).first()
        if food:
            item_stats[food.name]["quantity"] += oi.quantity
            item_stats[food.name]["revenue"] += oi.subtotal
            item_stats[food.name]["category"] = food.category
    
    # Convert to list and sort by quantity
    items_list = [
        {
            "name": name,
            "quantity": stats["quantity"],
            "revenue": stats["revenue"],
            "category": stats.get("category", "Unknown")
        }
        for name, stats in item_stats.items()
    ]
    
    items_list.sort(key=lambda x: x["quantity"], reverse=True)
    
    return items_list[:limit]

def get_revenue_by_category(db: Session):
    """
    Get revenue breakdown by food category
    Returns: dict with categories and revenue
    """
    categories = defaultdict(float)
    
    order_items = db.query(OrderItem).all()
    
    for oi in order_items:
        food = db.query(FoodItem).filter(FoodItem.id == oi.food_id).first()
        if food:
            categories[food.category] += oi.subtotal
    
    return {
        "categories": list(categories.keys()),
        "revenue": list(categories.values())
    }

def get_customer_order_frequency(db: Session):
    """
    Get customer order frequency distribution
    Returns: dict with order counts and customer counts
    """
    # Get all users
    users = db.query(User).filter(User.role == "customer").all()
    
    order_counts = defaultdict(int)
    
    for user in users:
        user_orders = db.query(Order).filter(Order.user_id == user.id).count()
        order_counts[user_orders] += 1
    
    # Sort by order count
    sorted_counts = dict(sorted(order_counts.items()))
    
    return {
        "order_counts": list(sorted_counts.keys()),
        "customer_counts": list(sorted_counts.values())
    }

def get_hourly_sales_pattern(db: Session):
    """
    Get sales pattern by hour of day
    Returns: dict with hours and order counts
    """
    orders = db.query(Order).all()
    
    hourly_data = defaultdict(int)
    
    for order in orders:
        hour = order.created_at.hour
        hourly_data[hour] += 1
    
    # Fill in missing hours with 0
    for h in range(24):
        if h not in hourly_data:
            hourly_data[h] = 0
    
    sorted_data = dict(sorted(hourly_data.items()))
    
    return {
        "hours": list(sorted_data.keys()),
        "orders": list(sorted_data.values())
    }

def get_inventory_alerts(db: Session):
    """
    Get items that might need restocking based on popularity
    Returns: list of items with predicted demand
    """
    best_sellers = get_best_selling_items(db, limit=20)
    
    # Simple prediction: items selling more than 10 units are "high demand"
    alerts = []
    
    for item in best_sellers:
        if item["quantity"] >= 10:
            alerts.append({
                "name": item["name"],
                "quantity_sold": item["quantity"],
                "revenue": item["revenue"],
                "status": "High Demand" if item["quantity"] >= 20 else "Medium Demand"
            })
    
    return alerts

def get_dashboard_summary(db: Session):
    """
    Get overall dashboard summary stats
    Returns: dict with key metrics
    """
    total_orders = db.query(Order).count()
    total_revenue = sum([o.total_price for o in db.query(Order).all()])
    total_customers = db.query(User).filter(User.role == "customer").count()
    total_items = db.query(FoodItem).count()
    
    # Get today's stats
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = db.query(Order).filter(Order.created_at >= today_start).count()
    today_revenue = sum([o.total_price for o in db.query(Order).filter(Order.created_at >= today_start).all()])
    
    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_customers": total_customers,
        "total_items": total_items,
        "today_orders": today_orders,
        "today_revenue": today_revenue
    }