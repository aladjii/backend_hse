import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from clients.kafka import kafka_producer
from services import repositories
from services.auth_dependency import get_current_account
from services.predictor import PredictionService

router = APIRouter()
logger = logging.getLogger("api")


class AdItem(BaseModel):
    seller_id: int
    is_verified_seller: bool
    item_id: int
    name: str
    description: str
    category: int
    images_qty: int = Field(ge=0)


class ItemId(BaseModel):
    item_id: int = Field(..., gt=0)


class PredictionResponse(BaseModel):
    is_violation: bool
    probability: float


class AsyncPredictRequest(BaseModel):
    item_id: int = Field(..., gt=0)


class AsyncPredictResponse(BaseModel):
    task_id: int
    status: str
    message: str


class ModerationStatusResponse(BaseModel):
    task_id: int
    status: str
    is_violation: bool | None = None
    probability: float | None = None


def get_prediction_service(request: Request) -> PredictionService:
    model = request.app.state.model
    if model is None:
        raise HTTPException(status_code=503, detail="Service Unavailable: model not loaded")
    return PredictionService(model)


@router.post("/predict", response_model=PredictionResponse)
async def predict_ad_violation(
    item: AdItem,
    request: Request,
    account=Depends(get_current_account),
    service: PredictionService = Depends(get_prediction_service),
):
    cache = request.app.state.cache
    cached = await cache.get_prediction(item.item_id)
    if cached:
        return PredictionResponse(**cached)

    try:
        is_violation, probability = service.predict(
            is_verified=item.is_verified_seller,
            images_qty=item.images_qty,
            description=item.description,
            category=item.category,
        )
    except Exception as e:
        logger.error("Prediction failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    result = {"is_violation": is_violation, "probability": probability}
    await cache.set_prediction(item.item_id, result)
    return PredictionResponse(**result)


@router.post("/simple_predict", response_model=PredictionResponse)
async def simple_predict(
    payload: ItemId,
    request: Request,
    account=Depends(get_current_account),
    service: PredictionService = Depends(get_prediction_service),
):
    cache = request.app.state.cache
    cached = await cache.get_prediction(payload.item_id)
    if cached:
        return PredictionResponse(**cached)

    pool = request.app.state.db_pool
    ad = await repositories.get_ad_by_item_id(pool, payload.item_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    seller = await repositories.get_user_by_id(pool, ad["seller_id"])
    is_violation, probability = service.predict(
        is_verified=bool(seller.get("is_verified", False)),
        images_qty=int(ad.get("images_qty", 0)),
        description=str(ad.get("description", "")),
        category=int(ad.get("category", 0)),
    )

    result = {"is_violation": is_violation, "probability": probability}
    await cache.set_prediction(payload.item_id, result)
    return PredictionResponse(**result)


@router.post("/async_predict", response_model=AsyncPredictResponse)
async def async_predict(
    payload: AsyncPredictRequest,
    request: Request,
    account=Depends(get_current_account),
):
    pool = request.app.state.db_pool
    ad = await repositories.get_ad_by_item_id(pool, payload.item_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Ad not found")

    task_id = await repositories.create_moderation_result(pool, ad["id"])
    await kafka_producer.send_moderation_request(payload.item_id)
    return AsyncPredictResponse(task_id=task_id, status="pending", message="Accepted")


@router.get("/moderation_result/{task_id}", response_model=ModerationStatusResponse)
async def get_moderation_result(
    task_id: int,
    request: Request,
    account=Depends(get_current_account),
):
    pool = request.app.state.db_pool
    result = await repositories.get_moderation_result(pool, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")

    if result["status"] == "completed":
        ad = await repositories.get_ad_by_id(pool, result["item_id"])
        if ad:
            cache_data = {
                "is_violation": result["is_violation"],
                "probability": result["probability"],
            }
            await request.app.state.cache.set_prediction(ad["item_id"], cache_data)

    return ModerationStatusResponse(
        task_id=result["id"],
        status=result["status"],
        is_violation=result["is_violation"],
        probability=result["probability"],
    )


@router.post("/close")
async def close_ad(
    payload: ItemId,
    request: Request,
    account=Depends(get_current_account),
):
    pool = request.app.state.db_pool
    cache = request.app.state.cache

    deleted = await repositories.delete_ad_by_item_id(pool, payload.item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ad not found")

    await cache.delete_prediction(payload.item_id)
    return {"message": f"Ad {payload.item_id} closed and deleted from storage"}
