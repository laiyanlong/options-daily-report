# Inline Highlight Markers — Spec

Single source of truth for the `[[type:text]]` markers used in AI
commentary. Any change here must be mirrored in all four consumers:

| Repo | File | What it does |
|---|---|---|
| `options-core` | `prompts/ai_commentary_v1.{zh,en}.md` | Tells Gemini how to sprinkle markers |
| `options-core` | `ai_analysis.py` (`_MARKER_RE`) | Strips markers for plain-text email/markdown |
| `dappgo-options-app` | `src/utils/highlight-markers.ts` (`MARKER_RX`) | Renders pills/underlines in React Native |
| `dappgo-website` | `options.html` (regex in script) | Renders pills/underlines on the web |

## Regex (authoritative)

```regex
\[\[(pos|neg|key|warn|u):([^\]\r\n]{1,120})\]\]
```

Notes:
- Case-sensitive. Variant names are always lowercase.
- Body (capture group 2) is 1–120 characters, no `]`, no newlines.
- Not nested. Two adjacent markers render as two adjacent pills.

## Variants

| Marker | Meaning | Web / Mobile rendering |
|---|---|---|
| `[[pos:text]]` | Positive / bullish signal, opportunity | Green pill, white text |
| `[[neg:text]]` | Negative / bearish signal, clear loss | Red pill, white text |
| `[[key:text]]` | Key number / price level / stat worth emphasis | Gold pill, dark text |
| `[[warn:text]]` | Caution, risk, must-notice caveat | Amber pill, dark text |
| `[[u:text]]` | Underline emphasis (no background) | Accent-coloured underline, bold |

## Body rules for Gemini prompts

- 1–8 words per marker
- No line breaks, no nested markers
- Use at most ~8 markers per commentary
- Prefer directional colour (pos/neg/key/warn) over `u` when the meaning
  has a clear direction
- Never wrap entire headings, sentences, or the disclaimer

## Stripping for plain-text contexts

Email HTML, `.md` file previews, and GitHub renderers don't support
these markers. Consumers must strip them to plain text:

- **Bold style** (default): `[[pos:text]]` → `**text**` (markdown bold)
- **Plain style**: `[[pos:text]]` → `text`

Python (`ai_analysis.py`):
```python
_MARKER_RE.sub(r"**\2**", text)   # bold
_MARKER_RE.sub(r"\2", text)       # plain
```

JavaScript / TypeScript (`highlight-markers.ts`):
```ts
text.replace(MARKER_RX, (_m, _t, body) => body);   // plain
```

## Version

Current spec version: **1.0** (2026-04-22). If a new variant is added or
the regex shape changes, bump this and update all four consumers in a
single coordinated release window.
