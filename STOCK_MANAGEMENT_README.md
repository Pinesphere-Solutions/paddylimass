# Stock Management Feature Documentation

## Overview

The **Stock Management** module allows admins to track rice and paddy inventory with automatic stock deduction when bills are generated. This feature supports multi-batch tracking, expiry date management, and complete deduction history.

## Features

✅ **Inventory Tracking**
- Track rice and paddy stocks separately
- Multiple batches per product
- Track expiry dates
- Auto-calculated total amount (Quantity × Rate)

✅ **Stock Management**
- Add new stock entries
- Update existing stocks
- Delete stock records
- Search and filter stocks

✅ **Automatic Deduction**
- Automatic stock deduction when bills are printed
- Deduction history tracking
- Insufficient stock validation

✅ **Access Control**
- **Admins**: Can add/edit/delete their own stocks, view deduction history
- **Superadmins**: Can view/manage all stocks
- **Customers**: Can view their admin's stocks (read-only)

✅ **Reporting**
- Stock balance calculation
- Deduction history
- Expiry date tracking
- Stock valuation

## Usage Guide

### 1. **Add Stock**

**Route**: `/stock/add/`

**Who Can Access**: Admin, Superadmin

**Form Fields**:
- **Product Name** (required): Rice or Paddy
- **Batch Number** (required): Unique batch identifier (e.g., BATCH-001, BATCH-2024-001)
- **Expiry Date** (required): Date when batch expires
- **Quantity** (required): Number of units in stock
- **Unit (Per)** (required): kg, bags, tons, liters, or units
- **Rate** (required): Price per unit in rupees
- **Amount** (auto-calculated): Total = Quantity × Rate

**Example**:
```
Product: Rice
Batch: BATCH-2024-001
Expiry Date: 2025-12-31
Quantity: 100
Unit: kg
Rate: 50.00
Amount: 5000.00 (auto-calculated)
```

### 2. **View Stocks**

**Route**: `/stock/`

**Who Can Access**: All users (Admin, Superadmin, Customer)

**Features**:
- List all stocks with pagination (10 per page)
- Search by batch number or product name
- Sort by creation date
- View action buttons for each stock
- Edit/Delete buttons (admins only)

### 3. **View Stock Details**

**Route**: `/stock/detail/<stock_id>/`

**Who Can Access**: All users

**Information Displayed**:
- Stock details (ID, Product, Batch, Admin)
- Quantity information:
  - Total Quantity
  - Total Deducted
  - Remaining Balance (calculated)
- Financial details:
  - Rate per unit
  - Total Amount
  - Expiry Date
  - Value of Remaining Stock
- Deduction history table with:
  - Deduction ID
  - Related Order ID
  - Quantity Deducted
  - Deduction Date/Time
  - Notes

### 4. **Edit Stock**

**Route**: `/stock/update/<stock_id>/`

**Who Can Access**: Admin (own stocks), Superadmin

**Editable Fields**:
- Product Name
- Batch Number
- Expiry Date
- Quantity
- Unit
- Rate

**Note**: Editing quantity recalculates the remaining balance for future deductions.

### 5. **Delete Stock**

**Route**: `/stock/delete/<stock_id>/`

**Who Can Access**: Admin (own stocks), Superadmin

**Warning**: Deletion is permanent and cannot be undone. Existing deduction records remain for audit purposes.

## Bill Integration

### How to Integrate Stock Deduction with Bill Generation

When a bill is printed/generated for an order, stock should be automatically deducted. Here's how to integrate:

#### Method 1: Using AJAX API Endpoint

**Endpoint**: `/stock/api/bill/<order_id>/deduct/`

**Method**: POST

**Parameters**:
```json
{
    "stock_id": "123",
    "custom_quantity": "50"  // Optional: defaults to order quantity
}
```

**Example JavaScript**:
```javascript
function generateBillWithStockDeduction(orderId, stockId, customQuantity = null) {
    const formData = new FormData();
    formData.append('stock_id', stockId);
    if (customQuantity) {
        formData.append('custom_quantity', customQuantity);
    }
    
    fetch(`/stock/api/bill/${orderId}/deduct/`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Stock deducted:', data.message);
            // Generate bill/PDF
            generateBillPDF(orderId);
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => console.error('Error:', error));
}
```

#### Method 2: Using Python Helper Functions

```python
from stock_app.helpers import deduct_stock_for_bill

# When generating a bill:
success, message, deduction_id = deduct_stock_for_bill(
    stock_id=123,
    order_id=order.order_id,
    quantity=order.quantity,
    notes=f"Bill generated for {order.customer.first_name}"
)

if success:
    # Generate bill PDF
    generate_bill_pdf(order)
else:
    # Handle error - show message to user
    raise Exception(message)
```

#### Method 3: Check Stock Before Bill Generation

**Endpoint**: `/stock/api/check-order-stock/`

**Method**: POST

**Parameters**:
```json
{
    "order_id": "100",
    "stock_id": "123",
    "quantity": "50"  // Optional
}
```

**Response**:
```json
{
    "success": true,
    "available": true,
    "message": "Stock available: 45 units",
    "available_quantity": 45,
    "required_quantity": 50,
    "stock": {
        "stock_id": 123,
        "product_name": "Rice",
        "batch": "BATCH-001",
        "rate": "50.00",
        "per": "kg"
    }
}
```

### Implementation in Orders App

In `orders_app/views.py`, when a bill is generated:

```python
from stock_app.helpers import deduct_stock_for_bill, check_stock_availability

def generate_bill(request, order_id):
    order = Orders.objects.get(order_id=order_id)
    
    # Check if stock is selected
    stock_id = request.POST.get('stock_id')
    if not stock_id:
        return JsonResponse({'error': 'Stock selection required'}, status=400)
    
    # Check availability first
    is_available, msg, available = check_stock_availability(stock_id, order.quantity)
    if not is_available:
        return JsonResponse({'error': msg}, status=400)
    
    # Deduct stock
    success, message, deduction_id = deduct_stock_for_bill(
        stock_id=stock_id,
        order_id=order_id,
        quantity=order.quantity
    )
    
    if success:
        # Generate bill PDF
        bill_data = generate_bill_pdf(order)
        return JsonResponse({
            'success': True,
            'deduction_id': deduction_id,
            'bill_url': bill_data['url']
        })
    else:
        return JsonResponse({'error': message}, status=400)
```

## Data Models

### Stock Model
```python
stock_id          # BigAutoField (Primary Key)
admin             # ForeignKey(AdminTable)
product_name      # CharField (choices: rice, paddy)
batch             # CharField (unique batch identifier)
expiry_date       # DateField
quantity          # IntegerField
rate              # DecimalField(10, 2)
per               # CharField (kg, bags, tons, liters, units)
amount            # DecimalField(15, 2) [auto-calculated]
created_at        # DateTimeField (auto-set)
updated_at        # DateTimeField (auto-updated)
```

### StockDeduction Model
```python
deduction_id      # BigAutoField (Primary Key)
stock             # ForeignKey(Stock)
order_id          # BigIntegerField (reference to Orders table)
quantity_deducted # IntegerField
deduction_date    # DateTimeField (auto-set)
notes             # TextField (optional)
```

## Helper Functions

### `get_stock_balance(stock_id)`
Returns remaining balance after all deductions.

```python
from stock_app.helpers import get_stock_balance

balance = get_stock_balance(123)
# {
#     'available': 45,
#     'total': 100,
#     'deducted': 55,
#     'percentage_available': 45.0,
#     'stock': <Stock object>
# }
```

### `check_stock_availability(stock_id, required_quantity)`
Checks if stock has enough quantity.

```python
from stock_app.helpers import check_stock_availability

is_available, message, available = check_stock_availability(123, 50)
# (True, 'Stock available: 45 units', 45)
```

### `deduct_stock_for_bill(stock_id, order_id, quantity, notes=None)`
Deducts stock when bill is generated.

```python
from stock_app.helpers import deduct_stock_for_bill

success, message, deduction_id = deduct_stock_for_bill(
    stock_id=123,
    order_id=100,
    quantity=50,
    notes="Bill for customer ABC"
)
# (True, 'Stock deducted successfully. Remaining: -5', 1)
```

### `get_admin_stocks(admin_id, product_name=None)`
Gets all stocks for an admin, optionally filtered by product.

### `get_expiring_stocks(admin_id=None, days_threshold=30)`
Gets stocks expiring within the threshold period.

### `generate_stock_report(admin_id=None)`
Generates comprehensive stock statistics.

## API Endpoints

### Check Stock Availability
- **URL**: `/stock/api/check/<stock_id>/`
- **Method**: GET
- **Response**: Stock details and balance information

### Generate Bill with Deduction
- **URL**: `/stock/api/bill/<order_id>/deduct/`
- **Method**: POST
- **Parameters**: stock_id, custom_quantity (optional)
- **Response**: Deduction details or error

### Check Stock for Order
- **URL**: `/stock/api/check-order-stock/`
- **Method**: POST
- **Parameters**: order_id, stock_id, quantity (optional)
- **Response**: Availability status and stock details

### Get Available Stocks
- **URL**: `/stock/api/available-stocks/<product_name>/`
- **Method**: GET
- **Query Parameters**: min_quantity (optional)
- **Response**: List of available stocks for product

## Admin Panel

Stock models are registered in Django Admin (`/admin/`):
- **Stock Admin**: View, filter, and manage stocks
- **StockDeduction Admin**: View deduction history, filter by date/product

## Database Migrations

```bash
# Generate migrations
python manage.py makemigrations stock_app

# Apply migrations
python manage.py migrate stock_app
```

## Testing

Test the stock management feature:

1. **Add Stock**:
   - Navigate to `/stock/add/`
   - Fill form with test data
   - Verify auto-calculation of amount

2. **View Stocks**:
   - Visit `/stock/`
   - Test search by batch name
   - Verify pagination

3. **Deduct Stock**:
   - Use integration endpoint
   - Verify deduction records created
   - Check remaining balance calculation

4. **Check Availability**:
   - Test API endpoint with order
   - Verify insufficient stock error handling
   - Test with valid stock levels

## Future Enhancements

- [ ] Stock level alerts (low stock warnings)
- [ ] Batch expiry warnings
- [ ] Automated stock reconciliation
- [ ] Stock transfer between admins
- [ ] Stock historical trends/analytics
- [ ] Barcode scanning for stock management
- [ ] Integration with purchase orders
- [ ] Stock forecasting

## Troubleshooting

### Issue: "Insufficient stock" error
**Solution**: Check remaining balance in stock detail view. Ensure quantity in stock is greater than order quantity.

### Issue: Stock not appearing in list
**Solution**: 
- If admin: Verify stock belongs to your admin account
- Check expiry date is in the future
- Verify stock_app is in INSTALLED_APPS

### Issue: Deduction not recorded
**Solution**:
- Ensure order_id exists in Orders table
- Verify stock_id is valid
- Check stock has sufficient quantity

## Support

For issues or questions, refer to:
- [Stock app code](./stock_app/)
- [Helper functions](./stock_app/helpers.py)
- [Integration module](./stock_app/integration.py)
