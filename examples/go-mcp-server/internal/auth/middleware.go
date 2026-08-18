package auth

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	descopeclient "github.com/descope/go-sdk/descope/client"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

type contextKey string

const tokenContextKey contextKey = "bearer_token"

// bearerToken extracts the raw bearer token from an HTTP request's
// Authorization header, or "" if none is present.
func bearerToken(r *http.Request) string {
	header := r.Header.Get("Authorization")
	if !strings.HasPrefix(header, "Bearer ") {
		return ""
	}
	return strings.TrimPrefix(header, "Bearer ")
}

// HTTPContextFunc extracts the Authorization header on each HTTP request
// and stashes the raw bearer token into context, before tool middleware runs.
func HTTPContextFunc(ctx context.Context, r *http.Request) context.Context {
	token := bearerToken(r)
	if token == "" {
		return ctx
	}
	return context.WithValue(ctx, tokenContextKey, token)
}

// RequireBearerToken returns an HTTP middleware that validates the caller's
// Descope session token before the request ever reaches the MCP layer. On
// failure it responds with HTTP 401 and a WWW-Authenticate header pointing
// at the given OAuth 2.0 Protected Resource Metadata document (RFC 9728),
// per the MCP Authorization spec. This is the primary auth gate for the
// HTTP transport; the tool-call middleware in NewAuthMiddleware still runs
// afterwards as defense in depth.
func RequireBearerToken(descopeClient *descopeclient.DescopeClient, resourceMetadataURL string) func(http.Handler) http.Handler {
	challenge := fmt.Sprintf("Bearer resource_metadata=%q", resourceMetadataURL)

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			token := bearerToken(r)
			if token == "" {
				writeUnauthorized(w, challenge, "missing bearer token")
				return
			}

			authorized, _, err := descopeClient.Auth.ValidateSessionWithToken(r.Context(), token)
			if err != nil {
				writeUnauthorized(w, challenge, fmt.Sprintf("invalid session token: %v", err))
				return
			}
			if !authorized {
				writeUnauthorized(w, challenge, "invalid or expired session token")
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func writeUnauthorized(w http.ResponseWriter, challenge, reason string) {
	w.Header().Set("WWW-Authenticate", challenge)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusUnauthorized)
	fmt.Fprintf(w, `{"error":"unauthorized","error_description":%q}`, reason)
}

// NewAuthMiddleware returns tool-call middleware that verifies a Descope
// session token before allowing the tool handler to run. It is registered
// only for the HTTP transport (see cmd/main.go) as defense in depth behind
// RequireBearerToken.
func NewAuthMiddleware(descopeClient *descopeclient.DescopeClient) server.ToolHandlerMiddleware {
	return func(next server.ToolHandlerFunc) server.ToolHandlerFunc {
		return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
			token, ok := ctx.Value(tokenContextKey).(string)
			if !ok || token == "" {
				return mcp.NewToolResultError("unauthorized: missing bearer token"), nil
			}

			authorized, _, err := descopeClient.Auth.ValidateSessionWithToken(ctx, token)
			if err != nil {
				return mcp.NewToolResultError(fmt.Sprintf("unauthorized: %v", err)), nil
			}
			if !authorized {
				return mcp.NewToolResultError("unauthorized: invalid or expired session token"), nil
			}

			return next(ctx, req)
		}
	}
}
