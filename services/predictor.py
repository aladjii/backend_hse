import logging
import time
from typing import Tuple

import numpy as np

from metrics import (
    MODEL_PREDICTION_PROBABILITY,
    PREDICTION_DURATION,
    PREDICTION_ERRORS_TOTAL,
    PREDICTIONS_TOTAL,
)

logger = logging.getLogger("predictor")


class PredictionService:
    def __init__(self, model):
        self.model = model

    def predict(
        self,
        is_verified: bool,
        images_qty: int,
        description: str,
        category: int,
    ) -> Tuple[bool, float]:
        if self.model is None:
            PREDICTION_ERRORS_TOTAL.labels(error_type="model_unavailable").inc()
            raise RuntimeError("Model is not loaded")

        features = np.array([[
            1.0 if is_verified else 0.0,
            images_qty / 10.0,
            len(description) / 1000.0,
            category / 100.0,
        ]])

        start = time.time()
        try:
            prob_violation = float(self.model.predict_proba(features)[0][1])
            is_violation = prob_violation >= 0.5

            PREDICTION_DURATION.observe(time.time() - start)
            PREDICTIONS_TOTAL.labels(
                result="violation" if is_violation else "no_violation"
            ).inc()
            MODEL_PREDICTION_PROBABILITY.observe(prob_violation)

            return bool(is_violation), prob_violation
        except Exception as e:
            logger.error("Inference error: %s", e)
            PREDICTION_ERRORS_TOTAL.labels(error_type="prediction_error").inc()
            raise
