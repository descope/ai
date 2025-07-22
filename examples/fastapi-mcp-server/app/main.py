from fastapi import FastAPI, Depends, Security, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from httpx import AsyncClient, RequestError
from typing import List
from PIL import Image
import pytesseract
from io import BytesIO
import requests
from pyzbar.pyzbar import decode as decode_barcode
import urllib.request

from app.auth.auth import TokenVerifier
from app.auth.auth_config import get_settings

from fastapi_mcp import FastApiMCP, AuthConfig

# We use PyJWKClient, which internally uses Python's built-in urllib.request, which sends requests
# without a standard User-Agent header (e.g., it sends "Python-urllib/3.x").
# Some CDNs or API gateways (like the one serving Descope's JWKS) may block such requests as they resemble bot traffic or security scanners.
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (DescopeFastAPISampleApp)')]
urllib.request.install_opener(opener)


app = FastAPI()
auth = TokenVerifier()
config = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class OCRRequest(BaseModel):
    image_url: HttpUrl  # Ensures it's a valid URL


@app.post("/ocr", operation_id="optical-character-recognition")
async def perform_ocr(request: OCRRequest, auth_result: str = Security(auth)):
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
        image = Image.open(BytesIO(response.content))
        text = pytesseract.image_to_string(image)
        return JSONResponse(content={"text": text.strip()})
    except HTTPException:
        raise  # Re-raise validation errors
    except Exception as e:
        # Catch-all for OCR or image errors
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


class BarcodeRequest(BaseModel):
    barcode_url: HttpUrl

@app.post("/scan-barcode", operation_id="scan-barcode")
async def scan_barcode(request: BarcodeRequest, auth_result: str = Security(auth)):
    """
    Scan a barcode or QR code from a publicly accessible image URL.

    **Note**:
    This endpoint ONLY supports **public HTTP(S) image URLs**. It does **NOT** support:
    - private URLs (e.g., behind authentication or firewalls)
    - raw image file uploads

    This endpoint accepts a POST request containing a JSON payload with a single field `url`,
    which must point to an image hosted on a public server. The image is fetched, validated,
    and scanned for one or more barcodes or QR codes using the ZBar engine.

    Parameters:
    -----------
    request : BarcodeRequest
        A Pydantic model containing:
        - barcode_url (HttpUrl): A valid, publicly accessible HTTP(S) URL pointing to an image file.

    Returns:
    --------
    JSON response

    Raises:
    -------
    - 400 Bad Request:
        - If the image cannot be fetched (invalid URL, network issue, etc.)
        - If the content at the URL is not a valid image
        - If a request-level error occurs (e.g: timeout)
    - 422 Unprocessable Entity:
        - If no barcode or QR code is found in the image
    - 500 Internal Server Error:
        - For any unexpected or unhandled exceptions during processing

    Example Request:
    ----------------
    POST /scan-barcode
    Content-Type: application/json
    {
        "barcode_url": "https://miro.medium.com/v2/resize:fit:405/1*k0h04CRy0j8MbBbqsodGAA.png"
    }

    Example Response:
    -----------------
    200 OK

    {
        "success": true,
        "barcodes": [
            {
                "type": "QRCODE",
                "data": "hello",
                "bounds": {
                    "left": 34,
                    "top": 22,
                    "width": 210,
                    "height": 210
                }
            }
        ]
    }
    """

    try:
        # Fetch the image from URL
        async with AsyncClient(timeout=5.0) as client:
            response = await client.get(str(request.barcode_url))
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch image from URL")

        # Attempt to open as image
        try:
            image = Image.open(BytesIO(response.content)).convert("RGB")
        except Exception:
            raise HTTPException(status_code=400, detail="Provided URL is not a valid image")

        # Attempt barcode decoding
        decoded = decode_barcode(image)
        if not decoded:
            raise HTTPException(status_code=422, detail="No barcode or QR code detected in image")

        # Return results
        results = []
        for item in decoded:
            results.append({
                "type": item.type,
                "data": item.data.decode("utf-8"),
                "bounds": item.rect
            })

        return {"success": True, "barcodes": results}

    except RequestError as e:
        raise HTTPException(status_code=400, detail=f"HTTP error: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

mcp = FastApiMCP(
    app,
    name="Image Tools MCP Server",
    description="MCP Server for Image transforms including OCR, etc.",
    auth_config=AuthConfig(
        custom_oauth_metadata={
            "issuer": HttpUrl(f"{config.descope_api_base_url}/v1/apps/{config.descope_project_id}"),
            "jwks_uri": HttpUrl(f"{config.descope_api_base_url}/{config.descope_project_id}/.well-known/jwks.json"),
            "authorization_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/authorize"),
            "response_types_supported": ["code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/token"),
            "userinfo_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/userinfo"),
            "scopes_supported": ["openid"],
            "claims_supported": [
                "iss", "aud", "iat", "exp", "sub", "name", "email",
                "email_verified", "phone_number", "phone_number_verified",
                "picture", "family_name", "given_name"
            ],
            "revocation_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/revoke"),
            "registration_endpoint": HttpUrl(f"{config.descope_api_base_url}/v1/mgmt/inboundapp/app/{config.descope_project_id}/register"),
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["client_secret_post"],
            "end_session_endpoint": HttpUrl(f"{config.descope_api_base_url}/oauth2/v1/apps/logout")
        },
        dependencies=[Depends(auth)],
    ),
)

mcp.setup_server()
mcp.mount()