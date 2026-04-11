import time
from login_config import setup_logging
rate_limits = {}

def rate_limited(key, limit, window_seconds):
    now = time.time()
    window_start = now - window_seconds
    timestamp = rate_limits.get(key, [])
    timestamp = [ts for ts in timestamp if ts>= window_start]

    if len(timestamp) >= limit:
        rate_limits[key] = timestamp
        return True
    
    timestamp.append(now)
    rate_limits[key] = timestamp
    return False

