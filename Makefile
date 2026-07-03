.PHONY: help install run test lint format typecheck docker-up docker-down docker-logs

help:
	@echo "Available commands:"
	@echo "  make install      Install project dependencies with Poetry"
	@echo "  make run          Run API locally"
	@echo "  make test         Run tests"
	@echo "  make lint         Run Ruff checks"
	@echo "  make format       Format code with Ruff"
	@echo "  make typecheck    Run mypy"
	@echo "  make docker-up    Start Docker Compose services"
	@echo "  make docker-down  Stop Docker Compose services"
	@echo "  make docker-logs  Follow Docker Compose logs"

install:
	poetry install

run:
	poetry run uvicorn app.main:app --reload

test:
	poetry run pytest

lint:
	poetry run ruff check .

format:
	poetry run ruff check . --fix
	poetry run ruff format .

typecheck:
	poetry run mypy app

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f
