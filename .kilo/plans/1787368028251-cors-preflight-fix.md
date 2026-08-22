# CORS Preflight Fix Plan

## Problem
The frontend dev server is running on port **3000** (`http://localhost:3000`), but the FastAPI backend CORS middleware only allows origins on port **3002**. All browser CORS preflight `OPTIONS` requests are rejected with `400 Bad Request`, so actual API calls never reach the route handlers.

## Evidence
- `backend/server.py:46-51` — `allow_origins=["http://localhost:3002", "http://127.0.0.1:3002"]`
- `next dev` logs show `Local: http://localhost:3000`
- Backend logs show repeated `OPTIONS /api/... HTTP/1.1" 400 Bad Request`

## Fix
Update `backend/server.py` to include the frontend origin on port **3000** in the CORS allowed origins list.

### Changed file
- `backend/server.py:48`

### New value
```python
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3002", "http://127.0.0.1:3002"],
```

## Validation
1. Restart the backend (`bun dev` or equivalent).
2. Confirm the frontend on port 3000 no longer receives `400` on `OPTIONS` requests.
3. Verify actual `GET`/`POST` API calls to `/api/token/status`, `/api/data/status`, `/api/chart/data`, etc. return `200`.

## Risk
None — this is a local-dev CORS allowlist change. No production or persistence impact.
