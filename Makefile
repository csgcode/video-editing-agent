.PHONY: setup migrate run test lint redis-up redis-down runserver-async worker-async

setup:
	cp -n .env.example .env || true
	uv sync

migrate:
	uv run python manage.py migrate

run:
	uv run python manage.py runserver

test:
	uv run pytest

lint:
	uv run ruff check .

redis-up:
	docker compose up -d redis
	@echo "Redis status:"
	docker compose ps redis

redis-down:
	docker compose down

runserver-async:
	CELERY_TASK_ALWAYS_EAGER=0 CELERY_BROKER_URL=redis://localhost:6379/0 CELERY_RESULT_BACKEND=redis://localhost:6379/1 uv run python manage.py runserver

worker-async:
	CELERY_TASK_ALWAYS_EAGER=0 CELERY_BROKER_URL=redis://localhost:6379/0 CELERY_RESULT_BACKEND=redis://localhost:6379/1 uv run celery -A config worker -l info --pool=solo
