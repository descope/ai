package com.github.stantonk;

import com.descope.client.DescopeClient;
import com.descope.exception.DescopeException;
import com.descope.model.jwt.Token;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Arrays;

/**
 * Service for handling authentication and token validation using Descope.
 */
public class AuthenticationService {
    private static final Logger log = LoggerFactory.getLogger(AuthenticationService.class);
    
    private final DescopeClient descopeClient;
    private final com.descope.sdk.auth.AuthenticationService authService;

    public AuthenticationService() {
        this.descopeClient = new DescopeClient();
        this.authService = descopeClient.getAuthenticationServices().getAuthService();
    }

    /**
     * Validates an inbound token and extracts user information
     * 
     * @param inboundToken The inbound token to validate
     * @return User ID from the validated token
     * @throws DescopeException if token validation fails
     */
    public String validateInboundToken(String inboundToken) throws DescopeException {
        if (inboundToken == null || inboundToken.trim().isEmpty()) {
            throw new RuntimeException("Inbound token is required");
        }

        // Remove "Bearer " prefix if present
        String cleanToken = inboundToken.startsWith("Bearer ") ? 
            inboundToken.substring(7) : inboundToken;

        log.debug("Validating inbound token");
        
        try {
            // Use Descope SDK to validate the session token
            Token token = authService.validateSessionWithToken(cleanToken);
            
            // Extract user ID from the token - try different possible method names
            String userId = extractUserIdFromToken(token);
            
            log.debug("Token validation successful for user: {}", userId);
            return userId;
            
        } catch (DescopeException e) {
            log.error("Token validation failed", e);
            throw e;
        }
    }

    /**
     * Extracts user ID from an inbound token (simplified implementation)
     * 
     * @param inboundToken The inbound token to validate
     * @return The user ID from the validated token
     * @throws DescopeException if token validation fails
     */
    public String getUserIdFromToken(String inboundToken) throws DescopeException {
        return validateInboundToken(inboundToken);
    }

    /**
     * Validates an inbound token and checks if the user has required scopes
     * 
     * @param inboundToken The inbound token to validate
     * @param requiredScopes The scopes required for the operation
     * @return User ID from the validated token
     * @throws DescopeException if token validation fails or user lacks required scopes
     */
    public String validateTokenWithScopes(String inboundToken, String[] requiredScopes) throws DescopeException {
        // Validate the token and get user info with scopes
        TokenValidationResult result = validateInboundTokenWithScopes(inboundToken);
        
        if (requiredScopes != null && requiredScopes.length > 0) {
            // Check if user has required scopes
            log.debug("Checking scopes for user: {} - required: {}, available: {}", 
                     result.getUserId(), requiredScopes, result.getScopes());
            
            for (String requiredScope : requiredScopes) {
                if (!result.getScopes().contains(requiredScope)) {
                    throw new RuntimeException("User lacks required scope: " + requiredScope);
                }
            }
            log.debug("All required scopes validated successfully for user: {}", result.getUserId());
        }
        
        return result.getUserId();
    }

    /**
     * Validates an inbound token and returns user info with scopes
     * 
     * @param inboundToken The inbound token to validate
     * @return TokenValidationResult containing user ID and scopes
     * @throws DescopeException if token validation fails
     */
    public TokenValidationResult validateInboundTokenWithScopes(String inboundToken) throws DescopeException {
        if (inboundToken == null || inboundToken.trim().isEmpty()) {
            throw new RuntimeException("Inbound token is required");
        }

        // Remove "Bearer " prefix if present
        String cleanToken = inboundToken.startsWith("Bearer ") ? 
            inboundToken.substring(7) : inboundToken;

        log.debug("Validating inbound token with scopes");
        log.debug("Clean token: {}", cleanToken);
        
        try {
            // Use Descope SDK to validate the session token
            Token token = authService.validateSessionWithToken(cleanToken);
            
            // Extract user ID from the token
            String userId = extractUserIdFromToken(token);
            
            // Extract scopes from the token
            List<String> scopes = extractScopesFromToken(token);
            
            log.debug("Token validation successful for user: {} with scopes: {}", userId, scopes);
            return new TokenValidationResult(userId, scopes);
            
        } catch (DescopeException e) {
            log.error("Token validation failed", e);
            throw e;
        }
    }

    /**
     * Extracts user ID from a Descope token
     * 
     * @param token The Descope token
     * @return User ID
     */
    private String extractUserIdFromToken(Token token) {
        try {
            return token.getId();
        } catch (Exception e) {
            log.warn("Failed to extract user ID from token", e);
            return "unknown_user";
        }
    }

    /**
     * Extracts scopes from a Descope token
     * 
     * @param token The Descope token
     * @return List of scopes
     */
    private List<String> extractScopesFromToken(Token token) {
        try {
            // Try different possible method names for getting scope
            String scope = null;
            
            try {
                Object scopeObj = token.getClaims().get("scope");
                scope = scopeObj != null ? scopeObj.toString() : null;
            } catch (Exception e1) {
                log.warn("Could not extract scope from token using standard methods", e1);
            }
            
            if (scope != null && !scope.trim().isEmpty()) {
                // Split the scope string by spaces and filter out empty strings
                return Arrays.asList(scope.split("\\s+"));
            }
        } catch (Exception e) {
            log.warn("Failed to extract scopes from token", e);
        }
        
        // Return empty list if no scopes found
        return List.of();
    }

    /**
     * Result class containing user ID and scopes from token validation
     */
    public static class TokenValidationResult {
        private final String userId;
        private final List<String> scopes;

        public TokenValidationResult(String userId, List<String> scopes) {
            this.userId = userId;
            this.scopes = scopes;
        }

        public String getUserId() {
            return userId;
        }

        public List<String> getScopes() {
            return scopes;
        }
    }
}
