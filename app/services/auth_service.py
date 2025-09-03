"""Authentication service for Trimble Identity integration."""
import httpx
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class TrimbleAuthService:
    """Service for handling Trimble Identity authentication using client credentials flow."""
    
    def __init__(self):
        self.token_endpoint = "https://id.trimble.com/oauth/token"
        self.client_id = settings.TRIMBLE_CLIENT_ID
        self.client_secret = settings.TRIMBLE_CLIENT_SECRET
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._token_type: str = "Bearer"
    
    async def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            force_refresh: Force token refresh even if current token is valid
            
        Returns:
            Valid access token string
            
        Raises:
            httpx.HTTPError: If token request fails
        """
        if not force_refresh and self._is_token_valid():
            return self._access_token
        
        return await self._request_new_token()
    
    def _is_token_valid(self) -> bool:
        """Check if current token is valid and not expired."""
        if not self._access_token or not self._token_expires_at:
            return False
        
        # Add 5-minute buffer before expiration
        buffer_time = timedelta(minutes=5)
        return datetime.now() < (self._token_expires_at - buffer_time)
    
    async def _request_new_token(self) -> str:
        """
        Request a new access token using client credentials flow.
        
        Based on Trimble Identity documentation:
        https://docs.trimblecloud.com/trimble-identity/content/how-to-guides/application_authentication/tid-client-credentials-grant-flow/#example-request
        
        Returns:
            New access token string
            
        Raises:
            httpx.HTTPError: If token request fails
        """
        # Encode client_id and client_secret to Base64 for Basic Auth
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": "tda"  # Common Trimble scope for developer access
        }
        
        try:
            logger.info("Requesting token from: %s", self.token_endpoint)
            logger.info("Request data: %s", {k: v if k != "client_secret" else "***" for k, v in data.items()})
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_endpoint,
                    headers=headers,
                    data=data,
                    timeout=30.0
                )
                
                logger.info("Response status: %s", response.status_code)
                logger.info("Response headers: %s", dict(response.headers))
                
                if response.status_code != 200:
                    logger.error("Response body: %s", response.text)
                
                response.raise_for_status()
                
                token_data = response.json()
                
                # Store token information
                self._access_token = token_data["access_token"]
                self._token_type = token_data.get("token_type", "Bearer")
                
                # Calculate expiration time
                expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info("Successfully obtained new access token, expires at: %s", self._token_expires_at)
                
                return self._access_token
                
        except httpx.HTTPError as e:
            logger.error("Failed to obtain access token: %s", e)
            if hasattr(e, 'response') and e.response is not None:
                logger.error("Response status: %s", e.response.status_code)
                logger.error("Response body: %s", e.response.text)
            raise
        except Exception as e:
            logger.error("Unexpected error during token request: %s", e)
            raise
    
    async def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers with valid access token.
        
        Returns:
            Dictionary with Authorization header
        """
        token = await self.get_access_token()
        return {
            "Authorization": f"{self._token_type} {token}",
            "Content-Type": "application/json"
        }
    
    def invalidate_token(self):
        """Invalidate current token to force refresh on next request."""
        self._access_token = None
        self._token_expires_at = None
        logger.info("Access token invalidated")


# Global instance
auth_service = TrimbleAuthService()


async def get_trimble_auth_headers() -> Dict[str, str]:
    """
    Convenience function to get Trimble authentication headers.
    
    Returns:
        Dictionary with Authorization and Content-Type headers
    """
    return await auth_service.get_auth_headers()


async def get_trimble_access_token(force_refresh: bool = False) -> str:
    """
    Convenience function to get Trimble access token.
    
    Args:
        force_refresh: Force token refresh even if current token is valid
        
    Returns:
        Valid access token string
    """
    return await auth_service.get_access_token(force_refresh)
