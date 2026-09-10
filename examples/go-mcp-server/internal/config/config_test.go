package config

import "testing"

func TestLoad_SucceedsWithProjectID(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("ADDR", "")
	t.Setenv("SERVER_URL", "")
	t.Setenv("DESCOPE_ISSUER_URL", "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned unexpected error: %v", err)
	}
	if cfg.DescopeProjectID != "Ptest0000000000000000000000000000" {
		t.Errorf("cfg.DescopeProjectID = %q, want %q", cfg.DescopeProjectID, "Ptest0000000000000000000000000000")
	}
}

func TestLoad_MissingProjectID(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "")
	t.Setenv("DESCOPE_ISSUER_URL", "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000")

	cfg, err := Load()
	if err == nil {
		t.Fatal("Load() returned nil error, want an error when DESCOPE_PROJECT_ID is unset")
	}
	if cfg != nil {
		t.Errorf("Load() returned a non-nil config alongside an error: %+v", cfg)
	}
}

func TestLoad_MissingIssuerURL(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("DESCOPE_ISSUER_URL", "")

	cfg, err := Load()
	if err == nil {
		t.Fatal("Load() returned nil error, want an error when DESCOPE_ISSUER_URL is unset")
	}
	if cfg != nil {
		t.Errorf("Load() returned a non-nil config alongside an error: %+v", cfg)
	}
}

func TestLoad_DefaultAddr(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("DESCOPE_ISSUER_URL", "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000")
	t.Setenv("ADDR", "")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned unexpected error: %v", err)
	}
	if cfg.Addr != ":8080" {
		t.Errorf("cfg.Addr = %q, want default %q", cfg.Addr, ":8080")
	}
}

func TestLoad_CustomAddr(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("DESCOPE_ISSUER_URL", "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000")
	t.Setenv("ADDR", ":9999")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned unexpected error: %v", err)
	}
	if cfg.Addr != ":9999" {
		t.Errorf("cfg.Addr = %q, want %q", cfg.Addr, ":9999")
	}
}

func TestLoad_ResourceURLDefaultUsesLocalhostRegardlessOfBindHost(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("DESCOPE_ISSUER_URL", "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000")
	t.Setenv("ADDR", "0.0.0.0:9090")
	t.Setenv("SERVER_URL", "")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned unexpected error: %v", err)
	}
	if want := "http://localhost:9090"; cfg.ResourceURL != want {
		t.Errorf("cfg.ResourceURL = %q, want %q (must not naively concatenate ADDR's host onto localhost)", cfg.ResourceURL, want)
	}
}

func TestLoad_ResourceURLTrimsTrailingSlash(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("DESCOPE_ISSUER_URL", "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000")
	t.Setenv("SERVER_URL", "https://example.com/")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned unexpected error: %v", err)
	}
	if want := "https://example.com"; cfg.ResourceURL != want {
		t.Errorf("cfg.ResourceURL = %q, want %q (trailing slash should be trimmed)", cfg.ResourceURL, want)
	}

	discoveryURL := cfg.ResourceURL + "/.well-known/oauth-protected-resource"
	if want := "https://example.com/.well-known/oauth-protected-resource"; discoveryURL != want {
		t.Errorf("joined discovery URL = %q, want %q (no double slash)", discoveryURL, want)
	}
}

func TestDescopeAPIBaseURL_ParsesStandardIssuer(t *testing.T) {
	cfg := &Config{
		DescopeProjectID: "Ptest0000000000000000000000000000",
		IssuerURL:        "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000",
	}

	base, err := cfg.DescopeAPIBaseURL()
	if err != nil {
		t.Fatalf("DescopeAPIBaseURL() returned unexpected error: %v", err)
	}
	if want := "https://api.descope.com"; base != want {
		t.Errorf("DescopeAPIBaseURL() = %q, want %q", base, want)
	}
}

func TestDescopeAPIBaseURL_ParsesCustomDomainIssuer(t *testing.T) {
	cfg := &Config{
		DescopeProjectID: "Ptest0000000000000000000000000000",
		IssuerURL:        "https://auth.example.com/v1/apps/Ptest0000000000000000000000000000",
	}

	base, err := cfg.DescopeAPIBaseURL()
	if err != nil {
		t.Fatalf("DescopeAPIBaseURL() returned unexpected error: %v", err)
	}
	if want := "https://auth.example.com"; base != want {
		t.Errorf("DescopeAPIBaseURL() = %q, want %q", base, want)
	}
}

func TestDescopeAPIBaseURL_ParsesAgenticIssuer(t *testing.T) {
	cfg := &Config{
		DescopeProjectID: "P3HsUC9rnbRt99JH05L97vu2ZIfP",
		IssuerURL:        "https://api.descope.com/v1/apps/agentic/P3HsUC9rnbRt99JH05L97vu2ZIfP/RS3J6Zgr7IKDImr5Hw7UUCymJNdOg",
	}

	base, err := cfg.DescopeAPIBaseURL()
	if err != nil {
		t.Fatalf("DescopeAPIBaseURL() returned unexpected error: %v", err)
	}
	if want := "https://api.descope.com"; base != want {
		t.Errorf("DescopeAPIBaseURL() = %q, want %q", base, want)
	}
}

func TestDescopeAPIBaseURL_AgenticShapeErrorsOnMismatchedProjectID(t *testing.T) {
	cfg := &Config{
		DescopeProjectID: "Ptest0000000000000000000000000000",
		IssuerURL:        "https://api.descope.com/v1/apps/agentic/SomeOtherProject/RS3J6Zgr7IKDImr5Hw7UUCymJNdOg",
	}

	base, err := cfg.DescopeAPIBaseURL()
	if err == nil {
		t.Fatalf("DescopeAPIBaseURL() = %q, nil error; want an error when the agentic issuer's project ID doesn't match cfg.DescopeProjectID", base)
	}
	if base != "" {
		t.Errorf("DescopeAPIBaseURL() returned a non-empty value (%q) alongside an error", base)
	}
}

func TestDescopeAPIBaseURL_ErrorsOnUnexpectedShape(t *testing.T) {
	cases := []struct {
		name      string
		issuerURL string
	}{
		{"wrong project ID suffix", "https://api.descope.com/v1/apps/SomeOtherProject"},
		{"missing /v1/apps/ segment entirely", "https://api.descope.com/Ptest0000000000000000000000000000"},
		{"not an absolute URL", "/v1/apps/Ptest0000000000000000000000000000"},
		{"not a URL at all", "://not a url"},
		{"agentic shape missing appID segment", "https://api.descope.com/v1/apps/agentic/Ptest0000000000000000000000000000"},
		{"agentic shape with extra trailing segment", "https://api.descope.com/v1/apps/agentic/Ptest0000000000000000000000000000/appid/extra"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			cfg := &Config{
				DescopeProjectID: "Ptest0000000000000000000000000000",
				IssuerURL:        tc.issuerURL,
			}

			base, err := cfg.DescopeAPIBaseURL()
			if err == nil {
				t.Fatalf("DescopeAPIBaseURL() = %q, nil error; want a clear error instead of a silently derived value", base)
			}
			if base != "" {
				t.Errorf("DescopeAPIBaseURL() returned a non-empty value (%q) alongside an error", base)
			}
		})
	}
}
