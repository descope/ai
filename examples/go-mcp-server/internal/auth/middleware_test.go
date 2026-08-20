package auth

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/descope/go-sdk/descope"
	sdkauth "github.com/modelcontextprotocol/go-sdk/auth"
)

// --- tokenInfoFromValidationResult: pure translation logic, no network needed ---

func TestTokenInfoFromValidationResult_Success(t *testing.T) {
	sessionToken := &descope.Token{ID: "user-123", Expiration: 1893456000} // 2030-01-01T00:00:00Z

	info, err := tokenInfoFromValidationResult(true, sessionToken, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if info == nil {
		t.Fatal("info is nil, want a populated TokenInfo")
	}
	if info.UserID != "user-123" {
		t.Errorf("info.UserID = %q, want %q", info.UserID, "user-123")
	}
	wantExpiration := time.Unix(1893456000, 0)
	if !info.Expiration.Equal(wantExpiration) {
		t.Errorf("info.Expiration = %v, want %v", info.Expiration, wantExpiration)
	}
}

func TestTokenInfoFromValidationResult_SDKError(t *testing.T) {
	info, err := tokenInfoFromValidationResult(false, nil, errors.New("[G030001] Missing or invalid public key"))
	if info != nil {
		t.Errorf("info = %+v, want nil on error", info)
	}
	if err == nil {
		t.Fatal("err is nil, want a generic invalid-token error")
	}
	if !errors.Is(err, sdkauth.ErrInvalidToken) {
		t.Errorf("err = %v, want it to wrap sdkauth.ErrInvalidToken", err)
	}
	if got := err.Error(); got != "invalid or expired session token: invalid token" {
		t.Errorf("err.Error() = %q, must not leak raw SDK error text", got)
	}
}

func TestTokenInfoFromValidationResult_NotAuthorized(t *testing.T) {
	info, err := tokenInfoFromValidationResult(false, nil, nil)
	if info != nil {
		t.Errorf("info = %+v, want nil when not authorized", info)
	}
	if !errors.Is(err, sdkauth.ErrInvalidToken) {
		t.Errorf("err = %v, want it to wrap sdkauth.ErrInvalidToken", err)
	}
}

// --- sdkauth.RequireBearerToken wrapping a fake verifier ---

func TestRequireBearerToken_ValidToken(t *testing.T) {
	ok := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	verifier := func(ctx context.Context, token string, req *http.Request) (*sdkauth.TokenInfo, error) {
		if token != "good-token" {
			t.Fatalf("verifier received token %q, want %q", token, "good-token")
		}
		return &sdkauth.TokenInfo{UserID: "user-123", Expiration: time.Now().Add(time.Hour)}, nil
	}

	srv := httptest.NewServer(sdkauth.RequireBearerToken(verifier, nil)(ok))
	defer srv.Close()

	req, _ := http.NewRequest(http.MethodGet, srv.URL, nil)
	req.Header.Set("Authorization", "Bearer good-token")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("status = %d, want %d", resp.StatusCode, http.StatusOK)
	}
}

func TestRequireBearerToken_InvalidToken(t *testing.T) {
	ok := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("handler should not be reached when the verifier rejects the token")
	})
	verifier := func(ctx context.Context, token string, req *http.Request) (*sdkauth.TokenInfo, error) {
		return nil, sdkauth.ErrInvalidToken
	}

	metadataURL := "https://example.com/.well-known/oauth-protected-resource"
	srv := httptest.NewServer(sdkauth.RequireBearerToken(verifier, &sdkauth.RequireBearerTokenOptions{
		ResourceMetadataURL: metadataURL,
	})(ok))
	defer srv.Close()

	req, _ := http.NewRequest(http.MethodGet, srv.URL, nil)
	req.Header.Set("Authorization", "Bearer bad-token")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusUnauthorized {
		t.Errorf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
	challenge := resp.Header.Get("WWW-Authenticate")
	if challenge == "" {
		t.Fatal("WWW-Authenticate header is empty, want it to be set")
	}
	if !strings.Contains(challenge, "Bearer") || !strings.Contains(challenge, metadataURL) {
		t.Errorf("WWW-Authenticate = %q, want it to reference %q", challenge, metadataURL)
	}
}

func TestRequireBearerToken_MissingToken(t *testing.T) {
	ok := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("handler should not be reached when no bearer token is present")
	})
	verifier := func(ctx context.Context, token string, req *http.Request) (*sdkauth.TokenInfo, error) {
		t.Fatal("verifier should not be called when no Authorization header is present")
		return nil, nil
	}

	srv := httptest.NewServer(sdkauth.RequireBearerToken(verifier, nil)(ok))
	defer srv.Close()

	resp, err := http.Get(srv.URL)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusUnauthorized {
		t.Errorf("status = %d, want %d", resp.StatusCode, http.StatusUnauthorized)
	}
}
