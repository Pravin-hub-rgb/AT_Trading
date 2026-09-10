"""Verification API endpoints.

Single responsibility: expose verification via HTTP.
Simple WSGI app - no framework needed.
"""

import json
from typing import Callable
from persistence.database import Database
from persistence.mark_store import get_marks
from verification.parity import daily_parity_check, format_parity_report


def create_app(db_path: str = "backbencher.db") -> Callable:
    """Create WSGI app.
    
    Usage:
        app = create_app("backbencher.db")
        # Use with any WSGI server
    """
    db = Database(db_path)
    db.connect()
    db.create_tables()
    
    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET")
        
        if method == "GET" and path == "/marks":
            return handle_get_marks(db, environ, start_response)
        elif method == "GET" and path == "/verify":
            return handle_verify(db, environ, start_response)
        elif method == "GET" and path == "/health":
            return handle_health(db, environ, start_response)
        else:
            return handle_404(start_response)
    
    return app


def handle_get_marks(db: Database, environ: dict, start_response):
    """GET /marks?tf=15m&from=...&to=..."""
    from urllib.parse import parse_qs
    
    params = parse_qs(environ.get("QUERY_STRING", ""))
    tf = params.get("tf", ["15m"])[0]
    from_ts = int(params.get("from", ["0"])[0])
    to_ts = int(params.get("to", ["0"])[0])
    
    marks = get_marks(db, tf, from_ts, to_ts)
    
    body = json.dumps({
        "tf": tf,
        "count": len(marks),
        "marks": [m.to_dict() for m in marks],
    })
    
    start_response("200 OK", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ])
    return [body.encode()]


def handle_verify(db: Database, environ: dict, start_response):
    """GET /verify?date=YYYY-MM-DD"""
    from urllib.parse import parse_qs
    
    params = parse_qs(environ.get("QUERY_STRING", ""))
    date = params.get("date", [""])[0]
    
    if not date:
        body = json.dumps({"error": "date parameter required"})
        start_response("400 Bad Request", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ])
        return [body.encode()]
    
    # For now, return a simple response
    # In production, this would run the full parity check
    body = json.dumps({
        "date": date,
        "status": "not_implemented",
        "message": "Full parity check requires backtest data",
    })
    
    start_response("200 OK", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ])
    return [body.encode()]


def handle_health(db: Database, environ: dict, start_response):
    """GET /health - health check."""
    body = json.dumps({
        "status": "ok",
        "database": "connected",
    })
    
    start_response("200 OK", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ])
    return [body.encode()]


def handle_404(start_response):
    """404 Not Found."""
    body = json.dumps({"error": "not found"})
    start_response("404 Not Found", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ])
    return [body.encode()]


def run_server(host: str = "0.0.0.0", port: int = 8080, db_path: str = "backbencher.db"):
    """Run the verification server."""
    from wsgiref.simple_server import make_server
    
    app = create_app(db_path)
    server = make_server(host, port, app)
    
    print(f"Verification server running on http://{host}:{port}")
    print("Endpoints:")
    print("  GET /health")
    print("  GET /marks?tf=15m&from=...&to=...")
    print("  GET /verify?date=YYYY-MM-DD")
    
    server.serve_forever()
