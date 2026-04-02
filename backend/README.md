# Backend

Python 3.12 FastAPI service. The current skeleton exposes:

- `GET /health`
- `GET /`

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
.venv/bin/uvicorn app.main:app --app-dir src --reload --host 0.0.0.0 --port 8000
```

