# Deployment & Production Guidelines

This document covers running Profile Guru in containerized production environments, non-Windows systems, and general production security guidelines.

---

## 1. Containerized Setup (Docker Compose)

Profile Guru includes Docker configuration files for multi-container deployments:

- [Dockerfile.backend](file:///f:/Github/Profile-Guru/Dockerfile.backend): Configures a lightweight Python environment running the FastAPI backend under Uvicorn.
- [docker-compose.yml](file:///f:/Github/Profile-Guru/docker-compose.yml): The production-ready composition, launching the backend, frontend, Redis cache, and persistent ChromaDB storage.
- [docker-compose.minimal.yml](file:///f:/Github/Profile-Guru/docker-compose.minimal.yml): A minimal setup for running local analytics without external cache requirements.

### Running with Docker Compose
To build and launch all containers in the background:

```bash
docker-compose up --build -d
```

To view logs for the running containers:

```bash
docker-compose logs -f
```

---

## 2. Production Security Hardening

Before deploying Profile Guru to a public network or clinical intranet, ensure the following configurations are applied:

### Secret Configuration
- **Rotate the SECRET_KEY:** Never deploy with default keys. Set a cryptographically secure key in your environment:
  ```bash
  export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
  ```
- **Enforce Bcrypt APP_PASSWORD:** Generate a strong password hash using `hash_password.py` and set it as `APP_PASSWORD`.
- **API Access Controls:** Ensure the backend endpoints are behind secure SSL/TLS connections (e.g., using Let's Encrypt).

### Reverse Proxy Settings (Nginx)
We recommend serving the Next.js frontend and routing API requests to the FastAPI backend through Nginx. Here is a sample routing block:

```nginx
server {
    listen 443 ssl;
    server_name profile-guru.local;

    # Frontend Next.js routing
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend FastAPI routing
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Enable WebSocket/SSE streaming
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

---

## 3. Deployment on macOS or Linux

Profile Guru can run natively on macOS and Linux:
1. Follow the standard setup steps in `docs/setup.md`.
2. Instead of `run.bat`, run the backend and frontend separately or write a shell script wrapper:
   ```bash
   # Start backend
   PYTHONPATH=. uvicorn main_api:app --host 0.0.0.0 --port 8000
   
   # Start frontend
   cd frontend
   npm run start
   ```
3. Update paths in `.env` to follow POSIX layout conventions instead of Windows drive letters (e.g., `/var/lib/profile_guru` instead of `F:\chats`).
