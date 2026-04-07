import hashlib
import hmac
import json
from db import get_user_by_username, get_user_by_id   
from sessions import del_session_data, get_session_data, set_session_data

def load_users():
    global USERS
    with open("user.json", "r", encoding="utf-8") as f:
        USERS = json.load(f)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, pass_hash: str)-> bool:
    cal_hash = hash_password(password)
    return hmac.compare_digest(cal_hash, pass_hash)

def get_user_by_username(username):                                                                                                       
      for user in USERS:                                                                                                                    
          if user["username"] == username:                                                                                                  
              return user                                                                                                                   
      return None                                                                                                                           
                                                                                                                                            
def get_user_by_id(user_id):                                                                                                              
      for user in USERS:                                                                                                                    
          if user["id"] == user_id:
              return user                                                                                                                   
      return None     

def get_logged_in_user(session_id):
    user_id = get_session_data(session_id, "user_id")
    if user_id is None:
        return None
    return get_user_by_id(user_id)

def login_user(session_id, user):
    set_session_data(session_id, "user_id", user["id"])

def logout_user(session_id):
    del_session_data(session_id, "user_id")
    
def auth_middleware(request, next_handler):
    session = request.get("session", {})
    if "user_id" not in session:
        return {
            "status": 401,
            "headers": {"Content-Type": "text/html"},
            "body": "<h1>Unauthorized</h1>"
        }
    return next_handler(request)
