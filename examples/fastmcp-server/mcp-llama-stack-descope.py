import json
import signal
import sys
import time
from fastmcp import FastMCP
from llama_stack_client import LlamaStackClient
from mcp.server.auth.settings import AuthSettings
from DescopeOAuthProvider import DescopeOAuthProvider
import logging
import requests
from typing import Optional, Dict, Any
from llama_stack_client.types import UserMessage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SecureApp")

# Handle SIGINT (Ctrl+C) gracefully
def signal_handler(sig, frame):
    logger.info("Received shutdown signal. Shutting down gracefully...")
    print("Shutting down server gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Configuration for LlamaStack
LLAMASTACK_BASE_URL = "http://localhost:8321"  
OLLAMA_MODEL = "llama2:3b"

# Initialize LlamaStack client
client = LlamaStackClient(
    base_url=LLAMASTACK_BASE_URL,
)

# Initialize MCP with Descope auth
mcp = FastMCP(
    name="SecureApp",
    auth_server_provider=DescopeOAuthProvider(
        project_id="YOUR_PROJECT_ID",  # Replace with your Descope project ID
        management_key="YOUR_MANAGEMENT_KEY",  # Replace with your management key
        client_id="YOUR_CLIENT_ID",  # Replace with your client ID
        client_secret="YOUR_CLIENT_SECRET"  # Replace with your client secret
    ),
    auth=AuthSettings(
        issuer_url="https://api.descope.com/oauth2/v1",
    ),
)

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    try:
        result = a + b
        logger.debug(f"Add operation: {a} + {b} = {result}")
        return result
    except Exception as e:
        logger.error(f"Error in add function: {str(e)}")
        raise

@mcp.tool()
def generate_text(
    prompt: str,
    model: Optional[str] = OLLAMA_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> str:
    """
    Generate text using LlamaStack's LLM inference server.
    
    Args:
        prompt: The input prompt for text generation
        model: The model to use (default: llama2)
        temperature: Controls randomness (0.0 to 1.0)
        max_tokens: Maximum length of the generated response
        
    Returns:
        Generated text response
    """
    try:
        client = LlamaStackClient(
            base_url=LLAMASTACK_BASE_URL,
        )
        response = client.inference.chat_completion(
            messages=[
                UserMessage(
                    content=prompt,
                    role="user",
                ),
            ],
            model_id=model,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
        logger.info(f"Sending request to LlamaStack with model: {model}")
        logger.info(response.model_dump_json())
        return response.model_dump_json()
    except Exception as e:
        logger.error(f"Error in generate_text: {str(e)}")
        raise

@mcp.tool()
def list_ollama_models() -> Dict[str, Any]:
    """
    List available models in the LlamaStack server
    
    Returns:
        Dictionary containing available models and their details
    """
    try: 
        client = LlamaStackClient(
            base_url=LLAMASTACK_BASE_URL,
        )
        response = client.models.list()
        return [model.model_dump() for model in response]
    except Exception as e:
        logger.error(f"Error listing LlamaStack models: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        print("Starting MCP server 'SecureApp' on 127.0.0.1:8001")
        print("Available tools:")
        print("- add: Add two numbers")
        print("- generate_text: Generate text using LlamaStack LLM")
        print("- list_ollama_models: List available LlamaStack models")
        
        # Use this approach to keep the server running
        mcp.run(
            transport="sse",
            host="127.0.0.1",
            port=8001,
            log_level="debug",
            path="/",
        )
    except KeyboardInterrupt as e:
        logger.error(f"descope: {e}")
    except Exception as e:
        logger.info("Server stopped by user")
        print(f"Error: {e}")
        # Sleep before exiting to give time for error logs
        time.sleep(5) 