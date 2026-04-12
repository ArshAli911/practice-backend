# Backend Practice

This repository is a backend practice project built to exercise core server-side concepts without depending on a web framework. The server is implemented directly on top of Python sockets, handles HTTP parsing manually, keeps sessions in memory, and stores persistent data in SQLite.

The project is meant for learning and experimentation rather than production use.

## Project Goals

- Practice building an HTTP server from scratch
- Understand request parsing, routing, and response generation
- Implement authentication and session handling without a framework
- Use SQLite for simple persistent storage
- Add practical backend protections such as rate limiting, CSRF checks, and input validation

## Tech Stack

- Python 3
- SQLite for persistence

There are no third-party Python dependencies in this project. Database storage is handled with SQLite through Python's standard `sqlite3` module.

## How It Works

The application starts from `server.py`. It:

- initializes the SQLite database
- starts a background cleanup thread for expired sessions
- opens a TCP socket on `127.0.0.1:8080`
- accepts client connections and handles them in separate daemon threads
- parses HTTP requests manually
- applies request validation and rate limiting
- resolves routes from `route.py`
- serves either dynamic responses or static files from the project directory

## Main Features

- Manual HTTP request parsing
- Socket-based multithreaded server
- SQLite-backed users and messages
- User signup and login
- In-memory session management with secure random session IDs
- Session rotation on login
- CSRF token generation and verification for forms
- Route protection for authenticated users
- Role-based access control for admin-only endpoints
- Rate limiting for general traffic and login attempts
- Login lockout after repeated failures
- Message submission and paginated message listing
- Rotating file logging under `logs/app.log`

## Project Structure

- `server.py` - socket server, request parsing, cookie handling, session cookie creation, static file serving, connection handling
- `route.py` - route handlers, form parsing, CSRF handling, login/signup/logout flow, message submission, health check
- `db.py` - SQLite connection management, schema creation, user and message queries
- `auth.py` - password hashing, password verification, login state helpers
- `sessions.py` - in-memory session store, expiration, cleanup, rotation
- `middleware.py` - login-required and role-required route wrappers
- `rate_limit.py` - rate limiting and login lockout tracking
- `responses.py` - HTTP response helpers, redirects, validation and error responses
- `config.py` - host, port, limits, and timeout-related configuration
- `login_config.py` - logging setup
- `client.py` - simple raw socket client example for testing the server
- `index.html`, `about.html`, `contacts.html`, `login.html`, `stylee.css`, `file.js` - static frontend assets used by the backend
- `app.db` - SQLite database file created and used by the application

## Database Schema

The database is initialized automatically in `db.py`.

### `users`

- `id` - integer primary key
- `username` - unique username
- `password_hash` - stored password hash
- `role` - user role, defaults to `user`

### `messages`

- `id` - integer primary key
- `user_id` - foreign key to `users.id`
- `content` - stored message text
- `created_at` - creation timestamp

During initialization, the code updates any existing user with the username `demo` to the role `admin`.

## Authentication and Security Notes

The backend includes several practice-oriented security mechanisms:

- Passwords are hashed with SHA-256 before storage
- Sessions are stored on the server side and identified by a random `session_id` cookie
- Session cookies are sent with `HttpOnly` and `SameSite=Lax`
- Session IDs are rotated after successful login and signup
- CSRF tokens are generated per session and checked on protected form submissions
- Request size and field count limits are enforced
- General request rate limiting is applied per client IP
- Login-specific rate limiting and temporary account lockouts are implemented

These protections are useful for learning, but the project should still be treated as a practice backend, not as a production-ready system.

## Config

Current runtime settings from `config.py`:

- Host: `127.0.0.1`
- Port: `8080`
- Database: `app.db`
- Max concurrent connections: `20`
- Socket backlog: `20`
- Receive chunk size: `1024` bytes
- Session TTL: `3600` seconds
- Session cleanup interval: `300` seconds
- Max header size: `8192` bytes
- Max body size: `1048576` bytes
- Max form fields: `20`
- Max username length: `50`
- Max password length: `128`
- Max message length: `1000`
- Max message page query: `1000`
- General rate limit: `100` requests per `60` seconds
- Login rate limit: `5` attempts per `60` seconds
- Login lockout threshold: `5` failures within `300` seconds
- Login lockout duration: `300` seconds

## Routes

### Public routes

- `GET /login` - login form
- `POST /login` - login submission
- `GET /signup` - signup form
- `POST /signup` - create account
- `GET /health` - simple health response

### Authenticated routes

- `GET /` - home page
- `POST /submit` - submit a message
- `GET /messages?page=N` - paginated message list
- `GET /logout` - log out current user

### Role-protected route

- `GET /admin` - admin-only page

### Static files

If no dynamic route matches, the server attempts to serve files directly from the project directory. The root path `/` maps to `index.html` when static serving is used.

## Running the Project

Make sure Python 3 is installed, then start the server from the project directory:

```bash
python server.py
```

The server listens on:

```text
http://127.0.0.1:8080
```

Because the home route is protected, opening `/` without a valid session redirects to `/login`.

## Simple Test Client

The repository also includes `client.py`, which sends a raw HTTP request to the server using sockets:

```bash
python client.py
```

This is useful for practicing low-level request and response inspection.

## Logging

Application logs are written to:

```text
logs/app.log
```

Logging uses a rotating file handler with a maximum file size of 1 MB and up to 5 backup log files.

## Practice Value

This project is useful for learning how backend systems work underneath higher-level frameworks. It covers:

- sockets
- HTTP basics
- routing
- cookies
- sessions
- authentication
- authorization
- SQLite persistence
- validation
- rate limiting
- logging

## Limitations

This project is intentionally simple. A few important limitations:

- it uses manual HTTP handling instead of a mature framework
- sessions are stored only in memory
- password hashing uses a basic SHA-256 approach instead of a dedicated password hashing algorithm
- static and dynamic concerns are mixed in the same application
- there is no automated test suite in the repository at the moment

## Summary

This is a backend practice project built to learn backend fundamentals by implementing them directly. It avoids third-party dependencies, uses SQLite for storage, and includes authentication, sessions, role checks, rate limiting, and message handling on top of a custom Python socket server.
