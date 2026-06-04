"""
Helper utilities for Stock Management
These functions facilitate integration between Stock and Orders systems
"""

from django.db.models import Sum
from .models import Stock, StockDeduction
from paddy_app.models import Orders


def get_stock_balance(stock_id):
    """
    Get the remaining balance of a stock after all deductions
    
    Args:
        stock_id: ID of the stock to check
    
    Returns:
        dict: {
            'available': remaining_quantity,
            'total': total_quantity,
            'deducted': total_deducted,
            'percentage_available': percentage
        }
    """
    try:
        stock = Stock.objects.get(stock_id=stock_id)
        total_deducted = stock.deductions.aggregate(total=Sum('quantity_deducted'))['total'] or 0
        available = stock.quantity - total_deducted
        
        percentage = (available / stock.quantity * 100) if stock.quantity > 0 else 0
        
        return {
            'available': available,
            'total': stock.quantity,
            'deducted': total_deducted,
            'percentage_available': round(percentage, 2),
            'stock': stock
        }
    except Stock.DoesNotExist:
        return None


def check_stock_availability(stock_id, required_quantity):
    """
    Check if a stock has enough quantity available for an order
    
    Args:
        stock_id: ID of the stock
        required_quantity: Quantity needed for the order
    
    Returns:
        tuple: (is_available: bool, message: str, available_quantity: int)
    """
    balance = get_stock_balance(stock_id)
    
    if balance is None:
        return False, "Stock not found", 0
    
    if balance['available'] < required_quantity:
        return False, f"Insufficient stock. Available: {balance['available']}, Required: {required_quantity}", balance['available']
    
    return True, f"Stock available: {balance['available']} units", balance['available']


def deduct_stock_for_bill(stock_id, order_id, quantity, notes=None):
    """
    Deduct stock when a bill is generated/printed
    
    Args:
        stock_id: ID of the stock to deduct from
        order_id: ID of the order (for reference)
        quantity: Quantity to deduct
        notes: Optional notes about the deduction
    
    Returns:
        tuple: (success: bool, message: str, deduction_id: int or None)
    """
    try:
        # Verify stock exists
        stock = Stock.objects.get(stock_id=stock_id)
        
        # Check availability
        is_available, msg, available = check_stock_availability(stock_id, quantity)
        if not is_available:
            return False, msg, None
        
        # Verify order exists
        try:
            order = Orders.objects.get(order_id=order_id)
        except Orders.DoesNotExist:
            return False, f"Order {order_id} not found", None
        
        # Create deduction record
        deduction = StockDeduction.objects.create(
            stock=stock,
            order_id=order_id,
            quantity_deducted=quantity,
            notes=notes or f"Deducted for Order {order_id} - {order.category if hasattr(order, 'category') else 'Product'}"
        )
        
        return True, f"Stock deducted successfully. Remaining: {available - quantity}", deduction.deduction_id
        
    except Stock.DoesNotExist:
        return False, "Stock not found", None
    except Orders.DoesNotExist:
        return False, "Order not found", None
    except Exception as e:
        return False, f"Error deducting stock: {str(e)}", None


def get_admin_stocks(admin_id, product_name=None):
    """
    Get all stocks for a specific admin, optionally filtered by product
    
    Args:
        admin_id: ID of the admin
        product_name: Optional product name filter ('rice', 'paddy')
    
    Returns:
        QuerySet of Stock objects
    """
    stocks = Stock.objects.filter(admin_id=admin_id)
    
    if product_name:
        stocks = stocks.filter(product_name=product_name)
    
    return stocks.order_by('-created_at')


def get_stock_deduction_history(stock_id):
    """
    Get the complete deduction history for a stock
    
    Args:
        stock_id: ID of the stock
    
    Returns:
        list of deductions with order details
    """
    try:
        stock = Stock.objects.get(stock_id=stock_id)
        deductions = stock.deductions.all().order_by('-deduction_date')
        
        return {
            'stock': stock,
            'deductions': deductions,
            'total_deductions': deductions.aggregate(total=Sum('quantity_deducted'))['total'] or 0,
        }
    except Stock.DoesNotExist:
        return None


def get_expiring_stocks(admin_id=None, days_threshold=30):
    """
    Get stocks that are expiring within the specified threshold
    
    Args:
        admin_id: Optional - filter for specific admin
        days_threshold: Number of days from now to consider as "expiring"
    
    Returns:
        QuerySet of expiring stocks
    """
    from datetime import timedelta
    from django.utils import timezone
    
    expiry_date_threshold = timezone.now().date() + timedelta(days=days_threshold)
    
    stocks = Stock.objects.filter(expiry_date__lte=expiry_date_threshold)
    
    if admin_id:
        stocks = stocks.filter(admin_id=admin_id)
    
    return stocks.order_by('expiry_date')


def generate_stock_report(admin_id=None):
    """
    Generate a comprehensive stock report
    
    Args:
        admin_id: Optional - filter for specific admin
    
    Returns:
        dict with stock statistics and details
    """
    if admin_id:
        stocks = Stock.objects.filter(admin_id=admin_id)
    else:
        stocks = Stock.objects.all()
    
    total_value = 0
    stocks_data = []
    
    for stock in stocks:
        balance_info = get_stock_balance(stock.stock_id)
        if balance_info:
            stock_value = balance_info['available'] * float(stock.rate)
            total_value += stock_value
            
            stocks_data.append({
                'stock': stock,
                'available': balance_info['available'],
                'total': balance_info['total'],
                'deducted': balance_info['deducted'],
                'value': stock_value,
            })
    
    return {
        'stocks': stocks_data,
        'total_stocks': stocks.count(),
        'total_value': total_value,
        'by_product': {
            'rice': stocks.filter(product_name='rice').count(),
            'paddy': stocks.filter(product_name='paddy').count(),
        }
    }
