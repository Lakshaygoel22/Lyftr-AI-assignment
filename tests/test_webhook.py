import pytest
import hmac
import hashlib
import json
from datetime import datetime

WEBHOOK_SECRET = "testsecret"

def generate_signature(body: dict):
    body_bytes = json.dumps(body).encode()
    return hmac.new(WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()

@pytest.mark.asyncio
async def test_webhook_success(client):
    payload = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    signature = generate_signature(payload)
    
    response = await client.post("/webhook", json=payload, headers={"X-Signature": signature})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    payload = {
        "message_id": "m2",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    
    response = await client.post("/webhook", json=payload, headers={"X-Signature": "invalid"})
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid signature"}

@pytest.mark.asyncio
async def test_webhook_missing_signature(client):
    payload = {
        "message_id": "m3",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    
    response = await client.post("/webhook", json=payload)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_webhook_idempotency(client):
    payload = {
        "message_id": "m4",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "First"
    }
    signature = generate_signature(payload)
    
    # First call
    response = await client.post("/webhook", json=payload, headers={"X-Signature": signature})
    assert response.status_code == 200
    
    # Second call
    response = await client.post("/webhook", json=payload, headers={"X-Signature": signature})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_webhook_validation_error(client):
    payload = {
        "message_id": "", # Invalid
        "from": "invalid",
        "to": "+14155550100",
        "ts": "invalid-date",
    }
    signature = generate_signature(payload) # Signature will be valid for the payload, but payload is bad
    
    response = await client.post("/webhook", json=payload, headers={"X-Signature": signature})
    assert response.status_code == 422
