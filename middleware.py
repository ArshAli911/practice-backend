from auth import get_logged_in_user
from login_config import setup_logging


logger = setup_logging()
def require_login(handler):
    def wrapped(method, path, session_id=None, body=None):
        user = get_logged_in_user(session_id)
        if user is None:
            return {
                "status": 303,
                "headers": {"Content-Type": "text/html", "Location": "/login"},
                "body": "",
            }
        return handler(method, path, session_id, body)
    return wrapped


def require_role(role):
    def decorator(handler):
        def wrapped(method, path, session_id=None, body=None):
            user = get_logged_in_user(session_id)
            if user is None:
                return {
                    "status": 303,
                    "headers": {"Content-Type": "text/html", "Location": "/login"},
                    "body": "",
                }
            if user["role"] != role:
                logger.warning("forbidden role_required=%s user_id=%s", role, user["id"])
                return {
                    "status": 403,
                    "headers": {"Content-Type": "text/html"},
                    "body": "<h1>Forbidden</h1>",
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
                "body": "",
            }
        return handler(method, path, session_id, body)

    return wrapped
