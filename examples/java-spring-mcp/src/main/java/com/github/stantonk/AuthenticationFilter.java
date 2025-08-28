package com.github.stantonk;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;

/**
 * Filter that validates bearer tokens for protected endpoints using Descope SDK.
 * This filter specifically protects the /sse endpoint and validates the Authorization header.
 */
public class AuthenticationFilter implements Filter {
    private static final Logger log = LoggerFactory.getLogger(AuthenticationFilter.class);
    private final AuthenticationService authService;

    public AuthenticationFilter() {
        this.authService = new AuthenticationService();
    }

    @Override
    public void init(FilterConfig filterConfig) throws ServletException {
        log.info("Authentication filter initialized");
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) 
            throws IOException, ServletException {
        
        HttpServletRequest httpRequest = (HttpServletRequest) request;
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        
        String requestId = java.util.UUID.randomUUID().toString().substring(0, 8);
        String method = httpRequest.getMethod();
        String uri = httpRequest.getRequestURI();
        String userAgent = httpRequest.getHeader("User-Agent");
        
        log.info("[{}] Authentication filter processing: {} {} | User-Agent: {}", 
                requestId, method, uri, userAgent);
        
        // Check if this is a request to the SSE endpoint
        if (uri.startsWith("/sse") || uri.startsWith("/mcp/message")) {
            log.info("[{}] SSE endpoint detected, checking authentication", requestId);
            
            // Extract the Authorization header
            String authHeader = httpRequest.getHeader("Authorization");
            
            // For SSE connections, allow requests without Authorization header for initial handshake
            // The MCP protocol may require an initial connection without authentication
            if (authHeader == null || authHeader.trim().isEmpty()) {
                log.info("[{}] No Authorization header - allowing SSE request to pass through for initial handshake", requestId);
                chain.doFilter(request, response);
                return;
            }
            
            // If Authorization header is present, validate it
            if (!authHeader.startsWith("Bearer ")) {
                log.warn("[{}] Authentication failed: Invalid Authorization header format", requestId);
                sendUnauthorizedResponse(httpResponse, "Invalid Authorization header format, expected 'Bearer TOKEN'");
                return;
            }
            
            String token = authHeader.substring(7); // Remove "Bearer " prefix
<<<<<<< HEAD
            System.out.println("Token: " + token);
            
            try {
                // Validate the token using the authentication service
                log.info("[{}] Validating token: {}", requestId, token);
=======
            
            try {
                // Validate the token using the authentication service
>>>>>>> c30ff510c86942f7ac81d024aa288c56c3b40d6a
                String userId = authService.validateInboundToken(authHeader);
                log.info("[{}] Authentication successful for user: {}", requestId, userId);
                
                // Add user ID to request attributes for downstream use
                httpRequest.setAttribute("userId", userId);
                httpRequest.setAttribute("authToken", token);
                
                // Continue with the request
                chain.doFilter(request, response);
                
            } catch (Exception e) {
                log.error("[{}] Authentication failed", requestId, e);
                sendUnauthorizedResponse(httpResponse, "Authentication failed: " + e.getMessage());
                return;
            }
        } else {
            // For non-SSE endpoints, allow the request to pass through
            log.debug("[{}] Non-SSE endpoint, allowing request to pass through", requestId);
            chain.doFilter(request, response);
        }
    }

    @Override
    public void destroy() {
        log.info("Authentication filter destroyed");
    }

    /**
     * Sends an unauthorized response with JSON error message
     */
    private void sendUnauthorizedResponse(HttpServletResponse response, String errorMessage) throws IOException {
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json");
        response.setCharacterEncoding("UTF-8");
        
        String jsonResponse = String.format(
            "{\"error\": \"Unauthorized\", \"message\": \"%s\", \"timestamp\": \"%s\"}",
            errorMessage,
            java.time.Instant.now()
        );
        
        response.getWriter().write(jsonResponse);
    }
}
