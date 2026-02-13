# Security Considerations

## Token Trust Boundaries

When choosing an auth strategy, the key security question is:
**where does the external provider token live?**

### Token Exchange (Strategies 1, 2, 4)

```
┌──────────┐          ┌─────────┐          ┌────────────┐
│  Agent   │ ◄──────► │ Descope │ ◄──────► │ MCP Server │
│          │  Descope │         │  Descope  │            │
│          │  token   │         │  token    │ ┌────────┐ │
│          │  (short) │         │           │ │External│ │
│          │          │         │           │ │Token   │ │
│          │          │         │           │ │(stays  │ │
│          │          │         │           │ │here)   │ │
└──────────┘          └─────────┘          │ └────────┘ │
                                           └────────────┘
```

The agent only holds a **Descope-issued token** that is:

- Short-lived (minutes, controlled by Descope)
- Scoped to specific MCP server capabilities
- Revocable by Descope

The external provider token (Google, HubSpot, etc.) stays inside
the MCP server and is never exposed to the agent.

### Connections API (Strategy 3)

```
┌──────────┐          ┌─────────┐
│  Agent   │ ◄──────► │ Descope │
│          │          │         │
│ ┌──────┐ │ External │         │
│ │Google│ │ token    │         │
│ │Token │ │ (sent to │         │
│ │      │ │  agent)  │         │
│ └──────┘ │          │         │
└──────────┘          └─────────┘
```

The agent holds the **raw third-party token** which is:

- Potentially long-lived (set by the provider, not Descope)
- Scoped to the full connection (not narrowed to MCP server needs)
- Not revocable by Descope (only the provider can revoke it)

## Token Lifetime Comparison

| Token source              | Lifetime                                        | Controlled by |
| ------------------------- | ----------------------------------------------- | ------------- |
| Descope `/token` endpoint | Minutes (configurable)                          | Descope       |
| Google OAuth              | 1 hour (access), months (refresh)               | Google        |
| HubSpot OAuth             | 30 minutes (access), 6 months (refresh)         | HubSpot       |
| GitHub OAuth              | No expiry (classic PAT), 8 hours (fine-grained) | GitHub        |
| Salesforce OAuth          | Session-based, potentially hours                | Salesforce    |

## Recommendations

1. **Use token exchange (strategies 1 or 2) whenever possible.**
   The agent never sees external tokens, and Descope controls lifetime.

2. **Use connections (strategy 3) only when the agent needs direct
   third-party API access** without an intermediary MCP server.

3. **Never log tokens.** The hook scripts write to `descope-auth.log`
   but never include token values — only metadata.

4. **Git-ignore the token cache.** The `.token-cache/` directory
   contains live tokens and must never be committed.

5. **Rotate client secrets regularly.** The `clientId` / `clientSecret`
   in the config file are long-lived credentials — treat them like
   any other secret.
