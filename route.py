import html
from urllib.parse import parse_qs
import secrets
import hmac
from sessions import get_session_data, set_session_data
from login_config import setup_logging


from auth import (
    get_logged_in_user,
    get_user_by_username,
    login_user,
    logout_user,
    verify_password,
)
from db import add_message, list_messages
from middleware import redir_if_logged_in, require_login, require_role
from sessions import del_session_data, get_session_data, rotate_session, set_session_data
logger = setup_logging()
EXTENSION = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".jpg": "image/jpeg",
}

def ensure_csrf_token(session_id):
    token = get_session_data(session_id, "csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        set_session_data(session_id, "csrf_token", token)
    return token

def refresh_csrf_token(session_id):
    token = secrets.token_urlsafe(32)
    set_session_data(session_id, "csrf_token", token)
    return token

def verify_csrf_token(session_id, form_data):
    sent_token  = form_data.get("csrf_token", [""])[0]
    stored_token = get_session_data(session_id, "csrf_token")
    return (
        stored_token is not None and
        hmac.compare_digest(sent_token, stored_token)
        )
        
def admin_handler(method, path, session_id=None, body=None):
    user = get_logged_in_user(session_id)
    if user is None:
        return {
            "status": 303,
            "headers": {"Content-Type": "text/html", "Location": "/login"},
            "body": "",
        }
    return {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": f"<h1>Admin Page</h1><p>Welcome, {html.escape(user['username'])}</p>",
    }


def login_route(method, path, session_id, body):
    if method == "GET":
        csrf_token = ensure_csrf_token(session_id)
        return {
            "status": 200,
            "headers": {"Content-Type": "text/html"},
            "body": (                                                                                                                             
                    "<form method='POST'>"                                                                                                            
                    f"<input type='hidden' name='csrf_token' value='{html.escape(csrf_token, quote=True)}'>"                                          
                    "Username: <input name='username' /><br>"                                                                                         
                    "Password: <input name='password' type='password' /><br>"                                                                         
                    "<button type='submit'>Login</button>"                                                                                            
                    "</form>"                                                                                                                         
            ),
        }
    elif method == "POST":
        form_data = parse_qs(body or "")
        if not verify_csrf_token(session_id, form_data):
            logger.warning("csrf_failed route=/login session_id=%s", session_id)
            return {
                "status": 403,
                "headers": {"Content-type": "text/html"},
                "body": "<h1>Forbidden</h1><p>Invalid CSRF Token</p>",
            }
        username = form_data.get("username", [""])[0]
        password = form_data.get("password", [""])[0]
        user = get_user_by_username(username)

        if user and verify_password(password, user["password_hash"]):
            new_session_id = rotate_session(session_id, 3600)
            login_user(new_session_id, user)
            logger.info("login_success username=%s", username)
            refresh_csrf_token(new_session_id)
            return {
                "status": 303,
                "headers": {"Content-Type": "text/html", "Location": "/"},
                "body": "",
                "session_id": new_session_id,
            }
        else:
            logger.warning("login_failed username=%s", username)
        return {
            "status": 401,
            "headers": {"Content-Type": "text/html"},
            "body": "Invalid credentials",
        }


def logout_route(method, path, session_id, body):
    logout_user(session_id)
    return {
        "status": 303,
        "headers": {"Content-type": "text/html", "Location": "/login"},
        "body": "",
    }


def extract_data_body(body, user_id):
    form_data = parse_qs(body or "")
    message = html.escape(form_data.get("message", [""])[0], quote=True)
    add_message(user_id, message)
    return message


def home_handler(method, path, session_id=None, body=None):
    user = get_logged_in_user(session_id)
    if user is None:
        return {
            "status": 303,
            "headers": {"Content-Type": "text/html", "Location": "/login"},
            "body": "",
        }
    csrf_token = ensure_csrf_token(session_id)
    with open("index.html", "r", encoding="utf-8") as f:
        page = f.read()

    saved_msg = load_messages()
    msg = get_session_data(session_id, "flash")
    del_session_data(session_id, "flash")
    flash_msg = f"<p>{html.escape(msg)}</p>" if msg else ""
    msg_html = f"<pre>{saved_msg}</pre>" if saved_msg else "<p>No messages yet</p>"
    page = page.replace(                                                                                                                  
      "<button type=\"submit\">Send</button>",                                                                                          
      f"<input type='hidden' name='csrf_token' value='{html.escape(csrf_token, quote=True)}'>"                                          
      "<button type=\"submit\">Send</button>"                                                                                           
  )        
    return {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": page,
    }


def about_handler(response, path, session_id=None, body=None):
    return {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<h1>About Page</h1>",
    }


def contact_handler(response, path, session_id=None, body=None):
    return {
        "status": 200,
        "headers": {"Content-Type": "text/html"},
        "body": "<h1>About Page</h1>",
    }


def not_found_handler(request):
    return {
        "status": 404,
        "headers": {"Content-Type": "text/html"},
        "body": "<h1>404 Not Found</h1>",
    }


def submit_handler(method, path, session_id=None, body=None):
    user = get_logged_in_user(session_id)
    if user is None:
        return {
            "status": 303,
            "headers": {"Content-Type": "text/html", "Location": "/login"},
            "body": "",
        }
    form_data = parse_qs(body or "")                                                                                                      
    if not verify_csrf_token(session_id, form_data):                                                                                      
        logger.warning("csrf_failed route=/submit session_id=%s", session_id)
        return {                                                                                                                          
          "status": 403,                                                                                                                
          "headers": {"Content-Type": "text/html"},                                                                                     
          "body": "<h1>Forbidden</h1><p>Invalid CSRF token</p>",                                                                        
        } 
    extract_data_body(body, user["id"])
    set_session_data(session_id, "flash", "Message sent")
    return {
        "status": 303,
        "headers": {"Content-Type": "text/html", "Location": "/"},
        "body": "",
    }


def messages_handler(method, path, session_id=None, body=None):
    user = get_logged_in_user(session_id)
    if user is None:
        return {
            "status": 303,
            "headers": {"Content-type": "text/html", "Location": "/login"},
            "body": "",
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
        ),
    }


def load_messages():
    rows = list_messages()
    return "\n".join(f"{row['username']}: {row['content']}" for row in rows)


routes = {
    "/": "index.html",
    "/about": "about.html",
    "/contact": "contacts.html",
}

method_routes = {
    ("POST", "/about"): about_handler,
    ("POST", "/contacts"): contact_handler,
    ("POST", "/submit"): submit_handler,
    ("GET", "/logout"): logout_route,
    ("GET", "/"): require_login(home_handler),
    ("GET", "/login"): redir_if_logged_in(login_route),
    ("POST", "/login"): redir_if_logged_in(login_route),
    ("GET", "/messages"): require_login(messages_handler),
    ("GET", "/admin"): require_role("admin")(admin_handler),
}
