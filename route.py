import html
from urllib.parse import parse_qs
import secrets
import hmac
from sessions import get_session_data, set_session_data
from login_config import setup_logging
from config import (
    LOGIN_LOCKOUT_LIMIT,
    LOGIN_LOCKOUT_SECONDS,
    LOGIN_LOCKOUT_WINDOW_SECONDS,
    SESSION_TTL_SECONDS,
    MAX_FORM_FIELDS,
    MAX_MESSAGE_CHARS,
    MAX_PASSWORD_CHARS,
    MAX_QUERY_PAGE,
    MAX_USERNAME_CHARS,
)

from auth import (
    get_logged_in_user,
    get_user_by_username,
    hash_password,
    login_user,
    logout_user,
    verify_password,
)
from db import add_message, count_messages, create_user_db, list_messages
from middleware import redir_if_logged_in, require_login, require_role
from rate_limit import clear_login_attempts, login_locked, record_failed_login
from responses import error_response, html_response, redirect, validation_response
from sessions import del_session_data, get_session_data, rotate_session, set_session_data
logger = setup_logging()


class ValidationError(Exception):
    pass


def parse_form(body):
    try:
        return parse_qs(
            body or "",
            keep_blank_values=True,
            max_num_fields=MAX_FORM_FIELDS,
        )
    except ValueError:
        raise ValidationError("Too many form fields")


def require_text(form_data, field, max_chars):
    value = form_data.get(field, [""])[0].strip()
    if not value:
        raise ValidationError(f"{field} is required")
    if len(value) > max_chars:
        raise ValidationError(f"{field} is too long")
    return value


def normalize_username(username):
    return username.strip().casefold()


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
        
def admin_handler(method, path, session_id=None, body=None, query_params=None):
    user = get_logged_in_user(session_id)
    return html_response(
        200,
        f"<h1>Admin Page</h1><p>Welcome, {html.escape(user['username'])}</p>",
    )


def login_route(method, path, session_id, body, query_params=None):
    if method == "GET":
        csrf_token = ensure_csrf_token(session_id)
        return html_response(
            200,
            (
                "<form method='POST'>"
                f"<input type='hidden' name='csrf_token' value='{html.escape(csrf_token, quote=True)}'>"
                "Username: <input name='username' /><br>"
                "Password: <input name='password' type='password' /><br>"
                "<button type='submit'>Login</button>"
                "</form>"
                "<p><a href='/signup'>Create an account</a></p>"
            ),
        )
    elif method == "POST":
        try:
            form_data = parse_form(body)
        except ValidationError as exc:
            return validation_response(str(exc), status=413)

        if not verify_csrf_token(session_id, form_data):
            logger.warning("csrf_failed route=/login session_id=%s", session_id)
            return error_response(403, "Invalid CSRF Token")
        try:
            username = normalize_username(require_text(form_data, "username", MAX_USERNAME_CHARS))
            password = require_text(form_data, "password", MAX_PASSWORD_CHARS)
        except ValidationError as exc:
            return validation_response(str(exc))

        lockout_key = f"account:{username}"
        locked, seconds_left = login_locked(lockout_key)
        if locked:
            logger.warning("login_locked username=%s seconds_left=%s", username, seconds_left)
            return error_response(429, "Too many login attempts. Try again later.")

        user = get_user_by_username(username)

        if user and verify_password(password, user["password_hash"]):
            new_session_id = rotate_session(session_id, SESSION_TTL_SECONDS)
            login_user(new_session_id, user)
            clear_login_attempts(lockout_key)
            logger.info("login_success username=%s", username)
            refresh_csrf_token(new_session_id)
            response = redirect("/")
            response["session_id"] = new_session_id
            return response
        else:
            logger.warning("login_failed username=%s", username)
            locked = record_failed_login(
                lockout_key,
                LOGIN_LOCKOUT_LIMIT,
                LOGIN_LOCKOUT_WINDOW_SECONDS,
                LOGIN_LOCKOUT_SECONDS,
            )
            if locked:
                return error_response(429, "Too many login attempts. Try again later.")
        return error_response(401, "Invalid credentials")


def signup_route(method, path, session_id, body, query_params=None):
    if method == "GET":
        csrf_token = ensure_csrf_token(session_id)
        return html_response(
            200,
            (
                "<h1>Signup</h1>"
                "<form method='POST'>"
                f"<input type='hidden' name='csrf_token' value='{html.escape(csrf_token, quote=True)}'>"
                "Username: <input name='username' /><br>"
                "Password: <input name='password' type='password' /><br>"
                "<button type='submit'>Signup</button>"
                "</form>"
                "<p><a href='/login'>Login</a></p>"
            ),
        )

    try:
        form_data = parse_form(body)
    except ValidationError as exc:
        return validation_response(str(exc), status=413)

    if not verify_csrf_token(session_id, form_data):
        logger.warning("csrf_failed route=/signup session_id=%s", session_id)
        return error_response(403, "Invalid CSRF Token")

    try:
        username = normalize_username(require_text(form_data, "username", MAX_USERNAME_CHARS))
        password = require_text(form_data, "password", MAX_PASSWORD_CHARS)
    except ValidationError as exc:
        return validation_response(str(exc))

    if create_user_db(username, hash_password(password)) is None:
        return validation_response("username already exists", status=400)

    user = get_user_by_username(username)
    new_session_id = rotate_session(session_id, SESSION_TTL_SECONDS)
    login_user(new_session_id, user)
    refresh_csrf_token(new_session_id)
    logger.info("signup_success username=%s", username)

    response = redirect("/")
    response["session_id"] = new_session_id
    return response


def logout_route(method, path, session_id, body, query_params=None):
    logout_user(session_id)
    return redirect("/login")


def extract_data_body(body, user_id):
    form_data = parse_form(body)
    message = html.escape(require_text(form_data, "message", MAX_MESSAGE_CHARS), quote=True)
    add_message(user_id, message)
    return message


def home_handler(method, path, session_id=None, body=None, query_params=None):
    user = get_logged_in_user(session_id)
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
    return html_response(200, page)


def about_handler(response, path, session_id=None, body=None, query_params=None):
    return html_response(200, "<h1>About Page</h1>")


def contact_handler(response, path, session_id=None, body=None, query_params=None):
    return html_response(200, "<h1>Contact Page</h1>")


def not_found_handler(request):
    return error_response(404, "Not Found")


def submit_handler(method, path, session_id=None, body=None, query_params=None):
    user = get_logged_in_user(session_id)
    try:
        form_data = parse_form(body)
    except ValidationError as exc:
        return validation_response(str(exc), status=413)

    if not verify_csrf_token(session_id, form_data):                                                                                      
        logger.warning("csrf_failed route=/submit session_id=%s", session_id)
        return error_response(403, "Invalid CSRF token")
    try:
        message = html.escape(require_text(form_data, "message", MAX_MESSAGE_CHARS), quote=True)
    except ValidationError as exc:
        return validation_response(str(exc))

    add_message(user["id"], message)
    set_session_data(session_id, "flash", "Message sent")
    return redirect("/")


def messages_handler(method, path, session_id=None, body=None, query_params=None):
    user = get_logged_in_user(session_id)

    query_params = query_params or {}
    try:
         page = int(query_params.get("page", ["1"])[0])
    except (ValueError, TypeError):
         page = 1

    if page < 1:
         page = 1
    if page > MAX_QUERY_PAGE:
         page = MAX_QUERY_PAGE

    per_page = 10
    offset = (page - 1) * per_page
    total_messages = count_messages()
    rows = list_messages(limit=per_page, offset=offset)
    saved_messages = format_messages(rows)
    msg = get_session_data(session_id, "flash")
    del_session_data(session_id, "flash")

    flash_html = f"<p>{html.escape(msg)}</p>" if msg else ""
    messages_html = f"<pre>{saved_messages}</pre>" if saved_messages else "<p>No messages yet.</p>"
    prev_link = f"<a href='/messages?page={page - 1}'>Previous</a>" if page > 1 else ""
    next_link = f"<a href='/messages?page={page + 1}'>Next</a>" if offset + per_page < total_messages else ""

    return html_response(
        200,
        (
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
            f"<p>{prev_link} {next_link}</p>"
            "<p><a href='/'>Back to home</a></p>"
            "</body>"
            "</html>"
        ),
    )


def health_handler(method, path, session_id=None, body=None, query_params=None):
    return html_response(200, "ok")


def load_messages():
    rows = list_messages()
    return format_messages(rows)


def format_messages(rows):
    return "\n".join(f"{row['username']}: {row['content']}" for row in rows)


routes = {
    "/": "index.html",
    "/about": "about.html",
    "/contact": "contacts.html",
}

method_routes = {
    ("POST", "/about"): about_handler,
    ("POST", "/contacts"): contact_handler,
    ("POST", "/submit"): require_login(submit_handler),
    ("GET", "/logout"): require_login(logout_route),
    ("GET", "/"): require_login(home_handler),
    ("GET", "/login"): redir_if_logged_in(login_route),
    ("POST", "/login"): redir_if_logged_in(login_route),
    ("GET", "/signup"): redir_if_logged_in(signup_route),
    ("POST", "/signup"): redir_if_logged_in(signup_route),
    ("GET", "/messages"): require_login(messages_handler),
    ("GET", "/admin"): require_role("admin")(admin_handler),
    ("GET", "/health"): health_handler,
}
