import time
import threading
from functools import wraps
from flask import request, jsonify, make_response, render_template

_LOCK = threading.Lock()
_HITS = {}  # key -> list of timestamps


def rate_limit(limit: int = 15, window_seconds: int = 60, by_ip: bool = True, key_func=None):
    """
    Thread-safe in-memory sliding-window rate limiter decorator for Flask.
    Protects against brute force and DDoS on authentication & transaction APIs.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            now = time.time()
            ident_parts = [f.__name__]
            if by_ip:
                # Use X-Forwarded-For if behind proxy/CDN, otherwise remote_addr
                forwarded = request.headers.get("X-Forwarded-For")
                ip = forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "127.0.0.1")
                ident_parts.append(ip)
            if key_func:
                try:
                    custom_key = str(key_func())
                    ident_parts.append(custom_key)
                except Exception:
                    pass

            key = ":".join(ident_parts)

            with _LOCK:
                # Clean expired hits
                timestamps = [t for t in _HITS.get(key, []) if now - t < window_seconds]
                if len(timestamps) >= limit:
                    retry_after = int(window_seconds - (now - timestamps[0])) + 1
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                        resp = jsonify({
                            "success": False,
                            "error": f"Too many requests. Please wait {retry_after} seconds.",
                            "retry_after": retry_after
                        })
                        resp.status_code = 429
                        resp.headers["Retry-After"] = str(retry_after)
                        return resp
                    else:
                        resp = make_response(
                            f"<h3>429 Too Many Requests</h3><p>Rate limit exceeded. Please try again in {retry_after} seconds.</p>",
                            429
                        )
                        resp.headers["Retry-After"] = str(retry_after)
                        return resp

                timestamps.append(now)
                _HITS[key] = timestamps

            return f(*args, **kwargs)
        return wrapper
    return decorator
