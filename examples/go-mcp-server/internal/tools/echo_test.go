package tools

import (
	"context"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestNewEchoTool(t *testing.T) {
	tool := NewEchoTool()

	if tool.Name != "echo" {
		t.Errorf("tool.Name = %q, want %q", tool.Name, "echo")
	}
	if tool.Description == "" {
		t.Error("tool.Description is empty, want a non-empty description")
	}
}

func TestEchoHandler_ReturnsMessage(t *testing.T) {
	result, output, err := EchoHandler(context.Background(), &mcp.CallToolRequest{}, EchoArgs{Message: "hello there"})
	if err != nil {
		t.Fatalf("EchoHandler returned unexpected error: %v", err)
	}
	if output != nil {
		t.Errorf("output = %v, want nil", output)
	}
	if result == nil {
		t.Fatal("result is nil, want a populated CallToolResult")
	}
	if result.IsError {
		t.Fatalf("result.IsError = true, want false; content: %+v", result.Content)
	}
	if len(result.Content) != 1 {
		t.Fatalf("len(result.Content) = %d, want 1", len(result.Content))
	}
	text, ok := result.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatalf("result.Content[0] is %T, want *mcp.TextContent", result.Content[0])
	}
	if want := "hello there"; text.Text != want {
		t.Errorf("text = %q, want %q", text.Text, want)
	}
}

func TestEchoHandler_EmptyMessageIsNotAnError(t *testing.T) {
	// An explicitly empty string still satisfies JSON Schema's "required"
	// (required means "present", not "non-empty"), and is a legitimate echo
	// input — see the comment on EchoHandler. This is a deliberate design
	// choice, not an oversight, so it's pinned here as a regression test.
	result, _, err := EchoHandler(context.Background(), &mcp.CallToolRequest{}, EchoArgs{Message: ""})
	if err != nil {
		t.Fatalf("EchoHandler returned unexpected error for an empty message: %v", err)
	}
	if result.IsError {
		t.Fatalf("result.IsError = true, want false for an empty (but present) message")
	}
	text, ok := result.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatalf("result.Content[0] is %T, want *mcp.TextContent", result.Content[0])
	}
	if text.Text != "" {
		t.Errorf("text = %q, want empty string", text.Text)
	}
}

// TestEchoTool_MissingMessageRejectedBeforeHandler confirms, end-to-end
// through an in-process client/server pair, that a tools/call with no
// "message" argument at all is rejected by the SDK's automatic schema
// validation before EchoHandler ever runs — not by any manual check inside
// the handler itself (there is none; see the comment on EchoHandler).
//
// This can't be exercised by calling EchoHandler directly: schema
// validation happens in the server's dispatch layer, one level above the
// typed handler, so a direct call always bypasses it regardless of the
// EchoArgs value passed in.
func TestEchoTool_MissingMessageRejectedBeforeHandler(t *testing.T) {
	ctx := context.Background()

	server := mcp.NewServer(&mcp.Implementation{Name: "test-server", Version: "0.0.1"}, nil)
	mcp.AddTool(server, NewEchoTool(), EchoHandler)

	serverTransport, clientTransport := mcp.NewInMemoryTransports()

	if _, err := server.Connect(ctx, serverTransport, nil); err != nil {
		t.Fatalf("server.Connect failed: %v", err)
	}

	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "0.0.1"}, nil)
	session, err := client.Connect(ctx, clientTransport, nil)
	if err != nil {
		t.Fatalf("client.Connect failed: %v", err)
	}
	defer session.Close()

	result, err := session.CallTool(ctx, &mcp.CallToolParams{
		Name:      "echo",
		Arguments: map[string]any{},
	})

	switch {
	case err != nil:
		// Rejected as a protocol-level error — also an acceptable shape for
		// "rejected before the handler ran", since either way EchoHandler
		// was never invoked with a missing message.
	case result != nil && result.IsError:
		// Rejected as a tool-level error result.
	default:
		t.Fatalf("expected the missing required \"message\" argument to be rejected before EchoHandler ran, got result=%+v, err=%v", result, err)
	}
}
