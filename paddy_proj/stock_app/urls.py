from django.urls import path
from . import views
from . import integration

app_name = 'stock_app'

urlpatterns = [
    # Stock management views
    path('', views.stock_list, name='stock_list'),
    path('detail/<int:stock_id>/', views.stock_detail, name='stock_detail'),
    path('add/', views.add_stock, name='add_stock'),
    path('update/<int:stock_id>/', views.update_stock, name='update_stock'),
    path('delete/<int:stock_id>/', views.delete_stock, name='delete_stock'),
    
    # API endpoints
    path('api/check/<int:stock_id>/', views.stock_api_check, name='api_check_stock'),
    
    # Bill Generation & Stock Deduction Integration
    path('api/bill/<int:order_id>/deduct/', integration.generate_bill_with_deduction, name='bill_deduct_stock'),
    path('api/check-order-stock/', integration.check_stock_for_order, name='check_order_stock'),
    path('api/available-stocks/<str:product_name>/', integration.get_available_stocks_for_product, name='available_stocks'),
]
