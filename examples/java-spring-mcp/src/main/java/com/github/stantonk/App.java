package com.github.stantonk;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.server.transport.HttpServletSseServerTransportProvider;
import io.modelcontextprotocol.spec.McpSchema;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.FilterConfig;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.List;
import java.util.Map;

/**
 * MCP Server implementation using Jetty and HttpServletSseServerTransportProvider
 */
public class App {

    private static final Logger log = LoggerFactory.getLogger(App.class);
    private static final GoogleCalendarService googleCalendarService = new GoogleCalendarService();
    private static final AuthenticationService authService = new AuthenticationService();
    
    // Descope configuration - read at runtime
    private static String getDescopeProjectId() {
        log.info("Getting Descope Project ID...");
        
        // Try system property first, then environment variable
        String projectId = System.getProperty("DESCOPE_PROJECT_ID");
        log.info("System property DESCOPE_PROJECT_ID: {}", projectId);
        
        if (projectId == null || projectId.trim().isEmpty()) {
            projectId = System.getenv("DESCOPE_PROJECT_ID");
            log.info("Environment variable DESCOPE_PROJECT_ID: {}", projectId);
        }
        
        if (projectId == null || projectId.trim().isEmpty()) {
            projectId = "P2zinVOiGTv8WEcvDrlUttNsb4Y4"; // Fallback value
            log.info("Using fallback Project ID: {}", projectId);
        }
        
        log.info("Final Descope Project ID: {}", projectId);
        return projectId;
    }
    
    private static String getDescopeBaseUrl() {
        // Try system property first, then environment variable
        String baseUrl = System.getProperty("DESCOPE_BASE_URL");
        if (baseUrl == null || baseUrl.trim().isEmpty()) {
            baseUrl = System.getenv("DESCOPE_BASE_URL");
        }
        if (baseUrl == null || baseUrl.trim().isEmpty()) {
            baseUrl = "https://api.descope.com";
        }
        log.info("Descope Base URL: {}", baseUrl);
        return baseUrl;
    }
    
    // OAuth Authorization Server servlet
    static class OAuthAuthorizationServerServlet extends HttpServlet {
        @Override
        protected void doGet(HttpServletRequest request, HttpServletResponse response) 
                throws ServletException, IOException {
            String requestId = java.util.UUID.randomUUID().toString().substring(0, 8);
            String userAgent = request.getHeader("User-Agent");
            
            log.info("[{}] OAuth Authorization Server Request: {} {} | User-Agent: {}", 
                    requestId, request.getMethod(), request.getRequestURI(), userAgent);
            
            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");
            
            PrintWriter out = response.getWriter();
            
            log.info("[{}] About to get Descope configuration", requestId);
            String projectId = getDescopeProjectId();
            log.info("[{}] Project ID retrieved: {}", requestId, projectId);
            String descopeBaseUrl = getDescopeBaseUrl();
            log.info("[{}] Base URL retrieved: {}", requestId, descopeBaseUrl);
            
            out.println("{");
            out.println("  \"issuer\": \"" + descopeBaseUrl + "/v1/apps/" + projectId + "\",");
            out.println("  \"jwks_uri\": \"" + descopeBaseUrl + "/" + projectId + "/.well-known/jwks.json\",");
            out.println("  \"authorization_endpoint\": \"" + descopeBaseUrl + "/oauth2/v1/apps/authorize\",");
            out.println("  \"response_types_supported\": [\"code\"],");
            out.println("  \"subject_types_supported\": [\"public\"],");
            out.println("  \"id_token_signing_alg_values_supported\": [\"RS256\"],");
            out.println("  \"code_challenge_methods_supported\": [\"S256\"],");
            out.println("  \"token_endpoint\": \"" + descopeBaseUrl + "/oauth2/v1/apps/token\",");
            out.println("  \"userinfo_endpoint\": \"" + descopeBaseUrl + "/oauth2/v1/apps/userinfo\",");
            out.println("  \"scopes_supported\": [\"openid\"],");
            out.println("  \"claims_supported\": [");
            out.println("    \"iss\", \"aud\", \"iat\", \"exp\", \"sub\", \"name\", \"email\",");
            out.println("    \"email_verified\", \"phone_number\", \"phone_number_verified\",");
            out.println("    \"picture\", \"family_name\", \"given_name\"");
            out.println("  ],");
            out.println("  \"revocation_endpoint\": \"" + descopeBaseUrl + "/oauth2/v1/apps/revoke\",");
            out.println("  \"registration_endpoint\": \"" + descopeBaseUrl + "/v1/mgmt/inboundapp/app/" + projectId + "/register\",");
            out.println("  \"grant_types_supported\": [\"authorization_code\", \"refresh_token\"],");
            out.println("  \"token_endpoint_auth_methods_supported\": [\"client_secret_post\"],");
            out.println("  \"end_session_endpoint\": \"" + descopeBaseUrl + "/oauth2/v1/apps/logout\"");
            out.println("}");
            
            log.info("[{}] OAuth Authorization Server response sent", requestId);
        }
    }
    
    // OAuth Protected Resource servlet
    static class OAuthProtectedResourceServlet extends HttpServlet {
        @Override
        protected void doGet(HttpServletRequest request, HttpServletResponse response) 
                throws ServletException, IOException {
            String requestId = java.util.UUID.randomUUID().toString().substring(0, 8);
            String userAgent = request.getHeader("User-Agent");
            
            log.info("[{}] OAuth Protected Resource Request: {} {} | User-Agent: {}", 
                    requestId, request.getMethod(), request.getRequestURI(), userAgent);
            
            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");
            
            PrintWriter out = response.getWriter();
            String baseUrl = getBaseUrl(request);
            
            out.println("{");
            out.println("  \"resource\": \"" + baseUrl + "\",");
            out.println("  \"authorization_servers\": [\"" + baseUrl + "\"],");
            out.println("  \"resource_name\": \"Java Spring MCP Server\"");
            out.println("}");
            
            log.info("[{}] OAuth Protected Resource response sent", requestId);
        }
    }
    
    // Helper method to get base URL
    private static String getBaseUrl(HttpServletRequest request) {
        String scheme = request.getScheme();
        String serverName = request.getServerName();
        int serverPort = request.getServerPort();
        
        if (("http".equals(scheme) && serverPort == 80) || ("https".equals(scheme) && serverPort == 443)) {
            return scheme + "://" + serverName;
        } else {
            return scheme + "://" + serverName + ":" + serverPort;
        }
    }
    
    // CORS Filter to handle cross-origin requests
    static class CorsFilter implements Filter {
        @Override
        public void init(FilterConfig filterConfig) throws ServletException {
            // No initialization needed
        }
        
        @Override
        public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) 
                throws IOException, ServletException {
            HttpServletRequest httpRequest = (HttpServletRequest) request;
            HttpServletResponse httpResponse = (HttpServletResponse) response;
            
            // Add CORS headers
            httpResponse.setHeader("Access-Control-Allow-Origin", "*");
            httpResponse.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
            httpResponse.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, Origin, User-Agent");
            httpResponse.setHeader("Access-Control-Max-Age", "86400");
            
            // Handle preflight OPTIONS requests
            if ("OPTIONS".equalsIgnoreCase(httpRequest.getMethod())) {
                httpResponse.setStatus(HttpServletResponse.SC_OK);
                return;
            }
            
            // Continue with the request
            chain.doFilter(request, response);
        }
        
        @Override
        public void destroy() {
            // No cleanup needed
        }
    }
    
    // Health check servlet
    static class HealthCheckServlet extends HttpServlet {
        @Override
        protected void doGet(HttpServletRequest request, HttpServletResponse response) 
                throws ServletException, IOException {
            String requestId = java.util.UUID.randomUUID().toString().substring(0, 8);
            log.info("[{}] Health check request", requestId);
            
            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");
            
            PrintWriter out = response.getWriter();
            out.println("{");
            out.println("  \"status\": \"healthy\",");
            out.println("  \"service\": \"Java Spring MCP Server\",");
            out.println("  \"timestamp\": \"" + java.time.Instant.now() + "\",");
            out.println("  \"version\": \"1.0.0\"");
            out.println("}");
            
            log.info("[{}] Health check response sent", requestId);
        }
    }
    
    // Authenticated MCP Servlet that requires Bearer token
    static class AuthenticatedMcpServlet extends HttpServlet {
        private final HttpServletSseServerTransportProvider mcpTransport;
        private final AuthenticationService authService;
        
        public AuthenticatedMcpServlet(HttpServletSseServerTransportProvider mcpTransport) {
            this.mcpTransport = mcpTransport;
            this.authService = new AuthenticationService();
        }
        
        @Override
        protected void doGet(HttpServletRequest request, HttpServletResponse response) 
                throws ServletException, IOException {
            String requestId = java.util.UUID.randomUUID().toString().substring(0, 8);
            String method = request.getMethod();
            String uri = request.getRequestURI();
            String userAgent = request.getHeader("User-Agent");
            String accept = request.getHeader("Accept");
            
            log.info("[{}] MCP Request: {} {} | User-Agent: {} | Accept: {}", 
                    requestId, method, uri, userAgent, accept);
            
            // Log all headers for debugging
            java.util.Enumeration<String> headerNames = request.getHeaderNames();
            while (headerNames.hasMoreElements()) {
                String headerName = headerNames.nextElement();
                String headerValue = request.getHeader(headerName);
                // Don't log the full token for security
                if ("authorization".equalsIgnoreCase(headerName)) {
                    if (headerValue != null && headerValue.startsWith("Bearer ")) {
                        String tokenPreview = headerValue.substring(0, Math.min(20, headerValue.length())) + "...";
                        log.info("[{}] Header: {} = {}", requestId, headerName, tokenPreview);
                    } else {
                        log.info("[{}] Header: {} = {}", requestId, headerName, headerValue);
                    }
                } else {
                    log.info("[{}] Header: {} = {}", requestId, headerName, headerValue);
                }
            }
            
            // Check if this is a metadata request (no Authorization header required)
            String authHeader = request.getHeader("Authorization");
            if (authHeader == null || authHeader.trim().isEmpty()) {
                log.info("[{}] No Authorization header - allowing metadata request to pass through", requestId);
                // Allow the request to pass through to the MCP transport for metadata
                mcpTransport.service(request, response);
                log.info("[{}] Metadata request completed", requestId);
                return;
            }
            
            if (!authHeader.startsWith("Bearer ")) {
                log.warn("[{}] Authentication failed: Invalid Authorization header format", requestId);
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.setContentType("application/json");
                response.getWriter().write("{\"error\": \"Invalid Authorization header format, expected 'Bearer TOKEN'\"}");
                return;
            }
            
            String token = authHeader.substring(7); // Remove "Bearer " prefix
            log.info("[{}] Token received (length: {})", requestId, token.length());
            
            try {
                // Validate token (basic validation - just check if it's not empty)
                // In a real implementation, you would validate with Descope SDK
                if (token.trim().isEmpty()) {
                    log.warn("[{}] Authentication failed: Empty token", requestId);
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.setContentType("application/json");
                    response.getWriter().write("{\"error\": \"Invalid token\"}");
                    return;
                }
                
                // For now, we'll accept any non-empty token for testing
                // TODO: Replace with actual Descope SDK validation
                log.info("[{}] Token validation passed, forwarding to MCP transport", requestId);
                
                // Forward to the actual MCP transport
                mcpTransport.service(request, response);
                
                log.info("[{}] MCP request completed successfully", requestId);
                
            } catch (Exception e) {
                log.error("[{}] Authentication error", requestId, e);
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.setContentType("application/json");
                response.getWriter().write("{\"error\": \"Authentication failed: " + e.getMessage() + "\"}");
            }
        }
        
        @Override
        protected void doPost(HttpServletRequest request, HttpServletResponse response) 
                throws ServletException, IOException {
            // Handle POST requests the same way as GET for SSE
            doGet(request, response);
        }
    }

    public static void main(String[] args) {
        log.info("=== Starting Java Spring MCP Server ===");
        log.info("Descope Project ID: {}", getDescopeProjectId());
        log.info("Descope Base URL: {}", getDescopeBaseUrl());
        log.info("Server will run on port 8080");
        System.out.println("Starting MCP Server...");

        /**
         * Note, HttpServletSseServerTransportProvider extends HttpServlet
         */
        HttpServletSseServerTransportProvider transportProvider =
            new HttpServletSseServerTransportProvider(new ObjectMapper(), "/mcp/message");

        // Create a server with custom configuration
        McpSyncServer syncServer = McpServer.sync(transportProvider)
                .serverInfo("mcp-jetty-server", "0.8.1")
                .capabilities(McpSchema.ServerCapabilities.builder()
                        .resources(true, true)     // Enable resource support
                        .tools(true)               // Enable tool support
                        .prompts(true)             // Enable prompt support
                        .logging()                 // Enable logging support
                        .build())
                .build();

        log.info("Registering MCP tools...");

        // Register Google Calendar tools using outbound app pattern
        McpServerFeatures.SyncToolSpecification upcomingEventsTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool(
                        "get_upcoming_events",
                        "gets upcoming events from the primary calendar using outbound app token",
                        new McpSchema.JsonSchema(
                                "object",
                                Map.of("max_results", Map.of("type", "number", "minimum", 1, "maximum", 50)),
                                List.of(),
                                false)
                ),
                (exchange, arguments) -> {
                    try {
                        // Scope definition
                        String[] requiredScopes = {"calendar:read"};
                        
                        // Validate token and get both inbound token and user ID
                        TokenUtils.TokenValidationResult auth = TokenUtils.validateTokenAndGetUser(exchange, requiredScopes);
                        log.debug("Calendar read tool accessed by user: {}", auth.getUserId());
                        
                        Integer maxResults = (Integer) arguments.getOrDefault("max_results", 10);
                        String result = googleCalendarService.getUpcomingEvents(auth.getInboundToken(), auth.getUserId(), maxResults);
                        return new McpSchema.CallToolResult(List.of(new McpSchema.TextContent(result)), false);
                    } catch (Exception e) {
                        log.error("Error getting upcoming events", e);
                        return new McpSchema.CallToolResult(List.of(new McpSchema.TextContent("Error: " + e.getMessage())), false);
                    }
                }
        );
        syncServer.addTool(upcomingEventsTool);
        log.info("Registered get_upcoming_events tool");

        McpServerFeatures.SyncToolSpecification dateRangeEventsTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool(
                        "get_events_by_date_range",
                        "gets events within a specific date range using outbound app token",
                        new McpSchema.JsonSchema(
                                "object",
                                Map.of("start_date", Map.of("type", "string", "pattern", "^\\d{4}-\\d{2}-\\d{2}$"),
                                        "end_date", Map.of("type", "string", "pattern", "^\\d{4}-\\d{2}-\\d{2}$")),
                                List.of("start_date", "end_date"),
                                false)
                ),
                (exchange, arguments) -> {
                    try {
                        // Scope definition
                        String[] requiredScopes = {"calendar:read"};
                        
                        // Validate token and get both inbound token and user ID
                        TokenUtils.TokenValidationResult auth = TokenUtils.validateTokenAndGetUser(exchange, requiredScopes);
                        log.debug("Calendar date range tool accessed by user: {}", auth.getUserId());
                        
                        String startDate = (String) arguments.get("start_date");
                        String endDate = (String) arguments.get("end_date");
                        String result = googleCalendarService.getEventsForDateRange(auth.getInboundToken(), auth.getUserId(), startDate, endDate);
                        return new McpSchema.CallToolResult(List.of(new McpSchema.TextContent(result)), false);
                    } catch (Exception e) {
                        log.error("Error getting events for date range", e);
                        return new McpSchema.CallToolResult(List.of(new McpSchema.TextContent("Error: " + e.getMessage())), false);
                    }
                }
        );
        syncServer.addTool(dateRangeEventsTool);
        log.info("Registered get_events_by_date_range tool");

        McpServerFeatures.SyncToolSpecification searchEventsTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool(
                        "search_events",
                        "searches for events with a specific query using outbound app token",
                        new McpSchema.JsonSchema(
                                "object",
                                Map.of("query", Map.of("type", "string", "minLength", 1)),
                                List.of("query"),
                                false)
                ),
                (exchange, arguments) -> {
                    try {
                        // Scope definition
                        String[] requiredScopes = {"calendar:search"};
                        
                        // Validate token and get both inbound token and user ID
                        TokenUtils.TokenValidationResult auth = TokenUtils.validateTokenAndGetUser(exchange, requiredScopes);
                        log.debug("Calendar search tool accessed by user: {}", auth.getUserId());
                        
                        String query = (String) arguments.get("query");
                        String result = googleCalendarService.searchEvents(auth.getInboundToken(), auth.getUserId(), query);
                        return new McpSchema.CallToolResult(List.of(new McpSchema.TextContent(result)), false);
                    } catch (Exception e) {
                        log.error("Error searching events", e);
                        return new McpSchema.CallToolResult(List.of(new McpSchema.TextContent("Error: " + e.getMessage())), false);
                    }
                }
        );
        syncServer.addTool(searchEventsTool);
        log.info("Registered search_events tool");

        McpServerFeatures.SyncToolSpecification createEventTool = new McpServerFeatures.SyncToolSpecification(
                new McpSchema.Tool(
                        "create_calendar_event",
                        "creates a new calendar event using outbound app token",
                        new McpSchema.JsonSchema(
                                "object",
                                Map.of("event_data", Map.of("type", "string", "description", "JSON string containing event details")),
                                List.of("event_data"),
                                false)
                ),
                (exchange, arguments) -> {
                    try {
                        // Scope definition
                        String[] requiredScopes = {"calendar:write"};
                        
                        // Validate token and get both inbound token and user ID
                        TokenUtils.TokenValidationResult auth = TokenUtils.validateTokenAndGetUser(exchange, requiredScopes);
                        log.debug("Calendar create event tool accessed by user: {}", auth.getUserId());
                        
                        String eventData = (String) arguments.get("event_data");
                        String result = googleCalendarService.createEvent(auth.getInboundToken(), auth.getUserId(), eventData);
                        return new McpSchema.CallToolResult(List.of(new McpSchema.TextContent(result)), false);
                    } catch (Exception e) {
                        log.error("Error creating event", e);
                        return new McpSchema.CallToolResult(List.of(new McpSchema.TextContent("Error: " + e.getMessage())), false);
                    }
                }
        );
        syncServer.addTool(createEventTool);
        log.info("Registered create_calendar_event tool");

        // Send logging notifications
        syncServer.loggingNotification(McpSchema.LoggingMessageNotification.builder()
                .level(McpSchema.LoggingLevel.INFO)
                .logger("mcp-server")
                .data("Server initialized and ready to handle connections")
                .build());

        log.info("MCP Server info: {}", syncServer.getServerInfo());
        log.info("Setting up Jetty server with authentication middleware...");

                // Set up Jetty with a context handler
        ServletContextHandler contextHandler = new ServletContextHandler(ServletContextHandler.SESSIONS);
        contextHandler.setContextPath("/");
        
        // Add CORS filter
        org.eclipse.jetty.servlet.FilterHolder corsFilter = new org.eclipse.jetty.servlet.FilterHolder(new CorsFilter());
        contextHandler.addFilter(corsFilter, "/*", java.util.EnumSet.of(jakarta.servlet.DispatcherType.REQUEST));
        log.info("Added CORS filter for all endpoints");

        // Add the OAuth Authorization Server servlet
        ServletHolder oauthServletHolder = new ServletHolder(new OAuthAuthorizationServerServlet());
        contextHandler.addServlet(oauthServletHolder, "/oauth/.well-known/openid-configuration");
        log.info("Added OAuth Authorization Server servlet at /oauth/.well-known/openid-configuration");
        
        // Add the OAuth Protected Resource servlet
        ServletHolder protectedServletHolder = new ServletHolder(new OAuthProtectedResourceServlet());
        contextHandler.addServlet(protectedServletHolder, "/oauth/protected-metadata-resource");
        log.info("Added OAuth Protected Resource servlet at /oauth/protected");
        
        // Add the Health Check servlet
        ServletHolder healthServletHolder = new ServletHolder(new HealthCheckServlet());
        contextHandler.addServlet(healthServletHolder, "/health");
        log.info("Added Health Check servlet at /health");
        
        // Add the MCP transport provider as a servlet (temporarily remove other endpoints)
        ServletHolder servletHolder = new ServletHolder(transportProvider);
        contextHandler.addServlet(servletHolder, "/*");
        log.info("Added MCP transport provider at /*");

        // Start Jetty on port 8080
        Server server = new Server(8080);
        server.setHandler(contextHandler);
        log.info("Jetty server configured and ready to start");

        try {
            server.start();
            log.info("Jetty server started on port 8080");
            
            // Add a shutdown hook for clean shutdown
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                try {
                    log.info("Shutting down MCP server...");
                    syncServer.close();
                    server.stop();
                } catch (Exception e) {
                    log.error("Error during shutdown", e);
                }
            }));
            
            server.join(); // Wait for the server to exit
        } catch (Exception e) {
            log.error("Error starting server", e);
            syncServer.close();
            throw new RuntimeException(e);
        }
    }
}
