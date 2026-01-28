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
async def test_get_messages_pagination_filtering(client):
    # Seed data
    messages = [
        {"message_id": "msg1", "from": "+111", "to": "+999", "ts": "2024-01-01T10:00:00Z", "text": "Alpha"},
        {"message_id": "msg2", "from": "+222", "to": "+999", "ts": "2024-01-02T10:00:00Z", "text": "Beta"},
        {"message_id": "msg3", "from": "+111", "to": "+999", "ts": "2024-01-03T10:00:00Z", "text": "Charlie"},
    ]
    
    for m in messages:
        sig = generate_signature(m)
        await client.post("/webhook", json=m, headers={"X-Signature": sig})

    # Test List All
    resp = await client.get("/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["data"]) == 3

    # Test Filter by From
    resp = await client.get("/messages", params={"from": "+111"})
    data = resp.json()
    assert data["total"] == 2
    assert len(data["data"]) == 2
    assert data["data"][0]["message_id"] == "msg1"

    # Test Search
    resp = await client.get("/messages", params={"q": "Beta"})
    data = resp.json()
    assert data["total"] == 1
    assert data["data"][0]["message_id"] == "msg2"

@pytest.mark.asyncio
async def test_stats(client):
    # Seed data
    messages = [
        {"message_id": "s1", "from": "+100", "to": "+999", "ts": "2024-01-01T10:00:00Z", "text": "A"},
        {"message_id": "s2", "from": "+100", "to": "+999", "ts": "2024-01-02T10:00:00Z", "text": "B"},
        {"message_id": "s3", "from": "+200", "to": "+999", "ts": "2024-01-03T10:00:00Z", "text": "C"},
    ]
    
    for m in messages:
        sig = generate_signature(m)
        await client.post("/webhook", json=m, headers={"X-Signature": sig})
        
    resp = await client.get("/stats")
    assert resp.status_code == 200
    stats = resp.json()
    
    assert stats["total_messages"] == 3
    assert stats["senders_count"] == 2
    
    top_sender = stats["messages_per_sender"][0]
    assert top_sender["from"] == "+100"
    assert top_sender["count"] == 2

@pytest.mark.asyncio
async def test_health_metrics(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    
    resp = await client.get("/health/ready")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text
