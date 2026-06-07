# rowpic — multi-stage Dockerfile
# Stage 1: build frontend
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: python backend with frontend dist
FROM python:3.12-slim

# System deps for rawpy (libraw) and opencv
RUN apt-get update && apt-get install -y --no-install-recommends \
        libraw-dev libjpeg-dev zlib1g-dev libtiff-dev libwebp-dev \
        libheif-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend /app/dist ./frontend/dist

ENV ROWPIC_HOST=0.0.0.0 \
    ROWPIC_PORT=8765 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend
EXPOSE 8765

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,sys; \
    sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/healthz',timeout=2).status==200 else 1)"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
