import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes.ads import router as ads_router
from model import get_or_create_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: Loading ML model")
    try:
        app.state.model = get_or_create_model()
        logger.info("ML model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        app.state.model = None

    yield

    logger.info("Shutting down")

app = FastAPI(title="Ad Moderation ML Service", lifespan=lifespan)

app.include_router(ads_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
