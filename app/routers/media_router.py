"""Router for media-related API endpoints."""
import asyncio
import requests
from fastapi import APIRouter, HTTPException, UploadFile,Query
from app.schemas.media import MessageRequest
from app.services.media_service import (
    call_assistant, process_hyperlinks, 
    upload_image, 
    BASE_URL, ASSISTANT_MAP, HEADERS
)
from app.core.config import settings

# Create router with prefix and tags
router = APIRouter(
    prefix=f"{settings.API_V1_STR}/media",
    tags=["media"]
)


@router.post("/agents/all/messages")
async def send_to_all_assistants(request: MessageRequest):
    """Route to send messages to all assistants and consolidate responses."""
    payload = request.dict()
    tasks = [
        call_assistant(f"{BASE_URL}/agents/{ASSISTANT_MAP[aid]}/messages", HEADERS, payload)
        for aid in ASSISTANT_MAP
    ]
    results = await asyncio.gather(*tasks)
    consolidated = "\n".join(f"{aid}: {result}" for aid, result in zip(ASSISTANT_MAP.keys(), results))
    return {"consolidated_response": consolidated}


@router.post("/agents/{assistant_id}/messages")
async def send_message(assistant_id: str, request: MessageRequest):
    """Route to send a message to a specific assistant."""
    url = f"{BASE_URL}/agents/{assistant_id}/messages"
    response = requests.post(url, headers=HEADERS, json=request.dict())

    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=f"Error: {response.text}")


@router.post("/agents/{assistant_id}/sessions/{session_id}/images")
async def upload_image_route(assistant_id: str, session_id: str, file: UploadFile):
    """Route to upload an image to an assistant."""
    return await upload_image(assistant_id, session_id, file)


@router.post("/process-hyperlinks")
async def trigger_process_hyperlinks(media_sheet_name: str = Query(..., description="Name of the sheet in the Excel file")):
    """Process hyperlinks from the Excel sheet and store responses."""
    await process_hyperlinks(
        settings.EXCEL_FILE_PATH, 
        "assistant_responses.xlsx", 
        media_sheet_name
    )
    return {"status": "Processing completed. Check output file."} 