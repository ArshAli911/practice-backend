import os
import socket
from datetime import datetime, timedelta, timezone

from route import EXTENSION, method_routes
from sessions import create_sessions, get_session


HOST = "127.0.0.1"
PORT = 8080
SESSION_TTL_SECONDS = 3600

MAX_HEADER_BYTES = 8192                                                                                                               
MAX_BODY_BYTES = 1024 * 1024                                                                                                          
RECV_CHUNK_SIZE = 1024 


class RequestParseError(Exception):
    pass


def build_http_response(resp):
    status_messages = {
        200: "OK",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        303: "See Other",
        404: "Not Found",
        405: "Method Not Allowed",
        413: "Payload Too Large",
        414: "URL Too Long"
    }

    status_line = f"HTTP/1.1 {resp['status']} {status_messages.get(resp['status'], '')}\r\n"

    headers = ""
    for k, v in resp["headers"].items():
        headers += f"{k}: {v}\r\n"

    return status_line + headers + "\r\n" + resp["body"]


def error_response(status, body):
    return build_http_response({
        "status": status,
        "headers": {"Content-Type": "text/html"},
        "body": body,
    })


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
        headers[key.strip()] = val.strip()

    content_length_text = headers.get("Content-Length", "0")
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


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

print("Server is running...")

while True:
    conn, addr = server_socket.accept()

    try:
        header_lines, headers, raw_body = read_http_request(conn)
    except RequestParseError as exc:
        reason = str(exc)
        if reason in {"headers_too_large", "body_too_large"}:
            conn.send(error_response(413, "<h1>Payload Too Large</h1>").encode())
        else:
            conn.send(error_response(400, "<h1>Bad Request</h1>").encode())
        conn.close()
        continue
    if not header_lines or not header_lines[0]:
        conn.close()
        continue

    request_line = header_lines[0]
    parts = request_line.split()
    if len(parts) != 3:
        conn.send(error_response(400, "<h1>Bad Request</h1>").encode())
        conn.close()
        continue
    method, path, version = parts

    if method not in {"GET", "POST"}:
        conn.send(error_response(405, "<h1>Method Not Allowed</h1>").encode())
        conn.close()
        continue
    if not path.startswith("/"):
        conn.send(error_response(400, "<h1>Bad Request</h1>").encode())
        conn.close()
        continue
    if len(path) > 2048:
        conn.send(error_response(414, "<h1>URI Too Long</h1>").encode())
        conn.close()
        continue
    if version not in {"HTTP/1.0", "HTTP/1.1"}:
        conn.send(error_response(400, "<h1>Bad Request</h1>").encode())
        conn.close()
        continue

    cookies = parse_cookies(headers.get("Cookie", ""))
    session_id = cookies.get("session_id")

    if not session_id or get_session(session_id) is None:
        session_id = create_sessions(SESSION_TTL_SECONDS)
        new_session = True
    else:
        new_session = False

    body = raw_body or None
    if method != "POST":
        body = None

    path = path.split("?", 1)[0]
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    print(method, path)

    handler = method_routes.get((method, path))

    if handler:
        resp_dict = handler(method, path, session_id, body)
        rotated_session_id = resp_dict.pop("session_id", None)
        if rotated_session_id is not None:
            session_id = rotated_session_id
            resp_dict["headers"]["Set-Cookie"] = build_session_cookie(session_id)
        elif new_session:
            resp_dict["headers"]["Set-Cookie"] = build_session_cookie(session_id)

        http_response = build_http_response(resp_dict)
        conn.send(http_response.encode())
        conn.close()
        continue

    if path == "/":
        file_name = "index.html"
    else:
        file_name = path.lstrip("/")

    name, ext = os.path.splitext(file_name)

    try:
        if ext in EXTENSION:
            with open(file_name, "rb") as file:
                content = file.read()

            header = f"HTTP/1.1 200 OK\r\nContent-Type: {EXTENSION[ext]}\r\n\r\n"
            conn.send(header.encode() + content)
        else:
            with open(file_name, "r") as file:
                content = file.read()

            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{content}"
            conn.send(response.encode())

    except FileNotFoundError:
        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 Not Found</h1>"
        conn.send(response.encode())

    conn.close()
