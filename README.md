# Online Cinema

Online Cinema is a FastAPI backend for a digital movie platform with authentication, movie catalog, cart, orders, payments, Swagger documentation, tests, and Docker-based local development.

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy + Alembic
- Redis
- Celery + Celery Beat
- MinIO
- Stripe
- Poetry
- Pytest
- Ruff + mypy
- Docker Compose

## Quick Start

1. Optional: copy environment variables if you want to override defaults:

```bash
cp .env.example .env
```

2. Start all services:

```bash
docker compose up --build
```

3. Open the API:

- API: http://localhost:8000
- Health check: http://localhost:8000/health
- Swagger docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001

MinIO object URLs use `MINIO_PUBLIC_ENDPOINT` from `.env.example`.
For local Docker it should point to `http://localhost:9000`, while the app
uses the internal `MINIO_ENDPOINT=http://minio:9000` to upload files.

## Local Development Without Docker

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

Poetry is configured to create the virtual environment inside the project as `.venv`.

## Tests And Quality

```bash
poetry run pytest
poetry run ruff check .
poetry run ruff format .
poetry run mypy app
```

Or through Makefile:

```bash
make test
make lint
make typecheck
```

## Branch And PR Workflow

- Create one branch per task.
- Use clear branch names, for example:
  - `chore/project-bootstrap`
  - `feature/auth-registration-activation`
  - `feature/movie-catalog`
  - `feature/cart`
  - `feature/stripe-payments`
- Open a pull request for every task.
- Require at least 2 approvals before merging.
- Open feature pull requests into `develop`.
- Merge `develop` into `main` only after the integrated version is stable.
- Do not push directly to `main` or `develop`.
- Rebase your feature branch if `develop` changed before your PR is merged.

See `docs/github-start-checklist.md` for the initial GitHub setup.

## Project Domains

- Authorization and authentication
- User profiles and avatar storage
- Movies catalog
- Shopping cart
- Orders
- Payments
- Swagger/OpenAPI documentation
- Tests and CI/CD

## User Profile API

Authenticated users can manage their profile data and avatar:

- `GET /api/v1/users/me/profile` returns the current user's profile.
- `PATCH /api/v1/users/me/profile` updates profile fields such as first name,
  last name, gender, date of birth, and info.
- `POST /api/v1/users/me/avatar` uploads an image file to MinIO-compatible
  storage and stores the avatar URL in the user profile.

## Useful Commands

```bash
make docker-up
make docker-down
make docker-logs
make test
make lint
make format
```

## Trello Planning

Sprint planning files are in `docs/`:

- `docs/trello-online-cinema-sprint.md`
- `docs/trello-online-cinema-sprint.csv`
- `docs/trello-api-import.md`

To create the Trello board through the API:

```bash
poetry run python scripts/import_trello_csv.py
```
