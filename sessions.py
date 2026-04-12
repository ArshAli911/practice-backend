import threading
import time
import secrets

session = {}
_session_lock = threading.RLock()

def _is_expired(session_id):
    record = session.get(session_id)
    if record is None:
        return True

    if record["expires_at"] <= time.time():
        del session[session_id]
        return True

    return False

def create_sessions(ttl_seconds):
    # Keep session data on the server and expose only the generated id to the client.
    session_id = secrets.token_urlsafe(32)
    with _session_lock:
        session[session_id] = {
            "data": {},
            "expires_at": time.time() + ttl_seconds,
        }
        return session_id

def get_session(session_id):
    with _session_lock:
        if _is_expired(session_id):
            return None
        return session[session_id]["data"]

def set_session_data(session_id , key , val):
    with _session_lock:
        if _is_expired(session_id):
            return
        session[session_id]["data"][key] = val
    
def get_session_data(session_id, key):
    with _session_lock:
        if _is_expired(session_id):
            return None
        return session[session_id]["data"].get(key)

def del_session_data(session_id,key):
    with _session_lock:
        if _is_expired(session_id):
            return

        sess = session[session_id]["data"]
        if key in sess:
            del sess[key]
def delete_session(session_id):
    with _session_lock:
        session.pop(session_id, None)

def rotate_session(session_id, ttl_s):
    with _session_lock:
        old_data = {}
        if not _is_expired(session_id):
            old_data = session[session_id]["data"].copy()
            session.pop(session_id, None)

        new_session_id = secrets.token_urlsafe(32)
        session[new_session_id] = {
            "data": old_data,
            "expires_at": time.time() + ttl_s,
        }
        return new_session_id


def cleanup_expired_sessions():
    now = time.time()
    with _session_lock:
        expired_ids = [
            session_id
            for session_id, record in session.items()
            if record["expires_at"] <= now
        ]
        for session_id in expired_ids:
            del session[session_id]
        return len(expired_ids)

