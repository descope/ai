import streamlit as st
import asyncio
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our OAuth agent
from descope_oauth_agent import (
    discover_descope_endpoints,
    perform_descope_oauth_flow,
    test_descope_mcp_connection,
    get_valid_bearer_token,
    handle_auth_error_and_reauth,
    token_manager
)

def format_agent_response(response):
    """Format agent response with proper message display"""
    if not hasattr(response, 'messages') or not response.messages:
        return str(response)
    
    formatted_messages = []
    
    for message in response.messages:
        if hasattr(message, 'content') and message.content:
            if message.__class__.__name__ == 'HumanMessage':
                formatted_messages.append(f"**👤 User:** {message.content}")
            elif message.__class__.__name__ == 'AIMessage':
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Show tool calls
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.get('name', 'unknown')
                        formatted_messages.append(f"**🔧 Tool Call:** `{tool_name}`")
                        if 'args' in tool_call:
                            # Format arguments nicely
                            args = tool_call['args']
                            if isinstance(args, dict):
                                # Format specific calendar event arguments nicely
                                if tool_name == 'create-calendar-event':
                                    formatted_args = format_calendar_args(args)
                                    formatted_messages.append(f"**📋 Meeting Details:**\n{formatted_args}")
                                else:
                                    formatted_messages.append(f"**📋 Arguments:** ```json\n{json.dumps(args, indent=2)}\n```")
                            else:
                                formatted_messages.append(f"**📋 Arguments:** {args}")
                if message.content:
                    formatted_messages.append(f"**🤖 Assistant:** {message.content}")
            elif message.__class__.__name__ == 'ToolMessage':
                # Format tool results nicely
                content = message.content
                if "Session terminated" in content:
                    formatted_messages.append(f"**⚙️ Tool Result:** ❌ Connection lost - session terminated")
                elif "Unable to access Google Calendar" in content:
                    formatted_messages.append(f"**⚙️ Tool Result:** ⚠️ Google Calendar access denied - check permissions")
                elif "Error:" in content:
                    # Extract the main error message
                    error_msg = content.split("Error:")[-1].strip()
                    formatted_messages.append(f"**⚙️ Tool Result:** ❌ {error_msg}")
                else:
                    formatted_messages.append(f"**⚙️ Tool Result:** {content}")
            else:
                formatted_messages.append(f"**📝 {message.__class__.__name__}:** {message.content}")
    
    return "\n\n".join(formatted_messages)

def format_calendar_args(args):
    """Format calendar event arguments in a nice readable format"""
    formatted = []
    
    if 'summary' in args:
        formatted.append(f"**📅 Title:** {args['summary']}")
    
    if 'startDateTime' in args:
        # Parse and format the datetime
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(args['startDateTime'].replace('Z', '+00:00'))
            formatted.append(f"**🕐 Start:** {dt.strftime('%A, %B %d, %Y at %I:%M %p %Z')}")
        except:
            formatted.append(f"**🕐 Start:** {args['startDateTime']}")
    
    if 'endDateTime' in args:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(args['endDateTime'].replace('Z', '+00:00'))
            formatted.append(f"**🕕 End:** {dt.strftime('%A, %B %d, %Y at %I:%M %p %Z')}")
        except:
            formatted.append(f"**🕕 End:** {args['endDateTime']}")
    
    if 'attendees' in args:
        attendees = args['attendees']
        if isinstance(attendees, list):
            formatted.append(f"**👥 Attendees:** {', '.join(attendees)}")
        else:
            formatted.append(f"**👥 Attendees:** {attendees}")
    
    if 'description' in args:
        formatted.append(f"**📝 Description:** {args['description']}")
    
    return "\n".join(formatted)

# Set page config
st.set_page_config(
    page_title="Descope MCP Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    .info-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .tool-item {
        background-color: #e9ecef;
        border-radius: 0.25rem;
        padding: 0.5rem;
        margin: 0.25rem 0;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">🤖 Descope MCP Agent</h1>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # MCP Server URL
        mcp_server_url = st.text_input(
            "MCP Server URL",
            value="https://hubspot-crm.preview.descope.org/mcp",
            help="The URL of the Descope MCP server to connect to"
        )
        
        # API Keys
        st.subheader("🔑 API Keys")
        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Your OpenAI API key for the language model"
        )
        
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        
        st.subheader("🎯 Actions")
        
        # Authentication status
        if 'bearer_token' in st.session_state and st.session_state.bearer_token:
            st.markdown('<p class="status-success">✅ Authenticated</p>', unsafe_allow_html=True)
            
            # Show token status
            if token_manager.token_expires_at:
                time_left = (token_manager.token_expires_at - datetime.now()).total_seconds()
                if time_left > 0:
                    st.info(f"⏰ Token expires in {time_left:.0f} seconds")
                else:
                    st.warning("⚠️ Token expired - will refresh automatically")
            
            # Show refresh token status
            if token_manager.refresh_token:
                st.success("🔄 Refresh token available")
            else:
                st.warning("⚠️ No refresh token - will need re-authentication on expiration")
            
            col_auth1, col_auth2 = st.columns(2)
            
            with col_auth1:
                if st.button("🔄 Refresh Token"):
                    with st.spinner("Refreshing token..."):
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            refresh_success = loop.run_until_complete(token_manager.refresh_access_token())
                            if refresh_success:
                                st.session_state.bearer_token = token_manager.access_token
                                st.success("✅ Token refreshed successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Token refresh failed")
                        except Exception as e:
                            st.error(f"❌ Error refreshing token: {str(e)}")
            
            with col_auth2:
                if st.button("🔄 Re-authenticate"):
                    if 'bearer_token' in st.session_state:
                        del st.session_state.bearer_token
                    if 'mcp_client' in st.session_state:
                        del st.session_state.mcp_client
                    # Clear token manager
                    token_manager.access_token = None
                    token_manager.refresh_token = None
                    st.rerun()
        else:
            st.markdown('<p class="status-warning">⚠️ Not authenticated</p>', unsafe_allow_html=True)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🚀 Agent Actions")
        
        # Step 1: Discover OAuth endpoints
        if st.button("🔍 Discover OAuth Endpoints", type="primary"):
            with st.spinner("Discovering OAuth endpoints..."):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    oauth_endpoints = loop.run_until_complete(discover_descope_endpoints(mcp_server_url))
                    
                    st.session_state.oauth_endpoints = oauth_endpoints
                    
                    st.success("✅ OAuth endpoints discovered!")
                    
                    with st.expander("📋 Discovery Results"):
                        st.json(oauth_endpoints)
                        
                except Exception as e:
                    st.error(f"❌ Error discovering endpoints: {str(e)}")
        
        # Step 2: Perform OAuth flow
        if 'oauth_endpoints' in st.session_state and st.button("🔐 Start OAuth Authentication"):
            with st.spinner("Starting OAuth flow..."):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    bearer_token = loop.run_until_complete(
                        perform_descope_oauth_flow(st.session_state.oauth_endpoints, mcp_server_url)
                    )
                    
                    if bearer_token:
                        st.session_state.bearer_token = bearer_token
                        st.success("✅ Authentication successful!")
                        st.info(f"Bearer token: {bearer_token[:20]}...")
                    else:
                        st.error("❌ Authentication failed")
                        
                except Exception as e:
                    st.error(f"❌ OAuth error: {str(e)}")
        
        # Step 3: Test MCP connection
        if 'bearer_token' in st.session_state and st.button("🔗 Test MCP Connection"):
            with st.spinner("Testing MCP connection..."):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        test_descope_mcp_connection(mcp_server_url, st.session_state.bearer_token)
                    )
                    
                    if result:
                        st.session_state.mcp_client = result
                        st.success("✅ MCP connection successful!")
                    else:
                        st.error("❌ MCP connection failed")
                        
                except Exception as e:
                    st.error(f"❌ MCP connection error: {str(e)}")
        
        # Step 4: Chat with agent
        if 'mcp_client' in st.session_state and st.session_state.mcp_client:
            st.header("💬 Chat with Agent")
            
            # Initialize chat history
            if "messages" not in st.session_state:
                st.session_state.messages = []
            
            # Display chat messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # Chat input
            if prompt := st.chat_input("Ask the agent to help you with CRM tasks..."):
                # Add user message to chat history
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Get agent response
                with st.chat_message("assistant"):
                    with st.spinner("Agent is thinking..."):
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            response = loop.run_until_complete(
                                st.session_state.mcp_client.ainvoke({"messages": prompt})
                            )
                            
                            # Format the response nicely
                            formatted_response = format_agent_response(response)
                            st.markdown(formatted_response)
                            
                            # Add assistant response to chat history
                            st.session_state.messages.append({"role": "assistant", "content": formatted_response})
                            
                        except Exception as e:
                            error_msg = f"❌ Error: {str(e)}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        # Quick actions
        if 'mcp_client' in st.session_state and st.session_state.mcp_client:
            st.header("⚡ Quick Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📅 Schedule Meeting", help="Ask the agent to schedule a calendar event"):
                    prompt = "Schedule a meeting for tomorrow at 2 PM with the title 'Team Standup'"
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.rerun()
                
                if st.button("👥 Search Contacts", help="Ask the agent to search for contacts"):
                    prompt = "Search for contacts with the name 'John'"
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.rerun()
            
            with col2:
                if st.button("📊 List Events", help="Ask the agent to list upcoming events"):
                    prompt = "Show me my upcoming calendar events for this week"
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.rerun()
                
                if st.button("🔍 Available Tools", help="Ask the agent what tools are available"):
                    prompt = "What tools and capabilities do you have available?"
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.rerun()
    
    with col2:
        st.header("📊 Status")
        
        # Connection status
        if 'bearer_token' in st.session_state:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown('<p class="status-success">✅ Authenticated with Descope</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown('<p class="status-warning">⚠️ Not authenticated</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if 'mcp_client' in st.session_state:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown('<p class="status-success">✅ Connected to MCP Server</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown('<p class="status-warning">⚠️ Not connected to MCP</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Session info
        st.subheader("ℹ️ Session Info")
        st.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if 'oauth_endpoints' in st.session_state:
            st.info(f"OAuth endpoints discovered: {len(st.session_state.oauth_endpoints)}")
        
        # Clear session button
        if st.button("🗑️ Clear Session", help="Clear all session data"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
