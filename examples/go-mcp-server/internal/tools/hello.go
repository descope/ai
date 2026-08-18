package tools

import (
	"context"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"
)

// NewHelloTool defines the schema for the hello_world tool.
func NewHelloTool() mcp.Tool {
	return mcp.NewTool("hello_world",
		mcp.WithDescription("Say hello to a given name"),
		mcp.WithString("name", mcp.Required(), mcp.Description("Name of the person to greet")),
	)
}

// HelloHandler runs when the hello_world tool is called.
func HelloHandler(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	name, err := req.RequireString("name")
	if err != nil {
		return mcp.NewToolResultError(err.Error()), nil
	}
	return mcp.NewToolResultText(fmt.Sprintf("Hello, %s!", name)), nil
}
