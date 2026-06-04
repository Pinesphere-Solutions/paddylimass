from django.test import TestCase
from .models import Stock, StockDeduction
from paddy_app.models import AdminTable


class StockModelTest(TestCase):
    def setUp(self):
        self.admin = AdminTable.objects.create(
            first_name='Test',
            last_name='Admin',
            phone_number='1234567890',
            email='admin@test.com',
            password='testpass'
        )

    def test_stock_creation(self):
        stock = Stock.objects.create(
            admin=self.admin,
            product_name='rice',
            batch='BATCH001',
            expiry_date='2025-12-31',
            quantity=100,
            rate=50.00,
            per='kg'
        )
        self.assertEqual(stock.quantity, 100)
        self.assertEqual(stock.rate, 50.00)
        self.assertEqual(stock.amount, 5000.00)

    def test_amount_auto_calculation(self):
        stock = Stock.objects.create(
            admin=self.admin,
            product_name='paddy',
            batch='BATCH002',
            expiry_date='2025-12-31',
            quantity=200,
            rate=25.50,
            per='kg'
        )
        expected_amount = 200 * 25.50
        self.assertEqual(stock.amount, expected_amount)
