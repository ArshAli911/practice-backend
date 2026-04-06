from auth import hash_password, verify_password, get_logged_in_user


def require_login(handler):
    def Wrapped(method, path, session_id = None, body=None):
        user = get_logged_in_user(session_id)
        if user is None:
              return {                                                                                                                                             
                  "status": 303,                                                                                                                                   
                  "headers": {"Content-Type": "text/html", "Location": "/login"},                                                                                  
                  "body": ""                                                                                                                                       
              }            
        return handler(method, path, session_id,body)
    return Wrapped

def redir_if_logged_in(handler):
     def wrapped(method, path, session_id=None, body=None):
          user = get_logged_in_user(session_id)
          if user is None:
               return {
                    "status": 303,
                    "headers": {"Content-Type": "text/html", "Location": "/"},
                    "body": ""
               }
          return handler(method,path,session_id,body)
     return wrapped
          