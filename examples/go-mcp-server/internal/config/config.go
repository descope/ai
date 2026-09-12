package config

import (
	"fmt"
	"net"
	"net/url"
	"os"
	"strings"
)

const (
	defaultAddr         = ":8080"
	defaultResourcePort = "8080"
)

type Config struct {
	DescopeProjectID string
	Addr             string
	// ResourceURL is this server's own externally-reachable base URL. It is
	// used as the OAuth 2.0 Protected Resource identifier (RFC 9728) that
	// unauthenticated clients are pointed at via the WWW-Authenticate header
	// and the /.well-known/oauth-protected-resource discovery document.
	ResourceURL string
	// IssuerURL is this Descope project's OAuth 2.0 authorization server
	// issuer identifier (RFC 8414), advertised to clients in OAuth Protected
	// Resource Metadata (RFC 9728). Set it up in the Descope Console under
	// the project's MCP server configuration.
	IssuerURL string
}

func Load() (*Config, error) {
	addr := getEnvOrDefault("ADDR", defaultAddr)
	resourceURL := strings.TrimRight(getEnvOrDefault("SERVER_URL", defaultResourceURL(addr)), "/")

	cfg := &Config{
		DescopeProjectID: os.Getenv("DESCOPE_PROJECT_ID"),
		Addr:             addr,
		ResourceURL:      resourceURL,
		IssuerURL:        os.Getenv("DESCOPE_ISSUER_URL"),
	}

	if cfg.DescopeProjectID == "" {
		return nil, fmt.Errorf("DESCOPE_PROJECT_ID is required")
	}
	if cfg.IssuerURL == "" {
		return nil, fmt.Errorf("DESCOPE_ISSUER_URL is required")
	}

	return cfg, nil
}

// DescopeAPIBaseURL derives the base URL of the Descope API that issued
// IssuerURL, by stripping the expected Descope issuer-path suffix from it —
// e.g. "https://api.descope.com/v1/apps/P123" becomes
// "https://api.descope.com". This is used to point the Descope SDK client
// at the right API host, including for custom domains or regions where
// IssuerURL doesn't point at the default "https://api.descope.com".
//
// Two issuer path shapes are recognized:
//   - flat: "/v1/apps/<DescopeProjectID>"
//   - agentic: "/v1/apps/agentic/<DescopeProjectID>/<appID>", used by
//     Descope's Agentic Identity Hub / MCP server resources. The appID
//     segment is parsed through but otherwise unvalidated.
//
// In both shapes, the project ID segment must match c.DescopeProjectID.
//
// It returns an error, rather than a silently wrong value, if IssuerURL
// isn't an absolute URL or doesn't match either expected shape.
func (c *Config) DescopeAPIBaseURL() (string, error) {
	u, err := url.Parse(c.IssuerURL)
	if err != nil {
		return "", fmt.Errorf("issuer URL %q is not a valid URL: %w", c.IssuerURL, err)
	}
	if u.Scheme == "" || u.Host == "" {
		return "", fmt.Errorf("issuer URL %q is not an absolute URL", c.IssuerURL)
	}

	const agenticMarker = "/v1/apps/agentic/"
	if i := strings.LastIndex(u.Path, agenticMarker); i != -1 {
		rest := strings.Split(u.Path[i+len(agenticMarker):], "/")
		if len(rest) == 2 && rest[0] != "" && rest[1] != "" {
			if rest[0] != c.DescopeProjectID {
				return "", fmt.Errorf("issuer URL %q has agentic project ID %q, want %q", c.IssuerURL, rest[0], c.DescopeProjectID)
			}
			base := &url.URL{Scheme: u.Scheme, Host: u.Host, Path: u.Path[:i]}
			return strings.TrimRight(base.String(), "/"), nil
		}
	}

	flatSuffix := "/v1/apps/" + c.DescopeProjectID
	if strings.HasSuffix(u.Path, flatSuffix) {
		base := &url.URL{Scheme: u.Scheme, Host: u.Host, Path: strings.TrimSuffix(u.Path, flatSuffix)}
		return strings.TrimRight(base.String(), "/"), nil
	}

	return "", fmt.Errorf("issuer URL %q does not match a known Descope issuer shape (flat %q or agentic %q); cannot derive the Descope API base URL from it",
		c.IssuerURL, flatSuffix, agenticMarker+c.DescopeProjectID+"/<appID>")
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
