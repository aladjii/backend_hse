import logging
import numpy as np
from typing import Tuple

logger = logging.getLogger("service")

class PredictionService:
    def __init__(self, model):
        self.model = model

    def predict(self, is_verified: bool, images_qty: int, description: str, category: int) -> Tuple[bool, float]:
        """
        преобразует входные данные в признаки и возвращает предсказание.
        [is_verified_seller, images_qty, description_length, category]
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        feature_verified = 1.0 if is_verified else 0.0
        feature_images = images_qty / 10.0
        feature_desc_len = len(description) / 1000.0
        feature_category = category / 100.0

        features = np.array([[
            feature_verified,
            feature_images,
            feature_desc_len,
            feature_category
        ]])

        try:
            probabilities = self.model.predict_proba(features)[0]
            prob_violation = probabilities[1]
            is_violation = bool(prob_violation >= 0.5)

            return is_violation, float(prob_violation)
        except Exception as e:
            logger.error(f"Error during inference: {e}")
            raise e
