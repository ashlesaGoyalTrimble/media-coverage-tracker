"""Media-related services for processing articles and images."""
import requests
from typing import List
import io
import asyncio
import httpx
import traceback
import pandas as pd
import time
from bs4 import BeautifulSoup
import openpyxl
from io import BytesIO
import os
from urllib.parse import urljoin
import pytesseract
from PIL import Image
import tempfile
import base64
import re
import uuid
from selenium import webdriver
from fastapi.responses import StreamingResponse
from openpyxl.utils.dataframe import dataframe_to_rows
from fastapi import HTTPException, UploadFile, File

from app.schemas.media import MessageRequest, AssistantCreateRequest, Tool


BASE_URL = "https://agw.construction-integration.trimble.cloud/trimbledeveloperprogram/assistants/v1"
API_ENDPOINT = "http://localhost:8000/agents/all/messages"

HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjEiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2lkLnRyaW1ibGUuY29tIiwiZXhwIjoxNzQ3MTIxMzUxLCJuYmYiOjE3NDcxMTc3NTEsImlhdCI6MTc0NzExNzc1MSwianRpIjoiZDg5NDdhNTVkZDA4NGNiNWIxNGI0NjVlNDAzZjdmOWQiLCJqd3RfdmVyIjoyLCJzdWIiOiI2N2UxN2FjNi1iZDBmLTQzNjAtYTJiYy02Y2NmYjA1NGU5ZmMiLCJpZGVudGl0eV90eXBlIjoidXNlciIsImFtciI6WyJmZWRlcmF0ZWQiLCJva3RhX3RyaW1ibGUiLCJtZmEiXSwiYXV0aF90aW1lIjoxNzQ3MTE3NzQ5LCJhenAiOiI2N2FlNjNlMy1jZGUxLTRhYzEtOTRmNi0yMmIwMGFhZGM1MDYiLCJhY2NvdW50X2lkIjoidHJpbWJsZS1wbGFjZWhvbGRlci1vZi1lbXBsb3llZXMiLCJhdWQiOlsiNjdhZTYzZTMtY2RlMS00YWMxLTk0ZjYtMjJiMDBhYWRjNTA2Il0sInNjb3BlIjoidGRhIiwiZGF0YV9yZWdpb24iOiJ1cyJ9.oeiafSkCEsXa82jv9zWNcePw-sczxQzgaKJsd_gHNDN0tfYUrOKbBTh8lmTFWa62jy69y8ZpvACC0UknXiR-JiveOR7n-T-szSa-ydsP8gJqjDRP9d2578QVU3zsInG7vm7YeY-kTFzSdoX6PSJlRrz1sGykBlmlor8kI89RhAOzGVNp-HoSGzd04RNkb3yRkJmYvnh4cU68sNJF-2ilLn_MAnwqH24jboIHtAkEYq2A1m5s5-6Mgc09P2-YN5HBb_VRU9yWCcQx_mT-wQA6pjtZ5V4FieQfPnntHB5_fqPFargNVWRL8DcVI09TcCuEbesEsdGlGF-9Bz31EK1TTA",
    "Content-Type": "application/json",
}

ASSISTANT_MAP = {
    "Content-type": "trimble-media-content-type",
    "Corporate": "trimble-media-corporate",
    "Media-types": "trimble-media-media-types",
    "Field-systems": "trimble-media-field-systems",
    "aeco": "trimble-media-coverage-aeco",
}

categories = [
    "Publication", "Article Title & Link", "Date", "Qtr", "Country", "Global Region Reached",
    "Corporate", "AECO", "B2W", "MEP", "SketchUp Visualization", "SketchUp Collaboration",
    "Structures", "Viewpoint", "Industry Cloud/TC1", "Civil Design & Engineering",
    "Civil Construction (CIS)", "O&PS", "FIELD SYSTEMS", "Civil", "Geospatial / BCFS",
    "Applanix", "OEM GNSS", "TAP / Auto IoT", "Paving / Milling", "Marine", "Drilling / Piling",
    "Earthmoving / Machine Control", "Surveying (human / drone / machine)", 
    "Bidding / Estimating / Takeoff", "Jobsite connectivity / F2O", "Safety",
    "Asset capture and inspection", "Monitoring", "Reality capture",
    "BIM / Model-based workflows", "Mixed reality", "Crash & Crime",
    "Field Systems Themes", "TRANSPORTATION & LOG.", "Forestry", "Mobility",
    "Transporeon", "MAPS", "Rail", "Thought Leadership / Byline", "Journalist Feature",
    "Customer Focus", "Award", "Podcast", "News release pickup", "Mention", "GREAT ONE",
    "Trimble in video", "Trimble quote", "Trimble image", "Trimble title mention",
    "T1: Business / Finance", "T1: Dailies", "T1: TV/Radio", "T1: Technology", "T1: Industry",
    "T2: Dailies, Business, Regional", "T2: Trade", "T2: Technology", "T2: Industry (adjacent)",
    "AI/ML", "Infrastructure", "Trimble revenue / business growth", 
    "Digital 2 Physical / Ph2Dig", "Connected Ecosystems", "Sustainability",
    "Trust & Security", "Workforce Optimization", "Innovation"]


# Function to read hyperlinks from Excel
async def read_hyperlinks(file: UploadFile, sheet_name: str) -> pd.DataFrame:
    """Reads URLs from an uploaded Excel file."""
    try:
        contents = await file.read()
        return pd.read_excel(BytesIO(contents), sheet_name=sheet_name)
    except Exception as e:
        print(f"catched error in read_hyperlinks: {e}")
        return pd.DataFrame()


# Function to extract text from web articles
def web_scrape_text(url: str) -> str:
    """Extracts article text from the given URL."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup.get_text().strip()
        else:
            return f"Failed to scrape URL: {url} (HTTP {response.status_code})"
    except Exception as e:
        print(f"catched error in web_scrape_text: {e}")
        return "Error: catched error"


# Function to call the assistant API with the scraped text
async def call_assistant(url: str, headers: dict, payload: dict) -> str:
    """Sends a message to the assistant API."""
    try:
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    json_data = response.json()
                    return json_data.get("message", str(json_data))
            except httpx.ReadTimeout:
                if attempt < 2:
                    await asyncio.sleep(2)
                else:
                    return "Error: Assistant request timed out."
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2)
                else:
                    return f"Unexpected error: {e}"
        return "Error: catched error"
    except Exception as e:
        print(f"catched error in call_assistant: {e}")
        return "Error: catched error"


# Function to upload an image and get its blob URL
async def upload_image(assistant_id: str, session_id: str, file: UploadFile) -> dict:
    """Uploads an image to the assistant and returns the response."""
    try:
        url = f"{BASE_URL}/agents/{assistant_id}/sessions/{session_id}/images"
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = requests.post(url, headers=HEADERS, files=files)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Upload failed with status code {response.status_code}"}
    except Exception as e:
        print(f"catched error in upload_image: {e}")
        return {"error": "catched error"}


# Function to check if a URL is an image
def is_image_url(url: str) -> bool:
    """Checks whether the given URL is likely to be an image."""
    try:
        return "qg" in url.lower() or "digital" in url.lower()
    except Exception as e:
        print(f"catched error in is_image_url: {e}")
        return False

# Writes the output to the Excel file in memory
def write_output_to_excel_memory(file_contents: bytes, df: pd.DataFrame) -> bytes:
    """Writes the output to the Excel file and returns the updated file as bytes."""
    try:
        wb = openpyxl.load_workbook(BytesIO(file_contents))
        sheet = wb["MediaScorecard"]  # Updated sheet name

        # Fixed known column range: CORP. (column 13) to CORPORATE THEMES (column 75)
        start_col_idx = 13
        end_col_idx = 75

        # Clear existing "X" marks from category columns (from row 5 to end)
        for row in sheet.iter_rows(min_row=5, max_row=sheet.max_row):
            for col_idx in range(start_col_idx, end_col_idx + 1):
                row[col_idx - 1].value = None

        # Write updated "X" values from the dataframe (assumes df starts with same headers)
        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=5):
            for c_idx, value in enumerate(row, start=1):
                sheet.cell(row=r_idx, column=c_idx, value=value)

        # Save to BytesIO and return the bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        print(f"catched error in write_output_to_excel_memory: {e}")
        return file_contents  # Return original file if processing fails

# Function to process an image link and return its blob URL
async def process_image_link(url: str) -> str:
    """Uploads image to the assistant and returns its blob URL."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            file_content = BytesIO(response.content)
            file = UploadFile(filename=url.split("/")[-1], file=file_content)
            upload_response = await upload_image("trimble-media-image-2-text", str(uuid.uuid4()), file)
            return upload_response.get("blob_url", "No blob URL found")
        else:
            return f"Failed to retrieve image: {response.status_code}"
    except Exception as e:
        print(f"catched error in process_image_link: {e}")
        return "Error: catched error"


# Sends a message to a specific assistant and returns the response
async def send_message(assistant_id: str, request: MessageRequest):
    try:
        url = f"{BASE_URL}/agents/{assistant_id}/messages"
        headers = {
            "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjEiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2lkLnRyaW1ibGUuY29tIiwiZXhwIjoxNzQ3MTIxMzUxLCJuYmYiOjE3NDcxMTc3NTEsImlhdCI6MTc0NzExNzc1MSwianRpIjoiZDg5NDdhNTVkZDA4NGNiNWIxNGI0NjVlNDAzZjdmOWQiLCJqd3RfdmVyIjoyLCJzdWIiOiI2N2UxN2FjNi1iZDBmLTQzNjAtYTJiYy02Y2NmYjA1NGU5ZmMiLCJpZGVudGl0eV90eXBlIjoidXNlciIsImFtciI6WyJmZWRlcmF0ZWQiLCJva3RhX3RyaW1ibGUiLCJtZmEiXSwiYXV0aF90aW1lIjoxNzQ3MTE3NzQ5LCJhenAiOiI2N2FlNjNlMy1jZGUxLTRhYzEtOTRmNi0yMmIwMGFhZGM1MDYiLCJhY2NvdW50X2lkIjoidHJpbWJsZS1wbGFjZWhvbGRlci1vZi1lbXBsb3llZXMiLCJhdWQiOlsiNjdhZTYzZTMtY2RlMS00YWMxLTk0ZjYtMjJiMDBhYWRjNTA2Il0sInNjb3BlIjoidGRhIiwiZGF0YV9yZWdpb24iOiJ1cyJ9.oeiafSkCEsXa82jv9zWNcePw-sczxQzgaKJsd_gHNDN0tfYUrOKbBTh8lmTFWa62jy69y8ZpvACC0UknXiR-JiveOR7n-T-szSa-ydsP8gJqjDRP9d2578QVU3zsInG7vm7YeY-kTFzSdoX6PSJlRrz1sGykBlmlor8kI89RhAOzGVNp-HoSGzd04RNkb3yRkJmYvnh4cU68sNJF-2ilLn_MAnwqH24jboIHtAkEYq2A1m5s5-6Mgc09P2-YN5HBb_VRU9yWCcQx_mT-wQA6pjtZ5V4FieQfPnntHB5_fqPFargNVWRL8DcVI09TcCuEbesEsdGlGF-9Bz31EK1TTA"
        }
        payload = request.dict()
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                print(f"catched error in send_message json parsing: {e}")
                return {"message": "Error: catched error"}
        else:
            print(f"catched error in send_message http error: {response.status_code}")
            return {"message": "Error: catched error"}
    except Exception as e:
        print(f"catched error in send_message: {e}")
        return {"message": "Error: catched error"}


# Sends a message to all assistants and consolidates the responses
async def send_to_all_assistants(request: MessageRequest):
    try:
        headers = {
            "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjEiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2lkLnRyaW1ibGUuY29tIiwiZXhwIjoxNzQ3MTIxMzUxLCJuYmYiOjE3NDcxMTc3NTEsImlhdCI6MTc0NzExNzc1MSwianRpIjoiZDg5NDdhNTVkZDA4NGNiNWIxNGI0NjVlNDAzZjdmOWQiLCJqd3RfdmVyIjoyLCJzdWIiOiI2N2UxN2FjNi1iZDBmLTQzNjAtYTJiYy02Y2NmYjA1NGU5ZmMiLCJpZGVudGl0eV90eXBlIjoidXNlciIsImFtciI6WyJmZWRlcmF0ZWQiLCJva3RhX3RyaW1ibGUiLCJtZmEiXSwiYXV0aF90aW1lIjoxNzQ3MTE3NzQ5LCJhenAiOiI2N2FlNjNlMy1jZGUxLTRhYzEtOTRmNi0yMmIwMGFhZGM1MDYiLCJhY2NvdW50X2lkIjoidHJpbWJsZS1wbGFjZWhvbGRlci1vZi1lbXBsb3llZXMiLCJhdWQiOlsiNjdhZTYzZTMtY2RlMS00YWMxLTk0ZjYtMjJiMDBhYWRjNTA2Il0sInNjb3BlIjoidGRhIiwiZGF0YV9yZWdpb24iOiJ1cyJ9.oeiafSkCEsXa82jv9zWNcePw-sczxQzgaKJsd_gHNDN0tfYUrOKbBTh8lmTFWa62jy69y8ZpvACC0UknXiR-JiveOR7n-T-szSa-ydsP8gJqjDRP9d2578QVU3zsInG7vm7YeY-kTFzSdoX6PSJlRrz1sGykBlmlor8kI89RhAOzGVNp-HoSGzd04RNkb3yRkJmYvnh4cU68sNJF-2ilLn_MAnwqH24jboIHtAkEYq2A1m5s5-6Mgc09P2-YN5HBb_VRU9yWCcQx_mT-wQA6pjtZ5V4FieQfPnntHB5_fqPFargNVWRL8DcVI09TcCuEbesEsdGlGF-9Bz31EK1TTA"
        }
        payload = request.dict()
        tasks = [
            call_assistant(f"{BASE_URL}/agents/{ASSISTANT_MAP[aid]}/messages", headers, payload)
            for aid in ASSISTANT_MAP
        ]

        results = await asyncio.gather(*tasks)

        consolidated = "\n".join(
            f"{aid}: {result}" for (aid, result) in zip(ASSISTANT_MAP.keys(), results)
        )
        return {"consolidated_response": consolidated}
    except Exception as e:
        print(f"catched error in send_to_all_assistants: {e}")
        return {"consolidated_response": "Error: catched error"}


# Main function to extract text, send to API, and store X for matching categories

async def process_hyperlinks(file: UploadFile, sheet_name: str) -> bytes:
    """Process hyperlinks from uploaded Excel file and return processed file as bytes."""
    try:
        # Read the original file contents
        file_contents = await file.read()
        
        # Reset file pointer for reading the dataframe
        await file.seek(0)
        df = await read_hyperlinks(file, sheet_name)

        async def process_link(row):
            """Handles individual link processing asynchronously."""
            try:
                link = row.get("Unnamed: 1")
                if pd.notnull(link):
                    print(f"Processing link: {link}")

                    try:
                        if is_image_url(link):
                            # Process image URL
                            blob_url = await process_image_link(link)
                            message_request = MessageRequest(message=blob_url, stream=False)
                            assistant_response = await send_message("trimble-media-image-2-text", message_request)
                            response_text = assistant_response.get("message", "No text found")
                        else:
                            # Process article URL
                            scraped_text = web_scrape_text(link)
                            message_request = MessageRequest(message=scraped_text, stream=False)
                            assistant_response = await send_to_all_assistants(message_request)
                            response_text = assistant_response["consolidated_response"]
                    except Exception as e:
                        print(f"catched error in processing link {link}: {e}")
                        response_text = "Error: catched error"

                    try:
                        row_dict = {cat: "" for cat in categories}
                        row_dict["Article Title & Link"] = link

                        for category in categories:
                            if re.search(rf'\b{re.escape(category)}\b', response_text, flags=re.IGNORECASE):
                                row_dict[category] = "X"

                        return row_dict
                    except Exception as e:
                        print(f"catched error in processing categories for {link}: {e}")
                        row_dict = {cat: "" for cat in categories}
                        row_dict["Article Title & Link"] = link
                        return row_dict

                return None
            except Exception as e:
                print(f"catched error in process_link: {e}")
                return None

        try:
            tasks = [process_link(row) for _, row in df.iterrows()]
            results = await asyncio.gather(*tasks)
            result_df = pd.DataFrame([r for r in results if r])
        except Exception as e:
            print(f"catched error in gathering results: {e}")
            result_df = pd.DataFrame()

        # Write output to Excel file in memory and return the bytes
        processed_file_bytes = write_output_to_excel_memory(file_contents, result_df)
        
        return processed_file_bytes
    except Exception as e:
        print(f"catched error in process_hyperlinks: {e}")
        # Return original file if everything fails
        try:
            file_contents = await file.read()
            return file_contents
        except:
            return b""