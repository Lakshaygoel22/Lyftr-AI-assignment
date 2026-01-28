import hmac
import hashlib
import time
import logging
from typing import Annotated, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, Request, HTTPException, Response, status, Query
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from datetime import timezone

from app.config import get_settings, Settings
from app.logging_utils import setup_logging
from app.models import WebhookPayload, MessageListResponse, StatsResponse, MessageResponse
from app.storage import init_db, get_db, Storage
from app.metrics import HTTP_REQUESTS_TOTAL, WEBHOOK_REQUESTS_TOTAL, REQUEST_LATENCY

# Initialize Settings and Logging
settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger("app")

app = FastAPI(title="Lyftr AI Backend")

@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse(status_code=307, headers={"Location": "/docs"}, content=None)

@app.on_event("startup")
async def on_startup():
    if not settings.webhook_secret:
        logger.critical("WEBHOOK_SECRET is not set! Application cannot start properly.")
        # In a real scenario, we might want to exit here, but for readiness check behavior we keep running.
    await init_db()

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    # Record metrics
    path = request.url.path
    # Simplify path for metrics to avoid high cardinality (e.g., removing query params is auto, but path params need care)
    # For this assignment, paths are static enough.
    
    REQUEST_LATENCY.observe(process_time)
    HTTP_REQUESTS_TOTAL.labels(path=path, status=response.status_code).inc()
    
    # Structured Logging
    # We add extra fields to the logger adapter or just pass them in extra
    logger.info(
        "Request processed",
        extra={
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "latency_ms": round(process_time, 2),
            "request_id": request.headers.get("x-request-id", "-") # Assuming a proxy might add it or we leave it empty
        }
    )
    
    return response

async def verify_signature(request: Request, settings: Settings = Depends(get_settings)):
    signature = request.headers.get("X-Signature")
    if not signature:
        logger.error("Missing X-Signature header")
        raise HTTPException(status_code=401, detail="invalid signature")
    
    if not settings.webhook_secret:
        # Should catch this in readiness, but safe guard here
        logger.error("WEBHOOK_SECRET missing in config")
        raise HTTPException(status_code=503, detail="Server misconfigured")

    body = await request.body()
    
    expected_signature = hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        logger.error("Invalid signature")
        raise HTTPException(status_code=401, detail="invalid signature")

@app.post("/webhook")
async def webhook(
    payload: WebhookPayload,
    request: Request, # for logger context if needed
    db_session = Depends(get_db),
    _ = Depends(verify_signature)
):
    storage = Storage(db_session)
    
    # Check if message exists (Idempotency)
    existing_message = await storage.get_message(payload.message_id)
    if existing_message:
        logger.info(
            "Duplicate webhook received",
            extra={
                "message_id": payload.message_id,
                "dup": True,
                "result": "duplicate"
            }
        )
        WEBHOOK_REQUESTS_TOTAL.labels(result="duplicate").inc()
        return {"status": "ok"}
    
    try:
        await storage.create_message(payload)
        logger.info(
            "Webhook message processed",
            extra={
                "message_id": payload.message_id,
                "dup": False,
                "result": "created"
            }
        )
        WEBHOOK_REQUESTS_TOTAL.labels(result="created").inc()
        return {"status": "ok"}
    except IntegrityError:
        # distinct possibility of race condition
        await db_session.rollback()
        logger.warning(
            "Race condition detected on webhook insert",
            extra={
                "message_id": payload.message_id,
                "dup": True,
                "result": "duplicate"
            }
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/messages", response_model=MessageListResponse)
async def get_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_: Optional[str] = Query(None, alias="from"),
    since: Optional[datetime] = None,
    q: Optional[str] = None,
    db_session = Depends(get_db)
):
    storage = Storage(db_session)
    # Convert since/from to string if needed by storage or pass date object
    # Pydantic handles 'since' query param parsing to datetime
    
    messages, total = await storage.get_messages(limit, offset, from_, since, q)
    
    # Map SQLAlchemy objects to Pydantic models
    data = [
        MessageResponse(
            message_id=m.message_id,
            from_=m.from_msisdn,
            to=m.to_msisddn,
            ts=m.ts,
            text=m.text
        ) for m in messages
    ]
    
    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/stats", response_model=StatsResponse)
async def get_stats(db_session = Depends(get_db)):
    storage = Storage(db_session)
    return await storage.get_stats()

@app.get("/health/live")
async def health_live():
    return {"status": "ok"}

@app.get("/health/ready")
async def health_ready(db_session = Depends(get_db), settings: Settings = Depends(get_settings)):
    if not settings.webhook_secret:
        raise HTTPException(status_code=503, detail="Config missing")
    
    try:
        # Test DB connection
        await db_session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")

    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
