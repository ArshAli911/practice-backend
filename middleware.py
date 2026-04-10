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
def req_role(role):
     def decorator(handler):
          def wrapped(method, path, session_id = None, body = None):
               user = get_logged_in_user(session_id)
               if user is None:
                    return {
                         "status": 303,
                         "headers": {"Content-type": "text/html"},
                         "body": "<h1>Forbidden</h1>"
                    }
               if user[ role] != role:
                    return {                                                                                        
                      "status": 403,                                                                              
                      "headers": {"Content-Type": "text/html"},                                                   
                      "body": "<h1>Forbidden</h1>"                                                                
                  }                                                                                               
                                                                                                                  
               return handler(method, path, session_id, body)                                                      
          return wrapped                                                                                          
     return decorator     
def redir_if_logged_in(handler):
     def wrapped(method, path, session_id=None, body=None):
          user = get_logged_in_user(session_id)
          if user is not None:
               return {
                    "status": 303,
                    "headers": {"Content-Type": "text/html", "Location": "/"},
                    "body": ""
               }
          return handler(method,path,session_id,body)
     return wrapped
