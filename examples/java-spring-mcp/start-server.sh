#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if required environment variables are set
if [ -z "$DESCOPE_PROJECT_ID" ]; then
    echo "Error: DESCOPE_PROJECT_ID environment variable is not set"
    echo "Please set it in your .env file or export it directly"
    echo "Example: export DESCOPE_PROJECT_ID=P2zinVOiGTv8WEcvDrlUttNsb4Y4"
    exit 1
fi

echo "Starting MCP server with Descope Project ID: $DESCOPE_PROJECT_ID"

# Compile and run the application
mvn clean compile exec:java -Dexec.mainClass="com.github.stantonk.App" 