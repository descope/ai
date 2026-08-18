package tools

import (
	"context"
	"testing"

	"github.com/mark3labs/mcp-go/mcp"
)

func TestNewHelloTool(t *testing.T) {
	tool := NewHelloTool()

	if tool.Name != "hello_world" {
		t.Errorf("tool.Name = %q, want %q", tool.Name, "hello_world")
	}

	nameProp, ok := tool.InputSchema.Properties["name"]
	if !ok {
		t.Fatal("expected a \"name\" property in the tool's input schema")
	}
	schema, ok := nameProp.(map[string]any)
	if !ok {
		t.Fatalf("\"name\" property is %T, want map[string]any", nameProp)
	}
	if schema["type"] != "string" {
		t.Errorf("\"name\" property type = %v, want %q", schema["type"], "string")
	}

	found := false
	for _, req := range tool.InputSchema.Required {
		if req == "name" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("tool.InputSchema.Required = %v, want it to include %q", tool.InputSchema.Required, "name")
	}
}

func callToolRequest(args map[string]any) mcp.CallToolRequest {
	return mcp.CallToolRequest{
		Params: mcp.CallToolParams{
			Name:      "hello_world",
			Arguments: args,
		},
	}
}

func TestHelloHandler_Success(t *testing.T) {
	req := callToolRequest(map[string]any{"name": "World"})

	result, err := HelloHandler(context.Background(), req)
	if err != nil {
		t.Fatalf("HelloHandler returned unexpected Go error: %v", err)
	}
	if result.IsError {
		t.Fatalf("result.IsError = true, want false; content: %+v", result.Content)
	}
	if len(result.Content) != 1 {
		t.Fatalf("len(result.Content) = %d, want 1", len(result.Content))
	}
	text, ok := result.Content[0].(mcp.TextContent)
	if !ok {
		t.Fatalf("result.Content[0] is %T, want mcp.TextContent", result.Content[0])
	}
	if want := "Hello, World!"; text.Text != want {
		t.Errorf("text = %q, want %q", text.Text, want)
	}
}

func TestHelloHandler_MissingName(t *testing.T) {
	req := callToolRequest(map[string]any{})

	result, err := HelloHandler(context.Background(), req)
	if err != nil {
		t.Fatalf("HelloHandler returned a Go error (%v); want a tool-level error result instead", err)
	}
	if result == nil {
		t.Fatal("result is nil, want a non-nil error result")
	}
	if !result.IsError {
		t.Fatalf("result.IsError = false, want true (missing required \"name\" argument); content: %+v", result.Content)
	}
	if len(result.Content) != 1 {
		t.Fatalf("len(result.Content) = %d, want 1", len(result.Content))
	}
	if _, ok := result.Content[0].(mcp.TextContent); !ok {
		t.Fatalf("result.Content[0] is %T, want mcp.TextContent", result.Content[0])
	}
}
