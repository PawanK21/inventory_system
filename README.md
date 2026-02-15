# Inventory Management System

A production-ready inventory management service for manufacturing operations with lot tracking, QC workflow, reservations, and strict correctness guarantees.

## Features

✅ **Core Requirements Met:**
- Multiple materials support
- Lot-wise stock tracking
- Reservations for production
- Actual issue/consumption
- Accurate availability calculations
- Hard correctness guarantees

✅ **Bonus Features:**
- Comprehensive test suite (15+ tests)
- Concurrent request safety (database-level locking)
- Clear error codes
- Idempotency protection
- FIFO lot issuing

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Server will start at `http://localhost:8000`

### Run Tests

```bash
pytest test_app.py -v
```

### API Documentation

Once running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Data Model

### Core Entities

#### 1. Item
Represents a material/product in the system.

```python
{
    "id": "uuid",
    "code": "STEEL-001",          # Unique identifier
    "name": "Steel Bar",
    "qc_required": true            # Whether QC is needed
}
```

#### 2. InventoryLot
Represents a batch of received inventory.

```python
{
    "id": "uuid",
    "item_id": "uuid",
    "lot_code": "LOT-2024-001",   # Unique lot identifier
    "received_qty": 100.0,
    "qc_status": "APPROVED"        # APPROVED | QUARANTINE | REJECTED
}
```

**QC Status Rules:**
- If `item.qc_required = true` → lot starts as `QUARANTINE`
- If `item.qc_required = false` → lot starts as `APPROVED`
- Only `APPROVED` lots can be issued

#### 3. InventoryLedger
**Ledger-Driven State** - All stock calculations derive from this.

```python
{
    "id": "uuid",
    "item_id": "uuid",
    "lot_id": "uuid",              # NULL for RESERVE/UNRESERVE
    "txn_type": "RECEIVE",         # RECEIVE | RESERVE | UNRESERVE | ISSUE
    "qty": 100.0,
    "timestamp": "ISO8601",
    "reservation_id": "uuid"       # Links transactions to reservations
}
```

**Transaction Types:**
- `RECEIVE`: Inventory received into a lot
- `RESERVE`: Stock reserved for future use (reduces available)
- `UNRESERVE`: Reservation released (when issued or cancelled)
- `ISSUE`: Stock actually dispensed (reduces on-hand)

#### 4. Reservations
Tracks reservation state for idempotency and validation.

```python
{
    "id": "uuid",
    "item_id": "uuid",
    "qty": 50.0,
    "status": "OPEN",              # OPEN | ISSUED | CANCELLED
    "created_at": "ISO8601"
}
```

## Stock Math

### Critical Calculations

All stock values are **computed from the ledger** - never stored as mutable fields.

#### 1. On-Hand Stock
```
onHand = Σ(RECEIVE) - Σ(ISSUE)
```
Represents physical stock in warehouse.

#### 2. Reserved Stock
```
reserved = Σ(qty) WHERE status='OPEN' in reservations table
```
Stock allocated but not yet issued.

#### 3. Available Stock
```
available = onHand - reserved
```
Stock that can be reserved for new orders.

### Example Calculation

```
Initial: 
- Receive 100 units → onHand=100, reserved=0, available=100

After Reserve 30:
- Reserve 30 units → onHand=100, reserved=30, available=70

After Issue 30:
- Issue 30 units → onHand=70, reserved=0, available=70
  (Issue adds ISSUE ledger + UNRESERVE ledger)
```

## API Endpoints

### 1. Receive Inventory

```http
POST /inventory/receive
Content-Type: application/json

{
    "item_id": "uuid",
    "lot_code": "LOT-2024-001",
    "qty": 100.0
}
```

**Response:**
```json
{
    "lot_id": "uuid",
    "item_id": "uuid",
    "lot_code": "LOT-2024-001",
    "received_qty": 100.0,
    "qc_status": "APPROVED"
}
```

**Rules:**
- Creates new lot
- Adds `RECEIVE` ledger entry
- If `qcRequired=true`, lot starts in `QUARANTINE`

### 2. Get Stock Summary

```http
GET /inventory/summary/{item_id}
```

**Response:**
```json
{
    "on_hand": 100.0,
    "reserved": 30.0,
    "available": 70.0
}
```

**Calculation:** Real-time from ledger (see Stock Math section)

### 3. Reserve Inventory

```http
POST /inventory/reserve
Content-Type: application/json

{
    "item_id": "uuid",
    "qty": 50.0
}
```

**Response:**
```json
{
    "reservation_id": "uuid",
    "item_id": "uuid",
    "qty": 50.0,
    "status": "OPEN"
}
```

**Validations:**
- Checks `available >= qty`
- Checks at least one QC-approved lot exists
- Creates `RESERVE` ledger entry

**Error Codes:**
- `INSUFFICIENT_STOCK`: Not enough available stock
- `NO_QC_APPROVED_LOT`: No approved lots available

### 4. Issue Inventory

```http
POST /inventory/issue
Content-Type: application/json

{
    "reservation_id": "uuid"
}
```

**Response:**
```json
{
    "reservation_id": "uuid",
    "item_id": "uuid",
    "qty": 50.0,
    "lots_issued": [
        {
            "lot_id": "uuid",
            "lot_code": "LOT-A",
            "qty": 30.0
        },
        {
            "lot_id": "uuid",
            "lot_code": "LOT-B",
            "qty": 20.0
        }
    ]
}
```

**Rules:**
- Can only issue against existing `OPEN` reservation
- Only issues from `APPROVED` lots
- Uses FIFO (First In, First Out) lot selection
- Creates `ISSUE` ledger entries (one per lot)
- Creates `UNRESERVE` ledger entry to close reservation
- Updates reservation status to `ISSUED`

**Error Codes:**
- `RESERVATION_NOT_FOUND`: Invalid reservation ID
- `RESERVATION_ALREADY_ISSUED`: Already issued
- `NO_QC_APPROVED_LOT`: No approved lots
- `INSUFFICIENT_STOCK`: Not enough stock in approved lots

### 5. Update QC Status (Helper)

```http
PATCH /inventory/lots/{lot_id}/qc-status?qc_status=APPROVED
```

Moves lots from `QUARANTINE` → `APPROVED` or `REJECTED`

## Correctness Guarantees

### 1. No Negative Stock ✅
- Reservations check `available >= qty` before allowing
- Issues check lot availability before dispensing
- Database constraints prevent invalid states

### 2. No Phantom Availability ✅
- Stock calculated in real-time from ledger
- Reserved stock excluded from available
- Atomic transactions prevent race conditions

### 3. No Double-Issuing ✅
- Reservation status checked (`OPEN` required)
- After issue, status set to `ISSUED`
- Subsequent issue attempts fail with `RESERVATION_ALREADY_ISSUED`

### 4. Ledger-Driven State ✅
- **No mutable `onHand` field exists**
- All stock derived from `SUM(RECEIVE) - SUM(ISSUE)`
- Immutable ledger = audit trail + correctness

### 5. Idempotency ✅
- Duplicate reservation/issue requests detected
- Reservation IDs are UUIDs (unique)
- Lot codes enforced as unique
- Database constraints prevent duplicates

### 6. Concurrency Safety ✅
- SQLite `BEGIN IMMEDIATE` provides write locking
- Critical sections protected with transactions
- Thread-safe database connections via thread-local storage

## Design Decisions & Trade-offs

### 1. SQLite vs PostgreSQL
**Choice:** SQLite for simplicity
**Trade-off:**
- ✅ Zero configuration, embedded
- ✅ Sufficient for single-instance deployments
- ❌ Limited concurrent writes (but safe with `BEGIN IMMEDIATE`)
- **Production:** Use PostgreSQL with proper connection pooling

### 2. Ledger-Only State
**Choice:** No derived fields (onHand, available)
**Trade-off:**
- ✅ Single source of truth
- ✅ Perfect audit trail
- ✅ Cannot have inconsistent state
- ❌ Slightly slower queries (requires aggregation)
- **Optimization:** Add materialized views for high-traffic items

### 3. FIFO Lot Selection
**Choice:** Issue from oldest lots first (by lot_code alphabetically)
**Trade-off:**
- ✅ Standard inventory practice
- ✅ Prevents lot expiration
- ❌ Could be optimized with explicit lot priorities
- **Alternative:** Allow caller to specify lot preferences

### 4. Synchronous API
**Choice:** Standard FastAPI sync handlers
**Trade-off:**
- ✅ Simple, easy to reason about
- ✅ Database locking handles concurrency
- ❌ Not optimal for high concurrency
- **Production:** Consider async with proper connection pool

### 5. In-Transaction Validation
**Choice:** All validations inside database transaction
**Trade-off:**
- ✅ Atomic - either all succeed or all fail
- ✅ No partial state corruption
- ❌ Holds locks during validation
- **Acceptable:** Validations are fast (simple queries)

## Error Handling

### Error Codes
- `INSUFFICIENT_STOCK`: Not enough available inventory
- `NO_QC_APPROVED_LOT`: No approved lots for item
- `RESERVATION_NOT_FOUND`: Invalid reservation ID
- `RESERVATION_ALREADY_ISSUED`: Reservation already consumed
- `ITEM_NOT_FOUND`: Invalid item ID
- `DUPLICATE_LOT_CODE`: Lot code already exists
- `LOT_NOT_APPROVED`: Attempted to issue from non-approved lot
- `INVALID_QTY`: Quantity must be positive

### HTTP Status Codes
- `200`: Success
- `201`: Resource created
- `400`: Validation error / Business rule violation
- `404`: Resource not found
- `500`: Internal server error

## Assumptions

1. **Quantities are decimals** - Supports fractional units (kg, liters, etc.)
2. **Lot codes are unique globally** - Not scoped per item
3. **FIFO within item** - Lots selected alphabetically by lot_code
4. **Single currency** - No multi-currency support
5. **No partial reserves** - Reserve all or nothing
6. **No reservation expiry** - Reservations don't auto-expire
7. **UTC timestamps** - All times in UTC
8. **No soft deletes** - Entities are never deleted (append-only ledger)
9. **Reservation = commitment** - Reserved stock is locked
10. **QC binary decision** - APPROVED or REJECTED (no pending states)

## Testing

### Test Coverage

The test suite covers:
- ✅ Basic CRUD operations
- ✅ Stock calculations (ledger-driven)
- ✅ QC workflow (QUARANTINE → APPROVED)
- ✅ Reservation validation (insufficient stock, no approved lots)
- ✅ Issue validation (reservation not found, already issued)
- ✅ Idempotency (duplicate lot codes, double issuing)
- ✅ Multi-lot scenarios (FIFO issuing)
- ✅ Complex workflows (multiple receives, reserves, issues)
- ✅ Negative stock prevention
- ✅ Ledger integrity

### Run Tests

```bash
# Run all tests with verbose output
pytest test_app.py -v

# Run specific test
pytest test_app.py::test_issue_inventory_success -v

# Run with coverage
pytest test_app.py --cov=app --cov-report=html
```

## Production Considerations

### Before Production Deployment:

1. **Database:**
   - Migrate to PostgreSQL
   - Add connection pooling (SQLAlchemy)
   - Enable WAL mode for better concurrency
   - Add database backups

2. **Security:**
   - Add authentication/authorization
   - Rate limiting
   - Input validation (additional)
   - SQL injection protection (parameterized queries ✅)

3. **Monitoring:**
   - Add logging (structured JSON logs)
   - Metrics (Prometheus)
   - Distributed tracing (OpenTelemetry)
   - Health checks (enhanced)

4. **Performance:**
   - Add caching (Redis) for stock summaries
   - Database indexes optimization
   - Async handlers for I/O operations
   - Load testing

5. **Features:**
   - Reservation expiry (TTL)
   - Batch operations
   - Lot priority/preferences
   - Stock adjustments (corrections)
   - Historical reports

## Architecture

```
┌─────────────┐
│   FastAPI   │  HTTP API Layer
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Business   │  Validation & Logic
│   Logic     │  (Stock calculations, FIFO, etc.)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   SQLite    │  Persistence Layer
│  (Ledger)   │  (Append-only ledger + lookups)
└─────────────┘
```

### Key Patterns:
- **Event Sourcing Lite**: Ledger stores all events
- **CQRS Lite**: Reads calculate from ledger
- **Domain-Driven Design**: Clear entity boundaries
- **Database-as-Lock**: SQLite transactions for concurrency

## License

MIT

## Author

Built for Technical Round - Inventory Management Challenge

---

**Note:** This implementation prioritizes correctness over performance. For production use with high throughput, consider the optimizations mentioned in the Production Considerations section.
