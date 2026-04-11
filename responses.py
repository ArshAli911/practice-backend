def html_response(status, body, headers=None):
    response_headers = {"Content-Type": "text/html"}
    if headers:
        response_headers.update(headers)
    return {
        "status": status,
        "headers": response_headers,
        "body": body,
    }