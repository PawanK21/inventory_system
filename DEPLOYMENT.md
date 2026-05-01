# 🚀 Deployment Guide - Inventory Management System

## Overview

This guide provides instructions to deploy the Inventory Management System using Docker to various cloud platforms or self-hosted environments.

---

## 📋 Prerequisites

- Docker installed on your machine (if building locally)
- Docker account (for pushing to Docker Hub - optional)
- Cloud platform account (if deploying to cloud)
- Git (optional, for version control)

---

## 🐳 Docker Setup

### 1. Build Docker Image Locally

```bash
# Navigate to project directory
cd inventory_system3

# Build the image
docker build -t inventory-management-system:latest .

# Or with a specific tag
docker build -t yourusername/inventory-management-system:1.0.0 .
```

### 2. Run Container Locally

**Using Docker directly:**
```bash
docker run -d \
  --name inventory-app \
  -p 8000:8000 \
  -v ./static:/app/static:ro \
  inventory-management-system:latest
```

**Using Docker Compose (Easier):**
```bash
docker-compose up -d
```

**Access the application:**
- Web Interface: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Stop the container:**
```bash
# Using Docker Compose
docker-compose down

# Or using Docker directly
docker stop inventory-app
docker rm inventory-app
```

---

## ☁️ Cloud Deployment Options

### Option 1: Railway (Easiest - Recommended)

**Steps:**

1. Create account at [railway.app](https://railway.app)
2. Connect your GitHub repository or upload files
3. Railway auto-detects Dockerfile and deploys automatically
4. Application is instantly live with a public URL

**Benefits:**
- ✅ Free tier available
- ✅ Auto-deploys on push
- ✅ Built-in domain
- ✅ Easy environment variables
- ✅ One-click deployment

**Environment Variables to Set:**
```
PORT=8000
PYTHONUNBUFFERED=1
```

### Option 2: Render

**Steps:**

1. Create account at [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect GitHub repository
4. Configure:
   - **Name**: inventory-management-system
   - **Environment**: Docker
   - **Build Command**: (leave empty)
   - **Start Command**: (leave empty)
   - **Plan**: Free (0.5 CPU, 512MB RAM)

**Environment Variables:**
```
PORT=8000
PYTHONUNBUFFERED=1
```

### Option 3: Heroku (with Docker)

**Steps:**

1. Install Heroku CLI
2. Login: `heroku login`
3. Create app:
```bash
heroku create inventory-management-system
```

4. Set Docker as builder:
```bash
heroku stack:set container
```

5. Deploy:
```bash
git push heroku main
```

### Option 4: AWS (EC2)

**Steps:**

1. Launch EC2 instance (Ubuntu 22.04)
2. SSH into instance
3. Install Docker:
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

4. Clone your repository:
```bash
git clone <your-repo-url>
cd inventory_system3
```

5. Run with Docker Compose:
```bash
docker-compose up -d
```

6. Configure security group to allow port 8000
7. Access via: `http://<your-ec2-ip>:8000`

### Option 5: DigitalOcean App Platform

**Steps:**

1. Create account at [digitalocean.com](https://digitalocean.com)
2. Go to "App Platform" → "Create App"
3. Connect GitHub repository
4. Set build command: `(leave empty)`
5. Set run command: `(leave empty - auto-detects Dockerfile)`
6. Deploy

---

## 📦 Docker Hub (Optional - For Sharing)

### Push Image to Docker Hub

```bash
# Login to Docker Hub
docker login

# Tag image
docker tag inventory-management-system:latest yourusername/inventory-management-system:latest

# Push to Docker Hub
docker push yourusername/inventory-management-system:latest
```

Others can then run:
```bash
docker run -d -p 8000:8000 yourusername/inventory-management-system:latest
```

---

## 🔧 Production Configuration

### Environment Variables

Create a `.env` file for production:

```env
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
PORT=8000
LOG_LEVEL=INFO
```

### Health Checks

The container includes health checks. Monitor status:
```bash
docker ps  # Check health status in PORTS column
```

---

## 📊 Monitoring & Logs

### View Logs

```bash
# Docker Compose
docker-compose logs -f inventory-app

# Docker directly
docker logs -f inventory-app
```

### Monitor Container

```bash
# Resource usage
docker stats

# Container details
docker inspect inventory-app
```

---

## 🛡️ Security Best Practices

1. **Use environment variables** for sensitive data (don't hardcode)
2. **Set PORT environment variable** instead of hardcoding in code
3. **Limit container resources** in production
4. **Use read-only volumes** where possible
5. **Keep dependencies updated** (regularly rebuild images)
6. **Use secrets management** on cloud platforms (not env files)

---

## 📈 Scaling

### Docker Compose Scaling

```bash
# Run multiple instances
docker-compose up -d --scale inventory-app=3
```

### Cloud Platform Scaling

- **Railway**: Auto-scales or configure manually in settings
- **Render**: Use "Autoscaling" in service settings
- **AWS**: Use ECS Fargate with Auto Scaling Groups
- **DigitalOcean**: Use App Platform scaling settings

---

## 🔄 CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Docker Registry

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v2
        with:
          push: true
          tags: yourusername/inventory-management-system:latest
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
```

---

## 🚨 Troubleshooting

### Container won't start
```bash
docker logs inventory-app
```

### Port already in use
```bash
# Use a different port
docker run -p 9000:8000 inventory-management-system:latest
```

### Dependencies not installing
- Check `requirements.txt` format
- Ensure base image has required libraries
- Check Docker build logs

### Health check failing
```bash
# Test manually
curl http://localhost:8000/api/stats
```

---

## 📞 Support

For issues:
1. Check Docker logs
2. Verify environment variables
3. Ensure dependencies are correct
4. Test locally before deploying

---

## 🎯 Summary

| Method | Ease | Cost | Best For |
|--------|------|------|----------|
| **Railway** | ⭐⭐⭐ | Free+ | Quick deployment |
| **Render** | ⭐⭐⭐ | Free+ | Hobby projects |
| **Heroku** | ⭐⭐ | Paid | Production apps |
| **AWS** | ⭐ | Variable | Large scale |
| **Docker Hub** | ⭐⭐ | Free+ | Image sharing |

**Recommended for first deployment:** Railway or Render (easiest, free tier available)

---

## ✅ Deployment Checklist

- [ ] Docker image builds successfully locally
- [ ] Container runs and responds to health checks
- [ ] API endpoints verified working
- [ ] Environment variables configured
- [ ] Static files accessible
- [ ] Logs showing normal operation
- [ ] Cloud platform account created
- [ ] Repository pushed to GitHub (if needed)
- [ ] Deployed and accessible via public URL
- [ ] HTTPS working (platform should handle automatically)
