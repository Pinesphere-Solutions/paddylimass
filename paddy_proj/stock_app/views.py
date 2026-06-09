from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Stock, StockDeduction
from paddy_app.models import AdminTable
import json


def get_template_name(template_base, role):
    """
    Return role-specific template name.
    Maps generic template names to role-specific versions.
    """
    role_map = {
        'admin': 'admin_app',
        'superadmin': 'superadmin_app',
        'customer': 'customer_app',
    }
    
    app_name = role_map.get(role, 'admin_app')  # Default to admin
    template_name = template_base.split('/')[-1]  # Get filename only
    
    return f'stock_app/{app_name}_{template_name}'


def get_admin_context(request):
    """
    Helper function to get admin context based on user role
    Returns the admin_id for filtering stocks
    """
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    
    if not role or not user_id:
        return None, None
    
    if role == 'admin':
        # Admins can only see their own stocks
        return user_id, True  # (admin_id, can_edit)
    elif role == 'superadmin':
        # Superadmins can see all stocks
        return None, True  # (None for all, can_edit)
    elif role == 'customer':
        # Customers can see stocks of their admin
        try:
            from paddy_app.models import CustomerTable
            customer = CustomerTable.objects.get(customer_id=user_id)
            return customer.admin.admin_id, False  # (admin_id, cannot_edit)
        except:
            return None, False
    
    return None, False


def stock_list(request):
    """
    Display all stocks with filtering and pagination
    All users can view, but only admins/superadmin can edit
    """
    admin_id, can_edit = get_admin_context(request)
    
    if admin_id is None and request.session.get('role') not in ['superadmin', 'customer']:
        messages.error(request, "Please log in to view stocks.")
        return redirect('login_app:login')
    
    # Filter stocks based on user role
    if admin_id:
        stocks = Stock.objects.filter(admin_id=admin_id)
    else:
        stocks = Stock.objects.all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        stocks = stocks.filter(
            Q(batch__icontains=search_query) |
            Q(product_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(stocks, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    role = request.session.get('role')
    context = {
        'page_obj': page_obj,
        'stocks': page_obj.object_list,
        'search_query': search_query,
        'can_edit': can_edit,
        'role': role,
    }
    
    template_name = get_template_name('stock_app/stock_list.html', role)
    return render(request, template_name, context)


def stock_detail(request, stock_id):
    """
    View detailed information about a specific stock
    """
    stock = get_object_or_404(Stock, stock_id=stock_id)
    admin_id, can_edit = get_admin_context(request)
    
    # Check access permissions
    if admin_id and stock.admin_id != admin_id and request.session.get('role') != 'superadmin':
        messages.error(request, "You don't have permission to view this stock.")
        return redirect('stock_app:stock_list')
    
    # Get deduction history
    deductions = stock.deductions.all()
    total_deducted = deductions.aggregate(total=Sum('quantity_deducted'))['total'] or 0
    remaining_quantity = stock.quantity - total_deducted
    remaining_value = remaining_quantity * stock.rate
    
    role = request.session.get('role')
    context = {
        'stock': stock,
        'deductions': deductions,
        'total_deducted': total_deducted,
        'remaining_quantity': remaining_quantity,
        'remaining_value': remaining_value,
        'can_edit': can_edit,
        'role': role,
    }
    
    template_name = get_template_name('stock_app/stock_detail.html', role)
    return render(request, template_name, context)


def add_stock(request):
    """
    Add new stock item
    Only admins and superadmins can add stocks
    """
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    
    # Only admins and superadmins can add stocks
    if role not in ['admin', 'superadmin']:
        messages.error(request, "Only admins can add stock.")
        return redirect('stock_app:stock_list')
    
    if request.method == 'POST':
        try:
            # Get admin reference
            if role == 'admin':
                admin = AdminTable.objects.get(admin_id=user_id)
            else:
                # Superadmin - need to select which admin to add stock for
                admin_id = request.POST.get('admin_id')
                admin = AdminTable.objects.get(admin_id=admin_id)
            
            stock = Stock.objects.create(
                admin=admin,
                product_name=request.POST.get('product_name'),
                batch=request.POST.get('batch'),
                expiry_date=request.POST.get('expiry_date'),
                quantity=int(request.POST.get('quantity')),
                rate=request.POST.get('rate'),
                per=request.POST.get('per', 'kg'),
            )
            
            messages.success(request, f"Stock added successfully! Batch: {stock.batch}")
            return redirect('stock_app:stock_detail', stock_id=stock.stock_id)
            
        except AdminTable.DoesNotExist:
            messages.error(request, "Admin not found.")
        except ValueError as e:
            messages.error(request, f"Invalid input: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error adding stock: {str(e)}")
    
    # Get admin options for superadmin
    admins = AdminTable.objects.all() if role == 'superadmin' else None
    
    context = {
        'admins': admins,
        'role': role,
    }
    
    template_name = get_template_name('stock_app/add_stock.html', role)
    return render(request, template_name, context)


def update_stock(request, stock_id):
    """
    Update existing stock item
    Only admins and superadmins can update stocks
    """
    stock = get_object_or_404(Stock, stock_id=stock_id)
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    
    # Check permissions
    if role == 'admin' and stock.admin_id != user_id:
        messages.error(request, "You can only update your own stock.")
        return redirect('stock_app:stock_list')
    elif role not in ['admin', 'superadmin']:
        messages.error(request, "Only admins can update stock.")
        return redirect('stock_app:stock_list')
    
    if request.method == 'POST':
        try:
            stock.product_name = request.POST.get('product_name', stock.product_name)
            stock.batch = request.POST.get('batch', stock.batch)
            stock.expiry_date = request.POST.get('expiry_date', stock.expiry_date)
            stock.quantity = int(request.POST.get('quantity', stock.quantity))
            stock.rate = request.POST.get('rate', stock.rate)
            stock.per = request.POST.get('per', stock.per)
            stock.save()
            
            messages.success(request, "Stock updated successfully!")
            return redirect('stock_app:stock_detail', stock_id=stock.stock_id)
            
        except ValueError as e:
            messages.error(request, f"Invalid input: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error updating stock: {str(e)}")
    
    context = {
        'stock': stock,
        'role': role,
    }
    
    template_name = get_template_name('stock_app/update_stock.html', role)
    return render(request, template_name, context)


def delete_stock(request, stock_id):
    """
    Delete stock item
    Only admins and superadmins can delete stocks
    """
    stock = get_object_or_404(Stock, stock_id=stock_id)
    role = request.session.get('role')
    user_id = request.session.get('user_id')
    
    # Check permissions
    if role == 'admin' and stock.admin_id != user_id:
        messages.error(request, "You can only delete your own stock.")
        return redirect('stock_app:stock_list')
    elif role not in ['admin', 'superadmin']:
        messages.error(request, "Only admins can delete stock.")
        return redirect('stock_app:stock_list')
    
    if request.method == 'POST':
        try:
            batch_info = stock.batch
            stock.delete()
            messages.success(request, f"Stock (Batch: {batch_info}) deleted successfully!")
            return redirect('stock_app:stock_list')
        except Exception as e:
            messages.error(request, f"Error deleting stock: {str(e)}")
    
    context = {
        'stock': stock,
        'role': role,
    }
    
    template_name = get_template_name('stock_app/delete_stock.html', role)
    return render(request, template_name, context)


def deduct_stock(stock_id, order_id, quantity):
    """
    Internal function to deduct stock when a bill is printed
    Called from orders_app when bill is generated
    
    Returns: (success: bool, message: str)
    """
    try:
        stock = Stock.objects.get(stock_id=stock_id)
        
        # Get total deducted for this stock
        total_deducted = stock.deductions.aggregate(total=Sum('quantity_deducted'))['total'] or 0
        remaining = stock.quantity - total_deducted
        
        # Check if enough stock available
        if remaining < quantity:
            return False, f"Insufficient stock. Available: {remaining}, Requested: {quantity}"
        
        # Create deduction record
        StockDeduction.objects.create(
            stock=stock,
            order_id=order_id,
            quantity_deducted=quantity,
            notes=f"Deducted for Order {order_id}"
        )
        
        return True, f"Stock deducted successfully. Remaining: {remaining - quantity}"
        
    except Stock.DoesNotExist:
        return False, "Stock not found."
    except Exception as e:
        return False, f"Error deducting stock: {str(e)}"


def stock_api_check(request, stock_id):
    """
    API endpoint to check available stock quantity
    Returns JSON with remaining quantity
    """
    try:
        stock = Stock.objects.get(stock_id=stock_id)
        total_deducted = stock.deductions.aggregate(total=Sum('quantity_deducted'))['total'] or 0
        remaining = stock.quantity - total_deducted
        
        return JsonResponse({
            'success': True,
            'stock_id': stock.stock_id,
            'product_name': stock.get_product_name_display(),
            'batch': stock.batch,
            'total_quantity': stock.quantity,
            'deducted_quantity': total_deducted,
            'remaining_quantity': remaining,
            'rate': str(stock.rate),
            'per': stock.per,
            'amount': str(stock.amount),
        })
    except Stock.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Stock not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
