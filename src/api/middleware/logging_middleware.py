from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response


logger = logging.getLogger("request")


async def logging_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response: Response
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": getattr(response, "status_code", 0),
                "duration_ms": duration_ms,
            },
        )


