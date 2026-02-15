"""
Integration Test - Tests the RUNNING server via HTTP
Run this while app.py is running on http://localhost:8000
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("=" * 70)
    print("TESTING LIVE SERVER AT", BASE_URL)
    print("=" * 70)
    
    try:
        # Test 1: Health Check
        print("\n[TEST 1] Health Check")
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200
        print("✅ PASS: Server is healthy")
        
        # Test 2: Create Item (No QC)
        print("\n[TEST 2] Create Item (No QC Required)")
        resp = requests.post(f"{BASE_URL}/items", json={
            "code": f"TEST-ITEM-001",
            "name": "Test Item",
            "qc_required": False
        })
        assert resp.status_code == 201
        item_id = resp.json()['id']
        print(f"✅ PASS: Created item {item_id}")
        
        # Test 3: Receive Inventory
        print("\n[TEST 3] Receive Inventory")
        resp = requests.post(f"{BASE_URL}/inventory/receive", json={
            "item_id": item_id,
            "lot_code": f"LOT-TEST-001",
            "qty": 100.0
        })
        assert resp.status_code == 201
        assert resp.json()['qc_status'] == 'APPROVED'
        print("✅ PASS: Received 100 units")
        
        # Test 4: Check Stock Summary
        print("\n[TEST 4] Check Stock Summary")
        resp = requests.get(f"{BASE_URL}/inventory/summary/{item_id}")
        assert resp.status_code == 200
        summary = resp.json()
        assert summary['on_hand'] == 100.0
        assert summary['reserved'] == 0
        assert summary['available'] == 100.0
        print(f"✅ PASS: Stock = {summary}")
        
        # Test 5: Reserve Inventory
        print("\n[TEST 5] Reserve Inventory")
        resp = requests.post(f"{BASE_URL}/inventory/reserve", json={
            "item_id": item_id,
            "qty": 30.0
        })
        assert resp.status_code == 201
        reservation_id = resp.json()['reservation_id']
        print(f"✅ PASS: Reserved 30 units (reservation: {reservation_id})")
        
        # Test 6: Check Stock After Reserve
        print("\n[TEST 6] Check Stock After Reserve")
        resp = requests.get(f"{BASE_URL}/inventory/summary/{item_id}")
        summary = resp.json()
        assert summary['on_hand'] == 100.0
        assert summary['reserved'] == 30.0
        assert summary['available'] == 70.0
        print(f"✅ PASS: Available reduced to {summary['available']}")
        
        # Test 7: Issue Inventory
        print("\n[TEST 7] Issue Inventory")
        resp = requests.post(f"{BASE_URL}/inventory/issue", json={
            "reservation_id": reservation_id
        })
        assert resp.status_code == 200
        assert resp.json()['qty'] == 30.0
        print("✅ PASS: Issued 30 units")
        
        # Test 8: Check Stock After Issue
        print("\n[TEST 8] Check Stock After Issue")
        resp = requests.get(f"{BASE_URL}/inventory/summary/{item_id}")
        summary = resp.json()
        assert summary['on_hand'] == 70.0
        assert summary['reserved'] == 0
        assert summary['available'] == 70.0
        print(f"✅ PASS: Final stock = {summary}")
        
        # Test 9: Test Insufficient Stock Error
        print("\n[TEST 9] Test Insufficient Stock Error")
        resp = requests.post(f"{BASE_URL}/inventory/reserve", json={
            "item_id": item_id,
            "qty": 1000.0
        })
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'INSUFFICIENT_STOCK'
        print("✅ PASS: Correctly rejected insufficient stock")
        
        # Test 10: Test Idempotency (Double Issue)
        print("\n[TEST 10] Test Idempotency (Cannot Issue Twice)")
        resp = requests.post(f"{BASE_URL}/inventory/issue", json={
            "reservation_id": reservation_id
        })
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'RESERVATION_ALREADY_ISSUED'
        print("✅ PASS: Correctly prevented double-issuing")
        
        # Test 11: QC Workflow
        print("\n[TEST 11] QC Workflow")
        resp = requests.post(f"{BASE_URL}/items", json={
            "code": "QC-ITEM-001",
            "name": "QC Required Item",
            "qc_required": True
        })
        qc_item_id = resp.json()['id']
        
        resp = requests.post(f"{BASE_URL}/inventory/receive", json={
            "item_id": qc_item_id,
            "lot_code": "LOT-QC-001",
            "qty": 50.0
        })
        assert resp.json()['qc_status'] == 'QUARANTINE'
        lot_id = resp.json()['lot_id']
        print("✅ PASS: Item in QUARANTINE")
        
        # Try to reserve (should fail)
        resp = requests.post(f"{BASE_URL}/inventory/reserve", json={
            "item_id": qc_item_id,
            "qty": 10.0
        })
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'NO_QC_APPROVED_LOT'
        print("✅ PASS: Cannot reserve from QUARANTINE")
        
        # Approve lot
        resp = requests.patch(f"{BASE_URL}/inventory/lots/{lot_id}/qc-status?qc_status=APPROVED")
        assert resp.status_code == 200
        print("✅ PASS: Lot approved")
        
        # Now reservation works
        resp = requests.post(f"{BASE_URL}/inventory/reserve", json={
            "item_id": qc_item_id,
            "qty": 10.0
        })
        assert resp.status_code == 201
        print("✅ PASS: Can reserve after approval")
        
        # Test 12: Multi-Lot FIFO
        print("\n[TEST 12] Multi-Lot FIFO Issuing")
        resp = requests.post(f"{BASE_URL}/items", json={
            "code": "MULTI-LOT-001",
            "name": "Multi Lot Item",
            "qc_required": False
        })
        multi_item_id = resp.json()['id']
        
        # Receive 3 lots
        requests.post(f"{BASE_URL}/inventory/receive", json={
            "item_id": multi_item_id,
            "lot_code": "LOT-A",
            "qty": 30.0
        })
        requests.post(f"{BASE_URL}/inventory/receive", json={
            "item_id": multi_item_id,
            "lot_code": "LOT-B",
            "qty": 40.0
        })
        requests.post(f"{BASE_URL}/inventory/receive", json={
            "item_id": multi_item_id,
            "lot_code": "LOT-C",
            "qty": 30.0
        })
        
        # Reserve 80 units (spans multiple lots)
        resp = requests.post(f"{BASE_URL}/inventory/reserve", json={
            "item_id": multi_item_id,
            "qty": 80.0
        })
        res_id = resp.json()['reservation_id']
        
        # Issue
        resp = requests.post(f"{BASE_URL}/inventory/issue", json={
            "reservation_id": res_id
        })
        lots_issued = resp.json()['lots_issued']
        assert len(lots_issued) >= 2  # Should span multiple lots
        assert lots_issued[0]['lot_code'] == 'LOT-A'  # FIFO order
        total = sum(lot['qty'] for lot in lots_issued)
        assert total == 80.0
        print(f"✅ PASS: Issued from {len(lots_issued)} lots in FIFO order")
        
        print("\n" + "=" * 70)
        print("ALL INTEGRATION TESTS PASSED! ✅")
        print("=" * 70)
        print("\nKey Features Verified:")
        print("  ✓ Basic CRUD operations")
        print("  ✓ Stock calculations (ledger-driven)")
        print("  ✓ Reservations and issues")
        print("  ✓ Error handling (insufficient stock)")
        print("  ✓ Idempotency (no double-issuing)")
        print("  ✓ QC workflow (QUARANTINE → APPROVED)")
        print("  ✓ Multi-lot FIFO issuing")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server")
        print("Make sure the server is running: python app.py")
        return False
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api()
    exit(0 if success else 1)
