# Java Spring MCP Server with Google Calendar Integration

This is a Model Context Protocol (MCP) server built with Java Spring that provides weather information and Google Calendar integration using Descope's outbound app pattern.

## Features

- **Weather Tool**: Fetches weather information using the National Weather Service API
- **Google Calendar Tools** (using outbound app tokens):
  - Get upcoming events
  - Search events by date range
  - Search events by query
  - Create new calendar events

## Setup

### Prerequisites

- Java 17 or higher
- Maven 3.6 or higher
- Descope project with outbound apps configured

### Descope Google Calendar Setup

1. Go to the [Descope Console](https://app.descope.com/)
2. Create a new project or select an existing one
3. Enable Inbound Apps feature
4. Create an outbound application for Google Calendar:
   - Go to "Inbound Apps" > "Outbound Applications"
   - Click "Create Outbound Application"
   - Configure Google Calendar OAuth settings
   - Note the outbound app ID (should be "google-calendar")
5. Get your Descope Management Key:
   - Go to "Settings" > "Management Keys"
   - Create a new management key with appropriate permissions

### Environment Variables

You can use the setup script to quickly configure your environment:

```bash
./setup-env.sh
```

Or manually copy the example environment file and configure your settings:

```bash
cp env.example .env
```

Then edit `.env` with your actual values:

```bash
# Required variables
DESCOPE_PROJECT_ID=your_descope_project_id
DESCOPE_MANAGEMENT_KEY=your_descope_management_key

# Optional variables (uncomment and modify as needed)
# DESCOPE_BASE_URL=https://api.descope.com
# DESCOPE_MANAGEMENT_BASE_URL=https://api.descope.com
# DESCOPE_LOG_LEVEL=INFO
# DESCOPE_TIMEOUT=30000
# MCP_SERVER_PORT=8080
# MCP_SERVER_HOST=localhost
```

**Note**: The Google Calendar outbound app ID is hardcoded as `"google-calendar"` in the `GoogleCalendarService`.

#### Environment Variable Details

- **DESCOPE_PROJECT_ID** (required): Your Descope project identifier
- **DESCOPE_MANAGEMENT_KEY** (required): Management key for outbound app operations
- **DESCOPE_BASE_URL** (optional): Custom Descope API base URL (defaults to https://api.descope.com)
- **DESCOPE_MANAGEMENT_BASE_URL** (optional): Custom management API base URL
- **DESCOPE_LOG_LEVEL** (optional): Logging level for Descope SDK (default: INFO)
- **DESCOPE_TIMEOUT** (optional): Request timeout in milliseconds (default: 30000)
- **MCP_SERVER_PORT** (optional): Port for the MCP server (default: 8080)
- **MCP_SERVER_HOST** (optional): Host for the MCP server (default: localhost)

### Running the Server

1. Build the project:

   ```bash
   mvn clean package
   ```

2. Run the server:

   ```bash
   java -jar target/mcp-server-1.0-SNAPSHOT.jar
   ```

3. The server will start on port 8080 and use outbound app tokens for Google Calendar access

## Available Tools

### Weather Tool

- **Name**: `weather`
- **Description**: Fetches weather from latitude and longitude coordinates
- **Parameters**:
  - `latitude` (number): Latitude coordinate (-90 to 90)
  - `longitude` (number): Longitude coordinate (-180 to 180)

### Calendar Tools

#### Get Upcoming Events

- **Name**: `get_upcoming_events`
- **Description**: Gets upcoming events from the primary calendar using outbound app token
- **Parameters**:
  - `max_results` (number): Maximum number of events to return (default: 10)

#### Get Events by Date Range

- **Name**: `get_events_by_date_range`
- **Description**: Gets events within a specific date range using outbound app token
- **Parameters**:
  - `start_date` (string): Start date in YYYY-MM-DD format
  - `end_date` (string): End date in YYYY-MM-DD format

#### Search Events

- **Name**: `search_events`
- **Description**: Searches for events with a specific query using outbound app token
- **Parameters**:
  - `query` (string): Search query for events

#### Create Calendar Event

- **Name**: `create_calendar_event`
- **Description**: Creates a new calendar event using outbound app token
- **Parameters**:
  - `event_data` (string): JSON string containing event details

## API Endpoints

- **MCP Endpoint**: `http://localhost:8080/mcp/message`

## Configuration

The server uses the following configuration:

- **Server Port**: 8080
- **Google Calendar Integration**: Uses Descope's outbound app pattern for Google Calendar access
- **Authentication**: Token validation and user ID extraction using Descope's authentication service

## Authentication Implementation

The server includes a comprehensive authentication system:

### `AuthenticationService.java`

- Validates inbound tokens using Descope's authentication service
- Extracts user IDs and scopes from validated tokens
- Implements proper scope validation by checking if required scopes are included in the token's scope list
- Returns `TokenValidationResult` containing both user ID and available scopes

### `TokenUtils.java`

- Provides a generic `validateTokenAndGetUser()` function that takes scopes as a parameter
- Returns both the inbound token and user ID in a `TokenValidationResult` object
- Implements scope validation for different tools
- Offers decorator-like scope definitions at the top of each tool

### `GoogleCalendarService.java`

- Handles Google Calendar operations using Descope's outbound app pattern
- Demonstrates how to use outbound app tokens to access Google Calendar API
- Provides methods for reading, searching, and creating calendar events
- Uses the outbound app token exchange to avoid storing Google credentials directly

### Tool-Level Authentication

Each tool now includes proper authentication with decorator-like scope definitions:

```java
// Scope definition (like a decorator)
String[] requiredScopes = {"weather:read"};

// Validate token and get both inbound token and user ID
TokenUtils.TokenValidationResult auth = TokenUtils.validateTokenAndGetUser(exchange, requiredScopes);

// Use both inbound token and user ID for outbound app operations
String result = outboundAppService.someMethod(auth.getInboundToken(), auth.getUserId(), ...);
```

**Available Scopes:**

- **Weather Tool**: `weather:read`
- **Calendar Read Tools**: `calendar:read` (get_upcoming_events, get_events_by_date_range)
- **Calendar Search Tool**: `calendar:search` (search_events)
- **Calendar Write Tool**: `calendar:write` (create_calendar_event)

## How It Works

1. **Authentication**: The MCP server validates inbound tokens from the Authorization header using Descope's authentication service
2. **User ID Extraction**: User ID is extracted from the validated token for outbound app operations
3. **Scope Validation**: Each tool validates that the user has the required scopes for the operation
4. **Outbound Token Exchange**: The server exchanges the inbound token for an outbound token using Descope's outbound app API
5. **Google Calendar API**: The outbound token is used to make authenticated requests to Google Calendar API
6. **Response**: Calendar data is returned to the MCP client

### Authentication Flow

```
Client Request → Authorization Header → Token Validation → User ID & Scope Extraction → Scope Validation → Outbound Token Exchange → API Call
```

### Scope Validation Process

1. **Token Validation**: The Descope SDK validates the inbound token and returns user information including scopes
2. **Scope Extraction**: Available scopes are extracted from the token response
3. **Scope Comparison**: Required scopes for the tool are compared against available scopes in the token
4. **Access Control**: If any required scope is missing, access is denied with a clear error message
5. **Success**: If all required scopes are present, the tool execution proceeds with both inbound token and user ID

### Tool-Specific Scopes

- **Weather Tool**: `weather:read`
- **Calendar Read Tools**: `calendar:read` (get_upcoming_events, get_events_by_date_range)
- **Calendar Search Tool**: `calendar:search` (search_events)
- **Calendar Write Tool**: `calendar:write` (create_calendar_event)

## Troubleshooting

1. **Missing environment variables**: Ensure all required environment variables are set
2. **Outbound app not configured**: Make sure the Google Calendar outbound app is properly configured in Descope
3. **Management key permissions**: Verify the management key has outbound app access permissions
4. **Network connectivity**: Ensure the server can reach both Descope and Google APIs
