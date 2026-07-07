# Meridian brand assets

Logo files for the fictional **Meridian** company used in this demo. The mark is
a *meridian globe* — a globe crossed by a meridian line and equator, topped by
the diamond marker used across the landing page — in the Descope purple → indigo
→ pink gradient.

| File | Use |
| --- | --- |
| `logo-mark.svg` | Icon / mark only (64×64, transparent). Primary asset — font-independent, scales anywhere. Use this as the **Descope project logo**. |
| `favicon.svg` | The mark on a dark rounded tile. Browser tab / app icon, and good where a solid background reads better than a transparent mark. |
| `logo-full-dark.svg` | Horizontal lockup (mark + "Meridian") for **dark** backgrounds — e.g. the landing page. |
| `logo-full-light.svg` | Horizontal lockup for **light** backgrounds — e.g. a hosted login page. |

## Colors

- Purple `#8B5CF6` · Indigo `#6366F1` · Pink `#EC4899` (accent / diamond)
- Light purple `#A78BFA` · Dark surface `#111827` · Border `#374151`

## Fonts (wordmark)

The lockups set the wordmark in **Barlow Semi Condensed** (600), falling back to
Barlow / Arial. The landing page already loads that font, so the inline nav mark
renders exactly. For a fully self-contained lockup that renders identically with
no font installed, outline the `<text>` to paths in your vector editor.

## Using it as the Descope project logo

The project `P3GC1znDUdJvIpvZLDdUTMk08nMk` wasn't reachable from the account this
session's Descope MCP is authenticated as, so these files weren't uploaded for
you. To apply the logo yourself:

1. In the [Descope Console](https://app.descope.com), open the target project.
2. **Project branding / theme:** Settings → Project → Branding (or the Flows
   theme editor) → upload `logo-mark.svg` (or `favicon.svg`) as the logo.
3. **Hosted login / Flows:** in the Flow editor's theme/branding panel, set the
   logo image to `logo-mark.svg`; use `logo-full-light.svg` anywhere a full
   wordmark fits on a light background.

SVG is accepted for most logo slots; if a slot requires PNG, export at 512×512
(mark) or 2× the display size (lockups) from any vector tool or a browser.
