from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Ad Moderation Service")

class AdItem(BaseModel):
    seller_id: int
    is_verified_seller: bool
    item_id: int
    name: str
    description: str
    category: int
    images_qty: int = Field(ge=0)

@app.post("/predict")
async def predict(item: AdItem) -> bool:
    try:
        # если продавец подтвержден - True 
        if item.is_verified_seller:
            return True
        
        # если не подтвержден - True только при наличии изображений
        if item.images_qty > 0:
            return True
        
        return False
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)