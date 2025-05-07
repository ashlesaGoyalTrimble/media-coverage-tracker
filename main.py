"""Main application module for the Trimble Media Coverage Tracker."""
from fastapi import FastAPI
import uvicorn
from app.routers import media_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for tracking and analyzing media coverage",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Include routers
app.include_router(media_router.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True) 