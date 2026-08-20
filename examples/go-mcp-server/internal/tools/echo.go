package tools

import (
	"context"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// EchoArgs is the input schema for the echo tool.
//
// Message deliberately has no omitempty/omitzero tag, so the SDK's schema
// inference marks it required. We chose a genuine echo-the-input tool over
// the Vercel MCP server example's literal zero-argument, static
// "Hello, world!" tool — a real echo is a more useful demo/test target for
// this sample.
type EchoArgs struct {
	Message string `json:"message" jsonschema:"the message to echo back"`
}

// NewEchoTool defines the schema for the echo tool.
func NewEchoTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "echo",
		Description: "Echo a message back to the caller",
	}
}

// EchoHandler runs when the echo tool is called. It returns args.Message
// back as the tool's text content.
//
// No manual "is Message present" check is needed here: mcp.AddTool
// validates a call's arguments against EchoArgs's inferred JSON schema
// (which marks "message" as required) before this handler ever runs — an
// entirely missing "message" argument is rejected at that layer, before
// reaching this function. An explicitly empty string ("") still satisfies
// "required" under JSON Schema semantics (required means "present", not
// "non-empty") and is a legitimate echo input, so it's intentionally not
// treated as an error here either.
func EchoHandler(ctx context.Context, req *mcp.CallToolRequest, args EchoArgs) (*mcp.CallToolResult, any, error) {
	return &mcp.CallToolResult{
		Content: []mcp.Content{&mcp.TextContent{Text: args.Message}},
	}, nil, nil
}
