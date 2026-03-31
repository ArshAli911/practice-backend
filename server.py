import socket
import os
from route import method_routes, EXTENSION
from sessions import create_sessions, get_session

HOST = '127.0.0.1'
PORT = 8080


# Converts your handler's dict into a valid HTTP response string
def build_http_response(resp):
    status_messages = {
        200: "OK",
        303: "See Other",
        404: "Not Found",
        405: "Method Not Allowed"
    }

    # Example: HTTP/1.1 200 OK
    status_line = f"HTTP/1.1 {resp['status']} {status_messages.get(resp['status'], '')}\r\n"

    # Convert headers dict → string
    headers = ""
    for k, v in resp["headers"].items():
        headers += f"{k}: {v}\r\n"

    # Final HTTP format: status + headers + blank line + body
    return status_line + headers + "\r\n" + resp["body"]


def parse_cookies(cookie_header):
    # Convert "a=1; b=2" into {"a": "1", "b": "2"}.
    cookies = {}
    for item in cookie_header.split(";"):
        if "=" in item:
            key, val = item.strip().split("=", 1)
            cookies[key] = val
    return cookies


# Create TCP socket (IPv4 + TCP)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind server to localhost:8080
server_socket.bind((HOST, PORT))

# Start listening with backlog queue
server_socket.listen(5)

print("Server is running...")


# Main server loop (runs forever)
while True:
    # Accept incoming client connection
    conn, addr = server_socket.accept()

    # Receive raw HTTP request (bytes)
    data = conn.recv(1024)
    # If client sends nothing, skip
    if not data:
        conn.close()
        continue

    # Decode bytes → string (HTTP is text-based)
    request_text = data.decode('utf-8', errors='replace')
    # HTTP separates headers and body with a blank line.
    header_text, _, raw_body = request_text.partition("\r\n\r\n")
    header_lines = header_text.split("\r\n")

    # The first header line contains method, path, and HTTP version.
    request_line = header_lines[0]
    try:
        method, path, version = request_line.split()
    except:
        conn.close()
        continue

    # Store request headers in a dictionary for easy lookup.
    headers = {}
    for line in header_lines[1:]:
        if ":" in line:
            key, val = line.split(":", 1)
            headers[key.strip()] = val.strip()

    # Look for an existing browser session cookie.
    cookies = parse_cookies(headers.get("Cookie", ""))
    session_id = cookies.get("session_id")

    # Reuse a known session; otherwise start a fresh one.
    if not session_id or get_session(session_id) is None:
        session_id = create_sessions()
        new_session = True
    else:
        new_session = False



    # Only POST requests are expected to carry a form body here.
    body = raw_body or None
    if method != "POST":
        body = None

    # Remove query params (?id=123)
    path = path.split('?', 1)[0]

    # Normalize trailing slash (/about/)
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')

    print(method, path)


    # ---------- 1. METHOD-BASED ROUTING ----------
    # Try to find handler for (method, path)
    handler = method_routes.get((method, path))

    if handler:
        # Handlers receive the resolved session_id so they can read/write session data.
        resp_dict = handler(method, path,session_id, body)
        if new_session:
            resp_dict["headers"]["Set-Cookie"] = (
                f"session_id={session_id}; Path=/; HttpOnly; SameSite=Lax"
            )

        # Convert dict → HTTP string
        http_response = build_http_response(resp_dict)

        # Send encoded response
        conn.send(http_response.encode())

        # Done with this request
        conn.close()
        continue
    

    
    # ---------- 2. STATIC FILE HANDLING ----------
    # If root → serve index.html
    if path == "/":
        file_name = "index.html"
    else:
        # Convert "/about" → "about"
        file_name = path.lstrip("/")

    # Extract file extension
    name, ext = os.path.splitext(file_name)

    try:
        # If extension is known (css, js, png, etc.)
        if ext in EXTENSION:
            # Read binary file
            with open(file_name, "rb") as file:
                content = file.read()

            # Send proper content-type header
            header = f"HTTP/1.1 200 OK\r\n Content-Type: {EXTENSION[ext]}\r\n\r\n"

            conn.send(header.encode() + content)

        else:
            # Default: treat as HTML/text
            with open(file_name, "r") as file:
                content = file.read()

            response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{content}"
            conn.send(response.encode())
 
    except FileNotFoundError:
        # ---------- 3. 404 FALLBACK ----------
        response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<h1>404 Not Found</h1>"
        conn.send(response.encode())
    if body is not None:

        print(body)
    

        
    # Close connection after response
    conn.close()
