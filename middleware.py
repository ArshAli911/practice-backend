from auth import get_logged_in_user
from login_config import setup_logging
from responses import error_response, redirect

logger = setup_logging()
def require_login(handler):
    def wrapped(method, path, session_id=None, body=None, query_params=None):
        user = get_logged_in_user(session_id)
        if user is None:
            return redirect("/login")
        return handler(method, path, session_id, body, query_params)
    return wrapped


def require_role(role):
    def decorator(handler):
        def wrapped(method, path, session_id=None, body=None, query_params=None):
            user = get_logged_in_user(session_id)
            if user is None:
                return redirect("/login")
            if user["role"] != role:
                logger.warning("forbidden role_required=%s user_id=%s", role, user["id"])
                return error_response(403, "Forbidden")
            return handler(method, path, session_id, body, query_params)

        return wrapped

    return decorator


def redir_if_logged_in(handler):
    def wrapped(method, path, session_id=None, body=None, query_params=None):
        user = get_logged_in_user(session_id)
        if user is not None:
            return redirect("/")
        return handler(method, path, session_id, body, query_params)

    return wrapped
