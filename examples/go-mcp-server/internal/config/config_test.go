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
