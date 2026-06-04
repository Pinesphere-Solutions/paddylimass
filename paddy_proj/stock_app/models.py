from django.db import models
from django.core.validators import MinValueValidator
from paddy_app.models import AdminTable
from datetime import datetime

class Stock(models.Model):
    PRODUCT_CHOICES = [
        ('rice', 'Rice'),
        ('paddy', 'Paddy'),
    ]

    stock_id = models.BigAutoField(primary_key=True)
    admin = models.ForeignKey(AdminTable, on_delete=models.CASCADE, related_name='stocks')
    product_name = models.CharField(
        max_length=50, 
        choices=PRODUCT_CHOICES,
        default='rice'
    )
    batch = models.CharField(max_length=100)
    expiry_date = models.DateField()
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    per = models.CharField(
        max_length=20,
        help_text="Unit of measurement (e.g., kg, bags, tons)",
        default='kg'
    )
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        editable=False,
        help_text="Auto-calculated: Quantity * Rate"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin', 'product_name']),
            models.Index(fields=['expiry_date']),
        ]

    def save(self, *args, **kwargs):
        """Auto-calculate amount before saving"""
        self.amount = self.quantity * self.rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_product_name_display()} - Batch: {self.batch} (Qty: {self.quantity} {self.per})"


class StockDeduction(models.Model):
    """Track stock deductions when bills are printed/generated"""
    deduction_id = models.BigAutoField(primary_key=True)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='deductions')
    order_id = models.BigIntegerField(help_text="Reference to Orders table")
    quantity_deducted = models.IntegerField(validators=[MinValueValidator(1)])
    deduction_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-deduction_date']

    def __str__(self):
        return f"Deduction: {self.quantity_deducted} from Stock {self.stock.stock_id} (Order: {self.order_id})"
