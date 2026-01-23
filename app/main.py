"""
RapidReportz Backend - Production Grade Main Application
Zero Errors | High Security | Enterprise Ready
"""

import sys
import os
import logging
from contextlib import asynccontextmanager

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import sentry_sdk
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# SENTRY MONITORING (Production)
# ============================================

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        environment=os.getenv("ENVIRONMENT", "production"),
    )
    logger.info("✅ Sentry monitoring enabled")


# ============================================
# RATE LIMITING
# ============================================

limiter = Limiter(key_func=get_remote_address)


# ============================================
# APPLICATION LIFESPAN
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 RapidReportz Backend Starting Up")
    logger.info("=" * 60)
    yield
    logger.info("🛑 RapidReportz Backend Shutting Down")
    app = FastAPI(title="RapidReportz API", lifespan=lifespan)
    
    # Verify database connection
    try:
        from core.database import engine, Base
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection verified")
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise
    
    # Verify configuration
    from core.config import settings
    
    config_warnings = []
    
    if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-change-in-production":
        logger.error("❌ CRITICAL: SECRET_KEY not configured properly!")
        raise ValueError("SECRET_KEY must be set in environment variables")
    
    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY == "your-jwt-secret-key":
        logger.error("❌ CRITICAL: JWT_SECRET_KEY not configured properly!")
        raise ValueError("JWT_SECRET_KEY must be set in environment variables")
    
    # Optional warnings
    if not settings.TWILIO_ACCOUNT_SID:
        config_warnings.append("📱 SMS not configured - OTP via SMS will not work")
    
    if config_warnings:
        logger.info("")
        logger.info("=" * 60)
        logger.info("⚠️  CONFIGURATION WARNINGS:")
        for warning in config_warnings:
            logger.info(f"   {warning}")
        logger.info("=" * 60)
        logger.info("")
    
    logger.info("✅ All critical configurations verified")
    logger.info("🎯 Application ready to accept requests")
    logger.info("")
    
    yield
    
    # Shutdown
    logger.info("🛑 RapidReportz Backend Shutting Down")


# ============================================
# CREATE APPLICATION
# ============================================

app = FastAPI(
    title="RapidReportz API",
    description="Enterprise Report Management System - Production Grade",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================
# CORS & SECURITY MIDDLEWARE
# ============================================

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import secrets

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [
    "https://rapidreportz.com",
    "https://www.rapidreportz.com",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-Request-ID",
    ],
    expose_headers=[
        "Content-Length",
        "Content-Type",
        "X-Request-ID",
    ],
    max_age=3600,
)

logger.info("✅ CORS middleware configured")


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        request_id = request.headers.get("X-Request-ID", secrets.token_hex(8))
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = request_id
        
        return response

app.add_middleware(SecurityHeadersMiddleware)
logger.info("✅ Security headers middleware configured")


# ============================================
# GLOBAL EXCEPTION HANDLERS
# ============================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} [Request ID: {request_id}]")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "request_id": request_id
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"Validation error: {errors} [Request ID: {request_id}]")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": errors,
                "request_id": request_id
            }
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    logger.error(f"Unhandled exception: {str(exc)} [Request ID: {request_id}]", exc_info=True)
    
    # Send to Sentry if configured
    if SENTRY_DSN:
        sentry_sdk.capture_exception(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error",
                "request_id": request_id
            }
        }
    )


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health", tags=["System"])
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Comprehensive health check"""
    from core.database import engine
    from sqlalchemy import text
    
    health_status = {
        "status": "healthy",
        "version": "2.0.0",
        "checks": {}
    }
    
    # Database check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
    
    # Configuration check
    from core.config import settings
    health_status["checks"]["config"] = "healthy" if settings.SECRET_KEY else "unhealthy"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(
        status_code=status_code,
        content=health_status
    )


# ============================================
# API ROUTES
# ============================================

from api.routes import auth, users, wallet, payment, templates, tickets, activities, dashboard

# Authentication
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
logger.info("✅ Auth routes registered")

# Users
app.include_router(users.router, prefix="/api/users", tags=["Users"])
logger.info("✅ User routes registered")

# Wallet
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
logger.info("✅ Wallet routes registered")

# Payment
app.include_router(payment.router, prefix="/api/payment", tags=["Payment"])
logger.info("✅ Payment routes registered")

# Templates
app.include_router(templates.router, prefix="/api/templates", tags=["Templates"])
logger.info("✅ Template routes registered")

# Tickets
app.include_router(tickets.router, prefix="/api/tickets", tags=["Support Tickets"])
logger.info("✅ Ticket routes registered")

# Activities
app.include_router(activities.router, prefix="/api/activities", tags=["Activities"])
logger.info("✅ Activity routes registered")

# Dashboard
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
logger.info("✅ Dashboard routes registered")


# ============================================
# ROOT ENDPOINT
# ============================================

@app.get("/", tags=["System"])
async def root():
    """Root endpoint"""
    return {
        "name": "RapidReportz API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        access_log=True
    )
