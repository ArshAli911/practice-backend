import html


STATUS_MESSAGES = {
    200: "OK",
    303: "See Other",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    413: "Payload Too Large",
    414: "URI Too Long",
    429: "Too Many Requests",
    500: "Internal Server Error",
}


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

def error_response(status, message=None):
    title = message or STATUS_MESSAGES.get(status, "Error")
    return html_response(
        status,
        f"<h1>{html.escape(title)}</h1>"
    )


def validation_response(message, status=400):
    return html_response(
        status,
        f"<h1>{html.escape(STATUS_MESSAGES.get(status, 'Bad Request'))}</h1>"
        f"<p>{html.escape(message)}</p>"
    )
