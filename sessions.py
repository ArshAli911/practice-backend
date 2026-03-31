import uuid

session ={}

def create_sessions():
    # Keep session data on the server and expose only the generated id to the client.
    session_id = str(uuid.uuid4())
    session[session_id] = {}
    return session_id

def get_session(session_id):
    return  session.get(session_id)

def set_session_data(session_id , key , val):
    if session_id in session:
        session[session_id][key] = val
    
def get_session_data(session_id, key):
    return session.get(session_id, {}).get(key)

def del_session_data(session_id,key):
    if session_id in session and key in session:
        del session[session_id][key]
