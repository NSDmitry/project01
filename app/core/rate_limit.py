from fastapi import Depends, Request, Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter


def rate_limiter(times: int, seconds: int):
    """Rate-limit зависимость на Redis (ключ - IP + путь).

    Если лимитер не инициализирован (например в тестах, где lifespan не
    запускается) - запрос пропускается без ограничения.
    """
    limiter = RateLimiter(times=times, seconds=seconds)

    async def dependency(request: Request, response: Response) -> None:
        if FastAPILimiter.redis is None:
            return
        await limiter(request, response)

    return Depends(dependency)
