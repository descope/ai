"use client";

import { useState } from "react";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`absolute right-2 top-2 rounded-lg px-2 py-1 text-xs font-medium
        ${
          copied
            ? "bg-green-500/90 text-white"
            : "bg-gray-700/50 text-gray-300 hover:bg-gray-700/70"
        } transition-all duration-200`}
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

function CodeBlock({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const content =
    typeof children === "string" ? children : JSON.stringify(children, null, 2);

  return (
    <div className="relative rounded-xl bg-gray-900/80 shadow-lg max-w-full">
      <CopyButton text={content} />
      <pre
        className={`w-full overflow-x-auto p-4 pt-8 text-sm break-words whitespace-pre-wrap ${className}`}
      >
        <code className="block font-mono">{content}</code>
      </pre>
    </div>
  );
}

export default function Home() {
  const baseUrl =
    process.env.NODE_ENV === "development"
      ? "http://localhost:3000"
      : "https://your-production-url.com";
  const serverUrl = `${baseUrl}/mcp`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#181c2b] via-[#232946] to-[#3a1c71] font-sans">
      <main className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl font-extrabold font-heading text-white mb-6 tracking-tight drop-shadow-lg flex items-center">
            <span className="inline-block align-middle text-6xl mr-3">🌤️</span>
            <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent align-middle">
              Weather MCP Server
            </span>
          </h1>
          <p className="text-xl text-gray-200 mb-10 font-light max-w-2xl mx-auto text-center">
            A{" "}
            <a
              href="https://github.com/modelcontextprotocol/typescript-sdk?tab=readme-ov-file#without-session-management-stateless"
              className="text-purple-300 hover:text-pink-400 transition-colors font-medium"
            >
              Stateless
            </a>{" "}
            <a
              href="https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http"
              className="text-purple-300 hover:text-pink-400 transition-colors font-medium"
            >
              Streamable HTTP
            </a>{" "}
            <a
              href="https://modelcontextprotocol.com/"
              className="text-purple-300 hover:text-pink-400 transition-colors font-medium"
            >
              Model Context Protocol (MCP)
            </a>{" "}
            server for weather data from the{" "}
            <a
              href="https://www.weather.gov/documentation/services-web-api"
              className="text-blue-300 hover:text-pink-400 transition-colors font-medium"
            >
              National Weather Service API
            </a>{" "}
            secured by{" "}
            <a
              href="https://www.descope.com/"
              className="text-pink-300 hover:text-purple-400 transition-colors font-medium"
            >
              Descope
            </a>{" "}
            <a
              href="https://www.npmjs.com/package/@descope/mcp-express"
              className="text-pink-300 hover:text-purple-400 transition-colors font-medium"
            >
              Auth
            </a>{" "}
            and hosted on{" "}
            <a
              href="https://vercel.com/"
              className="text-blue-300 hover:text-pink-400 transition-colors font-medium"
            >
              Vercel
            </a>
            .
          </p>

          <section className="grid md:grid-cols-2 gap-8 mb-12">
            <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-3xl p-8 shadow-xl">
              <h3 className="text-2xl font-bold text-white mb-6">
                Quick Start
              </h3>

              <div className="space-y-6">
                <div>
                  <h4 className="text-gray-400 mb-2 font-medium">Server URL</h4>
                  <CodeBlock className="text-green-400" language="url">
                    {serverUrl}
                  </CodeBlock>
                </div>

                <div>
                  <h4 className="text-gray-400 mb-2 font-medium">
                    Configuration
                  </h4>
                  <CodeBlock className="text-blue-300" language="json">{`{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "${serverUrl}"]
    }
  }
}`}</CodeBlock>
                </div>
              </div>
            </div>

            <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-3xl p-8 shadow-xl">
              <h3 className="text-2xl font-bold text-white mb-6">
                IDE Integration
              </h3>

              <div className="space-y-6">
                <div>
                  <h4 className="text-gray-400 mb-2 font-medium">Windsurf</h4>
                  <ol className="list-decimal pl-6 space-y-2 text-gray-300">
                    <li>Open Settings</li>
                    <li>
                      Navigate to{" "}
                      <span className="text-white font-medium">
                        Cascade → Model Context Provider Servers
                      </span>
                    </li>
                    <li>
                      Select{" "}
                      <span className="text-white font-medium">Add Server</span>
                    </li>
                  </ol>
                </div>

                <div>
                  <h4 className="text-gray-400 mb-2 font-medium">Cursor</h4>
                  <ol className="list-decimal pl-6 space-y-2 text-gray-300">
                    <li>
                      Press{" "}
                      <kbd className="px-2 py-1 bg-gray-800 rounded text-white font-medium">
                        ⌘ + ⇧ + J
                      </kbd>{" "}
                      to open Settings
                    </li>
                    <li>
                      Select <span className="text-white font-medium">MCP</span>
                    </li>
                    <li>
                      Select{" "}
                      <span className="text-white font-medium">
                        Add new global MCP server
                      </span>
                    </li>
                  </ol>
                </div>

                <div>
                  <h4 className="text-gray-400 mb-2 font-medium">VSCode</h4>
                  <p className="text-gray-300">
                    Read more{" "}
                    <a
                      href="https://code.visualstudio.com/docs/copilot/chat/mcp-servers"
                      className="text-purple-300 hover:text-pink-400 transition-colors"
                    >
                      here
                    </a>
                  </p>
                  <p className="text-gray-400 text-sm mt-1">
                    Note: Requires VSCode 1.99 or above
                  </p>
                </div>

                <div>
                  <h4 className="text-gray-400 mb-2 font-medium">Zed</h4>
                  <CodeBlock className="text-blue-300" language="json">{`{
  "context_servers": {
    "weather": {
      "command": {
        "command": "npx",
        "args": ["-y", "mcp-remote", "${serverUrl}"]
      }
    },
    "settings": {}
  }
}`}</CodeBlock>
                </div>
              </div>
            </div>
          </section>

          <section className="mb-12">
            <h2 className="text-2xl font-bold font-heading text-white mb-6">
              Available Tools
            </h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-3xl shadow-lg p-8 transition-transform hover:scale-[1.02]">
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
                    className="text-purple-300 hover:text-pink-400 transition-colors font-medium"
                  >
                    National Weather Service API
                  </a>
                  . This tool provides detailed information about active weather
                  warnings, watches, and advisories.
                </p>
                <div className="mt-3 bg-gray-700/60 p-4 rounded-2xl">
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
                      Event type (e.g., Flood Warning, Severe Thunderstorm
                      Watch)
                    </li>
                    <li>Affected area description</li>
                    <li>Alert severity level</li>
                    <li>Current status</li>
                    <li>Detailed headline information</li>
                  </ul>
                </div>
              </div>
              <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-3xl shadow-lg p-8 transition-transform hover:scale-[1.02]">
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
                  temperature, wind conditions, and short-term forecasts from
                  the National Weather Service.
                </p>
                <div className="mt-3 bg-gray-700/60 p-4 rounded-2xl">
                  <p className="font-semibold mb-2 text-white">Parameters:</p>
                  <ul className="list-disc pl-6 space-y-1 text-gray-300">
                    <li>
                      <code className="bg-gray-700 px-1 rounded">latitude</code>
                      : Location latitude (-90 to 90)
                    </li>
                    <li>
                      <code className="bg-gray-700 px-1 rounded">
                        longitude
                      </code>
                      : Location longitude (-180 to 180)
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
                  <p className="mt-3 text-xs text-gray-400">
                    Note: This tool supports locations within the United States
                    only, as provided by the National Weather Service.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="mb-12">
            <h2 className="text-2xl font-bold font-heading text-white mb-6">
              Example Workflows
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-gradient-to-br from-blue-900/60 to-purple-900/60 rounded-2xl p-6 shadow-md">
                <h4 className="text-lg font-semibold text-white mb-2">
                  Travel Planning
                </h4>
                <p className="text-gray-300">
                  "What's the weather forecast for San Francisco next week?"
                </p>
              </div>
              <div className="bg-gradient-to-br from-pink-900/60 to-purple-900/60 rounded-2xl p-6 shadow-md">
                <h4 className="text-lg font-semibold text-white mb-2">
                  Event Planning
                </h4>
                <p className="text-gray-300">
                  "Check weather alerts for outdoor events in New York"
                </p>
              </div>
              <div className="bg-gradient-to-br from-purple-900/60 to-blue-900/60 rounded-2xl p-6 shadow-md">
                <h4 className="text-lg font-semibold text-white mb-2">
                  Agriculture
                </h4>
                <p className="text-gray-300">
                  "Get weather alerts for farming regions in Iowa"
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold font-heading text-white mb-6">
              Troubleshooting
            </h2>
            <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-3xl shadow-xl p-8">
              <p className="mb-4 text-gray-300">
                If you encounter issues with{" "}
                <code className="bg-gray-900 px-2 py-1 rounded">
                  mcp-remote
                </code>
                , try clearing the authentication files:
              </p>
              <CodeBlock className="text-green-300 text-sm select-all">
                rm -rf ~/.mcp-auth
              </CodeBlock>
            </div>
          </section>
        </div>
      </main>
      <footer className="bg-gradient-to-r from-[#232946] to-[#3a1c71] py-8 mt-12 shadow-inner">
        <div className="container mx-auto px-4 text-center text-gray-400">
          <p>&copy; 2025 Descope Inc. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
