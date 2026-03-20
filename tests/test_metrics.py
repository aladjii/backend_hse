from metrics import (
    DB_QUERY_DURATION,
    MODEL_PREDICTION_PROBABILITY,
    PREDICTION_DURATION,
    PREDICTION_ERRORS_TOTAL,
    PREDICTIONS_TOTAL,
)


class TestMetricsExist:
    def test_predictions_total(self):
        # prometheus Counter stores _name without _total suffix
        assert PREDICTIONS_TOTAL._name == "predictions"

    def test_prediction_duration(self):
        assert PREDICTION_DURATION._name == "prediction_duration_seconds"

    def test_prediction_errors(self):
        assert PREDICTION_ERRORS_TOTAL._name == "prediction_errors"

    def test_db_query_duration(self):
        assert DB_QUERY_DURATION._name == "db_query_duration_seconds"

    def test_model_probability(self):
        assert MODEL_PREDICTION_PROBABILITY._name == "model_prediction_probability"

    def test_prediction_increments(self):
        before = PREDICTIONS_TOTAL.labels(result="test")._value.get()
        PREDICTIONS_TOTAL.labels(result="test").inc()
        after = PREDICTIONS_TOTAL.labels(result="test")._value.get()
        assert after == before + 1
