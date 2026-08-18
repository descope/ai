package main

import (
	"flag"
	"log"
	"net/http"

	descopeclient "github.com/descope/go-sdk/descope/client"
	"github.com/mark3labs/mcp-go/server"

	"github.com/descope/ai/examples/go-mcp-server/internal/auth"
	"github.com/descope/ai/examples/go-mcp-server/internal/config"
	"github.com/descope/ai/examples/go-mcp-server/internal/tools"
)

// mcpEndpointPath is the path the streamable-HTTP transport serves the MCP
// endpoint on. Pinned explicitly (rather than relying on mcp-go's default)
// since it's also used to build the auth-wrapping mux route below.
const mcpEndpointPath = "/mcp"

func main() {
	transport := flag.String("transport", "stdio", "Transport to use: stdio or http")
	flag.Parse()

	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config error: %v", err)
	}

	descopeClient, err := descopeclient.NewWithConfig(&descopeclient.Config{ProjectID: cfg.DescopeProjectID})
	if err != nil {
		log.Fatalf("failed to init descope client: %v", err)
	}

	s := server.NewMCPServer(
		"descope-go-mcp-server",
		"0.1.0",
	)
	s.AddTool(tools.NewHelloTool(), tools.HelloHandler)

	switch *transport {
	case "stdio":
		log.Println("Starting MCP server on stdio (no auth enforced locally)...")
		if err := server.ServeStdio(s); err != nil {
			log.Fatalf("server error: %v", err)
		}
	case "http":
		// Tool-call middleware runs as defense in depth behind the HTTP-level
		// 401 gate below; it's only registered here so stdio mode (which
		// shares this *MCPServer) stays unauthenticated.
		s.Use(auth.NewAuthMiddleware(descopeClient))

		prmPath := server.ProtectedResourceMetadataPath(cfg.ResourceURL)
		metadataURL := cfg.ResourceURL + prmPath

		httpServer := server.NewStreamableHTTPServer(s,
			server.WithHTTPContextFunc(auth.HTTPContextFunc),
			server.WithEndpointPath(mcpEndpointPath),
			server.WithProtectedResourceMetadata(server.ProtectedResourceMetadataConfig{
				Resource:             cfg.ResourceURL,
				AuthorizationServers: []string{cfg.DescopeBaseURL},
			}),
		)

		// The MCP endpoint requires a valid bearer token (HTTP 401 +
		// WWW-Authenticate on failure); the discovery document itself must
		// stay reachable without auth so clients can find out how to
		// authenticate in the first place.
		mux := http.NewServeMux()
		mux.Handle(mcpEndpointPath, auth.RequireBearerToken(descopeClient, metadataURL)(httpServer))
		mux.Handle(prmPath, httpServer)

		log.Printf("Starting MCP server on http at %s (endpoint: %s, discovery: %s)...", cfg.Addr, mcpEndpointPath, prmPath)
		if err := http.ListenAndServe(cfg.Addr, mux); err != nil {
			log.Fatalf("server error: %v", err)
		}
	default:
		log.Fatalf("unknown transport: %s (use 'stdio' or 'http')", *transport)
	}
}
