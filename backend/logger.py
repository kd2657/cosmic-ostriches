import os
import json
import time
import asyncio
from datetime import datetime
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "backend_requests.log")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Thread pool for asynchronous, non-blocking I/O writing
_log_executor = ThreadPoolExecutor(max_workers=1)

def _write_log(entry: dict):
    """Writes a single JSON line to the log file."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        # Failsafe: if logging fails, do not crash the app, just print
        print(f"Failed to write log entry: {e}")

def log_request(func):
    """
    Decorator for FastAPI endpoints to log requests non-intrusively.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        status = "success"
        error_msg = None
        
        req_obj = kwargs.get("req") or (args[0] if args else None)
        query = getattr(req_obj, "query", None) if req_obj else None
        projection = getattr(req_obj, "dim_reduction", None) if req_obj else None
        clustering = getattr(req_obj, "algorithm", None) if req_obj else None
        groups = getattr(req_obj, "k", None) if req_obj else None
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = "failure"
            error_msg = str(e)
            raise
        finally:
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            log_entry = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "query": query,
                "projection": projection,
                "clustering": clustering,
                "groups": groups,
                "status": status,
                "response_time_ms": response_time_ms,
                "error": error_msg
            }
            _log_executor.submit(_write_log, log_entry)
            
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        status = "success"
        error_msg = None
        
        req_obj = kwargs.get("req") or (args[0] if args else None)
        query = getattr(req_obj, "query", None) if req_obj else None
        projection = getattr(req_obj, "dim_reduction", None) if req_obj else None
        clustering = getattr(req_obj, "algorithm", None) if req_obj else None
        groups = getattr(req_obj, "k", None) if req_obj else None
            
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            status = "failure"
            error_msg = str(e)
            raise
        finally:
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            log_entry = {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "query": query,
                "projection": projection,
                "clustering": clustering,
                "groups": groups,
                "status": status,
                "response_time_ms": response_time_ms,
                "error": error_msg
            }
            _log_executor.submit(_write_log, log_entry)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
