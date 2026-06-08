.PHONY: install dev up down migrate test lint

install:
	pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

up:
	docker compose up --build -d postgres redis api

down:
	docker compose down

migrate:
	alembic upgrade head

worker:
	arq app.worker.WorkerSettings

test:
	pytest -q

lint:
	ruff check app tests
