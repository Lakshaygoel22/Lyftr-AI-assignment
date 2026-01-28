import logging
import sys
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_record["method"] = record.method
        if hasattr(record, "path"):
            log_record["path"] = record.path
        if hasattr(record, "status"):
            log_record["status"] = record.status
        if hasattr(record, "latency_ms"):
            log_record["latency_ms"] = record.latency_ms
        if hasattr(record, "message_id"):
            log_record["message_id"] = record.message_id
        if hasattr(record, "dup"):
            log_record["dup"] = record.dup
        if hasattr(record, "result"):
            log_record["result"] = record.result
            
        return json.dumps(log_record)

def setup_logging(log_level: str):
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    
    # Suppress uvicorn access logs to avoid duplicates if we middleware log
    logging.getLogger("uvicorn.access").disabled = True
