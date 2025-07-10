import { headers } from "next/headers";

export default async function Home() {
  const headersList = await headers();
  const host = headersList.get("host") || "";
  const protocol = process.env.NODE_ENV === "development" ? "http" : "https";
  const baseUrl = `${protocol}://${host}`;
  const serverUrl = `${baseUrl}/mcp`;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <main className="container mx-auto px-4 pb-12 flex-grow pt-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold font-heading text-white mb-6">
            🌤️ Weather MCP Server
          </h1>
          <p className="text-lg text-gray-300 mb-8">
            A{" "}
            <a
              href="https://github.com/modelcontextprotocol/typescript-sdk?tab=readme-ov-file#without-session-management-stateless"
              className="text-purple-400 hover:text-purple-300"
            >
              Stateless
            </a>{" "}
            <a
              href="https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http"
              className="text-purple-400 hover:text-purple-300"
            >
              Streamable HTTP
            </a>{" "}
            <a
              href="https://modelcontextprotocol.com/"
              className="text-purple-400 hover:text-purple-300"
            >
              Model Context Protocol (MCP)
            </a>{" "}
            server for weather data from the{" "}
            <a
              href="https://www.weather.gov/documentation/services-web-api"
              className="text-purple-400 hover:text-purple-300"
            >
              National Weather Service API
            </a>{" "}
            secured by{" "}
            <a
              href="https://www.descope.com/"
              className="text-purple-400 hover:text-purple-300"
            >
              Descope
            </a>{" "}
            <a
              href="https://www.npmjs.com/package/@descope/mcp-express"
              className="text-purple-400 hover:text-purple-300"
            >
              Auth
            </a>{" "}
            and hosted on{" "}
            <a
              href="https://vercel.com/"
              className="text-purple-400 hover:text-purple-300"
            >
              Vercel
            </a>
            .
          </p>

          <h2 className="text-2xl font-bold font-heading text-white mt-8 mb-4">
            Quick Start
          </h2>
          <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700 hover:border-purple-500 transition-colors">
            <h3 className="text-xl font-semibold text-white mb-3">
              Server URL
            </h3>
            <pre className="bg-gray-900 p-4 rounded-lg">
              <code className="text-green-400">{serverUrl}</code>
            </pre>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700 hover:border-purple-500 transition-colors">
            <h3 className="text-xl font-semibold text-white mb-3">
              Configuration
            </h3>
            <pre className="bg-gray-900 p-4 rounded-lg">
              <code className="text-green-400">{`{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "${serverUrl}"]
    }
  }
}`}</code>
            </pre>
          </div>

          <h2 className="text-2xl font-bold font-heading text-white mt-8 mb-4">
            IDE Integration
          </h2>
          <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700 hover:border-purple-500 transition-colors">
            <h3 className="text-xl font-semibold text-white mb-3">Windsurf</h3>
            <ol className="list-decimal pl-6 space-y-2 text-gray-300">
              <li>Open Settings</li>
              <li>
                Navigate to{" "}
                <strong className="font-semibold text-white">Cascade</strong> →{" "}
                <strong className="font-semibold text-white">
                  Model Context Provider Servers
                </strong>
              </li>
              <li>
                Select{" "}
                <strong className="font-semibold text-white">Add Server</strong>
              </li>
            </ol>

            <h3 className="text-xl font-semibold text-white mt-6 mb-3">
              Cursor
            </h3>
            <ol className="list-decimal pl-6 space-y-2 text-gray-300">
              <li>
                Press{" "}
                <strong className="font-semibold text-white">
                  Cmd + Shift + J
                </strong>{" "}
                to open Settings
              </li>
              <li>
                Select <strong className="font-semibold text-white">MCP</strong>
              </li>
              <li>
                Select{" "}
                <strong className="font-semibold text-white">
                  Add new global MCP server
                </strong>
              </li>
            </ol>

            <h3 className="text-xl font-semibold text-white mt-6 mb-3">
              VSCode
            </h3>
            <p className="mb-2 text-gray-300">
              Read more{" "}
              <a
                href="https://code.visualstudio.com/docs/copilot/chat/mcp-servers"
                className="text-purple-400 hover:text-purple-300"
              >
                here
              </a>
            </p>
            <p className="text-gray-400">Note: Requires VSCode 1.99 or above</p>

            <h3 className="text-xl font-semibold text-white mt-6 mb-3">Zed</h3>
            <pre className="bg-gray-900 p-4 rounded-lg">
              <code className="text-green-400">{`{
  "context_servers": {
    "weather": {
      "command": {
        "command": "npx",
        "args": ["-y", "mcp-remote", "${serverUrl}"]
      }
    },
    "settings": {}
  }
}`}</code>
            </pre>
          </div>

          <h2 className="text-2xl font-bold font-heading text-white mt-8 mb-4">
            Available Tools
          </h2>
          <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700 hover:border-purple-500 transition-colors">
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-white mb-3">
                Weather Alerts
              </h3>
              <code className="bg-gray-900 px-2 py-1 rounded text-green-400">
                get-alerts
              </code>
              <p className="mt-2 text-gray-300">
                Get real-time weather alerts for any US state using the{" "}
                <a
                  href="https://www.weather.gov/documentation/services-web-api"
                  className="text-purple-400 hover:text-purple-300"
                >
                  National Weather Service API
                </a>
                . This tool provides detailed information about active weather
                warnings, watches, and advisories.
              </p>
              <div className="mt-3 bg-gray-700 p-4 rounded">
                <p className="font-semibold mb-2 text-white">Parameters:</p>
                <ul className="list-disc pl-6 space-y-1 text-gray-300">
                  <li>
                    <code className="bg-gray-700 px-1 rounded">state</code>:
                    Two-letter state code (e.g., "CA" for California)
                  </li>
                </ul>
                <p className="mt-3 font-semibold mb-2 text-white">Returns:</p>
                <ul className="list-disc pl-6 space-y-1 text-gray-300">
                  <li>
                    Event type (e.g., Flood Warning, Severe Thunderstorm Watch)
                  </li>
                  <li>Affected area description</li>
                  <li>Alert severity level</li>
                  <li>Current status</li>
                  <li>Detailed headline information</li>
                </ul>
              </div>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-white mb-3">
                Weather Forecast
              </h3>
              <code className="bg-gray-900 px-2 py-1 rounded text-green-400">
                get-forecast
              </code>
              <p className="mt-2 text-gray-300">
                Get detailed weather forecasts for any location in the United
                States using latitude and longitude coordinates. This tool
                provides comprehensive weather information including
                temperature, wind conditions, and short-term forecasts from the
                National Weather Service.
              </p>
              <div className="mt-3 bg-gray-700 p-4 rounded">
                <p className="font-semibold mb-2 text-white">Parameters:</p>
                <ul className="list-disc pl-6 space-y-1 text-gray-300">
                  <li>
                    <code className="bg-gray-700 px-1 rounded">latitude</code>:
                    Location latitude (-90 to 90)
                  </li>
                  <li>
                    <code className="bg-gray-700 px-1 rounded">longitude</code>:
                    Location longitude (-180 to 180)
                  </li>
                </ul>
                <p className="mt-3 font-semibold mb-2 text-white">Returns:</p>
                <ul className="list-disc pl-6 space-y-1 text-gray-300">
                  <li>
                    Forecast period name (e.g., "This Afternoon", "Tonight")
                  </li>
                  <li>Temperature in Fahrenheit or Celsius</li>
                  <li>Wind speed and direction</li>
                  <li>Short-term weather forecast description</li>
                </ul>
                <p className="mt-3 text-sm text-gray-400">
                  Note: This tool supports locations within the United States
                  only, as provided by the National Weather Service.
                </p>
              </div>
            </div>
          </div>

          <h2 className="text-2xl font-bold font-heading text-white mt-8 mb-4">
            Example Workflows
          </h2>
          <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700 hover:border-purple-500 transition-colors">
            <div className="bg-gray-700 rounded-lg p-4 mb-4">
              <h4 className="text-lg font-semibold text-white mb-2">
                Travel Planning
              </h4>
              <p className="text-gray-300">
                "What's the weather forecast for San Francisco next week?"
              </p>
            </div>
            <div className="bg-gray-700 rounded-lg p-4 mb-4">
              <h4 className="text-lg font-semibold text-white mb-2">
                Event Planning
              </h4>
              <p className="text-gray-300">
                "Check weather alerts for outdoor events in New York"
              </p>
            </div>
            <div className="bg-gray-700 rounded-lg p-4">
              <h4 className="text-lg font-semibold text-white mb-2">
                Agriculture
              </h4>
              <p className="text-gray-300">
                "Get weather alerts for farming regions in Iowa"
              </p>
            </div>
          </div>

          <h2 className="text-2xl font-bold font-heading text-white mt-8 mb-4">
            Troubleshooting
          </h2>
          <div className="bg-gray-800 rounded-lg p-6 mb-6 border border-gray-700 hover:border-purple-500 transition-colors">
            <p className="mb-4 text-gray-300">
              If you encounter issues with{" "}
              <code className="bg-gray-900 px-2 py-1 rounded">mcp-remote</code>,
              try clearing the authentication files:
            </p>
            <pre className="bg-gray-900 p-4 rounded-lg">
              <code className="text-green-400">rm -rf ~/.mcp-auth</code>
            </pre>
          </div>
        </div>
      </main>
      <footer className="bg-gray-900 py-6 mt-12">
        <div className="container mx-auto px-4 text-center text-gray-400">
          <p>&copy; 2025 Descope Inc. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
