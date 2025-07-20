from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import pytesseract
import io
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel, HttpUrl

from fastapi_mcp import FastApiMCP

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class OCRRequest(BaseModel):
    image_url: HttpUrl  # Ensures it's a valid URL

@app.post("/ocr")
async def perform_ocr(request: OCRRequest):
    """
    Perform Optical Character Recognition (OCR) on a remote image URL.

    **Note:** This endpoint only works with publicly accessible image URLs.
        - It does **NOT** support file uploads, base64-encoded images, or attachments (yet).
        - It does **NOT** work with:
            - Private URLs (e.g., behind authentication or firewalls)
            - Expired signed URLs
            - Local file paths like `file:///home/user/image.png`

    This endpoint accepts a public image URL in the request body (as JSON),
    downloads the image, runs OCR using Tesseract, and returns the extracted text.

    **Request**
    ----------
    Content-Type: application/json

    JSON Body:
    {
        "image_url": "https://example.com/image.jpg"
    }

    - `image_url` must be a valid HTTP or HTTPS link pointing to an image file.
    - Supported formats: PNG, JPEG, TIFF, etc.

    **Response**
    -----------
    200 OK
    {
        "text": "<Extracted OCR text here>"
    }

    400 Bad Request
    {
        "detail": "Failed to fetch image: <error>" 
        // or
        "detail": "Provided URL does not point to an image."
    }

    500 Internal Server Error
    {
        "detail": "OCR failed: <error message>"
    }

    **Examples**
    ------------
    Using `curl`:
        curl -X POST http://localhost:8000/ocr \
             -H "Content-Type: application/json" \
             -d '{"image_url": "https://example.com/image.jpg"}'

    **Notes**
    ---------
    - Tesseract OCR must be installed and accessible via system PATH.
    - If the image is unreachable, not an image, or corrupted, appropriate errors will be returned.
    - No data is stored; the operation is stateless and real-time.

    Parameters
    ----------
    request : OCRRequest
        A Pydantic model containing a single field `image_url` representing the image URL.

    Returns
    -------
    JSONResponse
        A JSON object containing the extracted text or an error message.
    """
    
    try:
        response = requests.get(str(request.image_url), timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")

    if not response.headers.get("Content-Type", "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Provided URL does not point to an image.")

    try:
        image = Image.open(io.BytesIO(response.content))
        text = pytesseract.image_to_string(image)
        return JSONResponse(content={"text": text.strip()})
    except HTTPException:
        raise  # Re-raise validation errors
    except Exception as e:
        # Catch-all for OCR or image errors
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")
    
mcp = FastApiMCP(
    app,
    name="Image Tools MCP Server",
    description="MCP Server for Image transforms including OCR, etc.",
)
mcp.mount()