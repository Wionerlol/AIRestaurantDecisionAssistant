FROM python:3.12-slim

WORKDIR /app
COPY backend /app/backend
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e /app/backend

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --app-dir /app/backend/src --host ${BACKEND_HOST:-0.0.0.0} --port ${BACKEND_PORT:-8000}"]
