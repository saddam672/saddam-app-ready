from fastapi import Request
from slowapi import Limiter


def client_ip(request: Request) -> str:
    """Real client IP (works behind nginx / a load balancer)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)
