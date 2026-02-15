# API Usage Examples

This document shows practical examples of using the Inventory Management API.

## Starting the Server

```bash
# Install dependencies (when network is available)
pip install fastapi uvicorn pydantic pytest httpx

# Run the server
python app.py

# Server runs on http://localhost:8000
# API docs available at http://localhost:8000/docs
```

## Example Workflows

### Workflow 1: Simple Receive and Issue (No QC)

```bash
# Step 1: Create an item that doesn't require QC
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{
    "code": "STEEL-001",
    "name": "Steel Bar",
    "qc_required": false
  }'

# Response: {"id": "abc-123", "code": "STEEL-001", ...}

# Step 2: Receive 100 units
curl -X POST http://localhost:8000/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "abc-123",
    "lot_code": "LOT-2024-001",
    "qty": 100.0
  }'

# Response: {..., "qc_status": "APPROVED"}

# Step 3: Check stock
curl http://localhost:8000/inventory/summary/abc-123

# Response: {"on_hand": 100.0, "reserved": 0, "available": 100.0}

# Step 4: Reserve 30 units
curl -X POST http://localhost:8000/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "abc-123",
    "qty": 30.0
  }'

# Response: {"reservation_id": "res-456", "qty": 30.0, "status": "OPEN"}

# Step 5: Check stock after reservation
curl http://localhost:8000/inventory/summary/abc-123

# Response: {"on_hand": 100.0, "reserved": 30.0, "available": 70.0}

# Step 6: Issue the reserved stock
curl -X POST http://localhost:8000/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{
    "reservation_id": "res-456"
  }'

# Response: {
#   "reservation_id": "res-456",
#   "qty": 30.0,
#   "lots_issued": [{"lot_code": "LOT-2024-001", "qty": 30.0}]
# }

# Step 7: Final stock check
curl http://localhost:8000/inventory/summary/abc-123

# Response: {"on_hand": 70.0, "reserved": 0, "available": 70.0}
```

### Workflow 2: QC Workflow

```bash
# Step 1: Create item requiring QC
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{
    "code": "PHARMA-001",
    "name": "Active Ingredient",
    "qc_required": true
  }'

# Response: {"id": "xyz-789", ...}

# Step 2: Receive inventory (goes to QUARANTINE)
curl -X POST http://localhost:8000/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "xyz-789",
    "lot_code": "LOT-QC-001",
    "qty": 50.0
  }'

# Response: {..., "lot_id": "lot-999", "qc_status": "QUARANTINE"}

# Step 3: Try to reserve (FAILS - no approved lots)
curl -X POST http://localhost:8000/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "xyz-789",
    "qty": 20.0
  }'

# Response: 400 Bad Request
# {"detail": {"error_code": "NO_QC_APPROVED_LOT", ...}}

# Step 4: Approve the lot
curl -X PATCH "http://localhost:8000/inventory/lots/lot-999/qc-status?qc_status=APPROVED"

# Response: {"lot_id": "lot-999", "qc_status": "APPROVED"}

# Step 5: Now reservation succeeds
curl -X POST http://localhost:8000/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "xyz-789",
    "qty": 20.0
  }'

# Response: {"reservation_id": "res-111", ...}

# Step 6: Issue
curl -X POST http://localhost:8000/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{
    "reservation_id": "res-111"
  }'

# Success!
```

### Workflow 3: Multi-Lot FIFO Issue

```bash
# Create item
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"code": "WIDGET-001", "name": "Widget", "qc_required": false}'

# Receive 3 lots
curl -X POST http://localhost:8000/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item-123", "lot_code": "LOT-A", "qty": 30.0}'

curl -X POST http://localhost:8000/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item-123", "lot_code": "LOT-B", "qty": 40.0}'

curl -X POST http://localhost:8000/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item-123", "lot_code": "LOT-C", "qty": 30.0}'

# Total: 100 units in 3 lots

# Reserve 80 units
curl -X POST http://localhost:8000/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item-123", "qty": 80.0}'

# Response: {"reservation_id": "res-multi", ...}

# Issue (will span multiple lots in FIFO order)
curl -X POST http://localhost:8000/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{"reservation_id": "res-multi"}'

# Response:
# {
#   "qty": 80.0,
#   "lots_issued": [
#     {"lot_code": "LOT-A", "qty": 30.0},  # LOT-A exhausted
#     {"lot_code": "LOT-B", "qty": 40.0},  # LOT-B exhausted
#     {"lot_code": "LOT-C", "qty": 10.0}   # LOT-C partially used
#   ]
# }

# Check remaining stock
curl http://localhost:8000/inventory/summary/item-123

# Response: {"on_hand": 20.0, "reserved": 0, "available": 20.0}
# (20 units remain in LOT-C)
```

## Error Scenarios

### 1. Insufficient Stock

```bash
curl -X POST http://localhost:8000/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item-123", "qty": 999.0}'

# Response: 400 Bad Request
# {
#   "detail": {
#     "error_code": "INSUFFICIENT_STOCK",
#     "message": "Insufficient stock. Available: 100, Requested: 999"
#   }
# }
```

### 2. No QC Approved Lots

```bash
# Item requires QC, lot is in QUARANTINE
curl -X POST http://localhost:8000/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{"item_id": "qc-item", "qty": 10.0}'

# Response: 400 Bad Request
# {
#   "detail": {
#     "error_code": "NO_QC_APPROVED_LOT",
#     "message": "No QC-approved lots available for this item"
#   }
# }
```

### 3. Reservation Not Found

```bash
curl -X POST http://localhost:8000/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{"reservation_id": "fake-id"}'

# Response: 404 Not Found
# {
#   "detail": {
#     "error_code": "RESERVATION_NOT_FOUND",
#     "message": "Reservation fake-id not found"
#   }
# }
```

### 4. Already Issued (Idempotency)

```bash
# Issue once (succeeds)
curl -X POST http://localhost:8000/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{"reservation_id": "res-123"}'

# Try to issue again (fails)
curl -X POST http://localhost:8000/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{"reservation_id": "res-123"}'

# Response: 400 Bad Request
# {
#   "detail": {
#     "error_code": "RESERVATION_ALREADY_ISSUED",
#     "message": "Reservation res-123 is already ISSUED"
#   }
# }
```

### 5. Duplicate Lot Code

```bash
# Receive lot
curl -X POST http://localhost:8000/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item-1", "lot_code": "LOT-001", "qty": 100.0}'

# Try to receive with same lot code (fails)
curl -X POST http://localhost:8000/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{"item_id": "item-1", "lot_code": "LOT-001", "qty": 50.0}'

# Response: 400 Bad Request
# {
#   "detail": {
#     "error_code": "DUPLICATE_LOT_CODE",
#     "message": "Lot code LOT-001 already exists"
#   }
# }
```

## Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Create item
item_resp = requests.post(f"{BASE_URL}/items", json={
    "code": "STEEL-001",
    "name": "Steel Bar",
    "qc_required": False
})
item_id = item_resp.json()['id']

# Receive inventory
receive_resp = requests.post(f"{BASE_URL}/inventory/receive", json={
    "item_id": item_id,
    "lot_code": "LOT-001",
    "qty": 100.0
})
print(f"Received: {receive_resp.json()}")

# Check stock
summary = requests.get(f"{BASE_URL}/inventory/summary/{item_id}").json()
print(f"Stock: {summary}")  # on_hand: 100, reserved: 0, available: 100

# Reserve
reserve_resp = requests.post(f"{BASE_URL}/inventory/reserve", json={
    "item_id": item_id,
    "qty": 30.0
})
reservation_id = reserve_resp.json()['reservation_id']

# Check stock after reserve
summary = requests.get(f"{BASE_URL}/inventory/summary/{item_id}").json()
print(f"After reserve: {summary}")  # on_hand: 100, reserved: 30, available: 70

# Issue
issue_resp = requests.post(f"{BASE_URL}/inventory/issue", json={
    "reservation_id": reservation_id
})
print(f"Issued: {issue_resp.json()}")

# Final stock
summary = requests.get(f"{BASE_URL}/inventory/summary/{item_id}").json()
print(f"Final: {summary}")  # on_hand: 70, reserved: 0, available: 70
```

## Testing Tips

1. **Use the interactive docs**: Visit http://localhost:8000/docs to try APIs in browser

2. **Check ledger**: Query the database directly to see all transactions
   ```sql
   SELECT * FROM inventory_ledger ORDER BY timestamp;
   ```

3. **Verify stock calculations**: All stock is calculated from ledger
   ```sql
   SELECT 
     txn_type,
     SUM(qty) as total_qty
   FROM inventory_ledger 
   WHERE item_id = 'your-item-id'
   GROUP BY txn_type;
   ```

4. **Test concurrency**: Run multiple reserves/issues in parallel
   - The system uses database-level locking for safety
   - SQLite `BEGIN IMMEDIATE` prevents race conditions

## Common Patterns

### Pattern 1: Batch Receiving
```bash
# Receive multiple lots at once
for i in {1..5}; do
  curl -X POST http://localhost:8000/inventory/receive \
    -H "Content-Type: application/json" \
    -d "{\"item_id\": \"item-123\", \"lot_code\": \"LOT-$i\", \"qty\": 100.0}"
done
```

### Pattern 2: Reservation with Auto-Issue
```python
# Reserve and immediately issue
def reserve_and_issue(item_id, qty):
    # Reserve
    reserve_resp = requests.post(f"{BASE_URL}/inventory/reserve", 
        json={"item_id": item_id, "qty": qty})
    
    reservation_id = reserve_resp.json()['reservation_id']
    
    # Issue
    issue_resp = requests.post(f"{BASE_URL}/inventory/issue",
        json={"reservation_id": reservation_id})
    
    return issue_resp.json()
```

### Pattern 3: Stock Level Monitoring
```python
def check_stock_levels(item_ids):
    for item_id in item_ids:
        summary = requests.get(f"{BASE_URL}/inventory/summary/{item_id}").json()
        
        if summary['available'] < 20:
            print(f"⚠️  LOW STOCK: Item {item_id} has {summary['available']} available")
        else:
            print(f"✓ OK: Item {item_id} has {summary['available']} available")
```

## Performance Notes

- Stock calculations are done in real-time from ledger (no caching)
- For high-traffic items, consider adding a caching layer (Redis)
- Database locking ensures correctness at the cost of some throughput
- For production, migrate to PostgreSQL with proper connection pooling

## Troubleshooting

**Problem**: "INSUFFICIENT_STOCK" but stock looks correct
- **Solution**: Check for open reservations: `GET /inventory/summary/{item_id}`
- Reserved stock reduces available, even if physically present

**Problem**: Cannot reserve from new lot
- **Solution**: Check QC status. Use `PATCH /inventory/lots/{lot_id}/qc-status` to approve

**Problem**: "RESERVATION_ALREADY_ISSUED"
- **Solution**: This is correct behavior (idempotency). Each reservation can only be issued once.

**Problem**: Stock numbers don't match expectations
- **Solution**: Check ledger directly in database:
  ```sql
  SELECT txn_type, SUM(qty) FROM inventory_ledger 
  WHERE item_id = 'item-id' GROUP BY txn_type;
  ```
