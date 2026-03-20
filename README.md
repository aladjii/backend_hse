# Ad Moderation Service

Backend-сервис модерации объявлений с ML-моделью, асинхронной обработкой через Kafka и кэшированием в Redis.

## Архитектура

```
Client → FastAPI (HTTP API) → PostgreSQL
                ↓                  ↑
              Kafka → Worker → ML Model
                ↓
              Redis (cache)

Prometheus ← /metrics
MLflow ← Model Registry
```

### Компоненты

| Компонент | Назначение |
|-----------|-----------| 
| **FastAPI** | HTTP API для CRUD объявлений и модерации |
| **ML Model** | LogisticRegression — предсказание нарушений |
| **MLflow** | Model Registry, переключение через `MODEL_SOURCE=mlflow` |
| **PostgreSQL** | Хранение объявлений, пользователей, результатов модерации |
| **Kafka** | Асинхронная очередь задач модерации |
| **Redis** | Кэш результатов предсказаний (TTL 24ч) |
| **Prometheus** | Метрики: HTTP latency/count, ML inference, DB queries |
| **Grafana** | Визуализация метрик |
| **Worker** | Kafka consumer — фоновая обработка задач модерации |

## Структура проекта

```
├── main.py                  # FastAPI app, lifespan, middleware
├── config.py                # Переменные окружения
├── model.py                 # ML-модель + MLflow integration
├── metrics.py               # Prometheus метрики (HTTP, ML, DB)
├── middleware.py             # HTTP metrics middleware
├── clients/
│   └── kafka.py             # Kafka producer + DLQ
├── services/
│   ├── repositories.py      # PostgreSQL запросы (ads, users, moderation)
│   ├── account_repository.py# PostgreSQL запросы (accounts)
│   ├── cache.py             # Redis cache
│   ├── predictor.py         # ML inference service
│   ├── auth_service.py      # JWT create/verify
│   └── auth_dependency.py   # FastAPI dependency — auth guard
├── routes/
│   ├── ads.py               # /predict, /simple_predict, /async_predict, /close
│   └── auth.py              # /login
├── workers/
│   └── consumer.py          # Kafka consumer worker
├── migrations/
│   └── 001_init.sql         # DDL: таблицы + индексы + seed data
├── tests/
│   ├── conftest.py          # Фикстуры, моки, тестовый клиент
│   ├── test_model.py        # Unit: ML-модель
│   ├── test_predictor.py    # Unit: inference-сервис
│   ├── test_auth_service.py # Unit: JWT
│   ├── test_cache.py        # Unit: Redis-кэш (мок)
│   ├── test_routes.py       # Unit: API routes
│   ├── test_login.py        # Unit: авторизация
│   ├── test_worker.py       # Unit: Kafka worker
│   ├── test_metrics.py      # Unit: Prometheus метрики
│   ├── test_middleware.py   # Unit: HTTP middleware
│   ├── test_integration_postgres.py  # Integration: PostgreSQL
│   ├── test_integration_redis.py     # Integration: Redis
│   └── test_integration_kafka.py     # Integration: Kafka
├── docker-compose.yml       # Все сервисы: app, worker, postgres, redis, kafka, prometheus, grafana, mlflow
├── Dockerfile               # API image
├── Dockerfile.worker        # Worker image
├── prometheus.yml           # Prometheus config
├── requirements.txt         # Python зависимости
└── Makefile                 # Команды управления
```

## Запуск

### Docker Compose (рекомендуемый)

```bash
make up          # поднять все сервисы
make logs        # логи
make down        # остановить и удалить volumes
```

### Масштабирование воркеров

```bash
make scale-workers           # запуск 3 воркеров
# или вручную:
docker compose up -d --scale worker=5
```

### MLflow: регистрация модели

```bash
make mlflow-register         # обучить и зарегистрировать в MLflow
# после этого можно переключить источник:
MODEL_SOURCE=mlflow make up
```

## API

Все эндпоинты (кроме `/login` и `/health`) требуют cookie `access_token` с JWT.

### Аутентификация

```
POST /api/v1/login
Body: {"login": "admin", "password": "admin"}
→ Set-Cookie: access_token=<jwt>
```

### Синхронное предсказание

```
POST /api/v1/predict
Body: {"seller_id": 1, "is_verified_seller": true, "item_id": 100,
       "name": "Phone", "description": "Good phone", "category": 10, "images_qty": 3}
→ {"is_violation": false, "probability": 0.12}
```

### Предсказание по item_id (данные из БД)

```
POST /api/v1/simple_predict
Body: {"item_id": 100}
→ {"is_violation": false, "probability": 0.12}
```

### Асинхронное предсказание (через Kafka)

```
POST /api/v1/async_predict
Body: {"item_id": 100}
→ {"task_id": 77, "status": "pending", "message": "Accepted"}

GET /api/v1/moderation_result/77
→ {"task_id": 77, "status": "completed", "is_violation": false, "probability": 0.12}
```

### Закрытие объявления

```
POST /api/v1/close
Body: {"item_id": 100}
→ {"message": "Ad 100 closed and deleted from storage"}
```

### Health & Metrics

```
GET /health     → {"status": "ok"}
GET /metrics    → Prometheus metrics (http_requests_total, prediction_duration_seconds, ...)
```

## Тесты

### Unit-тесты (без инфраструктуры)

```bash
make test
# или
pytest -m "not integration" -v
```

### Интеграционные тесты (нужны Postgres, Redis, Kafka)

```bash
make test-integration-docker
# или локально при запущенной инфре:
make test-integration
```

### Все тесты

```bash
make test-all
```

### Покрытие

**Unit-тесты:**
- ML-модель: обучение, сериализация, детерминированность
- Predictor: inference, edge cases, ошибки
- Auth: JWT lifecycle, expired/tampered tokens
- Cache: hit/miss/set/delete (мок Redis)
- API routes: все эндпоинты, валидация, 401/403/404
- Worker: success, retry, DLQ, max retries
- Metrics: все Prometheus-счётчики и гистограммы
- Middleware: HTTP метрики

**Интеграционные тесты** (`@pytest.mark.integration`):
- PostgreSQL: CRUD users, ads, moderation_results, accounts
- Redis: set/get/delete/TTL
- Kafka: produce/consume сообщений, DLQ

## Переменные окружения

| Переменная | По умолчанию |
|-----------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/moderation` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` |
| `MODEL_SOURCE` | `local` (варианты: `local`, `mlflow`) |
| `MLFLOW_TRACKING_URI` | `http://localhost:5001` |
| `MLFLOW_MODEL_NAME` | `ad_moderation_model` |
| `MLFLOW_MODEL_STAGE` | `Production` |
| `HOST` | `0.0.0.0` |
| `PORT` | `8000` |

## Веб-интерфейсы

| Сервис | URL |
|--------|-----|
| FastAPI Swagger | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/admin) |
| MLflow | http://localhost:5001 |
