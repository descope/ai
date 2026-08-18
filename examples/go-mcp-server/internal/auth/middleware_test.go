package auth

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
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

// TestWriteUnauthorized_GenericMessageOnly confirms the HTTP 401 body built
// from genericSessionError never resembles raw Descope SDK error wording
// (e.g. "[G030001] Missing or invalid public key", observed in manual
// testing) — i.e. the message call sites are expected to pass is itself safe
// to expose to an unauthenticated caller.
func TestWriteUnauthorized_GenericMessageOnly(t *testing.T) {
	w := httptest.NewRecorder()
	challenge := `Bearer resource_metadata="https://example.com/.well-known/oauth-protected-resource"`

	writeUnauthorized(w, challenge, genericSessionError)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want %d", w.Code, http.StatusUnauthorized)
	}
	if got := w.Header().Get("WWW-Authenticate"); got != challenge {
		t.Errorf("WWW-Authenticate = %q, want %q", got, challenge)
	}

	body := w.Body.String()
	if !strings.Contains(body, genericSessionError) {
		t.Errorf("body = %q, want it to contain the generic message %q", body, genericSessionError)
	}
	for _, leaky := range []string{"G030001", "public key", "jwx", "malformed", "revoked"} {
		if strings.Contains(strings.ToLower(body), strings.ToLower(leaky)) {
			t.Errorf("body = %q, appears to leak SDK-specific wording (%q)", body, leaky)
		}
	}
}

// TestNoRawDescopeErrorLeakedToCaller is a regression guard for the security
// finding that RequireBearerToken and NewAuthMiddleware used to embed the
// raw error from ValidateSessionWithToken directly into the response sent to
// an unauthenticated caller (e.g. `fmt.Sprintf("unauthorized: %v", err)`).
//
// Because both functions depend on the concrete *descopeclient.DescopeClient
// rather than an interface (see the NOTE on TestNewAuthMiddleware_NoToken
// above), the err-returned-by-Descope branch can't be exercised end-to-end
// without a real API call or an interface refactor — that refactor is
// tracked as a separate follow-up, not done here. Until then, this test
// guards against the specific leaking pattern creeping back into the source.
func TestNoRawDescopeErrorLeakedToCaller(t *testing.T) {
	src, err := os.ReadFile("middleware.go")
	if err != nil {
		t.Fatalf("failed to read middleware.go: %v", err)
	}

	for _, pattern := range []string{
		`"invalid session token: %v"`,
		`"unauthorized: %v"`,
	} {
		if strings.Contains(string(src), pattern) {
			t.Errorf("middleware.go contains %s — a raw Descope error must not be formatted directly into a caller-facing message", pattern)
		}
	}
}
