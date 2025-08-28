#!/bin/bash

# Setup script for Java Spring MCP Server with Descope integration

echo "🚀 Setting up environment for Java Spring MCP Server"
echo ""

# Check if .env file exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Copy example file
if [ -f "env.example" ]; then
    cp env.example .env
    echo "✅ Created .env file from env.example"
else
    echo "❌ env.example file not found!"
    exit 1
fi

echo ""
echo "📝 Please edit the .env file with your actual Descope credentials:"
echo "   - DESCOPE_PROJECT_ID: Your Descope project identifier"
echo "   - DESCOPE_MANAGEMENT_KEY: Your Descope management key"
echo ""
echo "🔧 You can edit it with: nano .env or your preferred editor"
echo ""
echo "📋 Required steps to complete setup:"
echo "   1. Get your Descope Project ID from https://app.descope.com/"
echo "   2. Create a Management Key in Descope Console > Settings > Management Keys"
echo "   3. Configure Google Calendar outbound app in Descope Console > Inbound Apps > Outbound Applications"
echo "   4. Update the .env file with your credentials"
echo "   5. Run: mvn clean package && java -jar target/mcp-server-1.0-SNAPSHOT.jar"
echo ""
echo "🎯 For more information, see the README.md file"
