from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Load environment variables
load_dotenv()

from limiter import limiter

# Import all routers
from auth import router as auth_router
from routers.user import router as user_router
from routers.admin import router as admin_router
from routers.config import router as config_router
from routers.binance import router as binance_router
from routers.support import router as support_router
from routers.stripe import router as stripe_router
from routers.subscriptions import router as subscriptions_router
from routers.setup import router as setup_router

IS_PROD = os.getenv("ENVIRONMENT", "development").lower() == "production"

# ==========================================
# 1. APP INITIALIZATION
# ==========================================
app = FastAPI(
    title="Trading App Backend API",
    description="Trading platform with admin control, consent-gated Binance trading, and Stripe payments",
    version="1.0.0",
    # API docs are disabled in production (set ENVIRONMENT=production)
    docs_url=None if IS_PROD else "/api/docs",
    redoc_url=None if IS_PROD else "/api/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ==========================================
# 2. STATIC FILES (For Avatar Uploads)
# ==========================================
# Create static folder automatically if it doesn't exist
os.makedirs("static/avatars", exist_ok=True)

# Mount the static directory to serve images
# URL: http://localhost:8000/api/v1/static/avatars/filename.jpg
app.mount("/api/v1/static", StaticFiles(directory="static"), name="static")

# ==========================================
# 3. CORS MIDDLEWARE (SECURITY)
# ==========================================
# Allow frontend domains to access the API
origins = [
    "http://localhost:3000",      # Next.js development server
    "http://127.0.0.1:3000",
    os.getenv("FRONTEND_URL", "http://localhost:3000"),  # Production domain
]
if IS_PROD:
    origins = [o for o in origins if "localhost" not in o and "127.0.0.1" not in o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ==========================================
# 4. GLOBAL EXCEPTION HANDLER (BUG PREVENTION)
# ==========================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    If any unexpected error occurs, it prevents the server from crashing
    and sends a clean JSON response to the frontend.
    """
    import logging
    logging.getLogger("uvicorn.error").exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Please try again later."},
    )

# ==========================================
# 5. INCLUDE ALL ROUTERS
# ==========================================
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/api/v1/user", tags=["User Dashboard"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin Panel"])
app.include_router(config_router, prefix="/api/v1/config", tags=["Dynamic Config"])
app.include_router(binance_router, prefix="/api/v1/binance", tags=["Binance API"])
app.include_router(support_router, prefix="/api/v1/support", tags=["Live Support"])
app.include_router(stripe_router, prefix="/api/v1/stripe", tags=["Stripe Payments"])
app.include_router(subscriptions_router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
app.include_router(setup_router, prefix="/api/v1/setup", tags=["Setup"])

# Create tables on first start (safe to repeat)
from database import engine
from models import Base
Base.metadata.create_all(bind=engine)

# Auto-seed default admin, widgets, and plans on first launch
try:
    from seed_data import seed_database
    seed_database()
except Exception as _seed_err:
    import logging
    logging.getLogger("uvicorn.error").warning("Initial seed skipped or already applied: %s", _seed_err)


# ==========================================
# 6. HEALTH CHECK ROUTE
# ==========================================
@app.get("/", tags=["Health Check"])
def health_check():
    """Check if the server is running."""
    return {
        "status": "success",
        "message": "Trading App Backend is running successfully!",
        "version": "1.0.0"
    }

# ==========================================
# 7. RUN SERVER (For Local Development)
# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=not IS_PROD)