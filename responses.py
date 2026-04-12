def html_response(status, body, headers=None):
    response_headers = {"Content-Type": "text/html"}
    if headers:
        response_headers.update(headers)
    return {
        "status": status,
        "headers": response_headers,
        "body": body,
    }

def redirect(location):
    return html_response(
        303,
        "",
        {"Location":location},
        )

def error_response(status, message):
    return html_response(
        status,
        f"<h1>{message}</h1>"
    )