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
    
    // Inheritable thread-local storage for current request's auth info
    // This allows child threads (like MCP tool execution threads) to inherit auth info
    private static final InheritableThreadLocal<String> currentAuthToken = new InheritableThreadLocal<>();
    private static final InheritableThreadLocal<String> currentUserId = new InheritableThreadLocal<>();

    /**
     * Set authentication info for current thread (called by servlet)
     */
    public static void setAuthInfo(String authToken, String userId) {
        currentAuthToken.set(authToken);
        currentUserId.set(userId);
        log.debug("Set auth info for user: {} on thread: {}", userId, Thread.currentThread().getName());
    }

    /**
     * Clear authentication info for current thread
     */
    public static void clearAuthInfo() {
        currentAuthToken.set(null);
        currentUserId.set(null);
        log.debug("Cleared auth info on thread: {}", Thread.currentThread().getName());
    }

    /**
     * Validate token and get user ID with required scopes
     * 
     * @param exchange The MCP exchange (not used, but kept for compatibility)
     * @param requiredScopes The scopes required for the operation
     * @return TokenValidationResult containing both the inbound token and user ID
     * @throws RuntimeException if token validation fails
     */
    public static TokenValidationResult validateTokenAndGetUser(Object exchange, String[] requiredScopes) {
        try {
            // Get auth info from thread-local storage
            String authToken = currentAuthToken.get();
            String userId = currentUserId.get();
            
            log.debug("Attempting to get auth info on thread: {} - Token: {}, UserId: {}", 
                     Thread.currentThread().getName(), 
                     authToken != null ? "present" : "null", 
                     userId != null ? userId : "null");
            
            if (authToken == null || userId == null) {
                throw new RuntimeException("No authentication info found. User must be authenticated first.");
            }

            // Validate scopes if required
            if (requiredScopes != null && requiredScopes.length > 0) {
                authService.validateTokenWithScopes(authToken, requiredScopes);
                log.debug("User {} has required scopes: {}", userId, requiredScopes);
            }
            
            log.debug("Token validated successfully for user: {} with scopes: {}", userId, requiredScopes);
            return new TokenValidationResult(authToken, userId);
            
        } catch (DescopeException e) {
            log.error("Token validation failed", e);
            throw new RuntimeException("Authentication failed: " + e.getMessage());
        } catch (Exception e) {
            log.error("Unexpected error during token validation", e);
            throw new RuntimeException("Authentication failed: " + e.getMessage());
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
