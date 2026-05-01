# 🐳 Docker Setup Guide for Windows

## Install Docker

### Option 1: Docker Desktop (Recommended)

1. Download **Docker Desktop for Windows** from [docker.com](https://www.docker.com/products/docker-desktop)
2. Run the installer
3. Follow setup wizard (enable WSL 2 backend when prompted)
4. Restart your computer
5. Verify installation:
```bash
docker --version
docker-compose --version
```

### Option 2: Using Chocolatey (Package Manager)

```powershell
# Install Chocolatey first if not already installed
# Then run:
choco install docker-desktop -y
```

### Option 3: Using Windows Package Manager

```powershell
winget install Docker.DockerDesktop
```

---

## Quick Test After Installation

```bash
# Verify Docker works
docker run hello-world

# Should see: "Hello from Docker!"
```

---

## Next Steps: Deploy the Application

After Docker is installed, deploy using:

### Local Testing
```bash
cd inventory_system3
docker-compose up -d
```
Access: http://localhost:8000

### Cloud Deployment
See `DEPLOYMENT.md` for:
- Railway (easiest - recommended)
- Render
- AWS
- DigitalOcean
- Heroku

---

## Common Issues

**Docker command not found:**
- Restart PowerShell/Terminal after installation
- Add Docker to PATH if needed

**Docker service not running:**
- Open Docker Desktop application
- Check taskbar for Docker icon

**Port 8000 already in use:**
```bash
docker run -p 9000:8000 inventory-management-system:latest
```

---

## Uninstall Docker

**Windows:**
- Control Panel → Programs → Uninstall a program → Docker Desktop
- Or use: `choco uninstall docker-desktop` (if installed via Chocolatey)
