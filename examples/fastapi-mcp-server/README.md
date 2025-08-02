# FastAPI MCP Server with Authentication using Descope

![Descope Banner](https://github.com/descope/.github/assets/32936811/d904d37e-e3fa-4331-9f10-2880bb708f64)

## Introduction
This repository demonstrates how to:
- Convert an existing **FastAPI server** with arbitrary endpoints into an **MCP (Model Context Protocol) server** using the **[FastAPI-MCP](https://fastapi-mcp.tadata.com/getting-started/welcome) library**.
- Automatically expose each API route as a **callable tool** usable by LLMs, and MCP clients.
- Implement authentication via JWT token validation, using **Descope** as the auth provider.

The API server contains 2 basic image processing tasks - **Optical Character Recognition**, and **Barcode Scanning** on publicly accessible image URLs — with added support for Descope-based JWT token verification. 

### API Features
- `POST /ocr`: 
    Performs OCR (Optical Character Recognition) on an image accessible via a public URL.

- `POST /scan-barcode`:
    Detects and returns barcodes/QR codes found in the image at the provided URL.

**Note**: The API does not support image uploads or file data — only URL-based images for now.

## Setup Instructions
Follow the steps to get the FastAPI, and MCP server running locally on your machine:
### 1. Clone the Repository
```bash
git clone https://github.com/descope/ai.git
cd examples/fastapi-mcp-server
```

### 2. Create and activate Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  
# or venv\Scripts\activate on Windows
```

### 3. Install the dependencies
- First, install the python packages
```bash
pip install -r requirements.txt
```
- For the image tools (OCR, and Scan-Barcode), you will also need to install some system libraries. If you are building your own API, and MCP server, you may skip this step
```bash
# MacOS/Linux: Install System Libraries
brew install tesseract zbar
```

For Windows, Install Tesseract OCR, and ZBar for Windows. Ensure both binaries are added to your PATH.

### 4. Set up environment variables
- Create a new `.env` file in the `fastapi-mcp-server` directory, (optionally, by copying the `.env.example`) file
- Fill in the `DESCOPE_PROJECT_ID` variable. You can find your Descope Project ID in your [Project Settings Page](https://app.descope.com/settings/project)

### 5. Start the server
```bash
uvicorn app.main:app --reload
```
The server should now be running at http://localhost:8000.


## Testing the Server with MCP Clients
### CloudFlare Workers AI Playground
1. Visit: https://playground.ai.cloudflare.com/.
2. Enter your local MCP server URL: http://localhost:8000/mcp, and click connect.
3. Once authenticated, you will now have access to the tools (OCR, Scan-Barcode).

### Cursor/Claude
Add this configuration to your MCP tool config (e.g., in Cursor: Cmd/Ctrl + Shift + J → Tools & Integrations → MCP tools):
```json
"image-tools-server": {
  "url": "http://localhost:8000/mcp"
}
```
**Note**: Due to some Cursor bugs, and since the current `fastapi-mcp` server supports only **SSE transport** (not streamable HTTP), sometimes, the authentication is not triggered. Instead, you can modify your configuration to use `mcp-remote` to bridge:

```json
"image-tools-server": {
  "command": "npx",
  "args": [
    "mcp-remote",
    "http://localhost:8000/mcp"
  ]
}
```

## Debugging
- Auth Issues with MCP? Clear your MCP authentication cache:
```bash
rm -rf ~/.mcp-auth
```

- Image not processed? Ensure you’re sending a valid image URL (publicly accessible, not behind auth).
The API (or MCP) servers currently do not support image files/uploads.

- Descope not verifying token? Double-check your `DESCOPE_PROJECT_ID` in `.env` and ensure the token you’re passing is valid.

## Tech Stack
- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI-MCP](https://fastapi-mcp.tadata.com/getting-started/welcome) for MCP server integration
- [Descope](https://www.descope.com/) for authentication
- [Pytesseract](https://pypi.org/project/pytesseract/) for OCR
- [pyzbar](https://pypi.org/project/pyzbar/) for barcode detection
