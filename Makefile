.PHONY: up down migrate worker test

## Start all services (PostgreSQL, Redpanda, Console, API, Worker)
up:
	docker compose up -d --build

## Stop all services
down:
	docker compose down

## Apply database migrations via psql inside the postgres container
migrate:
	docker compose exec postgres psql -U postgres -d ads_db -f /dev/stdin < migrations/0001_create_tables.sql
	docker compose exec postgres psql -U postgres -d ads_db -f /dev/stdin < migrations/0002_create_moderation_results.sql

## Run the moderation worker locally (requires KAFKA_BOOTSTRAP_SERVERS and DATABASE_URL)
worker:
	python -m workers.moderation_worker

## Run unit tests
test:
	pytest test_api.py -v
