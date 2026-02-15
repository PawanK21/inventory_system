import pytest
from fastapi.testclient import TestClient
from app import app, init_db
import os
import sqlite3

# Test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db():
    """Setup fresh database for each test"""
    if os.path.exists("inventory.db"):
        os.remove("inventory.db")
    init_db()
    yield
    if os.path.exists("inventory.db"):
        os.remove("inventory.db")

def create_test_item(qc_required=False):
    """Helper to create a test item"""
    response = client.post("/items", json={
        "code": f"ITEM-{os.urandom(4).hex()}",
        "name": "Test Item",
        "qc_required": qc_required
    })
    assert response.status_code == 201
    return response.json()

def test_create_item():
    """Test item creation"""
    response = client.post("/items", json={
        "code": "STEEL-001",
        "name": "Steel Bar",
        "qc_required": True
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data['code'] == "STEEL-001"
    assert data['name'] == "Steel Bar"
    assert data['qc_required'] == True

def test_receive_inventory_no_qc():
    """Test receiving inventory without QC requirement"""
    item = create_test_item(qc_required=False)
    
    response = client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data['received_qty'] == 100.0
    assert data['qc_status'] == "APPROVED"

def test_receive_inventory_with_qc():
    """Test receiving inventory with QC requirement starts in QUARANTINE"""
    item = create_test_item(qc_required=True)
    
    response = client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-QC-001",
        "qty": 50.0
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data['received_qty'] == 50.0
    assert data['qc_status'] == "QUARANTINE"

def test_stock_summary_empty():
    """Test stock summary for item with no inventory"""
    item = create_test_item()
    
    response = client.get(f"/inventory/summary/{item['id']}")
    assert response.status_code == 200
    
    data = response.json()
    assert data['on_hand'] == 0
    assert data['reserved'] == 0
    assert data['available'] == 0

def test_stock_summary_after_receive():
    """Test stock summary after receiving inventory"""
    item = create_test_item(qc_required=False)
    
    # Receive 100 units
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    response = client.get(f"/inventory/summary/{item['id']}")
    data = response.json()
    
    assert data['on_hand'] == 100.0
    assert data['reserved'] == 0
    assert data['available'] == 100.0

def test_reserve_inventory_success():
    """Test successful reservation"""
    item = create_test_item(qc_required=False)
    
    # Receive inventory
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    # Reserve 50 units
    response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 50.0
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data['qty'] == 50.0
    assert data['status'] == "OPEN"
    
    # Check stock summary
    summary = client.get(f"/inventory/summary/{item['id']}").json()
    assert summary['on_hand'] == 100.0
    assert summary['reserved'] == 50.0
    assert summary['available'] == 50.0

def test_reserve_insufficient_stock():
    """Test reservation fails with insufficient stock"""
    item = create_test_item(qc_required=False)
    
    # Receive only 100 units
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    # Try to reserve 150 units
    response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 150.0
    })
    
    assert response.status_code == 400
    assert response.json()['detail']['error_code'] == "INSUFFICIENT_STOCK"

def test_reserve_no_qc_approved_lot():
    """Test reservation fails when no QC-approved lots available"""
    item = create_test_item(qc_required=True)
    
    # Receive inventory (will be in QUARANTINE)
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-QC-001",
        "qty": 100.0
    })
    
    # Try to reserve (should fail - no approved lots)
    response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 50.0
    })
    
    assert response.status_code == 400
    assert response.json()['detail']['error_code'] == "NO_QC_APPROVED_LOT"

def test_issue_inventory_success():
    """Test successful issue against reservation"""
    item = create_test_item(qc_required=False)
    
    # Receive inventory
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    # Reserve
    reserve_response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 30.0
    })
    reservation_id = reserve_response.json()['reservation_id']
    
    # Issue
    response = client.post("/inventory/issue", json={
        "reservation_id": reservation_id
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data['qty'] == 30.0
    assert len(data['lots_issued']) > 0
    
    # Check stock summary after issue
    summary = client.get(f"/inventory/summary/{item['id']}").json()
    assert summary['on_hand'] == 70.0  # 100 - 30 issued
    assert summary['reserved'] == 0    # Reservation closed
    assert summary['available'] == 70.0

def test_issue_nonexistent_reservation():
    """Test issue fails with non-existent reservation"""
    response = client.post("/inventory/issue", json={
        "reservation_id": "fake-reservation-id"
    })
    
    assert response.status_code == 404
    assert response.json()['detail']['error_code'] == "RESERVATION_NOT_FOUND"

def test_issue_twice_same_reservation():
    """Test cannot issue same reservation twice (idempotency)"""
    item = create_test_item(qc_required=False)
    
    # Receive and reserve
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    reserve_response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 30.0
    })
    reservation_id = reserve_response.json()['reservation_id']
    
    # Issue first time (should succeed)
    response1 = client.post("/inventory/issue", json={
        "reservation_id": reservation_id
    })
    assert response1.status_code == 200
    
    # Issue second time (should fail)
    response2 = client.post("/inventory/issue", json={
        "reservation_id": reservation_id
    })
    assert response2.status_code == 400
    assert response2.json()['detail']['error_code'] == "RESERVATION_ALREADY_ISSUED"

def test_no_negative_stock():
    """Test that stock never goes negative"""
    item = create_test_item(qc_required=False)
    
    # Receive 100 units
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    # Reserve and issue 100 units
    reserve_response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 100.0
    })
    
    client.post("/inventory/issue", json={
        "reservation_id": reserve_response.json()['reservation_id']
    })
    
    # Try to reserve more (should fail)
    response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 10.0
    })
    
    assert response.status_code == 400
    assert response.json()['detail']['error_code'] == "INSUFFICIENT_STOCK"

def test_multiple_lots_fifo_issuing():
    """Test issuing from multiple lots in FIFO order"""
    item = create_test_item(qc_required=False)
    
    # Receive multiple lots
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-A",
        "qty": 30.0
    })
    
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-B",
        "qty": 40.0
    })
    
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-C",
        "qty": 30.0
    })
    
    # Reserve 80 units (should span LOT-A, LOT-B, and part of LOT-C)
    reserve_response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 80.0
    })
    
    # Issue
    issue_response = client.post("/inventory/issue", json={
        "reservation_id": reserve_response.json()['reservation_id']
    })
    
    data = issue_response.json()
    assert data['qty'] == 80.0
    
    # Should issue from multiple lots
    lots_issued = data['lots_issued']
    assert len(lots_issued) >= 2
    
    # Total issued should be 80
    total_issued = sum(lot['qty'] for lot in lots_issued)
    assert total_issued == 80.0

def test_qc_workflow():
    """Test complete QC workflow"""
    item = create_test_item(qc_required=True)
    
    # Receive inventory (goes to QUARANTINE)
    receive_response = client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-QC-001",
        "qty": 100.0
    })
    lot_id = receive_response.json()['lot_id']
    assert receive_response.json()['qc_status'] == "QUARANTINE"
    
    # Cannot reserve yet
    reserve_response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 50.0
    })
    assert reserve_response.status_code == 400
    assert reserve_response.json()['detail']['error_code'] == "NO_QC_APPROVED_LOT"
    
    # Approve the lot
    client.patch(f"/inventory/lots/{lot_id}/qc-status", params={"qc_status": "APPROVED"})
    
    # Now can reserve
    reserve_response = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 50.0
    })
    assert reserve_response.status_code == 201
    
    # And issue
    issue_response = client.post("/inventory/issue", json={
        "reservation_id": reserve_response.json()['reservation_id']
    })
    assert issue_response.status_code == 200

def test_ledger_driven_state():
    """Test that all stock calculations are ledger-driven"""
    item = create_test_item(qc_required=False)
    
    # Check database directly - should not store onHand as column
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    # Check lots table columns
    cursor.execute("PRAGMA table_info(inventory_lots)")
    lot_columns = [row[1] for row in cursor.fetchall()]
    assert 'on_hand' not in lot_columns
    assert 'available' not in lot_columns
    
    # Perform operations
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    reserve_resp = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 30.0
    })
    
    client.post("/inventory/issue", json={
        "reservation_id": reserve_resp.json()['reservation_id']
    })
    
    # Verify all calculations come from ledger
    cursor.execute("SELECT COUNT(*) FROM inventory_ledger WHERE item_id = ?", (item['id'],))
    ledger_count = cursor.fetchone()[0]
    assert ledger_count > 0  # Should have RECEIVE, RESERVE, ISSUE, UNRESERVE entries
    
    # Verify stock summary matches ledger calculations
    summary = client.get(f"/inventory/summary/{item['id']}").json()
    
    # Manually calculate from ledger
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN txn_type = 'RECEIVE' THEN qty ELSE 0 END) as received,
            SUM(CASE WHEN txn_type = 'ISSUE' THEN qty ELSE 0 END) as issued
        FROM inventory_ledger
        WHERE item_id = ?
    """, (item['id'],))
    
    row = cursor.fetchone()
    expected_on_hand = row[0] - row[1]
    assert summary['on_hand'] == expected_on_hand
    
    conn.close()

def test_duplicate_lot_code():
    """Test that duplicate lot codes are rejected"""
    item = create_test_item()
    
    # Receive first lot
    response1 = client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-DUP-001",
        "qty": 100.0
    })
    assert response1.status_code == 201
    
    # Try to receive with same lot code
    response2 = client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-DUP-001",
        "qty": 50.0
    })
    assert response2.status_code == 400
    assert response2.json()['detail']['error_code'] == "DUPLICATE_LOT_CODE"

def test_complex_scenario():
    """Test complex multi-operation scenario"""
    item = create_test_item(qc_required=False)
    
    # Receive 3 lots
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-001",
        "qty": 100.0
    })
    
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-002",
        "qty": 150.0
    })
    
    client.post("/inventory/receive", json={
        "item_id": item['id'],
        "lot_code": "LOT-003",
        "qty": 75.0
    })
    
    # Make 2 reservations
    reserve1 = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 120.0
    })
    
    reserve2 = client.post("/inventory/reserve", json={
        "item_id": item['id'],
        "qty": 80.0
    })
    
    # Check summary
    summary1 = client.get(f"/inventory/summary/{item['id']}").json()
    assert summary1['on_hand'] == 325.0
    assert summary1['reserved'] == 200.0
    assert summary1['available'] == 125.0
    
    # Issue first reservation
    client.post("/inventory/issue", json={
        "reservation_id": reserve1.json()['reservation_id']
    })
    
    # Check summary after first issue
    summary2 = client.get(f"/inventory/summary/{item['id']}").json()
    assert summary2['on_hand'] == 205.0  # 325 - 120
    assert summary2['reserved'] == 80.0  # Only second reservation
    assert summary2['available'] == 125.0
    
    # Issue second reservation
    client.post("/inventory/issue", json={
        "reservation_id": reserve2.json()['reservation_id']
    })
    
    # Final summary
    summary3 = client.get(f"/inventory/summary/{item['id']}").json()
    assert summary3['on_hand'] == 125.0  # 325 - 120 - 80
    assert summary3['reserved'] == 0
    assert summary3['available'] == 125.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
