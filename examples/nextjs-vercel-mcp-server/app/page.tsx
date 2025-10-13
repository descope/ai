import Image from "next/image";

export default function Home() {
  return (
    <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <main className="flex flex-col gap-8 row-start-2 items-center sm:items-start max-w-4xl">
        <div className="flex flex-col items-center sm:items-start">
          <div className="flex items-center gap-4">
            <Image
              className="dark:invert"
              src="/next.svg"
              alt="Next.js logo"
              width={180}
              height={38}
              priority
            />
            <span className="text-3xl text-gray-400 font-light">+</span>
            <Image
              src="/descope-logo.png"
              alt="Descope logo"
              width={80}
              height={38}
              priority
            />
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold mt-6 text-center sm:text-left">
            NextJS MCP Server + Descope Auth
          </h1>
          <p className="text-lg text-center sm:text-left mt-4 text-gray-600 dark:text-gray-400">
            A Streamable HTTP Model Context Protocol (MCP) server secured by
            Descope Auth and hosted on Vercel.
          </p>
        </div>

        <div className="w-full border border-gray-200 dark:border-gray-800 rounded-lg p-6 bg-gray-50 dark:bg-gray-900">
          <h2 className="text-2xl font-semibold mb-4">Getting Started</h2>
          <ol className="font-mono list-inside list-decimal text-sm space-y-3">
            <li>
              Clone the repository and install dependencies with{" "}
              <code className="bg-black/[.05] dark:bg-white/[.06] px-1.5 py-0.5 rounded font-semibold">
                pnpm install
              </code>
            </li>
            <li>
              Set up environment variables in{" "}
              <code className="bg-black/[.05] dark:bg-white/[.06] px-1.5 py-0.5 rounded font-semibold">
                .env
              </code>
              :
              <ul className="list-disc ml-8 mt-2 space-y-1 text-xs">
                <li>DESCOPE_PROJECT_ID</li>
                <li>DESCOPE_BASE_URL (optional)</li>
              </ul>
            </li>
            <li>
              Run the development server with{" "}
              <code className="bg-black/[.05] dark:bg-white/[.06] px-1.5 py-0.5 rounded font-semibold">
                pnpm run dev
              </code>
            </li>
            <li>
              Connect your MCP Client (Claude, Cursor, etc.) to{" "}
              <code className="bg-black/[.05] dark:bg-white/[.06] px-1.5 py-0.5 rounded font-semibold">
                http://localhost:3000/api/mcp
              </code>
            </li>
          </ol>
        </div>

        <div className="w-full border border-gray-200 dark:border-gray-800 rounded-lg p-6 bg-gray-50 dark:bg-gray-900">
          <h2 className="text-2xl font-semibold mb-4">Key Features</h2>
          <ul className="space-y-3 text-sm">
            <li className="flex gap-3">
              <span className="text-xl">🔐</span>
              <div>
                <strong>Session Validation:</strong> Uses Descope Node SDK to
                validate JWT tokens and extract user context
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-xl">🛠️</span>
              <div>
                <strong>Echo Tool:</strong> Simple example tool demonstrating
                MCP integration that returns "Hello, world!"
              </div>
            </li>
            <li className="flex gap-3">
              <span className="text-xl">🔑</span>
              <div>
                <strong>API Key Management:</strong> Use Descope's Outbound
                Applications to securely manage API keys and OAuth tokens for
                your MCP tools.
              </div>
            </li>
          </ul>
        </div>

        <div className="flex gap-4 items-center flex-col sm:flex-row w-full">
          <a
            className="rounded-full border border-solid border-transparent transition-colors flex items-center justify-center bg-foreground text-background gap-2 hover:bg-[#383838] dark:hover:bg-[#ccc] font-medium text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-5 w-full sm:w-auto"
            href="https://github.com/descope/ai/tree/main/examples/nextjs-vercel-mcp-server"
            target="_blank"
            rel="noopener noreferrer"
          >
            View on GitHub
          </a>
          <a
            className="rounded-full border border-solid border-black/[.08] dark:border-white/[.145] transition-colors flex items-center justify-center hover:bg-[#f2f2f2] dark:hover:bg-[#1a1a1a] hover:border-transparent font-medium text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-5 w-full sm:w-auto"
            href="https://www.descope.com/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Learn about Descope
          </a>
          <a
            className="rounded-full border border-solid border-black/[.08] dark:border-white/[.145] transition-colors flex items-center justify-center hover:bg-[#f2f2f2] dark:hover:bg-[#1a1a1a] hover:border-transparent font-medium text-sm sm:text-base h-10 sm:h-12 px-4 sm:px-5 w-full sm:w-auto"
            href="https://docs.descope.com/mcp"
            target="_blank"
            rel="noopener noreferrer"
          >
            MCP Docs
          </a>
        </div>
      </main>
      <footer className="row-start-3 flex gap-6 flex-wrap items-center justify-center">
        <a
          className="flex items-center gap-2 hover:underline hover:underline-offset-4"
          href="https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Image
            aria-hidden
            src="/window.svg"
            alt="Window icon"
            width={16}
            height={16}
          />
          Streamable HTTP
        </a>
        <a
          className="flex items-center gap-2 hover:underline hover:underline-offset-4"
          href="https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fdescope%2Fai%2Ftree%2Fmain%2Fexamples%2Fnextjs-vercel-mcp-server&env=NEXT_PUBLIC_DESCOPE_PROJECT_ID&envDescription=Your%20Descope%20Project%20ID&envLink=https%3A%2F%2Fapp.descope.com%2Fsettings%2Fproject"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Image
            aria-hidden
            src="/globe.svg"
            alt="Globe icon"
            width={16}
            height={16}
          />
          Deploy on Vercel →
        </a>
      </footer>
    </div>
  );
}
