package auth

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"slices"
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
// resourceURL is this server's own resource identifier (cfg.ResourceURL) —
// the verifier rejects any token whose "aud" claim doesn't include it. The
// Descope Go SDK has no built-in audience-checking parameter on
// ValidateSessionWithToken (confirmed: its signature takes only a context
// and the token string), so this is enforced manually here; see
// audienceFromJWT.
//
// On success it returns a populated *auth.TokenInfo: UserID is taken from
// the Descope token's ID (subject) claim, Expiration from the token's
// expiration claim, and Scopes from the token's space-separated "scope"
// claim (standard OAuth 2.0 access token shape — RFC 6749 §5.1), if present.
//
// On any failure — a Descope SDK/network error, an explicitly unauthorized
// token, or an audience mismatch — the real reason is logged server-side and
// a generic error wrapping auth.ErrInvalidToken is returned to the caller,
// so a caller can't fingerprint which specific check failed.
// auth.RequireBearerToken turns that into the appropriate HTTP 401 +
// WWW-Authenticate response automatically; this package no longer
// hand-writes that response itself.
func NewDescopeTokenVerifier(descopeClient *descopeclient.DescopeClient, resourceURL string) auth.TokenVerifier {
	return func(ctx context.Context, token string, req *http.Request) (*auth.TokenInfo, error) {
		authorized, sessionToken, err := descopeClient.Auth.ValidateSessionWithToken(ctx, token)
		return tokenInfoFromValidationResult(authorized, sessionToken, err, resourceURL)
	}
}

// tokenInfoFromValidationResult translates the result of a
// ValidateSessionWithToken call into the *auth.TokenInfo/error shape
// auth.TokenVerifier expects. It's factored out from NewDescopeTokenVerifier
// so it can be unit tested directly, without a real Descope client or
// network access — see middleware_test.go.
func tokenInfoFromValidationResult(authorized bool, sessionToken *descope.Token, err error, resourceURL string) (*auth.TokenInfo, error) {
	if err != nil {
		log.Printf("auth: descope session validation error: %v", err)
		return nil, fmt.Errorf("invalid or expired session token: %w", auth.ErrInvalidToken)
	}
	if !authorized {
		log.Printf("auth: descope session token rejected (not authorized)")
		return nil, fmt.Errorf("invalid or expired session token: %w", auth.ErrInvalidToken)
	}

	aud, audErr := audienceFromJWT(sessionToken.JWT)
	if audErr != nil {
		log.Printf("auth: failed to parse audience from session token: %v", audErr)
		return nil, fmt.Errorf("invalid or expired session token: %w", auth.ErrInvalidToken)
	}
	if !slices.Contains(aud, resourceURL) {
		log.Printf("auth: session token audience %v does not include this resource (%s)", aud, resourceURL)
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

// audienceFromJWT extracts the "aud" claim from a JWT's payload segment,
// without re-verifying the signature (the caller has already done that via
// ValidateSessionWithToken). This manual decode is necessary because the
// Descope Go SDK doesn't expose "aud" anywhere on *descope.Token: it's a
// registered JWT claim (RFC 7519 §4.1.3), and descope.Token.Claims is
// populated from the underlying JWT library's PrivateClaims(), which
// excludes registered claims by definition — only non-standard claims like
// "scope" land there.
//
// Per RFC 7519, "aud" may be either a single string or a JSON array of
// strings; both shapes are normalized to a []string here.
func audienceFromJWT(rawJWT string) ([]string, error) {
	parts := strings.Split(rawJWT, ".")
	if len(parts) < 2 {
		return nil, fmt.Errorf("malformed JWT: expected at least 2 dot-separated segments, got %d", len(parts))
	}

	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, fmt.Errorf("decoding JWT payload: %w", err)
	}

	var claims struct {
		Audience json.RawMessage `json:"aud"`
	}
	if err := json.Unmarshal(payload, &claims); err != nil {
		return nil, fmt.Errorf("unmarshaling JWT payload: %w", err)
	}
	if len(claims.Audience) == 0 {
		return nil, nil
	}

	var multiple []string
	if err := json.Unmarshal(claims.Audience, &multiple); err == nil {
		return multiple, nil
	}
	var single string
	if err := json.Unmarshal(claims.Audience, &single); err == nil {
		return []string{single}, nil
	}
	return nil, fmt.Errorf("aud claim has unexpected shape: %s", claims.Audience)
}
