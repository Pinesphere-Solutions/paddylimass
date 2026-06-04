from django.contrib import admin
from .models import Stock, StockDeduction


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('stock_id', 'admin', 'product_name', 'batch', 'quantity', 'rate', 'per', 'expiry_date', 'created_at')
    list_filter = ('admin', 'product_name', 'expiry_date', 'created_at')
    search_fields = ('batch', 'product_name')
    readonly_fields = ('amount', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Admin & Product Info', {
            'fields': ('admin', 'product_name')
        }),
        ('Stock Details', {
            'fields': ('batch', 'expiry_date', 'quantity', 'per', 'rate', 'amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(StockDeduction)
class StockDeductionAdmin(admin.ModelAdmin):
    list_display = ('deduction_id', 'stock', 'order_id', 'quantity_deducted', 'deduction_date')
    list_filter = ('deduction_date', 'stock__admin', 'stock__product_name')
    search_fields = ('stock__batch', 'order_id')
    readonly_fields = ('deduction_date',)
