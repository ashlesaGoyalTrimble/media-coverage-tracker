"""Tests for the media router endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app


client = TestClient(app)


@pytest.mark.asyncio
@patch("app.routers.media_router.send_to_all_assistants", new_callable=AsyncMock)
async def test_send_to_all_assistants_endpoint(mock_send_to_all_assistants):
    mock_send_to_all_assistants.return_value = {"consolidated_response": "Test response"}
    
    response = client.post(
        "/api/v1/media/agents/all/messages",
        json={"message": "Test message", "stream": False}
    )
    
    assert response.status_code == 200
    assert response.json() == {"consolidated_response": "Test response"}
    mock_send_to_all_assistants.assert_called_once()


@pytest.mark.asyncio
@patch("app.routers.media_router.send_message", new_callable=AsyncMock)
async def test_send_message_endpoint(mock_send_message):
    mock_send_message.return_value = {"message": "Test response"}
    
    response = client.post(
        "/api/v1/media/agents/test-assistant/messages",
        json={"message": "Test message", "stream": False}
    )
    
    assert response.status_code == 200
    assert response.json() == {"message": "Test response"}
    mock_send_message.assert_called_once()


@pytest.mark.asyncio
@patch("app.routers.media_router.upload_image", new_callable=AsyncMock)
async def test_upload_image_endpoint(mock_upload_image):
    mock_upload_image.return_value = {"blob_url": "https://example.com/blob/123"}
    
    # Mock file upload
    files = {"file": ("test.jpg", b"test image content", "image/jpeg")}
    
    response = client.post(
        "/api/v1/media/agents/test-assistant/sessions/test-session/images",
        files=files
    )
    
    assert response.status_code == 200
    assert response.json() == {"blob_url": "https://example.com/blob/123"}
    mock_upload_image.assert_called_once()


@pytest.mark.asyncio
@patch("app.routers.media_router.process_hyperlinks", new_callable=AsyncMock)
async def test_process_hyperlinks_endpoint(mock_process_hyperlinks):
    mock_process_hyperlinks.return_value = None
    
    response = client.post("/api/v1/media/process-hyperlinks")
    
    assert response.status_code == 200
    assert response.json() == {"status": "Processing completed. Check output file."}
    mock_process_hyperlinks.assert_called_once() 