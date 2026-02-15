from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from contextlib import asynccontextmanager
import sqlite3
import uuid
import threading

# Thread-local storage for database connections
thread_local = threading.local()

# Database setup
def get_db():
    """Get thread-safe database connection"""
    if not hasattr(thread_local, "connection"):
        thread_local.connection = sqlite3.connect("inventory.db", check_same_thread=False)
        thread_local.connection.row_factory = sqlite3.Row
    return thread_local.connection

def init_db():
    """Initialize database schema"""
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    # Items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            qc_required INTEGER NOT NULL
        )
    """)
    
    # Inventory lots table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_lots (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            lot_code TEXT UNIQUE NOT NULL,
            received_qty REAL NOT NULL,
            qc_status TEXT NOT NULL CHECK(qc_status IN ('APPROVED', 'QUARANTINE', 'REJECTED')),
            FOREIGN KEY (item_id) REFERENCES items(id)
        )
    """)
    
    # Inventory ledger table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_ledger (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            lot_id TEXT,
            txn_type TEXT NOT NULL CHECK(txn_type IN ('RECEIVE', 'RESERVE', 'UNRESERVE', 'ISSUE')),
            qty REAL NOT NULL,
            timestamp TEXT NOT NULL,
            reservation_id TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id),
            FOREIGN KEY (lot_id) REFERENCES inventory_lots(id)
        )
    """)
    
    # Reservations tracking table for idempotency and state
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            qty REAL NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('OPEN', 'ISSUED', 'CANCELLED')),
            created_at TEXT NOT NULL,
            FOREIGN KEY (item_id) REFERENCES items(id)
        )
    """)
    
    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_item ON inventory_ledger(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_lot ON inventory_ledger(lot_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ledger_reservation ON inventory_ledger(reservation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reservations_item ON reservations(item_id, status)")
    
    conn.commit()
    conn.close()

# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Inventory Management System", lifespan=lifespan)

# Pydantic models
class ItemCreate(BaseModel):
    code: str
    name: str
    qc_required: bool = False

class ItemResponse(BaseModel):
    id: str
    code: str
    name: str
    qc_required: bool

class ReceiveInventoryRequest(BaseModel):
    item_id: str
    lot_code: str
    qty: float = Field(gt=0)

class ReceiveInventoryResponse(BaseModel):
    lot_id: str
    item_id: str
    lot_code: str
    received_qty: float
    qc_status: str

class StockSummary(BaseModel):
    on_hand: float
    reserved: float
    available: float

class ReserveInventoryRequest(BaseModel):
    item_id: str
    qty: float = Field(gt=0)

class ReserveInventoryResponse(BaseModel):
    reservation_id: str
    item_id: str
    qty: float
    status: str

class IssueInventoryRequest(BaseModel):
    reservation_id: str

class IssueInventoryResponse(BaseModel):
    reservation_id: str
    item_id: str
    qty: float
    lots_issued: List[dict]

# Error codes
class ErrorCode:
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    NO_QC_APPROVED_LOT = "NO_QC_APPROVED_LOT"
    RESERVATION_NOT_FOUND = "RESERVATION_NOT_FOUND"
    ITEM_NOT_FOUND = "ITEM_NOT_FOUND"
    DUPLICATE_LOT_CODE = "DUPLICATE_LOT_CODE"
    INVALID_QTY = "INVALID_QTY"
    RESERVATION_ALREADY_ISSUED = "RESERVATION_ALREADY_ISSUED"
    LOT_NOT_APPROVED = "LOT_NOT_APPROVED"

# Helper functions
def execute_with_lock(conn, query, params=()):
    """Execute query with database-level locking for concurrency safety"""
    cursor = conn.cursor()
    cursor.execute("BEGIN IMMEDIATE")
    try:
        result = cursor.execute(query, params)
        return result
    except Exception as e:
        conn.rollback()
        raise e

def get_item(conn, item_id: str):
    """Get item by ID"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error_code": ErrorCode.ITEM_NOT_FOUND, "message": f"Item {item_id} not found"}
        )
    return dict(row)

def calculate_stock(conn, item_id: str) -> StockSummary:
    """
    Calculate stock from ledger entries (ledger-driven state)
    
    onHand = RECEIVE entries - ISSUE entries
    reserved = sum of OPEN reservations
    available = onHand - reserved
    """
    cursor = conn.cursor()
    
    # Calculate on_hand from ledger
    cursor.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN txn_type = 'RECEIVE' THEN qty ELSE 0 END), 0) as received,
            COALESCE(SUM(CASE WHEN txn_type = 'ISSUE' THEN qty ELSE 0 END), 0) as issued
        FROM inventory_ledger
        WHERE item_id = ?
    """, (item_id,))
    
    row = cursor.fetchone()
    received = row['received']
    issued = row['issued']
    on_hand = received - issued
    
    # Calculate reserved from open reservations
    cursor.execute("""
        SELECT COALESCE(SUM(qty), 0) as reserved
        FROM reservations
        WHERE item_id = ? AND status = 'OPEN'
    """, (item_id,))
    
    reserved = cursor.fetchone()['reserved']
    available = on_hand - reserved
    
    return StockSummary(
        on_hand=on_hand,
        reserved=reserved,
        available=available
    )

def get_available_lots(conn, item_id: str, required_qty: float) -> List[dict]:
    """
    Get QC-approved lots with available stock for issuing
    
    For each lot, calculates:
    - received quantity
    - already issued quantity
    - available = received - issued
    """
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            l.id,
            l.lot_code,
            l.received_qty,
            l.qc_status,
            COALESCE(SUM(CASE WHEN led.txn_type = 'ISSUE' THEN led.qty ELSE 0 END), 0) as issued_qty
        FROM inventory_lots l
        LEFT JOIN inventory_ledger led ON l.id = led.lot_id
        WHERE l.item_id = ? AND l.qc_status = 'APPROVED'
        GROUP BY l.id, l.lot_code, l.received_qty, l.qc_status
        HAVING (l.received_qty - COALESCE(SUM(CASE WHEN led.txn_type = 'ISSUE' THEN led.qty ELSE 0 END), 0)) > 0
        ORDER BY l.lot_code ASC
    """, (item_id,))
    
    lots = []
    for row in cursor.fetchall():
        lot_dict = dict(row)
        lot_dict['available'] = lot_dict['received_qty'] - lot_dict['issued_qty']
        lots.append(lot_dict)
    
    return lots

# API Endpoints

@app.post("/items", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate):
    """Create a new item (helper endpoint for testing)"""
    conn = get_db()
    cursor = conn.cursor()
    
    item_id = str(uuid.uuid4())
    
    try:
        cursor.execute("""
            INSERT INTO items (id, code, name, qc_required)
            VALUES (?, ?, ?, ?)
        """, (item_id, item.code, item.name, int(item.qc_required)))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "DUPLICATE_ITEM_CODE", "message": f"Item code {item.code} already exists"}
        )
    
    return ItemResponse(
        id=item_id,
        code=item.code,
        name=item.name,
        qc_required=item.qc_required
    )

@app.get("/items/{item_id}", response_model=ItemResponse)
def get_item_endpoint(item_id: str):
    """Get item details"""
    conn = get_db()
    item = get_item(conn, item_id)
    return ItemResponse(
        id=item['id'],
        code=item['code'],
        name=item['name'],
        qc_required=bool(item['qc_required'])
    )

@app.post("/inventory/receive", response_model=ReceiveInventoryResponse, status_code=201)
def receive_inventory(request: ReceiveInventoryRequest):
    """
    Receive inventory into a new lot
    
    Rules:
    1. Creates a new lot
    2. Adds a RECEIVE ledger entry
    3. If qcRequired = true, lot starts in QUARANTINE
    4. Otherwise, lot is APPROVED
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Validate item exists
    item = get_item(conn, request.item_id)
    
    # Determine QC status
    qc_status = "QUARANTINE" if item['qc_required'] else "APPROVED"
    
    lot_id = str(uuid.uuid4())
    ledger_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        # Create lot
        cursor.execute("""
            INSERT INTO inventory_lots (id, item_id, lot_code, received_qty, qc_status)
            VALUES (?, ?, ?, ?, ?)
        """, (lot_id, request.item_id, request.lot_code, request.qty, qc_status))
        
        # Create RECEIVE ledger entry
        cursor.execute("""
            INSERT INTO inventory_ledger (id, item_id, lot_id, txn_type, qty, timestamp)
            VALUES (?, ?, ?, 'RECEIVE', ?, ?)
        """, (ledger_id, request.item_id, lot_id, request.qty, timestamp))
        
        conn.commit()
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "lot_code" in str(e):
            raise HTTPException(
                status_code=400,
                detail={"error_code": ErrorCode.DUPLICATE_LOT_CODE, "message": f"Lot code {request.lot_code} already exists"}
            )
        raise HTTPException(status_code=400, detail={"error_code": "DATABASE_ERROR", "message": str(e)})
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": str(e)})
    
    return ReceiveInventoryResponse(
        lot_id=lot_id,
        item_id=request.item_id,
        lot_code=request.lot_code,
        received_qty=request.qty,
        qc_status=qc_status
    )

@app.get("/inventory/summary/{item_id}", response_model=StockSummary)
def get_stock_summary(item_id: str):
    """
    Get stock summary for an item
    
    Returns:
    - onHand: received - issued (from ledger)
    - reserved: sum of open reservations
    - available: onHand - reserved
    """
    conn = get_db()
    
    # Validate item exists
    get_item(conn, item_id)
    
    # Calculate stock from ledger
    summary = calculate_stock(conn, item_id)
    
    return summary

@app.post("/inventory/reserve", response_model=ReserveInventoryResponse, status_code=201)
def reserve_inventory(request: ReserveInventoryRequest):
    """
    Reserve inventory for future issue
    
    Rules:
    1. Creates a reservation record
    2. Adds RESERVE ledger entry
    3. Checks available stock (onHand - reserved)
    4. Must have QC-approved lots
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        # Validate item exists
        get_item(conn, request.item_id)
        
        # Calculate current stock
        summary = calculate_stock(conn, request.item_id)
        
        # Check if enough available stock
        if summary.available < request.qty:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": ErrorCode.INSUFFICIENT_STOCK,
                    "message": f"Insufficient stock. Available: {summary.available}, Requested: {request.qty}"
                }
            )
        
        # Check if there are any QC-approved lots with stock
        lots = get_available_lots(conn, request.item_id, request.qty)
        if not lots:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": ErrorCode.NO_QC_APPROVED_LOT,
                    "message": "No QC-approved lots available for this item"
                }
            )
        
        # Create reservation
        reservation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO reservations (id, item_id, qty, status, created_at)
            VALUES (?, ?, ?, 'OPEN', ?)
        """, (reservation_id, request.item_id, request.qty, timestamp))
        
        # Create RESERVE ledger entry
        ledger_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO inventory_ledger (id, item_id, lot_id, txn_type, qty, timestamp, reservation_id)
            VALUES (?, ?, NULL, 'RESERVE', ?, ?, ?)
        """, (ledger_id, request.item_id, request.qty, timestamp, reservation_id))
        
        conn.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": str(e)})
    
    return ReserveInventoryResponse(
        reservation_id=reservation_id,
        item_id=request.item_id,
        qty=request.qty,
        status="OPEN"
    )

@app.post("/inventory/issue", response_model=IssueInventoryResponse)
def issue_inventory(request: IssueInventoryRequest):
    """
    Issue (dispense) inventory against a reservation
    
    Rules:
    1. Can only issue previously reserved stock
    2. Must have reservation in OPEN status
    3. Reduces onHand by adding ISSUE ledger entries
    4. Automatically closes reservation
    5. Only issues from QC-approved lots
    6. Uses FIFO (first lot first)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        # Get reservation
        cursor.execute("""
            SELECT * FROM reservations WHERE id = ?
        """, (request.reservation_id,))
        
        reservation_row = cursor.fetchone()
        if not reservation_row:
            conn.rollback()
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": ErrorCode.RESERVATION_NOT_FOUND,
                    "message": f"Reservation {request.reservation_id} not found"
                }
            )
        
        reservation = dict(reservation_row)
        
        if reservation['status'] != 'OPEN':
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": ErrorCode.RESERVATION_ALREADY_ISSUED,
                    "message": f"Reservation {request.reservation_id} is already {reservation['status']}"
                }
            )
        
        item_id = reservation['item_id']
        qty_to_issue = reservation['qty']
        
        # Get available lots (QC-approved with stock)
        lots = get_available_lots(conn, item_id, qty_to_issue)
        
        if not lots:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": ErrorCode.NO_QC_APPROVED_LOT,
                    "message": "No QC-approved lots available to issue"
                }
            )
        
        # Check if enough stock in approved lots
        total_available = sum(lot['available'] for lot in lots)
        if total_available < qty_to_issue:
            conn.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": ErrorCode.INSUFFICIENT_STOCK,
                    "message": f"Insufficient stock in approved lots. Available: {total_available}, Required: {qty_to_issue}"
                }
            )
        
        # Issue from lots (FIFO)
        remaining_qty = qty_to_issue
        lots_issued = []
        timestamp = datetime.utcnow().isoformat()
        
        for lot in lots:
            if remaining_qty <= 0:
                break
            
            qty_from_lot = min(lot['available'], remaining_qty)
            
            # Create ISSUE ledger entry
            ledger_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO inventory_ledger (id, item_id, lot_id, txn_type, qty, timestamp, reservation_id)
                VALUES (?, ?, ?, 'ISSUE', ?, ?, ?)
            """, (ledger_id, item_id, lot['id'], qty_from_lot, timestamp, request.reservation_id))
            
            lots_issued.append({
                "lot_id": lot['id'],
                "lot_code": lot['lot_code'],
                "qty": qty_from_lot
            })
            
            remaining_qty -= qty_from_lot
        
        # Update reservation status to ISSUED
        cursor.execute("""
            UPDATE reservations SET status = 'ISSUED' WHERE id = ?
        """, (request.reservation_id,))
        
        # Add UNRESERVE ledger entry to release the reservation
        ledger_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO inventory_ledger (id, item_id, lot_id, txn_type, qty, timestamp, reservation_id)
            VALUES (?, ?, NULL, 'UNRESERVE', ?, ?, ?)
        """, (ledger_id, item_id, qty_to_issue, timestamp, request.reservation_id))
        
        conn.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": str(e)})
    
    return IssueInventoryResponse(
        reservation_id=request.reservation_id,
        item_id=item_id,
        qty=qty_to_issue,
        lots_issued=lots_issued
    )

@app.patch("/inventory/lots/{lot_id}/qc-status")
def update_lot_qc_status(lot_id: str, qc_status: Literal["APPROVED", "REJECTED"]):
    """
    Update QC status of a lot (helper endpoint for testing)
    
    Can move QUARANTINE lots to APPROVED or REJECTED
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        cursor.execute("SELECT * FROM inventory_lots WHERE id = ?", (lot_id,))
        lot = cursor.fetchone()
        
        if not lot:
            raise HTTPException(status_code=404, detail={"error_code": "LOT_NOT_FOUND", "message": "Lot not found"})
        
        cursor.execute("""
            UPDATE inventory_lots SET qc_status = ? WHERE id = ?
        """, (qc_status, lot_id))
        
        conn.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": str(e)})
    
    return {"lot_id": lot_id, "qc_status": qc_status}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
