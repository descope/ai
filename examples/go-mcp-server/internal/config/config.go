package config

import (
	"fmt"
	"net"
	"os"
	"strings"
)

const (
	defaultAddr           = ":8080"
	defaultResourcePort   = "8080"
	defaultDescopeBaseURL = "https://api.descope.com"
)

type Config struct {
	DescopeProjectID string
	Addr             string
	// ResourceURL is this server's own externally-reachable base URL. It is
	// used as the OAuth 2.0 Protected Resource identifier (RFC 9728) that
	// unauthenticated clients are pointed at via the WWW-Authenticate header
	// and the /.well-known/oauth-protected-resource discovery document.
	ResourceURL string
	// DescopeBaseURL is advertised to clients as the authorization server in
	// the protected resource metadata document. It does not change how this
	// server talks to Descope's API.
	DescopeBaseURL string
}

func Load() (*Config, error) {
	addr := getEnvOrDefault("ADDR", defaultAddr)
	resourceURL := strings.TrimRight(getEnvOrDefault("SERVER_URL", defaultResourceURL(addr)), "/")

	cfg := &Config{
		DescopeProjectID: os.Getenv("DESCOPE_PROJECT_ID"),
		Addr:             addr,
		ResourceURL:      resourceURL,
		DescopeBaseURL:   getEnvOrDefault("DESCOPE_BASE_URL", defaultDescopeBaseURL),
	}

	if cfg.DescopeProjectID == "" {
		return nil, fmt.Errorf("DESCOPE_PROJECT_ID is required")
	}

	return cfg, nil
}

// defaultResourceURL builds the local discovery URL used when SERVER_URL is
// not set. It always yields "http://localhost:<port>", regardless of what
// host part ADDR binds to — e.g. ADDR="0.0.0.0:8080" still yields
// "http://localhost:8080" instead of the malformed "http://localhost0.0.0.0:8080"
// that a naive "http://localhost"+addr concatenation would produce.
func defaultResourceURL(addr string) string {
	_, port, err := net.SplitHostPort(addr)
	if err != nil || port == "" {
		port = defaultResourcePort
	}
	return "http://localhost:" + port
}

func getEnvOrDefault(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

