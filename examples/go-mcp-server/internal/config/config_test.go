package config

import "testing"

func TestLoad_SucceedsWithProjectID(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("ADDR", "")
	t.Setenv("SERVER_URL", "")
	t.Setenv("DESCOPE_BASE_URL", "")

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

	cfg, err := Load()
	if err == nil {
		t.Fatal("Load() returned nil error, want an error when DESCOPE_PROJECT_ID is unset")
	}
	if cfg != nil {
		t.Errorf("Load() returned a non-nil config alongside an error: %+v", cfg)
	}
}

func TestLoad_DefaultAddr(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
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

func TestIssuer_DefaultDerivesFromProjectIDAndBaseURL(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("DESCOPE_BASE_URL", "https://api.descope.com")
	t.Setenv("DESCOPE_ISSUER_URL", "")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned unexpected error: %v", err)
	}
	if want := "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000"; cfg.Issuer() != want {
		t.Errorf("cfg.Issuer() = %q, want %q", cfg.Issuer(), want)
	}
}

func TestIssuer_RespectsExplicitOverride(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("DESCOPE_BASE_URL", "https://api.descope.com")
	t.Setenv("DESCOPE_ISSUER_URL", "https://custom.example.com/my-issuer")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned unexpected error: %v", err)
	}
	if want := "https://custom.example.com/my-issuer"; cfg.Issuer() != want {
		t.Errorf("cfg.Issuer() = %q, want the explicit override %q unchanged", cfg.Issuer(), want)
	}
}

func TestIssuer_NoDoubleSlashWithTrailingSlashBaseURL(t *testing.T) {
	t.Setenv("DESCOPE_PROJECT_ID", "Ptest0000000000000000000000000000")
	t.Setenv("DESCOPE_BASE_URL", "https://api.descope.com/")
	t.Setenv("DESCOPE_ISSUER_URL", "")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned unexpected error: %v", err)
	}
	if want := "https://api.descope.com/v1/apps/Ptest0000000000000000000000000000"; cfg.Issuer() != want {
		t.Errorf("cfg.Issuer() = %q, want %q (no double slash from a trailing-slash base URL)", cfg.Issuer(), want)
	}
}
