"""Router for authentication-related API endpoints."""
from fastapi import APIRouter, HTTPException
from typing import Dict
from app.services.auth_service import get_trimble_auth_headers, get_trimble_access_token
from app.core.config import settings

# Create router with prefix and tags
router = APIRouter(
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["authentication"]
)


@router.get("/test")
async def test_authentication():
    """Test endpoint to verify Trimble Identity authentication is working."""
    try:
        # Get access token
        token = await get_trimble_access_token()
        
        # Get headers
        headers = await get_trimble_auth_headers()
        
        return {
            "status": "success",
            "message": "Authentication is working",
            "token_preview": f"{token[:20]}..." if token else "No token",
            "headers_present": "Authorization" in headers
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        ) from e


@router.get("/token")
async def get_access_token(force_refresh: bool = False):
    """Get current access token (for debugging purposes)."""
    try:
        token = await get_trimble_access_token(force_refresh=force_refresh)
        return {
            "status": "success",
            "token_preview": f"{token[:20]}..." if token else "No token",
            "message": "Token retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get access token: {str(e)}"
        ) from e


@router.get("/headers")
async def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API calls."""
    try:
        headers = await get_trimble_auth_headers()
        # Don't expose the actual token in response, just confirm it exists
        safe_headers = {
            "Content-Type": headers.get("Content-Type", ""),
            "has_authorization": "Authorization" in headers
        }
        return {
            "status": "success",
            "headers": safe_headers
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get auth headers: {str(e)}"
        ) from e


@router.post("/refresh")
async def refresh_token():
    """Force refresh the access token."""
    try:
        token = await get_trimble_access_token(force_refresh=True)
        return {
            "status": "success",
            "message": "Token refreshed successfully",
            "token_preview": f"{token[:20]}..." if token else "No token"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh token: {str(e)}"
        ) from e


@router.get("/cors-debug")
async def debug_cors():
    """Debug endpoint to check CORS configuration."""
    return {
        "status": "success",
        "environment": settings.ENVIRONMENT,
        "allowed_origins": "*",
        "message": "CORS debug info"
    }
