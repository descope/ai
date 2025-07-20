from fastapi import FastAPI, Depends, Security, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import pytesseract
import io
from fastapi.middleware.cors import CORSMiddleware
import requests
from pydantic import BaseModel, HttpUrl

from fastapi_mcp import FastApiMCP, AuthConfig
from app.auth.auth import TokenVerifier

import urllib.request
from app.auth.auth_config import get_settings

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


@app.post("/mcp")
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
mcp.mount()