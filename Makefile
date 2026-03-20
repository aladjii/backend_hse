up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart app worker

migrate:
	docker compose exec postgres psql -U postgres -d moderation -f /docker-entrypoint-initdb.d/001_init.sql

# --- tests -----------------------------------------------------------

test:
	python -m pytest tests/ -v

test-docker:
	docker compose build app
	docker compose run --rm --no-deps app python -m pytest tests/ -v

test-docker-full:
	docker compose up -d postgres redis kafka zookeeper
	docker compose run --rm app python -m pytest tests/ -v
	docker compose down

# --- lint ------------------------------------------------------------

lint:
	ruff check . --fix
	ruff format .

.PHONY: up down logs restart migrate test test-docker test-docker-full lint
