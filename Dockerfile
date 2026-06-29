# ============================================================
# Profile Guru — Multi-stage Dockerfile
# ============================================================

# ---- Builder Stage: Frontend ----
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- Builder Stage: Backend ----
FROM python:3.11-slim AS backend-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime Stage ----
FROM python:3.11-slim
WORKDIR /app

# Install Node for Next.js standalone
COPY --from=node:20-alpine /usr/local /usr/local

# Copy backend
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ src/
COPY main_api.py .
COPY hash_password.py .
COPY scripts/ scripts/

# Copy built frontend
COPY --from=frontend-builder /app/frontend/.next /app/frontend/.next
COPY --from=frontend-builder /app/frontend/public /app/frontend/public
COPY --from=frontend-builder /app/frontend/package.json /app/frontend/package.json
COPY --from=frontend-builder /app/frontend/node_modules/next /app/frontend/node_modules/next

# Environment defaults
ENV PYTHONPATH=/app
ENV DATA_DIR=/data

EXPOSE 8000 3000

# Start both servers using a wrapper
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
