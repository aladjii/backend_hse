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
```

### Компоненты

| Компонент | Назначение |
|-----------|-----------|
| **FastAPI** | HTTP API для CRUD объявлений и модерации |
| **ML Model** | LogisticRegression — предсказание нарушений |
| **PostgreSQL** | Хранение объявлений, пользователей, результатов модерации |
| **Kafka** | Асинхронная очередь задач модерации |
| **Redis** | Кэш результатов предсказаний (TTL 24ч) |
| **Prometheus** | Метрики: latency, counters, гистограммы |
| **Worker** | Kafka consumer — фоновая обработка задач модерации |

## Структура проекта

```
├── main.py                  # FastAPI app, lifespan, middleware
├── config.py                # Переменные окружения
├── model.py                 # Обучение и загрузка ML-модели
├── metrics.py               # Prometheus метрики
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
│   ├── test_model.py        # Тесты ML-модели
│   ├── test_predictor.py    # Тесты inference-сервиса
│   ├── test_auth_service.py # Тесты JWT
│   ├── test_cache.py        # Тесты Redis-кэша
│   ├── test_routes.py       # Интеграционные тесты API
│   ├── test_login.py        # Тесты авторизации
│   ├── test_worker.py       # Тесты Kafka worker
│   └── test_metrics.py      # Тесты Prometheus метрик
├── docker-compose.yml       # Все сервисы
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
make down        # остановить
```

### Локально

```bash
pip install -r requirements.txt
python main.py
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
GET /metrics    → Prometheus metrics
```

## Тесты

```bash
make test
# или
python -m pytest tests/ -v
```

Покрытие:
- ML-модель: обучение, сериализация, детерминированность
- Predictor: inference, edge cases, ошибки
- Auth: JWT lifecycle, expired/tampered tokens
- Cache: hit/miss/set/delete
- API routes: все эндпоинты, валидация, 401/403/404
- Worker: success, retry, DLQ, max retries
- Metrics: регистрация и инкремент счётчиков

## Переменные окружения

| Переменная | По умолчанию |
|-----------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/moderation` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` |
| `HOST` | `0.0.0.0` |
| `PORT` | `8000` |
