package config

import (
	"fmt"
	"os"
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
	addr := getEnvOrDefault("ADDR", ":8080")
	cfg := &Config{
		DescopeProjectID: os.Getenv("DESCOPE_PROJECT_ID"),
		Addr:             addr,
		ResourceURL:      getEnvOrDefault("SERVER_URL", "http://localhost"+addr),
		DescopeBaseURL:   getEnvOrDefault("DESCOPE_BASE_URL", "https://api.descope.com"),
	}

	if cfg.DescopeProjectID == "" {
		return nil, fmt.Errorf("DESCOPE_PROJECT_ID is required")
	}

	return cfg, nil
}

func getEnvOrDefault(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

