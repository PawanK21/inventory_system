# 🚀 QUICK START GUIDE - Run from Terminal

## Windows PowerShell (Recommended)

```powershell
cd C:\Users\PAWAN KUMAR\OneDrive\Desktop\inventory_system3
python main.py
```

**That's it!** The server will start at `http://localhost:8000`

---

## Windows Command Prompt (CMD)

```cmd
cd C:\Users\PAWAN KUMAR\OneDrive\Desktop\inventory_system3
python main.py
```

---

## First Time Setup (if needed)

```powershell
# PowerShell
.\setup.ps1

# Or Command Prompt
setup.bat
```

---

## Access the Application

Once running, open in your browser:

| What | URL |
|------|-----|
| **Web Interface** | http://localhost:8000 |
| **API Documentation** | http://localhost:8000/docs |
| **Alternative API Docs** | http://localhost:8000/redoc |

---

## API Examples (from PowerShell)

### Get all items:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/items" -UseBasicParsing | ConvertTo-Json
```

### Get stock summary:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/inventory/summary/1" -UseBasicParsing | ConvertTo-Json
```

### Get dashboard stats:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/stats" -UseBasicParsing | ConvertTo-Json
```

---

## Stop the Server

Press `Ctrl+C` in the terminal where it's running.

---

## Troubleshooting

**Port 8000 already in use?**
```powershell
python main.py --host 0.0.0.0 --port 8001
```

**Module not found error?**
```powershell
pip install fastapi uvicorn pydantic python-multipart starlette typing-extensions
```

**Verify dependencies:**
```powershell
pip list | grep -E "fastapi|uvicorn|pydantic"
```

---

## Server Status

✅ Server is **RUNNING NOW** at http://localhost:8000
✅ All dependencies **INSTALLED**
✅ Database **INITIALIZED** with sample data
✅ API endpoints **ACTIVE** and responding

**Enjoy!** 🎉
