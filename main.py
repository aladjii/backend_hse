import logging
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

import config
from clients.kafka import kafka_producer
from model import get_or_create_model
from routes import ads, auth
from services.cache import CacheStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    app.state.db_pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=2, max_size=10)
    app.state.cache = CacheStorage(config.REDIS_URL)
    app.state.model = get_or_create_model()

    try:
        await kafka_producer.start()
        app.state.kafka_started = True
    except Exception as e:
        logger.warning("Kafka unavailable: %s", e)
        app.state.kafka_started = False

    logger.info("Startup complete")
    yield

    logger.info("Shutting down...")
    if app.state.kafka_started:
        await kafka_producer.stop()
    await app.state.cache.close()
    await app.state.db_pool.close()
    logger.info("Shutdown complete")


app = FastAPI(title="Ad Moderation Service", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())
app.include_router(ads.router, prefix="/api/v1", tags=["ads"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
