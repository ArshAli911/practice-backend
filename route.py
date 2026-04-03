import html
from urllib.parse import parse_qs
from sessions import get_session_data, del_session_data,set_session_data
from auth import login_user, get_user_by_username, verify_password, get_logged_in_user, USERS, logout_user
EXTENSION = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".jpg": "image/jpeg"
    }

def login_route(method, path, session_id, body):
    if method == "GET":
        return {
            "status": 200,
            "headers": {"Content-Type": "text/html"},
            "body": "<form method='POST'>Username: <input name='username' /><br>Password: <input name='password' type='password' /><br><button type='submit'>Login</button></form>"
        }
    elif method == "POST":
        form_data = parse_qs(body or "")
        username = form_data.get("username", [""])[0]
        password = form_data.get("password", [""])[0]
        user = get_user_by_username(username)

        if user and verify_password(password, user["password_hash"]):
            login_user(session_id, user)
            return {
                "status": 303,
                "headers": {"Content-Type": "text/html", "Location": "/"},
                "body": ""
            }

        return {
            "status": 401,
            "headers": {"Content-Type": "text/html"},
            "body": "Invalid credentials"
        }
def logout_route(method, path, session_id, body):
    logout_user(session_id)
    return{
        "status": 303,
        "headers": {"Content-type": "text/html", "Location": "/login"},
        "body": ""
   }
def extract_data_body(body):
    form_data = parse_qs(body or "")
    username = html.escape(form_data.get("username", ["Guest"])[0], quote=True)
    message = html.escape(form_data.get("message", [""])[0], quote=True)
    with open("messages.txt", "a", encoding="utf-8") as f:
        f.write(f"{username}: {message}\n")
    return username, message

def home_handler(method, path, session_id=None, body=None):
    user = get_logged_in_user(session_id)
    if user is None:
        return {
        "status": 303,
        "headers": {"Content-Type": "text/html", "Location": "/login"},
        "body": ""
    }
    with open("index.html", "r", encoding="utf-8") as f:
        page = f.read()
    saved_msg = load_messages()
    msg = get_session_data(session_id,"flash")
    del_session_data(session_id, "flash")
    flash_msg = f"<p>{(html.escape(msg))}</p>" if msg else ""
    msg_html = f"<pre>{(saved_msg)}</pre>" if saved_msg else "<p>No messages yet</p>"
    page = page.replace(
        "</body>",                                                                                                    
        (                                                                                                             
            "<h2>Messages</h2>"                                                                                       
            f"{flash_msg}"                                                                                           
            f"{msg_html}"                                                                                        
            "<p><a href='/logout'>Logout</a></p>"                                                                     
            "</body>"                                                                                                 
        )                                                                                                             
    )                                                                                            
                                                                                                                     
                                                                                                                        
    return {                                                                                                          
          "status": 200,                                                                                                
          "headers": {"Content-Type": "text/html"},                                                                     
          "body": page                                                                                                  
      }                                                                                                                 
          
def about_handler(response, path,session_id= None, body=None):
    return {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<h1>About Page</h1>"
    }
def contact_handler(response, path,session_id= None, body=None):
    return {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<h1>About Page</h1>"
    }
def not_found_handler(request):
    return {
        "status": 404,
        "headers": {"Content-Type": "text/html"},
        "body": "<h1>404 Not Found</h1>"
    }

def submit_handler(method, path,session_id= None, body=None):
    extract_data_body(body)
    set_session_data(session_id, "flash", "Message sent")
    return {
        "status": 303,
        "headers": {"Content-Type": "text/html", "Location": "/"},
        "body": ""
    }


def messages_handler(method, path,session_id= None, body=None):
    user  = get_logged_in_user(session_id)
    if user is None:
        return {
        "status": 303,
        "headers": {"Content-type": "text/html", "Location": "/login"},
        "body": ""
    }
    saved_messages = load_messages()
    msg = get_session_data(session_id, "flash")
    del_session_data(session_id, "flash")

    flash_html = f"<p>{html.escape(msg)}</p>" if msg else ""
    messages_html = f"<pre>{saved_messages}</pre>" if saved_messages else "<p>No messages yet.</p>"

    return {
          "status": 200,
          "headers": {"Content-Type": "text/html"},
          "body": (
              "<!doctype html>"
              "<html lang='en'>"
              "<head>"
              "<meta charset='utf-8'>"
              "<meta name='viewport' content='width=device-width,initial-scale=1'>"
              "<title>Messages</title>"
              "</head>"
              "<body>"
              "<h1>Messages</h1>"
              f"{flash_html}"
              f"{messages_html}"
              "<p><a href='/'>Back to home</a></p>"
              "</body>"
              "</html>"
          )
      }
def load_messages():
    try:
        with open("messages.txt", "r", encoding = "utf-8") as f:
            return html.escape(f.read(), quote=True)
    except FileNotFoundError:
        return ""

routes = {
        "/": "index.html",
        "/about": "about.html",
        "/contact": "contacts.html"
    }
method_routes = {
        ("GET","/"): home_handler,
        ("GET", "/login"): login_route,
        ("POST", "/login"): login_route,
        ("POST","/about"): about_handler,
        ("POST","/contacts"): contact_handler,
        ("POST","/submit"): submit_handler,
        ("GET", "/messages"): messages_handler,
        ("GET", "/logout"): logout_route,
    }
