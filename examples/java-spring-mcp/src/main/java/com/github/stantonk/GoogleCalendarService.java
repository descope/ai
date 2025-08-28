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
    
    private final DescopeClient descopeClient;
    private final OutboundAppsByTokenService outboundAppsService;

    public GoogleCalendarService() {
        // Initialize Descope client using environment variables
        this.descopeClient = new DescopeClient();
        this.outboundAppsService = descopeClient.getManagementServices().getOutboundAppsByTokenService();
    }

    /**
     * Get an outbound app token from Descope using the inbound token and user ID
     * This method uses the Descope SDK pattern shown in the test examples
     */
    public String getOutboundAppToken(String inboundToken, String userId) throws IOException {
        try {
            FetchLatestOutboundAppUserTokenRequest request = new FetchLatestOutboundAppUserTokenRequest();
            request.setAppId(GOOGLE_OUTBOUND_APP_ID);
            request.setUserId(userId);
            
            FetchOutboundAppUserTokenResponse response = outboundAppsService.fetchLatestOutboundAppUserToken(inboundToken, request);
            return response.getToken().getAccessToken();
        } catch (DescopeException e) {
            log.error("Failed to get outbound token from Descope SDK", e);
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
