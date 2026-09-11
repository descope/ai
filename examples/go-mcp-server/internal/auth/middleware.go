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

// NewDescopeTokenVerifier returns a TokenVerifier that validates a bearer
// token against Descope and checks it was issued for resourceURL.
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
