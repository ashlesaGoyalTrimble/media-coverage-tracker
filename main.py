"""Main application module for the Trimble Media Coverage Tracker."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.routers import media_router, auth_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for tracking and analyzing media coverage",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS based on environment
cors_origins = settings.BACKEND_CORS_ORIGINS
if settings.ENVIRONMENT == "production":
    # In production, use exact origins for security
    cors_origins = settings.BACKEND_CORS_ORIGINS
elif settings.ENVIRONMENT == "development":
    # In development, allow additional origins or use wildcard if needed
    cors_origins = settings.BACKEND_CORS_ORIGINS + ["*"] if not any("*" in origin for origin in settings.BACKEND_CORS_ORIGINS) else ["*"]
else:
    # Default to allowing configured origins
    cors_origins = settings.BACKEND_CORS_ORIGINS

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
)

# Include routers
app.include_router(auth_router.router)
app.include_router(media_router.router)

# Add a simple health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "cors_origins": cors_origins,
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":

    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True) 

