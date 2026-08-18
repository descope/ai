package auth

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	descopeclient "github.com/descope/go-sdk/descope/client"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

// TestNewAuthMiddleware_NoToken exercises the "missing bearer token" branch
// of NewAuthMiddleware. It intentionally passes a nil *descopeclient.DescopeClient:
// the missing-token check short-circuits before the client is ever dereferenced,
// so this path can be tested without a real (or mocked) Descope client.
//
// NOTE: this is a real design limitation, not just a test-writing convenience.
// NewAuthMiddleware takes a concrete *descopeclient.DescopeClient rather than an
// interface, so the "valid token" / "invalid token" / "Descope API error" branches
// of this middleware (the ones that actually call ValidateSessionWithToken) cannot
// be unit tested without either hitting the real Descope API or refactoring
// internal/auth to accept a small interface (e.g. an Authenticator with just
// ValidateSessionWithToken) that a test double can implement. See the test report
// for a suggested follow-up.
func TestNewAuthMiddleware_NoToken(t *testing.T) {
	var nilClient *descopeclient.DescopeClient

	nextCalled := false
	next := server.ToolHandlerFunc(func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		nextCalled = true
		return mcp.NewToolResultText("should not get here"), nil
	})

	middleware := NewAuthMiddleware(nilClient)
	wrapped := middleware(next)

	result, err := wrapped(context.Background(), mcp.CallToolRequest{})
	if err != nil {
		t.Fatalf("wrapped handler returned a Go error (%v); want a tool-level unauthorized result", err)
	}
	if result == nil || !result.IsError {
		t.Fatalf("result.IsError = false, want true (no bearer token in context); result: %+v", result)
	}
	if nextCalled {
		t.Error("next handler was called despite the missing bearer token; auth should have short-circuited")
	}
}

func TestHTTPContextFunc_ExtractsToken(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/mcp", nil)
	req.Header.Set("Authorization", "Bearer abc123")

	ctx := HTTPContextFunc(context.Background(), req)

	token, ok := ctx.Value(tokenContextKey).(string)
	if !ok {
		t.Fatal("expected tokenContextKey to be set in the returned context")
	}
	if token != "abc123" {
		t.Errorf("extracted token = %q, want %q", token, "abc123")
	}
}

func TestHTTPContextFunc_NoAuthorizationHeader(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/mcp", nil)

	ctx := HTTPContextFunc(context.Background(), req)

	if v := ctx.Value(tokenContextKey); v != nil {
		t.Errorf("ctx.Value(tokenContextKey) = %v, want nil when no Authorization header is present", v)
	}
}

func TestHTTPContextFunc_NonBearerAuthorizationHeader(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/mcp", nil)
	req.Header.Set("Authorization", "Basic dXNlcjpwYXNz")

	ctx := HTTPContextFunc(context.Background(), req)

	if v := ctx.Value(tokenContextKey); v != nil {
		t.Errorf("ctx.Value(tokenContextKey) = %v, want nil when Authorization header is not a Bearer token", v)
	}
}
