from metrics import (
    DB_QUERY_DURATION,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
    MODEL_PREDICTION_PROBABILITY,
    PREDICTION_DURATION,
    PREDICTION_ERRORS_TOTAL,
    PREDICTIONS_TOTAL,
)


class TestMetricsExist:
    def test_http_requests_total(self):
        assert HTTP_REQUESTS_TOTAL._name == "http_requests"

    def test_http_request_duration(self):
        assert HTTP_REQUEST_DURATION._name == "http_request_duration_seconds"

    def test_predictions_total(self):
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

    def test_http_requests_increments(self):
        before = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/test", status="200")._value.get()
        HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/test", status="200").inc()
        after = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/test", status="200")._value.get()
        assert after == before + 1
