package auth

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/descope/go-sdk/descope"
	descopeclient "github.com/descope/go-sdk/descope/client"
	"github.com/modelcontextprotocol/go-sdk/auth"
)

// NewDescopeTokenVerifier returns an auth.TokenVerifier that validates a
// bearer token as a Descope session token via
// descopeClient.Auth.ValidateSessionWithToken. Pass the result to
// auth.RequireBearerToken to gate an HTTP handler.
//
// On success it returns a populated *auth.TokenInfo: UserID is taken from
// the Descope token's ID (subject) claim, Expiration from the token's
// expiration claim, and Scopes from the token's space-separated "scope"
// claim (standard OAuth 2.0 access token shape — RFC 6749 §5.1), if present.
//
// On any failure — a Descope SDK/network error, or an explicitly
// unauthorized token — the real error is logged server-side and a generic
// error wrapping auth.ErrInvalidToken is returned to the caller.
// auth.RequireBearerToken turns that into the appropriate HTTP 401 +
// WWW-Authenticate response automatically; this package no longer
// hand-writes that response itself.
func NewDescopeTokenVerifier(descopeClient *descopeclient.DescopeClient) auth.TokenVerifier {
	return func(ctx context.Context, token string, req *http.Request) (*auth.TokenInfo, error) {
		authorized, sessionToken, err := descopeClient.Auth.ValidateSessionWithToken(ctx, token)
		return tokenInfoFromValidationResult(authorized, sessionToken, err)
	}
}

// tokenInfoFromValidationResult translates the result of a
// ValidateSessionWithToken call into the *auth.TokenInfo/error shape
// auth.TokenVerifier expects. It's factored out from NewDescopeTokenVerifier
// so it can be unit tested directly, without a real Descope client or
// network access — see middleware_test.go.
func tokenInfoFromValidationResult(authorized bool, sessionToken *descope.Token, err error) (*auth.TokenInfo, error) {
	if err != nil {
		log.Printf("auth: descope session validation error: %v", err)
		return nil, fmt.Errorf("invalid or expired session token: %w", auth.ErrInvalidToken)
	}
	if !authorized {
		log.Printf("auth: descope session token rejected (not authorized)")
		return nil, fmt.Errorf("invalid or expired session token: %w", auth.ErrInvalidToken)
	}

	info := &auth.TokenInfo{
		UserID: sessionToken.ID,
	}
	if sessionToken.Expiration > 0 {
		info.Expiration = time.Unix(sessionToken.Expiration, 0)
	}
	if scope, ok := sessionToken.Claims["scope"].(string); ok && scope != "" {
		info.Scopes = strings.Fields(scope)
	}
	return info, nil
}
