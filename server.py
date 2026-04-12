import os
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

from config import (
    GENERAL_RATE_LIMIT,
    GENERAL_RATE_WINDOW_SECONDS,
    HOST,
    LOGIN_RATE_LIMIT,
    LOGIN_RATE_WINDOW_SECONDS,
    MAX_BODY_BYTES,
    MAX_CONCURRENT_CONNECTIONS,
    MAX_FORM_FIELDS,
    MAX_HEADER_BYTES,
    PORT,
    RECV_CHUNK_SIZE,
    SESSION_CLEANUP_INTERVAL_SECONDS,
    SESSION_TTL_SECONDS,
    SOCKET_BACKLOG,
)
from db import init_db
from login_config import setup_logging
from rate_limit import rate_limited
from responses import STATUS_MESSAGES, error_response
from route import EXTENSION, method_routes
from sessions import cleanup_expired_sessions, create_sessions, get_session


class RequestParseError(Exception):
    pass


logger = setup_logging()


def build_http_response(resp):
    status_line = f"HTTP/1.1 {resp['status']} {STATUS_MESSAGES.get(resp['status'], '')}\r\n"

    headers = ""
    for k, v in resp["headers"].items():
        headers += f"{k}: {v}\r\n"

    return status_line + headers + "\r\n" + resp["body"]


def send_response(conn, resp):
    conn.sendall(build_http_response(resp).encode())


def parse_cookies(cookie_header):
    cookies = {}
    for item in cookie_header.split(";"):
        if "=" in item:
            key, val = item.strip().split("=", 1)
            cookies[key] = val
    return cookies


def build_session_cookie(session_id):
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)
    expires_text = expires_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return (
        f"session_id={session_id}; Path=/; Max-Age={SESSION_TTL_SECONDS}; "
        f"Expires={expires_text}; HttpOnly; SameSite=Lax"
    )


def read_http_request(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(RECV_CHUNK_SIZE)
        if not chunk:
            break
        data += chunk

        if len(data) > MAX_HEADER_BYTES:
            raise RequestParseError("headers_too_large")
    if b"\r\n\r\n" not in data:
        raise RequestParseError("incomplete_headers")

    header_bytes, _, body = data.partition(b"\r\n\r\n")
    header_text = header_bytes.decode("utf-8", errors="replace")
    header_lines = header_text.split("\r\n")

    headers = {}
    for line in header_lines[1:]:
        if not line:
            continue
        if ":" not in line:
            raise RequestParseError("bad_header")
        key, val = line.split(":", 1)
        headers[key.strip().lower()] = val.strip()

    content_length_text = headers.get("content-length", "0")
    if not content_length_text.isdigit():
        raise RequestParseError("bad_content_length")
    content_length = int(content_length_text)
    if content_length > MAX_BODY_BYTES:
        raise RequestParseError("body_too_large")

    while len(body) < content_length:
        chunk = conn.recv(RECV_CHUNK_SIZE)
        if not chunk:
            raise RequestParseError("incomplete_body")
        body += chunk

    return header_lines, headers, body[:content_length].decode("utf-8", errors="replace")


def validate_request_line(header_lines):
    if not header_lines or not header_lines[0]:
        raise RequestParseError("empty_request_line")

    parts = header_lines[0].split()
    if len(parts) != 3:
        raise RequestParseError("bad_request_line")

    method, path, version = parts
    if method not in {"GET", "POST"}:
        raise RequestParseError("method_not_allowed")
    if not path.startswith("/"):
        raise RequestParseError("bad_path")
    if len(path) > 2048:
        raise RequestParseError("url_too_long")
    if version not in {"HTTP/1.0", "HTTP/1.1"}:
        raise RequestParseError("bad_http_version")

    return method, path


def route_request(conn, method, path, headers, raw_body, session_id, new_session):
    body = raw_body or None
    if method != "POST":
        body = None

    route_path, _, query_string = path.partition("?")
    try:
        query_params = parse_qs(query_string, max_num_fields=MAX_FORM_FIELDS)
    except ValueError:
        send_response(conn, error_response(413, "Too many query parameters"))
        return

    path = route_path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    handler = method_routes.get((method, path))
    if handler:
        resp_dict = handler(method, path, session_id, body, query_params)
        rotated_session_id = resp_dict.pop("session_id", None)
        if rotated_session_id is not None:
            session_id = rotated_session_id
            resp_dict["headers"]["Set-Cookie"] = build_session_cookie(session_id)
        elif new_session:
            resp_dict["headers"]["Set-Cookie"] = build_session_cookie(session_id)
        send_response(conn, resp_dict)
        return

    serve_static_file(conn, path)


def serve_static_file(conn, path):
    file_name = "index.html" if path == "/" else path.lstrip("/")
    safe_path = os.path.normpath(file_name)
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        send_response(conn, error_response(403, "Forbidden"))
        return

    _, ext = os.path.splitext(safe_path)

    try:
        if ext in EXTENSION:
            with open(safe_path, "rb") as file:
                content = file.read()

            header = f"HTTP/1.1 200 OK\r\nContent-Type: {EXTENSION[ext]}\r\n\r\n"
            conn.sendall(header.encode() + content)
        else:
            with open(safe_path, "r", encoding="utf-8") as file:
                content = file.read()

            send_response(conn, {
                "status": 200,
                "headers": {"Content-Type": "text/html"},
                "body": content,
            })
    except FileNotFoundError:
        send_response(conn, error_response(404, "Not Found"))
    except Exception:
        logger.exception("static_file_error path=%s file=%s", path, safe_path)
        send_response(conn, error_response(500, "Internal Server Error"))


def handle_client(conn, addr):
    client_ip = addr[0]
    try:
        try:
            header_lines, headers, raw_body = read_http_request(conn)
            method, path = validate_request_line(header_lines)
        except RequestParseError as exc:
            reason = str(exc)
            if reason in {"headers_too_large", "body_too_large"}:
                send_response(conn, error_response(413, "Payload Too Large"))
            elif reason == "url_too_long":
                send_response(conn, error_response(414, "URI Too Long"))
            elif reason == "method_not_allowed":
                send_response(conn, error_response(405, "Method Not Allowed"))
            else:
                send_response(conn, error_response(400, "Bad Request"))
            logger.warning("bad_request ip=%s reason=%s", client_ip, exc)
            return

        general_key = f"general:{client_ip}"
        if rate_limited(general_key, GENERAL_RATE_LIMIT, GENERAL_RATE_WINDOW_SECONDS):
            send_response(conn, error_response(429, "Too Many Requests"))
            logger.warning("rate_limited ip=%s scope=general", client_ip)
            return

        if method == "POST" and path.partition("?")[0] == "/login":
            login_key = f"login:{client_ip}"
            if rate_limited(login_key, LOGIN_RATE_LIMIT, LOGIN_RATE_WINDOW_SECONDS):
                send_response(conn, error_response(429, "Too Many Login Attempts"))
                logger.warning("rate_limited ip=%s scope=login path=%s", client_ip, path)
                return

        cookies = parse_cookies(headers.get("cookie", ""))
        session_id = cookies.get("session_id")

        if not session_id or get_session(session_id) is None:
            session_id = create_sessions(SESSION_TTL_SECONDS)
            new_session = True
        else:
            new_session = False

        route_path = path.partition("?")[0]
        logger.info("request method=%s path=%s ip=%s", method, route_path, client_ip)

        try:
            route_request(conn, method, path, headers, raw_body, session_id, new_session)
        except Exception:
            logger.exception("handler_error method=%s path=%s ip=%s", method, path, client_ip)
            send_response(conn, error_response(500, "Internal Server Error"))
    finally:
        conn.close()


def session_cleanup_loop():
    while True:
        time.sleep(SESSION_CLEANUP_INTERVAL_SECONDS)
        removed = cleanup_expired_sessions()
        if removed:
            logger.info("session_cleanup removed=%s", removed)


def run_server():
    init_db()
    cleanup_thread = threading.Thread(target=session_cleanup_loop, daemon=True)
    cleanup_thread.start()

    connection_slots = threading.BoundedSemaphore(MAX_CONCURRENT_CONNECTIONS)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(SOCKET_BACKLOG)

    logger.info("Server is running on %s:%s", HOST, PORT)

    while True:
        connection_slots.acquire()
        try:
            conn, addr = server_socket.accept()
        except Exception:
            connection_slots.release()
            raise

        def worker(client_conn=conn, client_addr=addr):
            try:
                handle_client(client_conn, client_addr)
            finally:
                connection_slots.release()

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    run_server()
