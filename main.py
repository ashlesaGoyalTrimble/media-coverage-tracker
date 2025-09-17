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


# Add CORS middleware - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        "cors_origins": "*",
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":

    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True) 

