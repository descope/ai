package com.github.stantonk;

import com.descope.client.DescopeClient;
import com.descope.exception.DescopeException;
import com.descope.model.outbound.FetchLatestOutboundAppUserTokenRequest;
import com.descope.model.outbound.FetchOutboundAppUserTokenResponse;
import com.descope.sdk.mgmt.OutboundAppsByTokenService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.io.entity.StringEntity;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;

/**
 * Service for Google Calendar operations using Descope's outbound app pattern.
 * 
 * This service demonstrates how to use Descope's outbound app tokens to access
 * Google Calendar API without storing Google credentials directly in the application.
 */
public class GoogleCalendarService {
    private static final Logger log = LoggerFactory.getLogger(GoogleCalendarService.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String GOOGLE_CALENDAR_BASE_URL = "https://www.googleapis.com/calendar/v3";
    
    private static final String GOOGLE_OUTBOUND_APP_ID = "google-calendar"; // Fixed app ID as specified
    
    // Descope configuration constants
    private static final String DESCOPE_BASE_URL = System.getenv("DESCOPE_BASE_URL") != null ? 
        System.getenv("DESCOPE_BASE_URL") : "https://api.descope.com";
    
    private final DescopeClient descopeClient;
    private final OutboundAppsByTokenService outboundAppsService;

    public GoogleCalendarService() {
        this.descopeClient = new DescopeClient();
        this.outboundAppsService = descopeClient.getManagementServices().getOutboundAppsByTokenService();
    }
    
    /**
     * Get the Descope project ID from environment variables
     */
    private String getDescopeProjectId() {
        String projectId = System.getenv("DESCOPE_PROJECT_ID");
        if (projectId == null || projectId.trim().isEmpty()) {
            throw new RuntimeException("DESCOPE_PROJECT_ID environment variable is not set");
        }
        return projectId;
    }

    /**
     * Get an outbound app token from Descope using the inbound token and user ID
     * This method makes a manual HTTP request to the Descope outbound app token endpoint
     */
    public String getOutboundAppToken(String inboundToken, String userId) throws IOException {
        try {
            String cleanToken = inboundToken;
            if (inboundToken.startsWith("Bearer ")) {
                cleanToken = inboundToken.substring(7);
            }
            
            // Build the request body
            String requestBody = String.format(
                "{\"appId\": \"%s\", \"userId\": \"%s\"}",
                GOOGLE_OUTBOUND_APP_ID,
                userId
            );
            
            // Build the authorization header: Descope_project_id:<inbound_token>
            String projectId = getDescopeProjectId();
            String authHeader = String.format("Bearer %s:%s", projectId, cleanToken);
            
            log.debug("Making outbound app token request to Descope with auth header: {}:...", projectId);
            log.debug("Request body: {}", requestBody);
            
            // Make the HTTP request manually
            try (CloseableHttpClient client = HttpClients.createDefault()) {
                HttpPost request = new HttpPost(DESCOPE_BASE_URL + "/v1/mgmt/outbound/app/user/token/latest");
                request.setHeader("Authorization", authHeader);
                request.setHeader("Content-Type", "application/json");
                request.setEntity(new StringEntity(requestBody, ContentType.APPLICATION_JSON));
                
                return client.execute(request, response -> {
                    if (response.getCode() == 200) {
                        JsonNode responseBody = MAPPER.readTree(response.getEntity().getContent());
                        String accessToken = responseBody.get("token").get("accessToken").asText();
                        log.debug("Successfully obtained outbound app token");
                        return accessToken;
                    } else {
                        String errorBody = EntityUtils.toString(response.getEntity());
                        log.error("Failed to get outbound token. Status: {}, Response: {}", response.getCode(), errorBody);
                        throw new RuntimeException("Failed to get outbound token. Status: " + response.getCode() + ", Response: " + errorBody);
                    }
                });
            }
        } catch (Exception e) {
            log.error("Failed to get outbound token", e);
            throw new RuntimeException("Failed to get outbound token: " + e.getMessage(), e);
        }
    }

    /**
     * Make a request to Google Calendar API using the outbound token
     */
    public String makeGoogleCalendarRequest(String outboundToken, String method, String endpoint, String requestBody) throws IOException {
        String url = GOOGLE_CALENDAR_BASE_URL + endpoint;
        
        try (CloseableHttpClient client = HttpClients.createDefault()) {
            if ("GET".equalsIgnoreCase(method)) {
                HttpGet request = new HttpGet(url);
                request.setHeader("Authorization", "Bearer " + outboundToken);
                request.setHeader("Content-Type", "application/json");

                return client.execute(request, response -> {
                    if (response.getCode() == 200) {
                        JsonNode responseBody = MAPPER.readTree(response.getEntity().getContent());
                        return MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(responseBody);
                    } else {
                        throw new RuntimeException("Google Calendar API error. Status: " + response.getCode());
                    }
                });
            } else if ("POST".equalsIgnoreCase(method)) {
                HttpPost request = new HttpPost(url);
                request.setHeader("Authorization", "Bearer " + outboundToken);
                request.setHeader("Content-Type", "application/json");
                if (requestBody != null) {
                    request.setEntity(new StringEntity(requestBody, ContentType.APPLICATION_JSON));
                }

                return client.execute(request, response -> {
                    if (response.getCode() == 200 || response.getCode() == 201) {
                        JsonNode responseBody = MAPPER.readTree(response.getEntity().getContent());
                        return MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(responseBody);
                    } else {
                        throw new RuntimeException("Google Calendar API error. Status: " + response.getCode());
                    }
                });
            } else {
                throw new RuntimeException("Unsupported HTTP method: " + method);
            }
        }
    }

    /**
     * Get upcoming events from Google Calendar using outbound app token
     */
    public String getUpcomingEvents(String inboundToken, String userId, int maxResults) {
        try {
            String outboundToken = getOutboundAppToken(inboundToken, userId);
            String endpoint = String.format("/calendars/primary/events?maxResults=%d&timeMin=%s&orderBy=startTime&singleEvents=true", 
                maxResults, java.time.Instant.now().toString());
            
            return makeGoogleCalendarRequest(outboundToken, "GET", endpoint, null);
        } catch (Exception e) {
            log.error("Error fetching upcoming events", e);
            return "Error fetching upcoming events: " + e.getMessage();
        }
    }

    /**
     * Get events for a specific date range using outbound app token
     */
    public String getEventsForDateRange(String inboundToken, String userId, String startDate, String endDate) {
        try {
            String outboundToken = getOutboundAppToken(inboundToken, userId);
            String endpoint = String.format("/calendars/primary/events?timeMin=%sT00:00:00Z&timeMax=%sT23:59:59Z&orderBy=startTime&singleEvents=true", 
                startDate, endDate);
            
            return makeGoogleCalendarRequest(outboundToken, "GET", endpoint, null);
        } catch (Exception e) {
            log.error("Error fetching events for date range", e);
            return "Error fetching events for date range: " + e.getMessage();
        }
    }

    /**
     * Search events using outbound app token
     */
    public String searchEvents(String inboundToken, String userId, String query) {
        try {
            String outboundToken = getOutboundAppToken(inboundToken, userId);
            String endpoint = String.format("/calendars/primary/events?q=%s&orderBy=startTime&singleEvents=true", 
                java.net.URLEncoder.encode(query, "UTF-8"));
            
            return makeGoogleCalendarRequest(outboundToken, "GET", endpoint, null);
        } catch (Exception e) {
            log.error("Error searching events", e);
            return "Error searching events: " + e.getMessage();
        }
    }

    /**
     * Create a new calendar event using outbound app token
     */
    public String createEvent(String inboundToken, String userId, String eventData) {
        try {
            String outboundToken = getOutboundAppToken(inboundToken, userId);
            String endpoint = "/calendars/primary/events";
            
            return makeGoogleCalendarRequest(outboundToken, "POST", endpoint, eventData);
        } catch (Exception e) {
            log.error("Error creating event", e);
            return "Error creating event: " + e.getMessage();
        }
    }
}
