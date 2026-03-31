import time
import uuid

session ={}

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
    session_id = str(uuid.uuid4())
    session[session_id] = {
        "data": {},
        "expires_at": time.time() + ttl_seconds,
    }
    return session_id

def get_session(session_id):
    if _is_expired(session_id):
        return None
    return session[session_id]["data"]

def set_session_data(session_id , key , val):
    if _is_expired(session_id):
        return
    session[session_id]["data"][key] = val
    
def get_session_data(session_id, key):
    if _is_expired(session_id):
        return None
    return session[session_id]["data"].get(key)

def del_session_data(session_id,key):
    if _is_expired(session_id):
        return

    sess = session[session_id]["data"]
    if key in sess:
        del sess[key]
