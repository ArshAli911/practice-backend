import hashlib, hmac, json
USERS = []


def verify_password(password: str, pass_hash: str)-> bool:
    cal_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
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


def login_user(session, user):
    session["user_id"] = user["id"]

def logout_user(session):
    session.pop("user_id", None)
    
def auth_middleware(request, next_handler):
    session = request.get("session", {})
    if "user_id" not in session:
        return {
            "status": 401,
            "headers": {"Content-Type": "text/html"},
            "body": "<h1>Unauthorized</h1>"
        }
    return next_handler(request)