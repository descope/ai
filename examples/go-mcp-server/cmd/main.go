package main

import (
	"log"
	"net/http"

	descopeclient "github.com/descope/go-sdk/descope/client"
	sdkauth "github.com/modelcontextprotocol/go-sdk/auth"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/modelcontextprotocol/go-sdk/oauthex"

	"github.com/descope/ai/examples/go-mcp-server/internal/auth"
	"github.com/descope/ai/examples/go-mcp-server/internal/config"
	"github.com/descope/ai/examples/go-mcp-server/internal/tools"
)

// mcpEndpointPath is the path the streamable-HTTP transport serves the MCP
// endpoint on.
const mcpEndpointPath = "/mcp"

// protectedResourceMetadataPath is the RFC 9728 well-known discovery path,
// which must stay reachable without auth so clients can find out how to
// authenticate in the first place.
const protectedResourceMetadataPath = "/.well-known/oauth-protected-resource"

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config error: %v", err)
	}

	descopeClient, err := descopeclient.NewWithConfig(&descopeclient.Config{ProjectID: cfg.DescopeProjectID})
	if err != nil {
		log.Fatalf("failed to init descope client: %v", err)
	}

	s := mcp.NewServer(&mcp.Implementation{
		Name:    "descope-go-mcp-server",
		Version: "0.1.0",
	}, nil)

	mcp.AddTool(s, tools.NewEchoTool(), tools.EchoHandler)

	handler := mcp.NewStreamableHTTPHandler(func(r *http.Request) *mcp.Server {
		return s
	}, &mcp.StreamableHTTPOptions{
		Stateless: true,
	})

	metadataURL := cfg.ResourceURL + protectedResourceMetadataPath
	authenticatedHandler := sdkauth.RequireBearerToken(
		auth.NewDescopeTokenVerifier(descopeClient),
		&sdkauth.RequireBearerTokenOptions{ResourceMetadataURL: metadataURL},
	)(handler)

	prmHandler := sdkauth.ProtectedResourceMetadataHandler(&oauthex.ProtectedResourceMetadata{
		Resource:             cfg.ResourceURL,
		AuthorizationServers: []string{cfg.Issuer()},
	})

	mux := http.NewServeMux()
	mux.Handle(mcpEndpointPath, authenticatedHandler)
	mux.Handle(protectedResourceMetadataPath, prmHandler)

	log.Printf("Starting MCP server on http at %s (endpoint: %s, discovery: %s)...", cfg.Addr, mcpEndpointPath, protectedResourceMetadataPath)
	if err := http.ListenAndServe(cfg.Addr, mux); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
