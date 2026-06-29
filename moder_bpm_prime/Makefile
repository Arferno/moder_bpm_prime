.PHONY: run migrate test lint format

run:
	docker compose up --build

run-prod:
	docker compose -f docker-compose.prod.yml up -d --build

migrate:
	docker compose exec bot alembic upgrade head

migrate-create:
	docker compose exec bot alembic revision --autogenerate -m "$(MSG)"

seed:
	docker compose exec bot python scripts/init_db.py

test:
	docker compose exec bot pytest -v

test-cov:
	docker compose exec bot pytest --cov=bot --cov-report=term-missing

lint:
	docker compose exec bot ruff check .

format:
	docker compose exec bot ruff check --fix .

logs:
	docker compose logs -f bot

logs-prod:
	docker compose -f docker-compose.prod.yml logs -f bot

shell:
	docker compose exec bot bash

db-shell:
	docker compose exec bot psql $${DATABASE_URL}

stop:
	docker compose down

stop-prod:
	docker compose -f docker-compose.prod.yml down