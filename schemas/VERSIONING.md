# Schema Versioning Policy

Every schema in this directory is tagged with a **semver string** via the
`$comment` field (there's no native semver slot in JSON Schema) or an
explicit `$schemaVersion` extension. Consumers must check it and refuse
to parse data produced under a major version they don't understand.

## Current state (2026-04-22)

| Schema | Version | Used by |
|---|---|---|
| `data.schema.json` | 1.0.0 | Mobile app Dashboard/Matrix, web viewer |
| `weekly_summary.schema.json` | 1.0.0 | Mobile app Weekly Summary screen |
| `ai_commentary.schema.json` | 1.0.0 | Mobile app Reports, dappgo.com/options |
| `manifest.schema.json` | 1.0.0 | Mobile app startup listing |

## Rules

**Patch bump (1.0.0 → 1.0.1)** — purely clarifying (descriptions, examples).
No behavioural change. No consumer update needed.

**Minor bump (1.0.0 → 1.1.0)** — add optional field, relax a constraint.
Old consumers keep working; new ones can opt in to the new field.

**Major bump (1.0.0 → 2.0.0)** — remove a required field, rename anything,
tighten a type. Create `data.v2.schema.json` alongside `data.v1.schema.json`
and give consumers a deprecation window of **≥ 30 days** before removing
v1 files.

## Publishing a breaking change

1. Copy `xx.schema.json` → `xx.v1.schema.json` (freeze v1 at current)
2. Edit `xx.schema.json` in place with the new shape, bump `$schemaVersion` to `2.0.0`
3. Write `docs/MIGRATION_v1_v2.md` with before/after examples
4. Update `manifest.json` writer to record `schema_version: "2.0.0"`
5. Announce in the repo's Releases page with "breaking" tag
6. Hold 30+ days; log v1 consumer count (User-Agent hit rate from Cloudflare)
7. Delete `xx.v1.schema.json`

## Manifest signalling

`manifest.json.schema_version` reflects the **data.schema.json** version.
When the app starts, it reads manifest first; if the major version is
higher than what it supports, it shows an "App needs update" banner
instead of crashing on unknown fields.
