inventory_system/
│
├── inventory_system/      # Django project
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── inventory/             # Main inventory app
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   │    └── inventory/
│   │         ├── dashboard.html
│   │         ├── login.html
│   │         └── register.html
│   └── migrations/
│
├── db.sqlite3
├── manage.py
└── README.md

🧠 Core Domain Model
1️⃣ Item

id

code

name

qcRequired (boolean)

2️⃣ InventoryLot

id

itemId

lotCode

receivedQty

qcStatus

APPROVED

QUARANTINE

REJECTED

3️⃣ InventoryLedger

id

itemId

lotId

txnType

RECEIVE

RESERVE

UNRESERVE

ISSUE

qty

timestamp

📊 Inventory Rules & Logic
🔹 On Hand
onHand = received − issued
reserved = open reservations
available = onHand − reserved

Authentication

User Registration

User Login

Logout

Login required for dashboard access

Routes:
/register/
/login/
/logout/


⚙️ Installation & Setup
1️⃣ Clone the repository
git clone https://github.com/your-username/inventory-management-system.git
cd inventory-management-system

2️⃣ Create Virtual Environment
python -m venv venv


Activate:

Windows:

venv\Scripts\activate


Mac/Linux:

source venv/bin/activate

3️⃣ Install Dependencies
pip install django

4️⃣ Run Migrations
python manage.py migrate

5️⃣ Create Superuser (Optional)
python manage.py createsuperuser

6️⃣ Run Server
python manage.py runserver


Visit:

http://127.0.0.1:8000/

🧪 Testing

Basic manual test cases:

Receive stock

Approve lot

Reserve stock

Issue stock

Validate summary

Edge cases handled:

Over-reservation

Over-issuing

QC blocked lots

Duplicate operations

🎯 Design Decisions
Why Ledger-Driven?

Instead of storing mutable stock values:

All inventory state is derived from ledger entries.

Ensures auditability.

Prevents state corruption.

Production-grade approach.

🔮 Future Improvements

PostgreSQL support

Batch-based reservations

Concurrency-safe transactions

API versioning

Unit tests

REST API with DRF

Dockerization

👨‍💻 Author

Pawan Kumar
Civil Engineering Graduate → Aspiring Software Engineer
Strong interest in System Design & Backend Architecture

📜 License

This project is for learning and demonstration purposes.
