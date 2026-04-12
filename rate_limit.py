import threading
import time

rate_limits = {}
lockouts = {}
_rate_limit_lock = threading.Lock()

def rate_limited(key, limit, window_seconds):
    now = time.time()
    window_start = now - window_seconds
    with _rate_limit_lock:
        timestamp = rate_limits.get(key, [])
        timestamp = [ts for ts in timestamp if ts >= window_start]

        if len(timestamp) >= limit:
            rate_limits[key] = timestamp
            return True

        timestamp.append(now)
        rate_limits[key] = timestamp
        return False


def login_locked(key):
    now = time.time()
    with _rate_limit_lock:
        locked_until = lockouts.get(key)
        if locked_until is None:
            return False, 0
        if locked_until <= now:
            lockouts.pop(key, None)
            rate_limits.pop(key, None)
            return False, 0
        return True, int(locked_until - now)


def record_failed_login(key, limit, window_seconds, lockout_seconds):
    now = time.time()
    window_start = now - window_seconds
    with _rate_limit_lock:
        timestamp = rate_limits.get(key, [])
        timestamp = [ts for ts in timestamp if ts >= window_start]
        timestamp.append(now)

        if len(timestamp) >= limit:
            lockouts[key] = now + lockout_seconds
            rate_limits[key] = timestamp
            return True

        rate_limits[key] = timestamp
        return False


def clear_login_attempts(key):
    with _rate_limit_lock:
        rate_limits.pop(key, None)
        lockouts.pop(key, None)

