import os
import socket
from datetime import datetime, timedelta, timezone

from route import EXTENSION, method_routes
from sessions import create_sessions, get_session


HOST = "127.0.0.1"
PORT = 8080
SESSION_TTL_SECONDS = 3600


def build_http_response(resp):
    status_messages = {
        200: "OK",
        401: "Unauthorized",
        403: "Forbidden",
        303: "See Other",
        404: "Not Found",
        405: "Method Not Allowed",
    }

    status_line = f"HTTP/1.1 {resp['status']} {status_messages.get(resp['status'], '')}\r\n"

    headers = ""
    for k, v in resp["headers"].items():
        headers += f"{k}: {v}\r\n"

    return status_line + headers + "\r\n" + resp["body"]


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
        chunk = conn.recv(1024)
        if not chunk:
            break
        data += chunk

    header_bytes, _, body = data.partition(b"\r\n\r\n")
    header_text = header_bytes.decode("utf-8", errors="replace")
    header_lines = header_text.split("\r\n")

    headers = {}
    for line in header_lines[1:]:
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip()] = val.strip()

    content_length = int(headers.get("Content-Length", "0"))
    while len(body) < content_length:
        chunk = conn.recv(1024)
        if not chunk:
            break
        body += chunk

    return header_lines, headers, body.decode("utf-8", errors="replace")


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

print("Server is running...")

while True:
    conn, addr = server_socket.accept()

    header_lines, headers, raw_body = read_http_request(conn)
    if not header_lines or not header_lines[0]:
        conn.close()
        continue

    request_line = header_lines[0]
    try:
        method, path, version = request_line.split()
    except Exception:
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
