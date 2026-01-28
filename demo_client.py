import httpx
import hmac
import hashlib
import json
import time

BASE_URL = "http://127.0.0.1:8000"
WEBHOOK_SECRET = "testsecret"

def generate_signature(body: dict):
    body_bytes = json.dumps(body).encode()
    return hmac.new(WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()

def check_health():
    print("\n--- Checking Health ---")
    try:
        with httpx.Client(base_url=BASE_URL) as client:
            resp = client.get("/health/live")
            print(f"Liveness: {resp.status_code} {resp.json()}")
            resp = client.get("/health/ready")
            print(f"Readiness: {resp.status_code} {resp.json()}")
    except Exception as e:
        print(f"Failed to connect: {e}")

def send_webhook():
    print("\n--- Sending Webhook ---")
    payload = {
        "message_id": f"msg_{int(time.time())}",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello from the demo script!"
    }
    signature = generate_signature(payload)
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature
    }
    
    print(f"Payload: {payload}")
    print(f"Signature: {signature}")
    
    with httpx.Client(base_url=BASE_URL) as client:
        resp = client.post("/webhook", json=payload, headers=headers)
        print(f"Response: {resp.status_code} {resp.json()}")

def get_messages():
    print("\n--- Fetching Messages ---")
    with httpx.Client(base_url=BASE_URL) as client:
        resp = client.get("/messages")
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

def get_stats():
    print("\n--- Fetching Stats ---")
    with httpx.Client(base_url=BASE_URL) as client:
        resp = client.get("/stats")
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    check_health()
    send_webhook()
    time.sleep(1)
    get_messages()
    get_stats()
