// Helper to generate the layout
import { html, raw } from "hono/html";
import type { HtmlEscapedString } from "hono/utils/html";
import { marked } from "marked";
import type { AuthRequest } from "@cloudflare/workers-oauth-provider";
import { env } from "cloudflare:workers";

// This file mainly exists as a dumping ground for uninteresting html and CSS
// to remove clutter and noise from the auth logic. You likely do not need
// anything from this file.

export const layout = (content: HtmlEscapedString | string, title: string) => html`
	<!DOCTYPE html>
	<html lang="en">
		<head>
			<meta charset="UTF-8" />
			<meta
				name="viewport"
				content="width=device-width, initial-scale=1.0"
			/>
			<title>${title}</title>
			<script src="https://cdn.tailwindcss.com"></script>
			<script>
				tailwind.config = {
					theme: {
						extend: {
							colors: {
								primary: "#3498db",
								secondary: "#2ecc71",
								accent: "#f39c12",
							},
							fontFamily: {
								sans: ["Inter", "system-ui", "sans-serif"],
								heading: ["Roboto", "system-ui", "sans-serif"],
							},
						},
					},
				};
			</script>
			<style>
				@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto:wght@400;500;700&display=swap");

				/* Custom styling for markdown content */
				.markdown h1 {
					font-size: 2.25rem;
					font-weight: 700;
					font-family: "Roboto", system-ui, sans-serif;
					color: #1a202c;
					margin-bottom: 1rem;
					line-height: 1.2;
				}

				.markdown h2 {
					font-size: 1.5rem;
					font-weight: 600;
					font-family: "Roboto", system-ui, sans-serif;
					color: #2d3748;
					margin-top: 1.5rem;
					margin-bottom: 0.75rem;
					line-height: 1.3;
				}

				.markdown h3 {
					font-size: 1.25rem;
					font-weight: 600;
					font-family: "Roboto", system-ui, sans-serif;
					color: #2d3748;
					margin-top: 1.25rem;
					margin-bottom: 0.5rem;
				}

				.markdown p {
					font-size: 1rem;
					color: #4a5568;
					margin-bottom: 1rem;
					line-height: 1.6;
				}

				.markdown a {
					color: #3498db;
					font-weight: 500;
					text-decoration: none;
				}

				.markdown a:hover {
					text-decoration: underline;
				}

				.markdown blockquote {
					border-left: 4px solid #f39c12;
					padding-left: 1rem;
					padding-top: 0.75rem;
					padding-bottom: 0.75rem;
					margin-top: 1.5rem;
					margin-bottom: 1.5rem;
					background-color: #fffbeb;
					font-style: italic;
				}

				.markdown blockquote p {
					margin-bottom: 0.25rem;
				}

				.markdown ul,
				.markdown ol {
					margin-top: 1rem;
					margin-bottom: 1rem;
					margin-left: 1.5rem;
					font-size: 1.125rem;
					color: #4a5568;
				}

				.markdown li {
					margin-bottom: 0.5rem;
				}

				.markdown ul li {
					list-style-type: disc;
				}

				.markdown ol li {
					list-style-type: decimal;
				}

				.markdown pre {
					background-color: #f7fafc;
					padding: 1rem;
					border-radius: 0.375rem;
					margin-top: 1rem;
					margin-bottom: 1rem;
					overflow-x: auto;
				}

				.markdown code {
					font-family: monospace;
					font-size: 0.875rem;
					background-color: #f7fafc;
					padding: 0.125rem 0.25rem;
					border-radius: 0.25rem;
				}

				.markdown pre code {
					background-color: transparent;
				}
					
				.markdown pre {
					background:rgb(45, 60, 80) !important;
					color:rgb(222, 222, 222) !important;
					position: relative;
				}

				.markdown pre .copy-button {
					position: absolute;
					top: 0.5rem;
					right: 0.5rem;
					padding: 0.25rem 0.5rem;
					background: rgba(255, 255, 255, 0.1);
					border: 1px solid rgba(255, 255, 255, 0.2);
					color: white;
					border-radius: 0.25rem;
					cursor: pointer;
					font-size: 0.75rem;
					transition: all 0.2s;
				}

				.markdown pre .copy-button:hover {
					background: rgba(255, 255, 255, 0.2);
				}

				// .markdown pre .copy-button.copied {
				// 	background: #2ecc71;
				// 	border-color: #2ecc71;
				// }
			</style>
			<script>
				// Add copy buttons to all pre code blocks
				document.addEventListener('DOMContentLoaded', () => {
					const preBlocks = document.querySelectorAll('.markdown pre');
					preBlocks.forEach(pre => {
						const button = document.createElement('button');
						button.className = 'copy-button';
						button.textContent = 'Copy';
						button.onclick = () => {
							const code = pre.querySelector('code')?.textContent || '';
							navigator.clipboard.writeText(code).then(() => {
								button.textContent = 'Copied!';
								button.classList.add('copied');
								setTimeout(() => {
									button.textContent = 'Copy';
									button.classList.remove('copied');
								}, 2000);
							});
						};
						pre.appendChild(button);
					});
				});
			</script>
		</head>
		<body
			class="bg-gray-50 text-gray-800 font-sans leading-relaxed flex flex-col min-h-screen"
		>
			<main class="container mx-auto px-4 pb-12 flex-grow pt-8">
				${content}
			</main>
			<footer class="bg-gray-100 py-6 mt-12">
				<div class="container mx-auto px-4 text-center text-gray-600">
					<p>
						&copy; ${new Date().getFullYear()} Descope.
						All rights reserved.
					</p>
				</div>
			</footer>
		</body>
	</html>
`;

export const homeContent = async (req: Request): Promise<HtmlEscapedString> => {
	// We have the README symlinked into the static directory, so we can fetch it
	// and render it into HTML
	const origin = new URL(req.url).origin;
	const res = await env.ASSETS.fetch(`${origin}/README.md`);
	const markdown = await res.text();
	const content = await marked(markdown);
	return html`
		<div class="max-w-4xl mx-auto markdown">${raw(content)}</div>
	`;
};