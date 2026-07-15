/**
 * Descope Agent OAuth Hooks
 * ─────────────────────────
 * Standardized pre-tool-use hooks for AI agents (Cursor, Claude Code, etc.)
 * that need to acquire scoped MCP server access tokens via Descope.
 *
 * Four strategies:
 *
 *  1. clientCredentialsTokenExchange
 *     → client_credentials grant → token exchange for MCP server token
 *
 *  2. userTokenExchange
 *     → user access_token → token exchange for MCP server token
 *
 *  3. userConnectionsToken
 *     → user access_token → Descope Connections API → connection token
 *     ⚠️ Security: returns raw third-party token to the agent
 *
 *  4. cibaFlow
 *     → access_token or login_hint → CIBA backchannel auth → MCP server token
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export interface DescopeOAuthConfig {
  /** Descope Project ID (used as the OAuth issuer namespace) */
  projectId: string;
  /** Base URL — override for dedicated / EU deployments */
  baseUrl?: string;
}

export interface ClientCredentialsConfig extends DescopeOAuthConfig {
  clientId: string;
  clientSecret: string;
}

export interface TokenExchangeParams {
  /** The target MCP server audience (resource indicator / audience URI) */
  audience: string;
  /** Space-separated scopes to request on the MCP server token */
  scopes: string;
  /** Optional `resource` parameter (RFC 8707) */
  resource?: string;
}

export interface CIBAParams {
  /** Target MCP server audience */
  audience: string;
  /** Scopes to request */
  scopes: string;
  /** Human-readable binding message shown to the user during consent */
  bindingMessage?: string;
  /** Polling interval in ms (default 2 000) */
  pollIntervalMs?: number;
  /** Max time to wait for user consent in ms (default 120 000) */
  timeoutMs?: number;
}

export interface ConnectionsParams {
  /** The Descope Outbound App ID (e.g., "google-contacts", "github") */
  appId: string;
  /** The Descope user ID to retrieve the connection token for */
  userId: string;
  /** Optional tenant ID if the user belongs to a specific tenant */
  tenantId?: string;
  /** Scopes to request on the connection token */
  scopes?: string[];
  /** Additional options */
  options?: {
    withRefreshToken?: boolean;
    forceRefresh?: boolean;
  };
}

export interface TokenResult {
  accessToken: string;
  tokenType: string;
  expiresAt: Date;
  scope?: string;
  raw: Record<string, unknown>;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const DEFAULT_BASE_URL = "https://api.descope.com";
const TOKEN_PATH = "/oauth2/v1/apps/token";
const TOKEN_EXCHANGE_PATH = (projectId: string) =>
  `/oauth2/v1/apps/${projectId}/token`;
const CIBA_AUTH_PATH = "/oauth2/v1/apps/bc-authorize";
const CONNECTIONS_PATH = "/v1/mgmt/outbound/app/user/token";

const GRANT_TYPE = {
  CLIENT_CREDENTIALS: "client_credentials",
  TOKEN_EXCHANGE: "urn:ietf:params:oauth:grant-type:token-exchange",
  CIBA: "urn:openid:params:grant-type:ciba",
} as const;

const TOKEN_TYPE = {
  ACCESS_TOKEN: "urn:ietf:params:oauth:token-type:access_token",
} as const;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function tokenUrl(cfg: DescopeOAuthConfig): string {
  return `${cfg.baseUrl ?? DEFAULT_BASE_URL}${TOKEN_PATH}`;
}

function tokenExchangeUrl(cfg: DescopeOAuthConfig): string {
  return `${cfg.baseUrl ?? DEFAULT_BASE_URL}${TOKEN_EXCHANGE_PATH(cfg.projectId)}`;
}

function cibaAuthUrl(cfg: DescopeOAuthConfig): string {
  return `${cfg.baseUrl ?? DEFAULT_BASE_URL}${CIBA_AUTH_PATH}`;
}

function connectionsUrl(cfg: DescopeOAuthConfig): string {
  return `${cfg.baseUrl ?? DEFAULT_BASE_URL}${CONNECTIONS_PATH}`;
}

function toJsonBody(params: Record<string, string | undefined>): string {
  return JSON.stringify(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v != null)),
  );
}

function parseTokenResponse(json: Record<string, unknown>): TokenResult {
  const expiresIn = (json.expires_in as number) ?? 3600;
  return {
    accessToken: json.access_token as string,
    tokenType: (json.token_type as string) ?? "Bearer",
    expiresAt: new Date(Date.now() + expiresIn * 1000),
    scope: json.scope as string | undefined,
    raw: json,
  };
}

async function postJson(
  url: string,
  body: Record<string, string | undefined>,
  headers?: Record<string, string>,
): Promise<Record<string, unknown>> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: toJsonBody(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Descope OAuth error ${res.status}: ${text}`);
  }
  return res.json() as Promise<Record<string, unknown>>;
}

async function postJsonRaw(
  url: string,
  body: Record<string, unknown>,
  bearerToken: string,
): Promise<Record<string, unknown>> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${bearerToken}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Descope API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<Record<string, unknown>>;
}

// ─── Simple In-Memory Token Cache ────────────────────────────────────────────

const cache = new Map<string, TokenResult>();

function cacheKey(...parts: string[]): string {
  return parts.join("|");
}

function getCached(key: string): TokenResult | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (entry.expiresAt.getTime() - Date.now() > 30_000) return entry;
  cache.delete(key);
  return null;
}

function setCache(key: string, result: TokenResult): TokenResult {
  cache.set(key, result);
  return result;
}

// ─── Hook 1: Client Credentials → Token Exchange ─────────────────────────────

export async function clientCredentialsTokenExchange(
  cfg: ClientCredentialsConfig,
  exchange: TokenExchangeParams,
): Promise<TokenResult> {
  const key = cacheKey(
    "cc-exchange",
    cfg.clientId,
    exchange.audience,
    exchange.scopes,
  );
  const cached = getCached(key);
  if (cached) return cached;

  // Step 1 — Client Credentials
  const ccJson = await postJson(tokenUrl(cfg), {
    grant_type: GRANT_TYPE.CLIENT_CREDENTIALS,
    client_id: cfg.clientId,
    client_secret: cfg.clientSecret,
  });

  const agentToken = ccJson.access_token as string;

  // Step 2 — Token Exchange for MCP server token (project-scoped endpoint)
  const teJson = await postJson(tokenExchangeUrl(cfg), {
    grant_type: GRANT_TYPE.TOKEN_EXCHANGE,
    client_id: cfg.clientId,
    client_secret: cfg.clientSecret,
    subject_token: agentToken,
    subject_token_type: TOKEN_TYPE.ACCESS_TOKEN,
    audience: exchange.audience,
    resource: exchange.resource,
  });

  return setCache(key, parseTokenResponse(teJson));
}

// ─── Hook 2: User Access Token → Token Exchange ──────────────────────────────

export async function userTokenExchange(
  cfg: DescopeOAuthConfig,
  userAccessToken: string,
  exchange: TokenExchangeParams,
): Promise<TokenResult> {
  const key = cacheKey(
    "user-exchange",
    exchange.audience,
    exchange.scopes,
    userAccessToken.slice(-8),
  );
  const cached = getCached(key);
  if (cached) return cached;

  const json = await postJson(tokenExchangeUrl(cfg), {
    grant_type: GRANT_TYPE.TOKEN_EXCHANGE,
    subject_token: userAccessToken,
    subject_token_type: TOKEN_TYPE.ACCESS_TOKEN,
    audience: exchange.audience,
    resource: exchange.resource,
  });

  return setCache(key, parseTokenResponse(json));
}

// ─── Hook 3: User Access Token → Connections API ─────────────────────────────
//
// ⚠️  SECURITY CONSIDERATIONS:
//     1. Unlike token exchange (Hooks 1 & 2), the Connections API returns the
//        raw third-party provider token directly to the agent. If the agent
//        caches or leaks this token, it can be used to access the third-party
//        service directly — outside the MCP server's control.
//
//     2. External tokens issued by providers like Google, HubSpot, etc. are
//        NOT controlled by Descope. They may be long-lived (hours or even
//        permanent) unlike the short-lived ephemeral tokens Descope issues
//        via its /token endpoint. A leaked external token could remain valid
//        far longer than expected.
//
//     With token exchange, external tokens stay server-side inside the MCP
//     server and are never exposed to the agent. Prefer Hooks 1 or 2 when
//     the MCP server can handle token resolution internally.

export async function userConnectionsToken(
  cfg: DescopeOAuthConfig,
  userAccessToken: string,
  params: ConnectionsParams,
): Promise<TokenResult> {
  const key = cacheKey(
    "connections",
    params.appId,
    params.userId,
    userAccessToken.slice(-8),
  );
  const cached = getCached(key);
  if (cached) return cached;

  const body: Record<string, unknown> = {
    appId: params.appId,
    userId: params.userId,
  };
  if (params.tenantId) body.tenantId = params.tenantId;
  if (params.scopes) body.scopes = params.scopes;
  if (params.options) body.options = params.options;

  const json = await postJsonRaw(
    connectionsUrl(cfg),
    body,
    `${cfg.projectId}:${userAccessToken}`,
  );

  const token =
    (json as any).token ??
    (json as any).accessToken ??
    (json as any).access_token;
  const expiresIn = (json as any).expiresIn ?? (json as any).expires_in ?? 3600;

  const result: TokenResult = {
    accessToken: token as string,
    tokenType: "Bearer",
    expiresAt: new Date(Date.now() + (expiresIn as number) * 1000),
    raw: json,
  };

  return setCache(key, result);
}

// ─── Hook 4: CIBA ────────────────────────────────────────────────────────────

export async function cibaFlow(
  cfg: ClientCredentialsConfig,
  userIdentifier: { accessToken: string } | { loginHint: string },
  params: CIBAParams,
): Promise<TokenResult> {
  const pollInterval = params.pollIntervalMs ?? 2_000;
  const timeout = params.timeoutMs ?? 120_000;

  // Step 1 — Initiate backchannel authorization
  const authBody: Record<string, string | undefined> = {
    client_id: cfg.clientId,
    client_secret: cfg.clientSecret,
    scope: params.scopes,
    audience: params.audience,
    login_hint: undefined,
    login_hint_token: undefined,
    binding_message: params.bindingMessage,
  };

  if ("accessToken" in userIdentifier) {
    authBody.login_hint_token = userIdentifier.accessToken;
  } else {
    authBody.login_hint = userIdentifier.loginHint;
  }

  const authJson = await postJson(cibaAuthUrl(cfg), authBody);
  const authReqId = authJson.auth_req_id as string;
  const serverInterval =
    (authJson.interval as number) ?? Math.ceil(pollInterval / 1000);
  const effectivePollMs = Math.max(pollInterval, serverInterval * 1000);

  // Step 2 — Poll for token
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, effectivePollMs));

    try {
      const json = await postJson(tokenUrl(cfg), {
        grant_type: GRANT_TYPE.CIBA,
        auth_req_id: authReqId,
        client_id: cfg.clientId,
        client_secret: cfg.clientSecret,
      });
      return parseTokenResponse(json);
    } catch (err: any) {
      const msg = err?.message ?? "";
      if (msg.includes("authorization_pending")) continue;
      if (msg.includes("slow_down")) {
        await new Promise((r) => setTimeout(r, effectivePollMs));
        continue;
      }
      throw err;
    }
  }

  throw new Error("CIBA flow timed out waiting for user consent");
}

// ─── Unified Pre-Tool-Use Hook ───────────────────────────────────────────────

export type HookStrategy =
  | {
      type: "client_credentials_exchange";
      config: ClientCredentialsConfig;
      exchange: TokenExchangeParams;
    }
  | {
      type: "user_token_exchange";
      config: DescopeOAuthConfig;
      userAccessToken: string;
      exchange: TokenExchangeParams;
    }
  | {
      type: "connections";
      config: DescopeOAuthConfig;
      userAccessToken: string;
      connection: ConnectionsParams;
    }
  | {
      type: "ciba";
      config: ClientCredentialsConfig;
      userIdentifier: { accessToken: string } | { loginHint: string };
      ciba: CIBAParams;
    };

/**
 * Universal pre-tool-use hook.
 *
 * @example
 * ```ts
 * const token = await preToolUseHook({
 *   type: "user_token_exchange",
 *   config: { projectId: "P2abc..." },
 *   userAccessToken: session.token,
 *   exchange: {
 *     audience: "mcp-github-server",
 *     scopes: "repo:read repo:write",
 *   },
 * });
 *
 * headers["Authorization"] = `Bearer ${token.accessToken}`;
 * ```
 */
export async function preToolUseHook(
  strategy: HookStrategy,
): Promise<TokenResult> {
  switch (strategy.type) {
    case "client_credentials_exchange":
      return clientCredentialsTokenExchange(strategy.config, strategy.exchange);

    case "user_token_exchange":
      return userTokenExchange(
        strategy.config,
        strategy.userAccessToken,
        strategy.exchange,
      );

    case "connections":
      return userConnectionsToken(
        strategy.config,
        strategy.userAccessToken,
        strategy.connection,
      );

    case "ciba":
      return cibaFlow(strategy.config, strategy.userIdentifier, strategy.ciba);
  }
}

/**
 * Creates a bound hook you can call repeatedly with no arguments.
 *
 * @example
 * ```ts
 * const getToken = createPreToolHook({
 *   type: "client_credentials_exchange",
 *   config: {
 *     projectId: "P2abc...",
 *     clientId: "DS_...",
 *     clientSecret: "ds_...",
 *   },
 *   exchange: {
 *     audience: "mcp-server-github",
 *     scopes: "repo:read issues:write",
 *   },
 * });
 *
 * const { accessToken } = await getToken();
 * ```
 */
export function createPreToolHook(
  strategy: HookStrategy,
): () => Promise<TokenResult> {
  return () => preToolUseHook(strategy);
}
