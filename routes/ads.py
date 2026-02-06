import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from services.predictor import PredictionService
from services import repositories

router = APIRouter()
logger = logging.getLogger("api")

class AdItem(BaseModel):
    seller_id: int
    is_verified_seller: bool
    item_id: int
    name: str
    description: str
    category: int
    images_qty: int = Field(ge=0, description="Количество изображений, >= 0")

class ItemId(BaseModel):
    item_id: int = Field(..., gt=0)

class PredictionResponse(BaseModel):
    is_violation: bool
    probability: float

def get_prediction_service(request: Request) -> PredictionService:
    model = request.app.state.model
    if model is None:
        logger.critical("Model not found in app state")
        raise HTTPException(status_code=503, detail="Service Unavailable: model not loaded")
    return PredictionService(model)

@router.post("/predict", response_model=PredictionResponse)
async def predict_ad_violation(
    item: AdItem,
    service: PredictionService = Depends(get_prediction_service)
):
    logger.info(
        f"Incoming prediction request: seller_id={item.seller_id}, item_id={item.item_id}, "
        f"features=[ver={item.is_verified_seller}, img={item.images_qty}, len_desc={len(item.description)}, cat={item.category}]"
    )

    try:
        is_violation, probability = service.predict(
            is_verified=item.is_verified_seller,
            images_qty=item.images_qty,
            description=item.description,
            category=item.category
        )

        logger.info(f"Prediction result: item_id={item.item_id}, is_violation={is_violation}, probability={probability:.4f}")

        return PredictionResponse(is_violation=is_violation, probability=probability)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed for item_id={item.item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.post("/simple_predict", response_model=PredictionResponse)
async def simple_predict(
    payload: ItemId,
    request: Request,
    service: PredictionService = Depends(get_prediction_service)
):

    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        logger.critical("DB pool not initialized")
        raise HTTPException(status_code=500, detail="DB connection is not available")

    ad = await repositories.get_ad_by_item_id(pool, payload.item_id)
    if ad is None:
        logger.info(f"Ad not found: item_id={payload.item_id}")
        raise HTTPException(status_code=404, detail="Ad not found")

    seller = await repositories.get_user_by_id(pool, ad["seller_id"])
    if seller is None:
        logger.warning(f"Seller not found for ad: item_id={payload.item_id}, seller_id={ad['seller_id']}")
        raise HTTPException(status_code=500, detail="Seller not found")

    try:
        is_violation, probability = service.predict(
            is_verified=bool(seller.get("is_verified", False)),
            images_qty=int(ad.get("images_qty", 0)),
            description=str(ad.get("description", "")),
            category=int(ad.get("category", 0))
        )

        logger.info(f"Simple prediction: item_id={payload.item_id}, is_violation={is_violation}, probability={probability:.4f}")

        return PredictionResponse(is_violation=is_violation, probability=probability)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Simple prediction failed for item_id={payload.item_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
