#!/usr/bin/env python3
"""
Simple script to run the Streamlit UI for the Descope MCP Agent
"""

import subprocess
import sys
import os

def main():
    """Run the Streamlit UI"""
    print("🚀 Starting Descope MCP Agent UI...")
    print("📱 The UI will open in your default web browser")
    print("🔗 URL: http://localhost:8501")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run streamlit with the UI file
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_ui.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Shutting down UI server...")
    except Exception as e:
        print(f"❌ Error running UI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
