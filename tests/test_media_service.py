"""Tests for the media service module."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.media_service import ASSISTANT_MAP
from app.services.media_service import (
    is_image_url,
    read_hyperlinks,
    web_scrape_text,
    process_image_link,
    send_message,
    send_to_all_assistants,
    process_hyperlinks,
    categories,
    call_assistant
)
from app.schemas.media import MessageRequest


# Unit test case for the function is_image_url
def test_is_image_url_true():
    url = "https://www.qgdigitalpublishing.com/publication/?i=837448&p=10&view=issueViewer"
    assert is_image_url(url) is True

def test_is_image_url_false():
    url = "https://safecarnews.com/trimble-and-qualcomm-to-deliver-precise-positioning-solutions-for-oems-tier-1s-in-new-partnership/"
    assert is_image_url(url) is False


# Unit test case for the function read_hyperlinks
@patch("app.services.media_service.pd.read_excel")
def test_read_hyperlinks(mock_read_excel):
    df = pd.DataFrame({"Unnamed: 1": ["http://example.com"]})
    mock_read_excel.return_value = df

    result = read_hyperlinks("fake.xlsx", "Sheet1")
    assert result.equals(df)
    mock_read_excel.assert_called_once_with("fake.xlsx", sheet_name="Sheet1")


# Unit test case for the function web_scrape_text success
@patch("app.services.media_service.requests.get")
def test_web_scrape_text_success(mock_get):
    # Simulate a successful HTTP response (status code 200)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'<html><body><p>Sample article text about construction</p></body></html>'
    mock_get.return_value = mock_response

    # Call the function
    result = web_scrape_text("http://example.com")

    # Assert that the result contains the expected text
    assert "Sample article text about construction" in result
    mock_get.assert_called_once_with("http://example.com", headers={'User-Agent': 'Mozilla/5.0'})


# Unit test case for the function web_scrape_text failure
@patch("app.services.media_service.requests.get")
def test_web_scrape_text_failure(mock_get):
    # Simulate a failure HTTP response (status code 404)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    # Call the function
    result = web_scrape_text("http://example.com")

    # Assert that the result indicates failure
    assert "Failed to scrape URL: http://example.com (HTTP 404)" in result
    mock_get.assert_called_once_with("http://example.com", headers={'User-Agent': 'Mozilla/5.0'})


# Unit test case for the function process_image_link success
@pytest.mark.asyncio
@patch("app.services.media_service.requests.get")
@patch("app.services.media_service.upload_image", new_callable=AsyncMock)
async def test_process_image_link_success(mock_upload_image, mock_get):
    # Simulate a successful image retrieval (status code 200)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"image content"
    mock_get.return_value = mock_response

    # Simulate a successful image upload response
    mock_upload_response = {"blob_url": "http://example.com/blob/12345"}
    mock_upload_image.return_value = mock_upload_response

    # Call the function
    result = await process_image_link("http://example.com/image.png")

    # Assert the result is the expected blob URL
    assert result == "http://example.com/blob/12345"
    mock_get.assert_called_once_with("http://example.com/image.png", headers={'User-Agent': 'Mozilla/5.0'})
    mock_upload_image.assert_called_once()

# Unit test case for the function process_image_link failure
@pytest.mark.asyncio
@patch("app.services.media_service.requests.get")
async def test_process_image_link_failure(mock_get):
    # Simulate an HTTP failure (status code 404)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    # Call the function
    result = await process_image_link("http://example.com/image.png")

    # Assert the result indicates failure
    assert result == "Failed to retrieve image: 404"
    mock_get.assert_called_once_with("http://example.com/image.png", headers={'User-Agent': 'Mozilla/5.0'})


# Unit test case for the function send_message
@pytest.mark.asyncio
@patch("app.services.media_service.requests.post")
async def test_send_message_success(mock_post):
    # Mock request data
    request_data = MessageRequest(message="Hi", stream=False)

    # Mock response from requests.post
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Success"}
    mock_post.return_value = mock_response

    # Call the function directly
    response = await send_message("assistant-123", request_data)

    # Assertions
    assert response == {"message": "Success"}
    mock_post.assert_called_once()

@pytest.mark.asyncio
@patch("app.services.media_service.requests.post")
async def test_send_message_failure(mock_post):
    request_data = MessageRequest(message="Hi", stream=False)

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_post.return_value = mock_response

    # Expect HTTPException to be raised
    with pytest.raises(Exception) as exc_info:
        await send_message("assistant-123", request_data)

    assert "Error: Server error" in str(exc_info.value)

# Unit test case for the function send_to_all_assistants
@pytest.mark.asyncio
@patch("app.services.media_service.call_assistant", new_callable=AsyncMock)
async def test_send_to_all_assistants(mock_call_assistant):
    mock_call_assistant.side_effect = [f"Response from {aid}" for aid in ASSISTANT_MAP]

    request_data = MessageRequest(message="Hello World", stream=False)

    result = await send_to_all_assistants(request_data)

    assert "consolidated_response" in result
    for aid in ASSISTANT_MAP:
        assert f"{aid}: Response from {aid}" in result["consolidated_response"]

    assert mock_call_assistant.call_count == len(ASSISTANT_MAP)

    for i, (aid, _) in enumerate(zip(ASSISTANT_MAP, mock_call_assistant.call_args_list)):
        assert f"/agents/{ASSISTANT_MAP[aid]}/messages" in mock_call_assistant.call_args_list[i][0][0]


@pytest.mark.asyncio
@patch("app.services.media_service.httpx.AsyncClient")
async def test_call_assistant_success(mock_client_class):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": "Success!"}
    
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    url = "https://mock.api"
    headers = {"Authorization": "Bearer token"}
    payload = {"message": "Hello"}

    result = await call_assistant(url, headers, payload)

    assert result == "Success!"
    mock_client.post.assert_called_once_with(url, headers=headers, json=payload)

@pytest.mark.asyncio
@patch("app.services.media_service.httpx.AsyncClient")
async def test_call_assistant_json_error(mock_client_class):
    # Mock response that raises an error when .json() is called
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await call_assistant("url", {}, {})
    assert "Unexpected error" in result


# Unit test case for the function process_hyperlinks
@pytest.mark.asyncio
@patch("app.services.media_service.openpyxl.load_workbook")
@patch("app.services.media_service.send_to_all_assistants", new_callable=AsyncMock)
@patch("app.services.media_service.send_message", new_callable=AsyncMock)
@patch("app.services.media_service.process_image_link", new_callable=AsyncMock)
@patch("app.services.media_service.web_scrape_text")
@patch("app.services.media_service.is_image_url")
@patch("app.services.media_service.read_hyperlinks")
@patch("pandas.DataFrame.to_excel")
@patch("pandas.ExcelWriter")
async def test_process_hyperlinks(
    mock_excel_writer,
    mock_to_excel,
    mock_read_hyperlinks,
    mock_is_image_url,
    mock_web_scrape_text,
    mock_process_image_link,
    mock_send_message,
    mock_send_to_all_assistants,
    mock_load_workbook
):
    # Save original categories and restore them at the end
    original_categories = categories.copy()
    categories[:] = ["Construction", "Surveying"]

    test_df = pd.DataFrame({
        "Unnamed: 1": ["http://example.com/image.png", "http://example.com/article"]
    })
    mock_read_hyperlinks.return_value = test_df

    mock_is_image_url.side_effect = [True, False]
    mock_process_image_link.return_value = "http://example.com/blob.png"
    mock_send_message.return_value = {"message": "Construction progress update"}
    mock_web_scrape_text.return_value = "Surveying improves accuracy"
    mock_send_to_all_assistants.return_value = {"consolidated_response": "Surveying improves accuracy"}

    mock_writer = MagicMock()
    mock_excel_writer.return_value.__enter__.return_value = mock_writer
    
    # Mock the sheet
    mock_sheet = MagicMock()
    mock_wb = mock_load_workbook.return_value
    mock_wb.__getitem__.return_value = mock_sheet

    await process_hyperlinks("input.xlsx", "output.xlsx", "Sheet1")

    assert mock_read_hyperlinks.called
    assert mock_load_workbook.called
    assert mock_wb.save.called
    assert mock_send_message.called
    assert mock_send_to_all_assistants.called
    
    # Restore original categories
    categories[:] = original_categories 