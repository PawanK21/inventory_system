# Inventory Management System API

This is a Production-ready Inventory Management System built with FastAPI and designed for manufacturing environments.

## Setup Instructions

### Windows (PowerShell)
```bash
# Run the setup script
.\setup.ps1

# Start the server
python main.py

# Or use the run script
.\run.ps1
```

### Linux/macOS
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

## Running the Application

**Start the server:**
```bash
python main.py
```

The server will start at `http://localhost:8000`

- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **Frontend**: http://localhost:8000/

## API Endpoints

### Items Management
- `GET /api/items` - Get all items
- `GET /api/items/{item_id}` - Get a specific item
- `POST /api/items` - Add a new item

### Inventory Operations
- `POST /api/inventory/receive` - Receive inventory and create a new lot
- `GET /api/inventory/summary/{item_id}` - Get stock summary for an item
- `GET /api/inventory/lot/{lot_id}` - Get summary for a specific lot

### Reservations
- `POST /api/inventory/reserve` - Reserve inventory for a batch
- `POST /api/inventory/issue` - Issue inventory from a reservation
- `GET /api/reservations` - Get all reservations
- `GET /api/reservations/{reservation_id}` - Get a specific reservation

### Lots Management
- `GET /api/lots` - Get all lots
- `GET /api/lots/{lot_id}` - Get a specific lot
- `PUT /api/lots/qc-status` - Update QC status of a lot

### Ledger
- `GET /api/ledger` - Get all ledger entries
- `GET /api/ledger/item/{item_id}` - Get ledger entries for an item
- `GET /api/ledger/lot/{lot_id}` - Get ledger entries for a lot

### Dashboard
- `GET /api/stats` - Get dashboard statistics

## Features

✅ **Lot Tracking** - Track materials through different lots with QC status
✅ **Reservations** - Reserve inventory for specific batches
✅ **FIFO Allocation** - Automatic FIFO-based inventory allocation
✅ **QC Management** - Quality control status tracking
✅ **Inventory Ledger** - Complete audit trail of all transactions
✅ **Stock Summary** - Real-time stock calculations
✅ **Web Interface** - Interactive frontend for inventory management

## Technology Stack

- **Backend**: FastAPI 0.104.1
- **Server**: Uvicorn 0.24.0
- **Data Validation**: Pydantic 2.5.0
- **Database**: In-memory (can be extended to use SQL database)
- **Frontend**: HTML5 with modern CSS styling

## Project Structure

```
inventory_system3/
├── main.py                 # FastAPI application
├── index.html             # Web frontend
├── static/                # Static files (index.html)
├── requirements.txt       # Python dependencies
├── setup.ps1             # Windows setup script
├── run.ps1               # Windows run script
├── setup.sh              # Unix setup script
└── README.md             # This file
```

## Example API Usage

### Add an Item
```bash
curl -X POST http://localhost:8000/api/items \
  -H "Content-Type: application/json" \
  -d '{
    "code": "RM-004",
    "name": "New Raw Material",
    "qcRequired": true
  }'
```

### Receive Inventory
```bash
curl -X POST http://localhost:8000/api/inventory/receive \
  -H "Content-Type: application/json" \
  -d '{
    "itemId": "1",
    "lotCode": "SS-2024-003",
    "qty": 500,
    "qcRequired": true
  }'
```

### Reserve Inventory
```bash
curl -X POST http://localhost:8000/api/inventory/reserve \
  -H "Content-Type: application/json" \
  -d '{
    "itemId": "1",
    "qty": 100,
    "batchId": "BATCH-002"
  }'
```

### Issue Inventory
```bash
curl -X POST http://localhost:8000/api/inventory/issue \
  -H "Content-Type: application/json" \
  -d '{
    "reservationId": "RES-001",
    "qty": 50
  }'
```

## Troubleshooting

**Port already in use?**
Add port parameter when running:
```bash
python main.py --port 8001
```

**Dependencies not installing?**
Manually install each package:
```bash
pip install fastapi uvicorn pydantic python-multipart
```

**Module not found errors?**
Ensure you're using the correct Python environment:
```bash
python --version
pip list
```

## License

This project is provided as-is for inventory management use.
