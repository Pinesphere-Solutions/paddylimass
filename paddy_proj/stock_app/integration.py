"""
Integration module for Stock Management with Orders/Bills
This module provides views and utilities for integrating stock deduction with bill generation
"""

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.contrib import messages
from paddy_app.models import Orders
from paddy_app.decorators import role_required
from .models import Stock, StockDeduction
from .helpers import deduct_stock_for_bill, check_stock_availability
import json


@require_POST
@role_required(['admin', 'superadmin'])
def generate_bill_with_deduction(request, order_id):
    """
    Generate a bill and automatically deduct stock
    
    POST Parameters:
        stock_id: ID of the stock to deduct from
        custom_quantity: Optional custom quantity to deduct (defaults to order quantity)
    
    Returns:
        JSON response with success status
    """
    try:
        # Get order
        order = get_object_or_404(Orders, order_id=order_id)
        
        # Get stock ID from request
        stock_id = request.POST.get('stock_id') or request.POST.get('stockId')
        if not stock_id:
            return JsonResponse({
                'success': False,
                'error': 'Stock ID is required'
            }, status=400)
        
        # Get quantity to deduct (defaults to order quantity)
        quantity_str = request.POST.get('custom_quantity') or request.POST.get('customQuantity')
        if quantity_str:
            try:
                quantity = int(quantity_str)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid quantity format'
                }, status=400)
        else:
            quantity = order.quantity
        
        # Check if user has permission to deduct stock from this order's admin
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'admin' and order.admin.admin_id != user_id:
            return JsonResponse({
                'success': False,
                'error': 'You don\'t have permission to deduct stock from this order'
            }, status=403)
        
        # Deduct stock
        success, message, deduction_id = deduct_stock_for_bill(
            stock_id=stock_id,
            order_id=order_id,
            quantity=quantity,
            notes=f"Bill generated for Order {order_id}"
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'deduction_id': deduction_id,
                'order_id': order_id,
                'deducted_quantity': quantity
            })
        else:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
            
    except Orders.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Order {order_id} not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating bill: {str(e)}'
        }, status=500)


@require_POST
@role_required(['admin', 'superadmin'])
def check_stock_for_order(request):
    """
    Check if stocks are available for an order (AJAX API)
    
    POST Parameters:
        order_id: ID of the order
        stock_id: ID of the stock to check
        quantity: Quantity to check availability for (optional, defaults to order quantity)
    
    Returns:
        JSON response with availability info
    """
    try:
        order_id = request.POST.get('order_id') or request.POST.get('orderId')
        stock_id = request.POST.get('stock_id') or request.POST.get('stockId')
        quantity_str = request.POST.get('quantity')
        
        if not order_id or not stock_id:
            return JsonResponse({
                'success': False,
                'error': 'Order ID and Stock ID are required'
            }, status=400)
        
        # Get order to determine default quantity
        try:
            order = Orders.objects.get(order_id=order_id)
        except Orders.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Order not found'
            }, status=404)
        
        # Determine quantity to check
        if quantity_str:
            try:
                quantity = int(quantity_str)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid quantity format'
                }, status=400)
        else:
            quantity = order.quantity
        
        # Check availability
        is_available, message, available = check_stock_availability(stock_id, quantity)
        
        # Get stock details
        try:
            stock = Stock.objects.get(stock_id=stock_id)
            stock_data = {
                'stock_id': stock.stock_id,
                'product_name': stock.get_product_name_display(),
                'batch': stock.batch,
                'rate': str(stock.rate),
                'per': stock.per,
            }
        except Stock.DoesNotExist:
            stock_data = None
        
        return JsonResponse({
            'success': True,
            'available': is_available,
            'message': message,
            'available_quantity': available,
            'required_quantity': quantity,
            'stock': stock_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error checking stock: {str(e)}'
        }, status=500)


@role_required(['admin', 'superadmin'])
def get_available_stocks_for_product(request, product_name):
    """
    Get all available stocks for a specific product and admin
    
    Query Parameters:
        min_quantity: Minimum quantity required (optional)
    
    Returns:
        JSON response with available stocks
    """
    try:
        admin_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if role == 'admin':
            # Admins can only see their own stocks
            stocks = Stock.objects.filter(
                admin_id=admin_id,
                product_name=product_name
            )
        else:
            # Superadmins can see all stocks for a product
            stocks = Stock.objects.filter(product_name=product_name)
        
        min_quantity = request.GET.get('min_quantity')
        if min_quantity:
            try:
                min_qty = int(min_quantity)
                # Filter by minimum available quantity
                stocks_data = []
                for stock in stocks:
                    from .helpers import get_stock_balance
                    balance = get_stock_balance(stock.stock_id)
                    if balance and balance['available'] >= min_qty:
                        stocks_data.append({
                            'stock_id': stock.stock_id,
                            'batch': stock.batch,
                            'rate': str(stock.rate),
                            'per': stock.per,
                            'available_quantity': balance['available'],
                            'expiry_date': str(stock.expiry_date),
                        })
                stocks = stocks_data
            except ValueError:
                pass
        else:
            stocks = [{
                'stock_id': stock.stock_id,
                'batch': stock.batch,
                'rate': str(stock.rate),
                'per': stock.per,
                'expiry_date': str(stock.expiry_date),
            } for stock in stocks]
        
        return JsonResponse({
            'success': True,
            'product': product_name,
            'stocks': stocks
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
