# FastAPI User Auth

Async FastAPI authentication API backed by PostgreSQL and SQLModel. It includes email OTP verification through Resend, JWT access/refresh tokens, password reset, self-service profile endpoints, and admin user management.

## Quick start

1. Install dependencies: `uv sync --dev`
2. Copy `.env.example` to `.env` and set secure production values.
3. Create the PostgreSQL database, then run `uv run alembic upgrade head`.
4. Start the API: `uv run uvicorn app.main:app --reload`
5. Open `http://127.0.0.1:8000/docs`.

Resend sending is skipped when `RESEND_API_KEY` is empty. Set a verified sender domain before testing real delivery.

## API

- Auth: register, verify OTP, resend OTP, login, refresh, forgot/reset password
- Users: current profile update/deactivation and paginated admin management
- Health: `GET /health`

## Tests

Run `uv run pytest`.

## Security notes

Change `JWT_SECRET` before deployment. In-memory resend throttling is suitable for one process only; use Redis for horizontally scaled production deployments. Add perimeter/IP rate limiting at the proxy or gateway.
