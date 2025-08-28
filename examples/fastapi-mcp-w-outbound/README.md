# Google Calendar MCP Server with Descope Outbound Apps

This FastAPI MCP server provides Google Calendar integration using Descope outbound apps for OAuth token management.

## Features

- **Create Calendar Events**: Create new events in Google Calendar
- **List Calendar Events**: Retrieve events from Google Calendar with optional time filtering
- **OAuth Integration**: Uses Descope outbound apps to manage Google OAuth tokens
- **Secure Authentication**: Validates tokens using Descope's JWT verification

## Setup

### 1. Environment Variables

Create a `.env` file with the following variables:

```env
# Descope Configuration
DESCOPE_PROJECT_ID=your-descope-project-id
DESCOPE_API_BASE_URL=https://api.descope.com

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
GOOGLE_OUTBOUND_APP_ID=google-calendar-app
```

### 2. Google OAuth Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Set application type to "Web application"
   - Add authorized redirect URIs for your Descope outbound app
   - Copy the Client ID and Client Secret

### 3. Descope Outbound App Setup

1. In your Descope project, create an outbound application for Google Calendar
2. Configure the OAuth settings with your Google OAuth credentials
3. Set the appropriate scopes: `https://www.googleapis.com/auth/calendar`
4. Note the outbound app ID and update `GOOGLE_OUTBOUND_APP_ID` in your `.env` file

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Server

```bash
python -m uvicorn app.main:app --reload
```

## API Endpoints

### Create Calendar Event

**POST** `/calendar/events`

Request body:

```json
{
  "summary": "Team Meeting",
  "description": "Weekly team sync",
  "start_time": "2024-01-15T10:00:00",
  "end_time": "2024-01-15T11:00:00",
  "location": "Conference Room A",
  "attendees": ["user1@example.com", "user2@example.com"]
}
```

### List Calendar Events

**GET** `/calendar/events?time_min=2024-01-15T00:00:00&time_max=2024-01-16T00:00:00&max_results=10`

Query parameters:

- `time_min` (optional): Start time for the query (ISO format)
- `time_max` (optional): End time for the query (ISO format)
- `max_results` (optional): Maximum number of events to return (default: 10)

## Authentication

All endpoints require a valid Descope JWT token in the Authorization header:

```
Authorization: Bearer <descope-jwt-token>
```

The server will:

1. Validate the JWT token using Descope's public keys
2. Extract the user ID from the token
3. Use the token to fetch the Google OAuth access token from Descope's outbound app
4. Use the Google access token to interact with the Google Calendar API

## MCP Integration

This server is configured as an MCP (Model Context Protocol) server, allowing it to be used with MCP-compatible clients. The server provides two tools:

- `create-calendar-event`: Creates a new calendar event
- `list-calendar-events`: Lists calendar events within a time range

## Error Handling

The server includes comprehensive error handling for:

- Invalid or expired tokens
- Google Calendar API errors
- Missing required fields
- Network connectivity issues

## Security Considerations

- All tokens are validated using Descope's JWT verification
- Google OAuth tokens are fetched securely through Descope's outbound app system
- No sensitive credentials are stored in the application code
- All API responses are properly sanitized
