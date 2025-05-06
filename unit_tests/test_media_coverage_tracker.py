import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import pandas as pd

from src.media_coverage_tracker import ASSISTANT_MAP
from src.media_coverage_tracker import (
    is_image_url,
    read_hyperlinks,
    web_scrape_text,
    process_image_link,
    send_message,
    send_to_all_assistants,
    process_hyperlinks,
    MessageRequest,
    categories,
    call_assistant,
    app
)

import io
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

client = TestClient(app)

#Unit test case for the function is_image_url
def test_is_image_url_true():
    url = "https://www.qgdigitalpublishing.com/publication/?i=837448&p=10&view=issueViewer"
    assert is_image_url(url) is True

def test_is_image_url_false():
    url = "https://safecarnews.com/trimble-and-qualcomm-to-deliver-precise-positioning-solutions-for-oems-tier-1s-in-new-partnership/"
    assert is_image_url(url) is False


#Unit test case for the function read_hyperlinks
@patch("src.media_coverage_tracker.pd.read_excel")
def test_read_hyperlinks(mock_read_excel):
    df = pd.DataFrame({"Unnamed: 1": ["http://example.com"]})
    mock_read_excel.return_value = df

    result = read_hyperlinks("fake.xlsx", "Sheet1")
    assert result.equals(df)
    mock_read_excel.assert_called_once_with("fake.xlsx", sheet_name="Sheet1")


#Unit test case for the function web_scrape_text success
@patch("src.media_coverage_tracker.requests.get")
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


#Unit test case for the function web_scrape_text failure
@patch("src.media_coverage_tracker.requests.get")
def test_web_scrape_text_failure(mock_get):
    # Simulate a failure HTTP response (status code 404)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    # Call the function
    result = web_scrape_text("http://example.com")

    # Assert that the result indicates failure
    assert result == "Failed to retrieve content: 404"
    mock_get.assert_called_once_with("http://example.com", headers={'User-Agent': 'Mozilla/5.0'})


#Unit test case for the function process_image_link success
@pytest.mark.asyncio
@patch("src.media_coverage_tracker.requests.get")
@patch("src.media_coverage_tracker.upload_image", new_callable=AsyncMock)
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

#Unit test case for the function process_image_link failure
@pytest.mark.asyncio
@patch("src.media_coverage_tracker.requests.get")
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


#Unit test case for the function send_message
@pytest.mark.asyncio
@patch("src.media_coverage_tracker.requests.post")
async def test_send_message_success(mock_post):
    # Mock request data
    request_data = MessageRequest(message="Hi", stream="false")

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
@patch("src.media_coverage_tracker.requests.post")
async def test_send_message_failure(mock_post):
    request_data = MessageRequest(message="Hi", stream="false")

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_post.return_value = mock_response

    # Expect HTTPException to be raised
    with pytest.raises(Exception) as exc_info:
        await send_message("assistant-123", request_data)

    assert "Error: Server error" in str(exc_info.value)

#Unit test case for the function send_to_all_assistants
@pytest.mark.asyncio
@patch("src.media_coverage_tracker.call_assistant", new_callable=AsyncMock)
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
@patch("src.media_coverage_tracker.httpx.AsyncClient")
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
@patch("src.media_coverage_tracker.httpx.AsyncClient")
async def test_call_assistant_json_error(mock_client_class):
    # Mock response that raises an error when .json() is called
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("Invalid JSON")

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client_class.return_value.__aenter__.return_value = mock_client

    result = await call_assistant("url", {}, {})
    assert "Error parsing response JSON" in result


@patch("src.media_coverage_tracker.requests.post") 
def test_upload_image_returns_blob_url(mock_post):
    # Prepare the fake blob_url response from the mock
    fake_blob_url = "https://blob.trimble.com/blob.png"
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"blob_url": fake_blob_url}
    mock_post.return_value = mock_response

    # Create a dummy image file
    file_content = b"fake image content"
    files = {
        "file": ("test_image.png", io.BytesIO(file_content), "image/png")
    }

    response = client.post(
        "/agents/test-agent/sessions/f3a7c066-7c89-44b1-9471-589eb7a26814/images",
        files=files
    )

    assert response.status_code == 200
    data = response.json()
    assert "blob_url" in data
    assert data["blob_url"] == fake_blob_url

    # Verify the requests.post call was made once with expected args
    mock_post.assert_called_once()




#Unit test case for the function process_hyperlinks
@pytest.mark.asyncio
@patch("src.media_coverage_tracker.send_to_all_assistants", new_callable=AsyncMock)
@patch("src.media_coverage_tracker.send_message", new_callable=AsyncMock)
@patch("src.media_coverage_tracker.process_image_link", new_callable=AsyncMock)
@patch("src.media_coverage_tracker.web_scrape_text")
@patch("src.media_coverage_tracker.is_image_url")
@patch("src.media_coverage_tracker.read_hyperlinks")
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
):
    categories[:] = ["Construction", "Surveying"]

    test_df = pd.DataFrame({
        "Unnamed: 1": ["http://example.com/image.png", "http://example.com/article"]
    })
    mock_read_hyperlinks.return_value = test_df

    mock_is_image_url.side_effect = [True, False]
    mock_process_image_link.return_value = "http://example.com/blob.png"
    mock_send_message.return_value = {"converted_text": "Construction progress update"}
    mock_web_scrape_text.return_value = "Surveying improves accuracy"
    mock_send_to_all_assistants.return_value = {"consolidated_response": "Surveying improves accuracy"}

    mock_writer = MagicMock()
    mock_excel_writer.return_value.__enter__.return_value = mock_writer

    await process_hyperlinks("input.xlsx", "output.xlsx", "Sheet1")

    assert mock_read_hyperlinks.called
    assert mock_to_excel.called
    assert mock_send_message.called
    assert mock_send_to_all_assistants.called

