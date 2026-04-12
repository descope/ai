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

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * MCP Server implementation using Jetty and HttpServletSseServerTransportProvider
 */
public class App {

    private static final Logger log = LoggerFactory.getLogger(App.class);
    private static final GoogleCalendarService googleCalendarService = new GoogleCalendarService();
    private static final AuthenticationService authService = new AuthenticationService();

    public static void main(String[] args) {
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
                        String[] requiredScopes = {"outbound.token.fetch"};
                        
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
                        String[] requiredScopes = {"outbound.token.fetch"};
                        
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
                        String[] requiredScopes = {"outbound.token.fetch"};
                        
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
                        String[] requiredScopes = {"outbound.token.fetch"};
                        
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

        // Send logging notifications
        syncServer.loggingNotification(McpSchema.LoggingMessageNotification.builder()
                .level(McpSchema.LoggingLevel.INFO)
                .logger("mcp-server")
                .data("Server initialized and ready to handle connections")
                .build());

        log.info("MCP Server info: {}", syncServer.getServerInfo());

        // Set up Jetty with a context handler
        ServletContextHandler contextHandler = new ServletContextHandler(ServletContextHandler.SESSIONS);
        contextHandler.setContextPath("/");
        
        // Add the MCP transport provider as a servlet
        ServletHolder servletHolder = new ServletHolder(transportProvider);
        contextHandler.addServlet(servletHolder, "/*");

        // Start Jetty on port 8080
        Server server = new Server(8080);
        server.setHandler(contextHandler);

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
