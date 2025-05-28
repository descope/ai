# Securing MCP Server-Client Architecture with Descope Using Ollama, LLaMA Stack in Python

As AI workloads scale in sensitivity and compute cost, it's crucial to secure interactions between clients and inference servers. This post demonstrates how to secure a Python-based MCP server-client architecture using Ollama and the LLaMA model stack, protected via OAuth 2.0 using Descope.

## Prerequisites

- Python 3.10+
- Docker & Docker Compose (optional)
- Descope Account and Project
- Ollama installed (ollama serve)
- Descope Python SDK
- HTTP libraries: requests, httpx

## Run ollama

```bash
ollama run llama2:3b --keepalive 60m
```

## Run llama stack (optional)

```bash
INFERENCE_MODEL=llama2:3b uv run --with llama-stack llama stack build --template ollama --image-type venv --run
```

## Run MCP Server and Client

Setup virtual environment

```bash
uv venv
source .venv/bin/activate
```

Add Python dependencies

```bash
uv add fastmcp descope llama-stack-client
```

### Configure Credentials

Update the following files with your Descope credentials:

1. In `mcp-llama-stack-descope.py`:

```python
mcp = FastMCP(
    name="SecureApp",
    auth_server_provider=DescopeOAuthProvider(
        project_id="YOUR_PROJECT_ID",
        management_key="YOUR_MANAGEMENT_KEY",
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET"
    ),
    ...
)
```

2. In `client-descope.py`:

```python
PROJECT_ID = "YOUR_PROJECT_ID"
MANAGEMENT_KEY = "YOUR_MANAGEMENT_KEY"
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
```

### Run FastMCP Server

```bash
uv run mcp-llama-stack-descope.py
```

### Run FastMCP Client

```bash
uv run client-descope.py
```

## Available Tools

The server provides the following tools:

1. `add`: Simple addition of two numbers
2. `generate_text`: Text generation using LlamaStack's LLM
   - Parameters:
     - prompt: The input text to generate from
     - model: The model to use (default: llama2:3b)
     - temperature: Controls randomness (0.0 to 1.0)
     - max_tokens: Maximum length of the generated response
3. `list_ollama_models`: List available models in the LlamaStack server

## Security Features

- OAuth 2.0 authentication via Descope
- Secure token management
- Client credentials flow for server-to-server communication
- Token validation and revocation
- Proper error handling and logging

## Error Handling

The implementation includes comprehensive error handling for:

- Authentication failures
- Token validation errors
- LLM inference errors
- Network issues
- Invalid requests

## Logging

The server and client both implement detailed logging for:

- Authentication events
- API calls
- Error conditions
- Performance metrics

## Contributing

Feel free to submit issues and enhancement requests!
