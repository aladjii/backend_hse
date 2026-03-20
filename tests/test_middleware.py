import pytest

from metrics import HTTP_REQUESTS_TOTAL


class TestPrometheusMiddleware:
    @pytest.mark.asyncio
    async def test_health_increments_http_counter(self, client):
        before = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/health", status="200")._value.get()
        resp = await client.get("/health")
        assert resp.status_code == 200
        after = HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/health", status="200")._value.get()
        assert after >= before + 1
