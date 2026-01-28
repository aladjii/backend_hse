import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
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
    images_qty: int = Field(ge=0, description="Количество изображений, >= 0")

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
