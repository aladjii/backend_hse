import pytest

from services.predictor import PredictionService


class TestPredictionService:
    def test_returns_tuple(self, prediction_service):
        is_violation, prob = prediction_service.predict(
            is_verified=True, images_qty=5, description="test", category=1
        )
        assert isinstance(is_violation, bool)
        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_verified_seller_lower_probability(self, prediction_service):
        _, prob_verified = prediction_service.predict(
            is_verified=True, images_qty=5, description="good item", category=10
        )
        _, prob_unverified = prediction_service.predict(
            is_verified=False, images_qty=0, description="x", category=10
        )
        assert prob_verified <= prob_unverified

    def test_no_model_raises(self):
        service = PredictionService(None)
        with pytest.raises(RuntimeError, match="Model is not loaded"):
            service.predict(True, 5, "test", 1)

    @pytest.mark.parametrize(
        "verified,images,desc,cat",
        [
            (True, 0, "", 0),
            (False, 10, "a" * 1000, 100),
            (True, 3, "short", 50),
            (False, 0, "spam spam spam", 1),
        ],
    )
    def test_various_inputs(self, prediction_service, verified, images, desc, cat):
        is_violation, prob = prediction_service.predict(verified, images, desc, cat)
        assert isinstance(is_violation, bool)
        assert 0.0 <= prob <= 1.0
