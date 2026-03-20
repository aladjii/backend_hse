import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        status = str(response.status_code)
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=path, status=status).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=path).observe(duration)

        return response
