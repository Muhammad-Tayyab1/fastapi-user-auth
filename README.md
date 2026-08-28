# FastAPI User Auth

Async FastAPI authentication API backed by PostgreSQL and SQLModel. It includes email OTP verification through Resend, JWT access/refresh tokens, password reset, self-service profile endpoints, and admin user management.

## Quick start

1. Install dependencies: `uv sync --dev`
2. Copy `.env.example` to `.env` and set secure production values.
3. Start PostgreSQL with `docker compose up -d postgres` (or use an existing server).
4. Run `uv run alembic upgrade head`.
5. Start the API: `uv run uvicorn app.main:app --reload`
6. Open `http://127.0.0.1:8000/docs`.

Resend sending is skipped when `RESEND_API_KEY` is empty. Set a verified sender domain before testing real delivery.

## API

- Auth: register, verify OTP, resend OTP, login, refresh, forgot/reset password
- Users: current profile update/deactivation and paginated admin management
- Health: `GET /health`

## Tests

Run `uv run pytest`. The suite includes complete register → verify → login → refresh → profile and password-reset flows using an isolated async test database.

## Security notes

Change `JWT_SECRET` before deployment. Registration, login, resend, and password-reset requests are limited by both client IP and email. The included in-memory store is suitable for one process only; use Redis for horizontally scaled production deployments and configure trusted-proxy handling at the server boundary.
