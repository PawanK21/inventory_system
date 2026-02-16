# Inventory Management System

A production-grade inventory management system built with FastAPI (Python) backend and vanilla JavaScript frontend.

## Features

### Core Functionality
- ✅ **Receive Inventory**: Create new lots with automatic QC status management
- ✅ **Stock Summary**: Real-time calculations (on-hand, reserved, available)
- ✅ **Reserve Stock**: FIFO allocation from QC-approved lots
- ✅ **Issue Stock**: Dispense from reservations with full validation
- ✅ **Ledger-Driven**: All stock derived from transaction ledger (no mutable state)
- ✅ **QC Workflow**: Approve/reject lots in quarantine
- ✅ **Error Handling**: Clear error codes (INSUFFICIENT_STOCK, NO_QC_APPROVED_LOT, etc.)

### Technical Implementation

#### Data Model
```
Item
├── id: string
├── code: string
├── name: string
└── qcRequired: boolean

InventoryLot
├── id: string
├── itemId: string
├── lotCode: string
├── receivedQty: number
├── qcStatus: APPROVED | QUARANTINE | REJECTED
└── receivedDate: datetime

InventoryLedger
├── id: string
├── itemId: string
├── lotId: string
├── txnType: RECEIVE | RESERVE | UNRESERVE | ISSUE
├── qty: number
├── timestamp: datetime
└── metadata: object

Reservation
├── id: string
├── itemId: string
├── allocations: array
├── totalQty: number
├── issuedQty: number
├── timestamp: datetime
├── batchId: string
└── status: ACTIVE | PARTIAL | COMPLETED
```

#### Stock Math (Ledger-Driven)
```python
# All calculations derived from ledger entries
onHand = received - issued
reserved = reserve_txns - unreserve_txns
available = onHand - reserved
```

### Design Highlights
- **Industrial-Modern UI**: Dark theme with cyan/purple gradients
- **Typography**: JetBrains Mono + Archivo fonts
- **Animations**: Smooth transitions, hover effects, loading states
- **Real-time Updates**: Instant stock calculations via API
- **Toast Notifications**: Success/error feedback system
- **Modal Details**: Deep-dive into items and lots

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip

### Installation

1. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

2. **Create static directory and move frontend**:
```bash
mkdir -p static
mv index.html static/
```

3. **Run the FastAPI server**:
```bash
python main.py
```

The server will start on `http://localhost:8000`

4. **Access the application**:
Open your browser and navigate to:
```
http://localhost:8000
```

## API Endpoints

### Inventory Operations
- `POST /api/inventory/receive` - Receive new inventory
- `GET /api/inventory/summary/{item_id}` - Get stock summary for item
- `GET /api/inventory/lot/{lot_id}` - Get lot summary
- `POST /api/inventory/reserve` - Reserve inventory
- `POST /api/inventory/issue` - Issue inventory from reservation

### Items
- `GET /api/items` - List all items
- `GET /api/items/{item_id}` - Get specific item
- `POST /api/items` - Add new item

### Lots
- `GET /api/lots` - List all lots
- `GET /api/lots/{lot_id}` - Get specific lot
- `PUT /api/lots/qc-status` - Update QC status

### Ledger
- `GET /api/ledger` - Get all ledger entries
- `GET /api/ledger/item/{item_id}` - Get item ledger
- `GET /api/ledger/lot/{lot_id}` - Get lot ledger

### Reservations
- `GET /api/reservations` - List all reservations
- `GET /api/reservations/{reservation_id}` - Get specific reservation

### Statistics
- `GET /api/stats` - Get dashboard statistics

## API Documentation

Once the server is running, access the auto-generated API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Usage Examples

### 1. Receive Inventory
```bash
curl -X POST http://localhost:8000/api/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{
    "itemId": "1",
    "lotCode": "LOT-2024-003",
    "qty": 500,
    "qcRequired": true
  }'
```

### 2. Get Stock Summary
```bash
curl http://localhost:8000/api/inventory/summary/1
```

Response:
```json
{
  "itemId": "1",
  "onHand": 850,
  "reserved": 200,
  "available": 650,
  "received": 1000,
  "issued": 150
}
```

### 3. Reserve Stock
```bash
curl -X POST http://localhost:8000/api/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "itemId": "1",
    "qty": 100,
    "batchId": "BATCH-002"
  }'
```

### 4. Issue Stock
```bash
curl -X POST http://localhost:8000/api/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{
    "reservationId": "RES-001",
    "qty": 50
  }'
```

## Architecture Decisions

### 1. Ledger-Driven State
**Decision**: Store all transactions in an immutable ledger; derive stock from ledger entries.

**Rationale**:
- Complete audit trail
- No state corruption from concurrent updates
- Easy to debug and verify correctness
- Can rebuild state from ledger at any time

### 2. FIFO Allocation
**Decision**: Reserve from oldest approved lots first.

**Rationale**:
- Prevents stock aging
- Industry standard for manufacturing
- Simple to understand and implement

### 3. QC Status Management
**Decision**: Lots start in QUARANTINE if item requires QC; only APPROVED lots can be reserved.

**Rationale**:
- Prevents using unverified materials
- Clear separation between inspection and production
- Supports compliance requirements

### 4. In-Memory Database
**Decision**: Use in-memory storage for this implementation.

**Rationale**:
- Simplifies deployment for demo/testing
- Easy to swap for PostgreSQL/MySQL in production
- Fast for prototyping

**Production Alternative**:
```python
# For production, use SQLAlchemy with PostgreSQL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://user:password@localhost/inventory"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
```

## Error Codes

| Code | Description |
|------|-------------|
| `ITEM_NOT_FOUND` | Item does not exist |
| `LOT_NOT_FOUND` | Lot does not exist |
| `RESERVATION_NOT_FOUND` | Reservation does not exist |
| `INSUFFICIENT_STOCK` | Not enough available stock |
| `INSUFFICIENT_APPROVED_STOCK` | Not enough QC-approved stock |
| `NO_QC_APPROVED_LOT` | No approved lots available |
| `INSUFFICIENT_RESERVED_STOCK` | Trying to issue more than reserved |
| `ITEM_CODE_ALREADY_EXISTS` | Duplicate item code |

## Testing

Run manual tests:

```bash
# Test receive inventory
curl -X POST http://localhost:8000/api/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{"itemId": "1", "lotCode": "TEST-001", "qty": 100, "qcRequired": false}'

# Verify stock summary
curl http://localhost:8000/api/inventory/summary/1

# Test reservation
curl -X POST http://localhost:8000/api/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{"itemId": "1", "qty": 50, "batchId": "TEST-BATCH"}'

# Test issue
curl -X POST http://localhost:8000/api/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{"reservationId": "<reservation_id>", "qty": 25}'
```

## Assumptions

1. **Lot Traceability**: Each lot is tracked separately; cannot merge lots
2. **FIFO**: Reservations allocate from oldest approved lots first
3. **Atomicity**: Each API call is atomic (no partial failures)
4. **Idempotency**: Same request IDs would be idempotent in production
5. **Concurrency**: In-memory implementation is not thread-safe; use database locks in production
6. **Units**: All quantities are in base units (no unit conversion)

## Production Considerations

For production deployment:

1. **Database**: Replace in-memory storage with PostgreSQL
2. **Authentication**: Add JWT-based auth
3. **Logging**: Add structured logging (ELK stack)
4. **Monitoring**: Add Prometheus metrics
5. **Testing**: Add pytest unit/integration tests
6. **Concurrency**: Use database transactions with proper locking
7. **Idempotency**: Implement idempotency keys for operations
8. **Rate Limiting**: Add rate limiting middleware
9. **Validation**: Enhanced input validation
10. **CORS**: Configure CORS for specific origins only

## License

MIT

AI tools used:
  - claude.ai
  - copilot
