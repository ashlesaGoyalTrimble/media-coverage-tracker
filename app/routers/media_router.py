"""Router for media-related API endpoints."""
import asyncio
import io
import requests
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from app.schemas.media import MessageRequest
from app.services.media_service import (
    call_assistant, process_hyperlinks, 
    upload_image, 
    BASE_URL, ASSISTANT_MAP
)
from app.services.auth_service import get_trimble_auth_headers, get_trimble_access_token
from app.core.config import settings

# Create router with prefix and tags
router = APIRouter(
    prefix=f"{settings.API_V1_STR}/media",
    tags=["media"]
)


@router.post("/agents/all/messages")
async def send_to_all_assistants(request: MessageRequest):
    """Route to send messages to all assistants and consolidate responses."""
    try:
        headers = await get_trimble_auth_headers()
        payload = request.dict()
        tasks = [
            call_assistant(f"{BASE_URL}/agents/{ASSISTANT_MAP[aid]}/messages", headers, payload)
            for aid in ASSISTANT_MAP
        ]
        results = await asyncio.gather(*tasks)
        consolidated = "\n".join(f"{aid}: {result}" for aid, result in zip(ASSISTANT_MAP.keys(), results))
        return {"consolidated_response": consolidated}
    except Exception as e:
        print(f"catched error in send_to_all_assistants route: {e}")
        return {"consolidated_response": "Error: catched error"}


@router.post("/agents/{assistant_id}/messages")
async def send_message(assistant_id: str, request: MessageRequest):
    """Route to send a message to a specific assistant."""
    try:
        url = f"{BASE_URL}/agents/{assistant_id}/messages"
        headers = await get_trimble_auth_headers()
        response = requests.post(url, headers=headers, json=request.dict())

        if response.status_code == 200:
            return response.json()
        else:
            print(f"catched error in send_message route: HTTP {response.status_code}")
            raise HTTPException(status_code=response.status_code, detail=f"Error: {response.text}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"catched error in send_message route: {e}")
        raise HTTPException(status_code=500, detail="Error: catched error")


@router.post("/agents/{assistant_id}/sessions/{session_id}/images")
async def upload_image_route(assistant_id: str, session_id: str, file: UploadFile):
    """Route to upload an image to an assistant."""
    try:
        return await upload_image(assistant_id, session_id, file)
    except Exception as e:
        print(f"catched error in upload_image_route: {e}")
        return {"error": "catched error"}


# @router.post("/process-hyperlinks")
# async def trigger_process_hyperlinks(media_sheet_name: str = Query(..., description="Name of the sheet in the Excel file")):
#     """Process hyperlinks from the Excel sheet and store responses."""
#     result = await process_hyperlinks(
#         settings.EXCEL_FILE_PATH, 
#         "assistant_responses.xlsx", 
#         media_sheet_name
#     )
#     return {"status": result}

@router.post("/process-hyperlinks")
async def trigger_process_hyperlinks(
    file: UploadFile = File(..., description="Excel file to process"),
    sheet_name: str = Form(..., description="Name of the sheet in the Excel file")
):
    """Process hyperlinks from uploaded Excel file and return the processed file."""
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            print("catched error: invalid file type")
            raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx or .xls)")
        
        # Process the uploaded file
        processed_file_bytes = await process_hyperlinks(file, sheet_name)
        
        # Return the processed file as a download
        return StreamingResponse(
            io.BytesIO(processed_file_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=processed_{file.filename}"
            }
        )
    except HTTPException:
        # Re-raise HTTPException as is
        raise
    except Exception as e:
        print(f"catched error in trigger_process_hyperlinks: {e}")
        # Return original file if processing fails
        try:
            await file.seek(0)
            original_file_bytes = await file.read()
            return StreamingResponse(
                io.BytesIO(original_file_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=original_{file.filename}"
                }
            )
        except:
            raise HTTPException(status_code=500, detail="Error: catched error")