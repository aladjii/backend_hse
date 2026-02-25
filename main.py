import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncpg
from routes.ads import router as ads_router
from model import get_or_create_model
from clients.kafka import kafka_producer
from services.cache import CacheStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = get_or_create_model()
    app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    app.state.cache = CacheStorage(REDIS_URL)
    await kafka_producer.start()
    
    yield
    
    await kafka_producer.stop()
    await app.state.db_pool.close()
    await app.state.cache.close()

app = FastAPI(title="Ad Moderation Service", lifespan=lifespan)
app.include_router(ads_router)