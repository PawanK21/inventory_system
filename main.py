from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uvicorn
from uuid import uuid4

# ==================== ENUMS ====================

class QCStatus(str, Enum):
    APPROVED = "APPROVED"
    QUARANTINE = "QUARANTINE"
    REJECTED = "REJECTED"

class TxnType(str, Enum):
    RECEIVE = "RECEIVE"
    RESERVE = "RESERVE"
    UNRESERVE = "UNRESERVE"
    ISSUE = "ISSUE"

class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PARTIAL = "PARTIAL"
    COMPLETED = "COMPLETED"

# ==================== MODELS ====================

class Item(BaseModel):
    id: str
    code: str
    name: str
    qcRequired: bool

class InventoryLot(BaseModel):
    id: str
    itemId: str
    lotCode: str
    receivedQty: int
    qcStatus: QCStatus
    receivedDate: datetime

class InventoryLedger(BaseModel):
    id: str
    itemId: str
    lotId: str
    txnType: TxnType
    qty: int
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class Reservation(BaseModel):
    id: str
    itemId: str
    allocations: List[Dict[str, Any]]
    totalQty: int
    issuedQty: int
    timestamp: datetime
    batchId: str
    status: ReservationStatus

# ==================== REQUEST/RESPONSE MODELS ====================

class ReceiveInventoryRequest(BaseModel):
    itemId: str
    lotCode: str
    qty: int = Field(gt=0)
    qcRequired: bool = False

class ReceiveInventoryResponse(BaseModel):
    lot: InventoryLot
    ledgerEntry: InventoryLedger
    message: str

class StockSummary(BaseModel):
    itemId: str
    onHand: int
    reserved: int
    available: int
    received: int
    issued: int

class ReserveInventoryRequest(BaseModel):
    itemId: str
    qty: int = Field(gt=0)
    batchId: str

class ReserveInventoryResponse(BaseModel):
    reservation: Reservation
    message: str

class IssueInventoryRequest(BaseModel):
    reservationId: str
    qty: int = Field(gt=0)

class IssueInventoryResponse(BaseModel):
    reservation: Reservation
    issues: List[InventoryLedger]
    message: str

class AddItemRequest(BaseModel):
    code: str
    name: str
    qcRequired: bool = False

class UpdateQCStatusRequest(BaseModel):
    lotId: str
    status: QCStatus

class LotSummary(BaseModel):
    lotId: str
    received: int
    reserved: int
    issued: int
    onHand: int
    available: int

# ==================== DATABASE (In-Memory) ====================

class Database:
    def __init__(self):
        self.items: List[Item] = []
        self.lots: List[InventoryLot] = []
        self.ledger: List[InventoryLedger] = []
        self.reservations: List[Reservation] = []
        self._initialize_sample_data()

    def _initialize_sample_data(self):
        # Create sample items
        self.items = [
            Item(id='1', code='RM-001', name='Steel Sheet A4', qcRequired=True),
            Item(id='2', code='RM-002', name='Aluminum Rod 20mm', qcRequired=True),
            Item(id='3', code='RM-003', name='Copper Wire 2.5mm', qcRequired=False),
            Item(id='4', code='CH-001', name='Industrial Adhesive', qcRequired=True),
            Item(id='5', code='PK-001', name='Cardboard Box Large', qcRequired=False),
        ]

        # Create sample lots
        sample_lots = [
            {
                'id': 'LOT-001',
                'itemId': '1',
                'lotCode': 'SS-2024-001',
                'receivedQty': 1000,
                'qcStatus': QCStatus.APPROVED,
                'receivedDate': datetime(2024, 2, 10)
            },
            {
                'id': 'LOT-002',
                'itemId': '2',
                'lotCode': 'AL-2024-001',
                'receivedQty': 500,
                'qcStatus': QCStatus.APPROVED,
                'receivedDate': datetime(2024, 2, 12)
            },
            {
                'id': 'LOT-003',
                'itemId': '3',
                'lotCode': 'CW-2024-001',
                'receivedQty': 2000,
                'qcStatus': QCStatus.APPROVED,
                'receivedDate': datetime(2024, 2, 13)
            },
            {
                'id': 'LOT-004',
                'itemId': '1',
                'lotCode': 'SS-2024-002',
                'receivedQty': 800,
                'qcStatus': QCStatus.QUARANTINE,
                'receivedDate': datetime(2024, 2, 15)
            },
        ]

        for lot_data in sample_lots:
            lot = InventoryLot(**lot_data)
            self.lots.append(lot)
            
            # Create RECEIVE ledger entry
            ledger_entry = InventoryLedger(
                id=f'LED-{len(self.ledger) + 1}',
                itemId=lot.itemId,
                lotId=lot.id,
                txnType=TxnType.RECEIVE,
                qty=lot.receivedQty,
                timestamp=lot.receivedDate,
                metadata={'lotCode': lot.lotCode}
            )
            self.ledger.append(ledger_entry)

        # Add sample transactions
        reserve_entry = InventoryLedger(
            id='LED-5',
            itemId='1',
            lotId='LOT-001',
            txnType=TxnType.RESERVE,
            qty=200,
            timestamp=datetime(2024, 2, 14),
            metadata={'reservationId': 'RES-001', 'batchId': 'BATCH-001'}
        )
        self.ledger.append(reserve_entry)

        issue_entry = InventoryLedger(
            id='LED-6',
            itemId='1',
            lotId='LOT-001',
            txnType=TxnType.ISSUE,
            qty=150,
            timestamp=datetime(2024, 2, 15),
            metadata={'reservationId': 'RES-001', 'batchId': 'BATCH-001'}
        )
        self.ledger.append(issue_entry)

        reservation = Reservation(
            id='RES-001',
            itemId='1',
            allocations=[{'lotId': 'LOT-001', 'qty': 200}],
            totalQty=200,
            issuedQty=150,
            timestamp=datetime(2024, 2, 14),
            batchId='BATCH-001',
            status=ReservationStatus.PARTIAL
        )
        self.reservations.append(reservation)

    def get_item(self, item_id: str) -> Optional[Item]:
        return next((item for item in self.items if item.id == item_id), None)

    def get_lot(self, lot_id: str) -> Optional[InventoryLot]:
        return next((lot for lot in self.lots if lot.id == lot_id), None)

    def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        return next((res for res in self.reservations if res.id == reservation_id), None)

# ==================== INVENTORY SERVICE ====================

class InventoryService:
    def __init__(self, db: Database):
        self.db = db

    def receive_inventory(self, request: ReceiveInventoryRequest) -> ReceiveInventoryResponse:
        # Validate item exists
        item = self.db.get_item(request.itemId)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ITEM_NOT_FOUND"
            )

        # Create new lot
        lot_id = f"LOT-{uuid4().hex[:8].upper()}"
        lot = InventoryLot(
            id=lot_id,
            itemId=request.itemId,
            lotCode=request.lotCode,
            receivedQty=request.qty,
            qcStatus=QCStatus.QUARANTINE if request.qcRequired else QCStatus.APPROVED,
            receivedDate=datetime.now()
        )
        self.db.lots.append(lot)

        # Create ledger entry
        ledger_entry = InventoryLedger(
            id=f"LED-{len(self.db.ledger) + 1}",
            itemId=request.itemId,
            lotId=lot_id,
            txnType=TxnType.RECEIVE,
            qty=request.qty,
            timestamp=datetime.now(),
            metadata={'lotCode': request.lotCode}
        )
        self.db.ledger.append(ledger_entry)

        return ReceiveInventoryResponse(
            lot=lot,
            ledgerEntry=ledger_entry,
            message=f"Successfully received {request.qty} units of lot {request.lotCode}"
        )

    def get_stock_summary(self, item_id: str) -> StockSummary:
        # Validate item exists
        item = self.db.get_item(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ITEM_NOT_FOUND"
            )

        # Calculate from ledger
        item_ledger = [entry for entry in self.db.ledger if entry.itemId == item_id]
        
        received = sum(e.qty for e in item_ledger if e.txnType == TxnType.RECEIVE)
        issued = sum(e.qty for e in item_ledger if e.txnType == TxnType.ISSUE)
        reserved = sum(e.qty for e in item_ledger if e.txnType == TxnType.RESERVE)
        unreserved = sum(e.qty for e in item_ledger if e.txnType == TxnType.UNRESERVE)
        
        reserved_net = reserved - unreserved
        on_hand = received - issued
        available = on_hand - reserved_net

        return StockSummary(
            itemId=item_id,
            onHand=on_hand,
            reserved=reserved_net,
            available=available,
            received=received,
            issued=issued
        )

    def get_lot_summary(self, lot_id: str) -> LotSummary:
        # Validate lot exists
        lot = self.db.get_lot(lot_id)
        if not lot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LOT_NOT_FOUND"
            )

        # Calculate from ledger
        lot_ledger = [entry for entry in self.db.ledger if entry.lotId == lot_id]
        
        received = sum(e.qty for e in lot_ledger if e.txnType == TxnType.RECEIVE)
        reserved = sum(e.qty for e in lot_ledger if e.txnType == TxnType.RESERVE)
        unreserved = sum(e.qty for e in lot_ledger if e.txnType == TxnType.UNRESERVE)
        issued = sum(e.qty for e in lot_ledger if e.txnType == TxnType.ISSUE)
        
        reserved_net = reserved - unreserved
        on_hand = received - issued
        available = on_hand - reserved_net

        return LotSummary(
            lotId=lot_id,
            received=received,
            reserved=reserved_net,
            issued=issued,
            onHand=on_hand,
            available=available
        )

    def reserve_inventory(self, request: ReserveInventoryRequest) -> ReserveInventoryResponse:
        # Validate item exists
        item = self.db.get_item(request.itemId)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="ITEM_NOT_FOUND"
            )

        # Check available stock
        summary = self.get_stock_summary(request.itemId)
        if summary.available < request.qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INSUFFICIENT_STOCK"
            )

        # Find approved lots
        approved_lots = [
            lot for lot in self.db.lots
            if lot.itemId == request.itemId and lot.qcStatus == QCStatus.APPROVED
        ]

        if not approved_lots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NO_QC_APPROVED_LOT"
            )

        # FIFO allocation
        remaining_qty = request.qty
        allocations = []

        for lot in sorted(approved_lots, key=lambda x: x.receivedDate):
            lot_summary = self.get_lot_summary(lot.id)
            available_in_lot = lot_summary.available

            if available_in_lot > 0 and remaining_qty > 0:
                alloc_qty = min(available_in_lot, remaining_qty)
                allocations.append({'lotId': lot.id, 'qty': alloc_qty})
                remaining_qty -= alloc_qty

            if remaining_qty == 0:
                break

        if remaining_qty > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INSUFFICIENT_APPROVED_STOCK"
            )

        # Create reservation
        reservation_id = f"RES-{uuid4().hex[:8].upper()}"

        for alloc in allocations:
            ledger_entry = InventoryLedger(
                id=f"LED-{len(self.db.ledger) + 1}",
                itemId=request.itemId,
                lotId=alloc['lotId'],
                txnType=TxnType.RESERVE,
                qty=alloc['qty'],
                timestamp=datetime.now(),
                metadata={'reservationId': reservation_id, 'batchId': request.batchId}
            )
            self.db.ledger.append(ledger_entry)

        reservation = Reservation(
            id=reservation_id,
            itemId=request.itemId,
            allocations=allocations,
            totalQty=request.qty,
            issuedQty=0,
            timestamp=datetime.now(),
            batchId=request.batchId,
            status=ReservationStatus.ACTIVE
        )
        self.db.reservations.append(reservation)

        return ReserveInventoryResponse(
            reservation=reservation,
            message=f"Successfully reserved {request.qty} units for batch {request.batchId}"
        )

    def issue_inventory(self, request: IssueInventoryRequest) -> IssueInventoryResponse:
        # Get reservation
        reservation = self.db.get_reservation(request.reservationId)
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RESERVATION_NOT_FOUND"
            )

        # Check if enough reserved
        remaining_reserved = reservation.totalQty - reservation.issuedQty
        if request.qty > remaining_reserved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INSUFFICIENT_RESERVED_STOCK"
            )

        # Get reservation ledger entries
        reserve_ledger = [
            entry for entry in self.db.ledger
            if entry.metadata 
            and entry.metadata.get('reservationId') == request.reservationId
            and entry.txnType == TxnType.RESERVE
        ]

        remaining_qty = request.qty
        issues = []

        for reserve in reserve_ledger:
            if remaining_qty == 0:
                break

            # Check lot QC status
            lot = self.db.get_lot(reserve.lotId)
            if lot.qcStatus != QCStatus.APPROVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="NO_QC_APPROVED_LOT"
                )

            # Calculate how much from this lot can be issued
            lot_issues = [
                entry for entry in self.db.ledger
                if entry.lotId == reserve.lotId
                and entry.txnType == TxnType.ISSUE
                and entry.metadata
                and entry.metadata.get('reservationId') == request.reservationId
            ]
            already_issued = sum(e.qty for e in lot_issues)
            available_to_issue = reserve.qty - already_issued

            if available_to_issue > 0:
                issue_qty = min(available_to_issue, remaining_qty)
                
                ledger_entry = InventoryLedger(
                    id=f"LED-{len(self.db.ledger) + 1}",
                    itemId=reserve.itemId,
                    lotId=reserve.lotId,
                    txnType=TxnType.ISSUE,
                    qty=issue_qty,
                    timestamp=datetime.now(),
                    metadata={'reservationId': request.reservationId, 'batchId': reservation.batchId}
                )
                self.db.ledger.append(ledger_entry)
                issues.append(ledger_entry)
                remaining_qty -= issue_qty

        # Update reservation
        reservation.issuedQty += request.qty
        if reservation.issuedQty >= reservation.totalQty:
            reservation.status = ReservationStatus.COMPLETED
        else:
            reservation.status = ReservationStatus.PARTIAL

        return IssueInventoryResponse(
            reservation=reservation,
            issues=issues,
            message=f"Successfully issued {request.qty} units from reservation {request.reservationId}"
        )

    def add_item(self, request: AddItemRequest) -> Item:
        # Check if code already exists
        existing = next((item for item in self.db.items if item.code == request.code), None)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ITEM_CODE_ALREADY_EXISTS"
            )

        item = Item(
            id=str(uuid4()),
            code=request.code,
            name=request.name,
            qcRequired=request.qcRequired
        )
        self.db.items.append(item)
        return item

    def update_qc_status(self, request: UpdateQCStatusRequest) -> InventoryLot:
        lot = self.db.get_lot(request.lotId)
        if not lot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LOT_NOT_FOUND"
            )
        
        lot.qcStatus = request.status
        return lot

# ==================== FASTAPI APP ====================

app = FastAPI(
    title="Inventory Management System",
    description="Manufacturing inventory management with lot tracking, reservations, and QC",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and service
db = Database()
inventory_service = InventoryService(db)

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """Serve the frontend HTML"""
    return FileResponse("static/index.html")

@app.post("/api/inventory/receive", response_model=ReceiveInventoryResponse)
async def receive_inventory(request: ReceiveInventoryRequest):
    """Receive inventory and create a new lot"""
    return inventory_service.receive_inventory(request)

@app.get("/api/inventory/summary/{item_id}", response_model=StockSummary)
async def get_stock_summary(item_id: str):
    """Get stock summary for an item"""
    return inventory_service.get_stock_summary(item_id)

@app.get("/api/inventory/lot/{lot_id}", response_model=LotSummary)
async def get_lot_summary(lot_id: str):
    """Get summary for a specific lot"""
    return inventory_service.get_lot_summary(lot_id)

@app.post("/api/inventory/reserve", response_model=ReserveInventoryResponse)
async def reserve_inventory(request: ReserveInventoryRequest):
    """Reserve inventory for a batch"""
    return inventory_service.reserve_inventory(request)

@app.post("/api/inventory/issue", response_model=IssueInventoryResponse)
async def issue_inventory(request: IssueInventoryRequest):
    """Issue inventory from a reservation"""
    return inventory_service.issue_inventory(request)

@app.get("/api/items", response_model=List[Item])
async def get_all_items():
    """Get all items"""
    return db.items

@app.get("/api/items/{item_id}", response_model=Item)
async def get_item(item_id: str):
    """Get a specific item"""
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="ITEM_NOT_FOUND")
    return item

@app.post("/api/items", response_model=Item)
async def add_item(request: AddItemRequest):
    """Add a new item"""
    return inventory_service.add_item(request)

@app.get("/api/lots", response_model=List[InventoryLot])
async def get_all_lots():
    """Get all lots"""
    return db.lots

@app.get("/api/lots/{lot_id}", response_model=InventoryLot)
async def get_lot(lot_id: str):
    """Get a specific lot"""
    lot = db.get_lot(lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="LOT_NOT_FOUND")
    return lot

@app.put("/api/lots/qc-status", response_model=InventoryLot)
async def update_qc_status(request: UpdateQCStatusRequest):
    """Update QC status of a lot"""
    return inventory_service.update_qc_status(request)

@app.get("/api/ledger", response_model=List[InventoryLedger])
async def get_all_ledger():
    """Get all ledger entries"""
    return sorted(db.ledger, key=lambda x: x.timestamp, reverse=True)

@app.get("/api/ledger/item/{item_id}", response_model=List[InventoryLedger])
async def get_item_ledger(item_id: str):
    """Get ledger entries for a specific item"""
    return [entry for entry in db.ledger if entry.itemId == item_id]

@app.get("/api/ledger/lot/{lot_id}", response_model=List[InventoryLedger])
async def get_lot_ledger(lot_id: str):
    """Get ledger entries for a specific lot"""
    return [entry for entry in db.ledger if entry.lotId == lot_id]

@app.get("/api/reservations", response_model=List[Reservation])
async def get_all_reservations():
    """Get all reservations"""
    return sorted(db.reservations, key=lambda x: x.timestamp, reverse=True)

@app.get("/api/reservations/{reservation_id}", response_model=Reservation)
async def get_reservation(reservation_id: str):
    """Get a specific reservation"""
    reservation = db.get_reservation(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="RESERVATION_NOT_FOUND")
    return reservation

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    total_items = len(db.items)
    total_lots = len(db.lots)
    approved_lots = len([lot for lot in db.lots if lot.qcStatus == QCStatus.APPROVED])
    quarantine_lots = len([lot for lot in db.lots if lot.qcStatus == QCStatus.QUARANTINE])
    active_reservations = len([res for res in db.reservations if res.status == ReservationStatus.ACTIVE])
    total_transactions = len(db.ledger)

    return {
        "totalItems": total_items,
        "totalLots": total_lots,
        "approvedLots": approved_lots,
        "quarantineLots": quarantine_lots,
        "activeReservations": active_reservations,
        "totalTransactions": total_transactions
    }

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
