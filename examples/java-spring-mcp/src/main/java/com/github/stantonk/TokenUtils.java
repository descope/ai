package com.github.stantonk;

import com.descope.exception.DescopeException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Utility class for handling token extraction and validation.
 */
public class TokenUtils {
    private static final Logger log = LoggerFactory.getLogger(TokenUtils.class);
    private static final AuthenticationService authService = new AuthenticationService();

    /**
     * Generic function to validate token and extract user ID with required scopes
     * 
     * @param exchange The MCP exchange containing the request
     * @param requiredScopes The scopes required for the operation
     * @return TokenValidationResult containing both the inbound token and user ID
     * @throws RuntimeException if token validation fails
     */
    public static TokenValidationResult validateTokenAndGetUser(Object exchange, String[] requiredScopes) {
        try {
            // Extract token from authorization header
            String authHeader = extractAuthorizationHeader(exchange);
            if (authHeader == null || authHeader.trim().isEmpty()) {
                throw new RuntimeException("Authorization header is required");
            }

            // Validate token and get user ID
            String userId = authService.validateTokenWithScopes(authHeader, requiredScopes);
            log.debug("Token validated successfully for user: {} with scopes: {}", userId, requiredScopes);
            
            return new TokenValidationResult(authHeader, userId);
        } catch (DescopeException e) {
            log.error("Token validation failed", e);
            throw new RuntimeException("Authentication failed: " + e.getMessage());
        } catch (Exception e) {
            log.error("Unexpected error during token validation", e);
            throw new RuntimeException("Authentication failed: " + e.getMessage());
        }
    }

    /**
     * Extracts the authorization header from the MCP exchange
     * 
     * @param exchange The MCP exchange
     * @return The authorization header value or null if not found
     */
    public static String extractAuthorizationHeader(Object exchange) {
        try {
            // This is a placeholder implementation
            // Replace with actual header extraction logic based on your MCP server implementation
            // The exact method depends on how the MCP server exposes HTTP headers
            
            // For now, we'll use a demo token for testing
            // In a real implementation, you would extract the Authorization header from the exchange
            // TODO: Implement actual header extraction from the MCP exchange object
            return "Bearer demo_token";
        } catch (Exception e) {
            log.warn("Could not extract authorization header", e);
            return null;
        }
    }

    /**
     * Result class containing both the inbound token and user ID
     */
    public static class TokenValidationResult {
        private final String inboundToken;
        private final String userId;

        public TokenValidationResult(String inboundToken, String userId) {
            this.inboundToken = inboundToken;
            this.userId = userId;
        }

        public String getInboundToken() {
            return inboundToken;
        }

        public String getUserId() {
            return userId;
        }
    }
}
