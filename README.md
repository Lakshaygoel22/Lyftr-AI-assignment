# Backend Assignment - Lyftr AI

**Submitted by:** Lakshay Goel (lakshayworks22@gmail.com)

Here is my solution for the webhook ingestion service. I focused on building something that is clean, handles concurrency well, and is easy to run.

## Overview

The service listens for webhook events (like WhatsApp messages), verifies them, and stores them in a database. I used **FastAPI** because of its async support, which is perfect for this kind of I/O-heavy workload.

Top features:
*   **Async/Await:** Everything from the API handlers to the database queries is async to keep the main thread free.
*   **Signature Verification:** Added a middleware to validate the `X-Signature` header so we don't process garbage requests.
*   **Idempotency:** I'm checking msg IDs before inserting to handle duplicate webhooks (which happens a lot in real life).
*   **Dockerized:** Just run `make up` and it works.

## Tech Choices

*   **FastAPI & Python 3.11** - Fast and modern.
*   **SQLite (aiosqlite)** - It's simple for a standalone assignment. switching to Postgres is just a config change away.
*   **Pydantic** - For validating the incoming JSON payloads.
*   **Prometheus** - I added some basic metrics (`/metrics`) to track how many requests we're getting.

## How to Run

1.  **Start it up:**
    ```bash
    make up
    ```
    This spins up the container. API will be at `http://localhost:8000`.

2.  **Check logs:**
    ```bash
    make logs
    ```

3.  **Run Tests:**
    I wrote some tests to cover the main logic (signature checks, DB storage).
    ```bash
    make test
    ```

4.  **Stop:**
    ```bash
    make down
    ```

## API Endpoints

*   `POST /webhook` - Send messages here. Needs the correct signature.
*   `GET /messages` - See what's been saved.
*   `GET /stats` - Simple count of messages.
*   `GET /health/live` & `/health/ready` - Standard health checks.

## Notes

- The default webhook secret is set in the `docker-compose.yml`. In a real prod env, I'd inject this via a secure store.
- I've included a `demo_client.py` script if you want to test sending a signed request manually.
