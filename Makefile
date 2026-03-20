up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f

restart:
	docker compose restart app worker

migrate:
	docker compose exec postgres psql -U postgres -d moderation -f /docker-entrypoint-initdb.d/001_init.sql

# --- scaling ----------------------------------------------------------

scale-workers:
	docker compose up -d --scale worker=3

# --- tests ------------------------------------------------------------

test:
	python -m pytest tests/ -v -m "not integration"

test-integration:
	python -m pytest tests/ -v -m integration

test-all:
	python -m pytest tests/ -v

test-docker:
	docker compose build app
	docker compose run --rm --no-deps app python -m pytest tests/ -v -m "not integration"

test-integration-docker:
	docker compose up -d postgres redis kafka zookeeper
	@echo "Waiting for infra to be ready..."
	@sleep 10
	docker compose run --rm app python -m pytest tests/ -v -m integration
	docker compose down

# --- mlflow -----------------------------------------------------------

mlflow-register:
	docker compose up -d mlflow
	@sleep 3
	docker compose run --rm app python -c "from model import train_model, register_model_in_mlflow; register_model_in_mlflow(train_model())"

# --- lint -------------------------------------------------------------

lint:
	ruff check . --fix
	ruff format .

.PHONY: up down logs restart migrate scale-workers test test-integration test-all test-docker test-integration-docker mlflow-register lint
