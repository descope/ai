import streamlit as st
import asyncio
import json
import re
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
    handle_session_termination,
    update_mcp_client_with_new_token,
    validate_token_scopes,
    token_manager
)

def format_agent_response(response, show_full=False):
    """Format agent response with proper message display and bullet points"""
    if not hasattr(response, 'messages') or not response.messages:
        return str(response)
    
    # Find the final AI message with actual content (not just tool calls)
    final_ai_message = None
    tool_results = []
    
    for message in response.messages:
        if message.__class__.__name__ == 'AIMessage' and message.content and message.content.strip():
            final_ai_message = message
        elif message.__class__.__name__ == 'ToolMessage':
            tool_results.append(message)
    
    # If we have a final AI message with content, use that
    if final_ai_message and final_ai_message.content.strip():
        content = final_ai_message.content.strip()
        
        # Format the content with bullet points
        if not show_full:
            content = format_response_summary(content)
        
        return content
    
    # If no final AI message, show tool results in a clean format
    if tool_results:
        formatted_results = []
        for tool_result in tool_results:
            content = tool_result.content
            
            # Format different types of tool results
            if "Session terminated" in content:
                formatted_results.append("❌ **Connection lost** - session terminated")
                # Trigger session recovery
                formatted_results.append("🔄 **Attempting to recover session...**")
            elif "Unable to access Google Calendar" in content:
                formatted_results.append("⚠️ **Google Calendar access denied** - check permissions")
            elif "Insufficient permissions" in content:
                formatted_results.append("🔐 **Permission required** - additional scopes needed")
            elif "Error:" in content:
                error_msg = content.split("Error:")[-1].strip()
                formatted_results.append(f"❌ **Error:** {error_msg}")
            elif "Found" in content and "calendar events" in content:
                # Format calendar events nicely
                formatted_results.append(format_calendar_events(content))
            else:
                # Clean up the content
                content = content.replace('\n\n', '\n').strip()
                formatted_results.append(content)
        
        return "\n\n".join(formatted_results)
    
    # Fallback: show the raw response
    return str(response)

def format_response_summary(content):
    """Format response content with bullet points and better readability"""
    # Split content into lines and process
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Convert numbered lists to bullet points
        if re.match(r'^\d+\.', line):
            line = f"• {line[2:].strip()}"
        # Convert dash lists to bullet points
        elif line.startswith('- '):
            line = f"• {line[2:].strip()}"
        # Add bullet points to action items
        elif any(keyword in line.lower() for keyword in ['created', 'scheduled', 'found', 'updated', 'deleted']):
            line = f"• {line}"
        
        formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def format_calendar_events(content):
    """Format calendar events content in a clean, readable way"""
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Format event headers
        if line.startswith('Found') and 'calendar events' in line:
            formatted_lines.append(f"📅 **{line}**")
        elif line.startswith('---'):
            formatted_lines.append("---")
        elif line.startswith('📅 Time:'):
            formatted_lines.append(f"🕐 **Time:** {line[7:].strip()}")
        elif line.startswith('📍 Location:'):
            formatted_lines.append(f"📍 **Location:** {line[12:].strip()}")
        elif line.startswith('👥 Attendees:'):
            formatted_lines.append(f"👥 **Attendees:** {line[13:].strip()}")
        elif line.startswith('🔗 Link:'):
            formatted_lines.append(f"🔗 **Link:** {line[8:].strip()}")
        elif line.startswith('📊 Status:'):
            formatted_lines.append(f"📊 **Status:** {line[10:].strip()}")
        elif line.startswith('📝 Description:'):
            formatted_lines.append(f"📝 **Description:** {line[15:].strip()}")
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

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

async def handle_session_termination_errors(response, mcp_server_url):
    """Check for session termination errors and trigger recovery"""
    if not hasattr(response, 'messages') or not response.messages:
        return
    
    # Look for session termination errors in tool messages
    for message in response.messages:
        if hasattr(message, 'content') and message.content:
            content = str(message.content)
            
            # Check for session termination
            if "Session terminated" in content:
                st.warning("🚨 **Session Terminated!**")
                st.info("The connection to the CRM system was lost. Attempting to recover...")
                
                if st.button("🔄 Recover Session", key="recover_session"):
                    with st.spinner("Recovering session..."):
                        try:
                            # Try to recover the session
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            new_token = loop.run_until_complete(handle_session_termination(mcp_server_url))
                            
                            if new_token:
                                st.session_state.bearer_token = new_token
                                token_manager.access_token = new_token
                                
                                # Validate token scopes first
                                scope_valid = loop.run_until_complete(
                                    validate_token_scopes(new_token, ['outbound.token.fetch', 'calendar:read'])
                                )
                                
                                if not scope_valid:
                                    st.warning("⚠️ Token may not have required scopes")
                                
                                # Reconnect to MCP with new token
                                result = loop.run_until_complete(
                                    test_descope_mcp_connection(mcp_server_url, new_token)
                                )
                                
                                if result:
                                    st.session_state.mcp_client = result
                                    st.success("✅ Session recovered successfully!")
                                    st.info(f"🔑 Using new token: {new_token[:20]}...")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to reconnect to CRM")
                                    st.info("💡 This might be due to token scope issues or server connectivity problems")
                            else:
                                st.error("❌ Failed to recover session")
                                
                        except Exception as e:
                            st.error(f"❌ Error recovering session: {str(e)}")
                return

async def handle_permission_errors(response, mcp_server_url):
    """Check for permission errors in tool responses and trigger scope upgrade"""
    if not hasattr(response, 'messages') or not response.messages:
        return
    
    # Look for permission errors in tool messages
    for message in response.messages:
        if hasattr(message, 'content') and message.content:
            content = str(message.content)
            
            # Check for common permission error patterns
            if any(phrase in content.lower() for phrase in [
                'insufficient permissions',
                'scope is required',
                'permission denied',
                'access denied',
                'unauthorized'
            ]):
                st.warning("🔐 **Permission Error Detected!**")
                
                # Extract required scope if mentioned
                required_scope = None
                if 'scope is required' in content.lower():
                    # Try to extract the scope name
                    scope_match = re.search(r"'(.*?):write'", content)
                    if scope_match:
                        required_scope = scope_match.group(1) + ':write'
                
                if required_scope:
                    st.info(f"**Required scope:** `{required_scope}`")
                    
                    # Show option to upgrade scopes
                    if st.button(f"🔑 Request Additional Scope: {required_scope}", key="upgrade_scope"):
                        with st.spinner("Requesting additional permissions..."):
                            try:
                                # Get current OAuth endpoints
                                if 'oauth_endpoints' not in st.session_state:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    oauth_endpoints = loop.run_until_complete(discover_descope_endpoints(mcp_server_url))
                                    st.session_state.oauth_endpoints = oauth_endpoints
                                
                                # Get current scopes
                                current_scopes = token_manager.scopes or ['outbound.token.fetch', 'calendar:read']
                                
                                # Add the required scope
                                new_scopes = list(set(current_scopes + [required_scope]))
                                
                                # Perform OAuth flow with expanded scopes
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                from descope_oauth_agent import perform_descope_oauth_flow_with_scopes
                                callback_url = "http://localhost:8085/callback"
                                
                                # Don't use stored client ID for scope upgrades to avoid callback URL mismatch
                                # Always register a new client for scope upgrades
                                client_id_to_use = None
                                
                                new_token = loop.run_until_complete(
                                    perform_descope_oauth_flow_with_scopes(
                                        st.session_state.oauth_endpoints, 
                                        callback_url, 
                                        new_scopes,
                                        client_id_to_use
                                    )
                                )
                                
                                if new_token:
                                    st.session_state.bearer_token = new_token
                                    token_manager.access_token = new_token
                                    token_manager.scopes = new_scopes
                                    
                                    # Validate token scopes first
                                    scope_valid = loop.run_until_complete(
                                        validate_token_scopes(new_token, new_scopes)
                                    )
                                    
                                    if not scope_valid:
                                        st.warning("⚠️ Token may not have all required scopes")
                                    
                                    # Reconnect to MCP with new token
                                    result = loop.run_until_complete(
                                        test_descope_mcp_connection(mcp_server_url, new_token)
                                    )
                                    
                                    if result:
                                        st.session_state.mcp_client = result
                                        st.success(f"✅ Successfully obtained token with scope: {required_scope}")
                                        st.info(f"🔑 Using new token: {new_token[:20]}...")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to reconnect to CRM with new permissions")
                                        st.info("💡 This might be due to token scope issues or server connectivity problems")
                                else:
                                    st.error("❌ Failed to obtain token with additional scope")
                                    
                            except Exception as e:
                                st.error(f"❌ Error requesting additional scope: {str(e)}")

# Set page config
st.set_page_config(
    page_title="Descope CRM Assistant",
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
    .chat-container {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
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
    .permission-section {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.375rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stButton > button {
        background-color: #1f77b4;
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #1565c0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🤖 Descope CRM Assistant</h1>', unsafe_allow_html=True)
    
    # Create two columns
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Main chat interface
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # MCP Server URL (hidden in sidebar)
        mcp_server_url = "https://hubspot-crm.preview.descope.org/mcp"
        
        # Authentication section
        if 'bearer_token' not in st.session_state or not st.session_state.bearer_token:
            st.subheader("🔐 Authentication Required")
            st.info("Please authenticate with Descope to start using the CRM assistant.")
            
            col_auth1, col_auth2 = st.columns(2)
            
            with col_auth1:
                if st.button("🔐 Start OAuth Authentication", type="primary"):
                    with st.spinner("Starting OAuth flow..."):
                        try:
                            # Discover OAuth endpoints
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            oauth_endpoints = loop.run_until_complete(discover_descope_endpoints(mcp_server_url))
                            st.session_state.oauth_endpoints = oauth_endpoints
                            
                            # Perform OAuth flow
                            bearer_token = loop.run_until_complete(
                                perform_descope_oauth_flow(oauth_endpoints, mcp_server_url, None)
                            )
                            
                            if bearer_token:
                                st.session_state.bearer_token = bearer_token
                                # Update token manager and save to storage
                                token_manager.set_token_info(
                                    access_token=bearer_token,
                                    expires_in=3600,  # Default 1 hour
                                    scopes=['outbound.token.fetch', 'calendar:read']
                                )
                                st.success("✅ Authentication successful!")
                                st.rerun()
                            else:
                                st.error("❌ Authentication failed")
                                
                        except Exception as e:
                            st.error(f"❌ Authentication error: {str(e)}")
            
            with col_auth2:
                # Manual token input
                st.subheader("🔑 Manual Token Input")
                bearer_token_input = st.text_input(
                    "Bearer Token",
                    type="password",
                    placeholder="Paste your bearer token here",
                    help="If you have a bearer token, paste it here"
                )
                
                if st.button("🔑 Use Token", disabled=not bearer_token_input):
                    if bearer_token_input and len(bearer_token_input.strip()) > 10:
                        st.session_state.bearer_token = bearer_token_input.strip()
                        
                        # Store token in token manager for consistency
                        token_manager.set_token_info(
                            access_token=bearer_token_input.strip(),
                            expires_in=3600,  # Default 1 hour
                            scopes=['outbound.token.fetch', 'calendar:read']
                        )
                        
                        st.success("✅ Bearer token set!")
                        st.rerun()
                    else:
                        st.error("❌ Please enter a valid bearer token")
        
        # Test MCP connection
        elif 'mcp_client' not in st.session_state or not st.session_state.mcp_client:
            st.subheader("🔗 Connect to CRM")
            st.info("Authenticated! Now let's connect to the CRM system.")
            
            if st.button("🔗 Connect to CRM", type="primary"):
                with st.spinner("Connecting to CRM..."):
                    try:
                        # Log the bearer token being used
                        print(f"🔑 Streamlit UI using bearer token: {st.session_state.bearer_token[:20]}...")
                        print(f"🔑 Full bearer token: {st.session_state.bearer_token}")
                        
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(
                            test_descope_mcp_connection(mcp_server_url, st.session_state.bearer_token)
                        )
                        
                        if result:
                            st.session_state.mcp_client = result
                            st.success("✅ Connected to CRM successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to connect to CRM")
                            
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")
        
        # Main chat interface
        else:
            st.subheader("💬 Chat with CRM Assistant")
            
            # Initialize chat history
            if "messages" not in st.session_state:
                st.session_state.messages = []
            
            # Display chat messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant":
                        # Show formatted response
                        st.markdown(message["content"])
                    else:
                        st.markdown(message["content"])
            
            # Response format toggle
            col_toggle1, col_toggle2 = st.columns([1, 4])
            with col_toggle1:
                show_full_response = st.checkbox("Show full response", value=False, help="Toggle between formatted and raw response")
            
            # Chat input
            if prompt := st.chat_input("Ask me to help with your CRM tasks..."):
                # Add user message to chat history
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Get agent response
                with st.chat_message("assistant"):
                    with st.spinner("Assistant is thinking..."):
                        try:
                            # Log the bearer token being used for the request
                            if 'bearer_token' in st.session_state:
                                print(f"🔑 Chat using bearer token: {st.session_state.bearer_token[:20]}...")
                                print(f"🔑 Full bearer token: {st.session_state.bearer_token}")
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            response = loop.run_until_complete(
                                st.session_state.mcp_client.ainvoke({"messages": prompt})
                            )
                            
                            # Format the response nicely
                            formatted_response = format_agent_response(response, show_full=show_full_response)
                            
                            if show_full_response:
                                # Show raw response in an expandable section
                                with st.expander("🔍 Raw Response", expanded=False):
                                    st.json(response)
                                st.markdown("**Formatted Response:**")
                                st.markdown(formatted_response)
                            else:
                                st.markdown(formatted_response)
                            
                            # Check for session termination and permission errors
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                
                                # First check for session termination
                                loop.run_until_complete(handle_session_termination_errors(response, mcp_server_url))
                                
                                # Then check for permission errors
                                loop.run_until_complete(handle_permission_errors(response, mcp_server_url))
                            except Exception as e:
                                st.error(f"Error handling session/permission errors: {str(e)}")
                            
                            # Add assistant response to chat history
                            st.session_state.messages.append({"role": "assistant", "content": formatted_response})
                            
                        except Exception as e:
                            error_msg = f"❌ Error: {str(e)}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Sidebar with status and controls
        st.header("📊 Status")
        
        # Connection status
        if 'bearer_token' in st.session_state:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown('<p class="status-success">✅ Authenticated</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown('<p class="status-warning">⚠️ Not authenticated</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if 'mcp_client' in st.session_state:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown('<p class="status-success">✅ Connected to CRM</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown('<p class="status-warning">⚠️ Not connected</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Permission management
        if 'mcp_client' in st.session_state and st.session_state.mcp_client:
            st.header("🔑 Permissions")
            
            # Show current scopes
            current_scopes = token_manager.scopes or ['outbound.token.fetch', 'calendar:read']
            st.info(f"**Current permissions:** {', '.join(current_scopes)}")
            
            # Calendar write permission
            if 'calendar:write' not in current_scopes:
                st.markdown('<div class="permission-section">', unsafe_allow_html=True)
                st.subheader("📅 Calendar Write Access")
                st.info("Request permission to create and modify calendar events")
                
                if st.button("🔑 Request Calendar Write Permission", type="secondary"):
                    with st.spinner("Requesting calendar write permission..."):
                        try:
                            # Get current OAuth endpoints
                            if 'oauth_endpoints' not in st.session_state:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                oauth_endpoints = loop.run_until_complete(discover_descope_endpoints(mcp_server_url))
                                st.session_state.oauth_endpoints = oauth_endpoints
                            
                            # Get current scopes
                            current_scopes = token_manager.scopes or ['outbound.token.fetch', 'calendar:read']
                            
                            # Add the calendar write scope
                            new_scopes = list(set(current_scopes + ['calendar:write']))
                            
                            # Perform OAuth flow with expanded scopes
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            from descope_oauth_agent import perform_descope_oauth_flow_with_scopes
                            callback_url = "http://localhost:8085/callback"
                            
                            # Don't use stored client ID for scope upgrades to avoid callback URL mismatch
                            # Always register a new client for scope upgrades
                            client_id_to_use = None
                            
                            new_token = loop.run_until_complete(
                                perform_descope_oauth_flow_with_scopes(
                                    st.session_state.oauth_endpoints, 
                                    callback_url, 
                                    new_scopes,
                                    client_id_to_use
                                )
                            )
                            
                            if new_token:
                                st.session_state.bearer_token = new_token
                                token_manager.access_token = new_token
                                token_manager.scopes = new_scopes
                                
                                # Validate token scopes first
                                scope_valid = loop.run_until_complete(
                                    validate_token_scopes(new_token, new_scopes)
                                )
                                
                                if not scope_valid:
                                    st.warning("⚠️ Token may not have all required scopes")
                                
                                # Reconnect to MCP with new token
                                result = loop.run_until_complete(
                                    test_descope_mcp_connection(mcp_server_url, new_token)
                                )
                                
                                if result:
                                    st.session_state.mcp_client = result
                                    st.success("✅ Successfully obtained calendar write permission!")
                                    st.info(f"🔑 Using new token: {new_token[:20]}...")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to reconnect to CRM with new permissions")
                                    st.info("💡 This might be due to token scope issues or server connectivity problems")
                            else:
                                st.error("❌ Failed to obtain calendar write permission")
                                
                        except Exception as e:
                            st.error(f"❌ Error requesting calendar permission: {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Calendar write permission granted")
        
        # Session controls
        st.header("⚙️ Controls")
        
        # Clear chat history
        if st.button("🗑️ Clear Chat", help="Clear chat history"):
            if "messages" in st.session_state:
                del st.session_state.messages
            st.success("✅ Chat history cleared!")
            st.rerun()
        
        # Disconnect
        if st.button("🔌 Disconnect", help="Disconnect from CRM"):
            if 'mcp_client' in st.session_state:
                del st.session_state.mcp_client
            if 'bearer_token' in st.session_state:
                del st.session_state.bearer_token
            if "messages" in st.session_state:
                del st.session_state.messages
            st.success("✅ Disconnected!")
            st.rerun()
        
        # Session info
        st.subheader("ℹ️ Session Info")
        st.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if 'oauth_endpoints' in st.session_state:
            st.info(f"OAuth endpoints: {len(st.session_state.oauth_endpoints)}")

if __name__ == "__main__":
    main()