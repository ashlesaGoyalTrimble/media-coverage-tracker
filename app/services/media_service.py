"""Media-related services for processing articles and images."""
import requests
import asyncio
import httpx
import traceback
import pandas as pd
from bs4 import BeautifulSoup
import openpyxl
from io import BytesIO
import re
import uuid
from openpyxl.utils.dataframe import dataframe_to_rows
from fastapi import UploadFile

from app.schemas.media import MessageRequest
from app.services.auth_service import get_trimble_auth_headers


BASE_URL = "https://api.assistant.trimble.cloud/ui/trimbledeveloperprogram/assistants/v1"
API_ENDPOINT = "http://localhost:8000/agents/all/messages"

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
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            return soup.get_text().strip()
        else:
            return f"Failed to scrape URL: {url} (HTTP {response.status_code})"
    except requests.RequestException as e:
        print(f"Request error in web_scrape_text: {e}")
        return "Error: Request failed"
    except Exception as e:
        print(f"Unexpected error in web_scrape_text: {e}")
        return "Error: Processing failed"


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
        
        # Get fresh authentication headers
        headers = await get_trimble_auth_headers()
        # Remove Content-Type for multipart/form-data uploads
        auth_headers = {k: v for k, v in headers.items() if k != "Content-Type"}
        
        response = requests.post(url, headers=auth_headers, files=files)
        
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
        
        # Get fresh authentication headers
        headers = await get_trimble_auth_headers()
        payload = request.dict()
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
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
        # Get fresh authentication headers
        headers = await get_trimble_auth_headers()
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
    processed_count = 0
    failed_count = 0
    
    try:
        # Read the original file contents
        file_contents = await file.read()
        
        # Reset file pointer for reading the dataframe
        await file.seek(0)
        df = await read_hyperlinks(file, sheet_name)
        
        print(f"Starting to process {len(df)} hyperlinks from sheet '{sheet_name}'")

        async def process_link(row_index, row):
            """Handles individual link processing asynchronously with enhanced error handling."""
            nonlocal processed_count, failed_count
            
            link = None
            try:
                link = row.get("Unnamed: 1")
                if pd.isnull(link) or not str(link).strip():
                    print(f"Row {row_index + 1}: Skipping empty or null link")
                    return None
                
                link = str(link).strip()
                print(f"Row {row_index + 1}: Processing link: {link}")

                response_text = ""
                try:
                    if is_image_url(link):
                        print(f"Row {row_index + 1}: Processing as image URL")
                        # Process image URL
                        blob_url = await process_image_link(link)
                        message_request = MessageRequest(message=blob_url, stream=False)
                        assistant_response = await send_message("trimble-media-image-2-text", message_request)
                        response_text = assistant_response.get("message", "No text found")
                        print(f"Row {row_index + 1}: Image processing completed")
                    else:
                        print(f"Row {row_index + 1}: Processing as article URL")
                        # Process article URL
                        scraped_text = web_scrape_text(link)
                        if not scraped_text or scraped_text.strip() == "":
                            print(f"Row {row_index + 1}: Warning - No text scraped from {link}")
                            response_text = "No content scraped"
                        else:
                            message_request = MessageRequest(message=scraped_text, stream=False)
                            assistant_response = await send_to_all_assistants(message_request)
                            response_text = assistant_response.get("consolidated_response", "No response")
                            print(f"Row {row_index + 1}: Article processing completed")
                            
                except Exception as e:
                    print(f"Row {row_index + 1}: Error processing link {link}: {str(e)}")
                    print(f"Row {row_index + 1}: Exception type: {type(e).__name__}")
                    response_text = f"Processing error: {type(e).__name__}"
                    # Continue with category processing even if link processing fails

                # Process categories - this should always work even if response_text is empty/error
                try:
                    row_dict = {cat: "" for cat in categories}
                    row_dict["Article Title & Link"] = link

                    if response_text and response_text != "Processing error":
                        matched_categories = []
                        for category in categories:
                            try:
                                if re.search(rf'\b{re.escape(category)}\b', response_text, flags=re.IGNORECASE):
                                    row_dict[category] = "X"
                                    matched_categories.append(category)
                            except Exception as cat_e:
                                print(f"Row {row_index + 1}: Error matching category '{category}': {str(cat_e)}")
                                continue
                        
                        if matched_categories:
                            print(f"Row {row_index + 1}: Matched categories: {', '.join(matched_categories)}")
                        else:
                            print(f"Row {row_index + 1}: No categories matched")
                    else:
                        print(f"Row {row_index + 1}: Skipping category matching due to processing error")

                    processed_count += 1
                    print(f"Row {row_index + 1}: Successfully processed ({processed_count} total)")
                    return row_dict
                    
                except Exception as e:
                    print(f"Row {row_index + 1}: Error in category processing for {link}: {str(e)}")
                    # Return basic row dict even if category processing fails
                    try:
                        row_dict = {cat: "" for cat in categories}
                        row_dict["Article Title & Link"] = link
                        processed_count += 1
                        return row_dict
                    except Exception as final_e:
                        print(f"Row {row_index + 1}: Final fallback error: {str(final_e)}")
                        failed_count += 1
                        return None

            except Exception as e:
                failed_count += 1
                print(f"Row {row_index + 1}: Unexpected error in process_link for {link}: {str(e)}")
                print(f"Row {row_index + 1}: Exception traceback: {traceback.format_exc()}")
                
                # Try to return at least the link information
                try:
                    if link:
                        row_dict = {cat: "" for cat in categories}
                        row_dict["Article Title & Link"] = link
                        return row_dict
                except Exception:
                    pass
                    
                return None

        # Process all links with enhanced error handling
        try:
            print(f"Creating processing tasks for {len(df)} rows")
            tasks = [process_link(idx, row) for idx, (_, row) in enumerate(df.iterrows())]
            
            # Use return_exceptions=True to prevent one failure from stopping all processing
            print("Starting parallel processing of all links...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and None results, but log them
            valid_results = []
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Row {idx + 1}: Task failed with exception: {str(result)}")
                    failed_count += 1
                elif result is not None:
                    valid_results.append(result)
                # None results are already counted in process_link
            
            print(f"Processing completed: {len(valid_results)} successful, {failed_count} failed")
            
            if valid_results:
                result_df = pd.DataFrame(valid_results)
                print(f"Created result DataFrame with {len(result_df)} rows")
            else:
                print("No valid results - creating empty DataFrame")
                result_df = pd.DataFrame()
                
        except Exception as e:
            print(f"Critical error in task processing: {str(e)}")
            print(f"Exception traceback: {traceback.format_exc()}")
            result_df = pd.DataFrame()

        # Write output to Excel file in memory and return the bytes
        try:
            processed_file_bytes = write_output_to_excel_memory(file_contents, result_df)
            print(f"Successfully created processed file. Total processed: {processed_count}, Failed: {failed_count}")
            return processed_file_bytes
        except Exception as e:
            print(f"Error writing to Excel: {str(e)}")
            return file_contents  # Return original file if Excel writing fails
        
    except Exception as e:
        print(f"Critical error in process_hyperlinks: {str(e)}")
        print(f"Exception traceback: {traceback.format_exc()}")
        # Return original file if everything fails
        try:
            await file.seek(0)
            file_contents = await file.read()
            return file_contents
        except Exception as final_e:
            print(f"Failed to read original file: {str(final_e)}")
            return b""