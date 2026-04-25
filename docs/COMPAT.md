# Cross-Repo Compatibility Matrix

Tracks which mobile app versions are known to work against which schema
versions, and which `options-core` commits produced the schema.

Three repos are involved:

- `laiyanlong/dappgo-options-app` — the React Native mobile client
- `laiyanlong/options-daily-report` — this repo; holds the schemas and
  generated JSON artifacts
- `options-core` — the private analysis engine that writes the artifacts

| App version | Schema version | options-core commit range | Notes |
|---|---|---|---|
| 1.0.x | 1.0.0 | current | Initial launch — flat, no breaking changes |

## Bump policy

- **Schema major bump** (e.g. `1.x.x` → `2.0.0`) requires the app to ship
  a matching major bump within **30 days**. The schema's own deprecation
  window (see `schemas/VERSIONING.md`) is also 30 days — these run in
  parallel, not back-to-back.
- **App releases go out via TestFlight.** Schema changes must land in
  `options-core` and produce artifacts here at least **7 days** before
  the matching app release is submitted. This lets the contract test
  (see `.github/workflows/contract-test.yml`) prove the new app still
  parses the new artifacts before any user is exposed.
- **Patch/minor schema bumps** need no app release. Old apps keep working
  because minor bumps only add optional fields; patch bumps are purely
  editorial.

## How to record a new row

1. Tag the app release on the `dappgo-options-app` repo
2. Note the `options-core` commit SHA that first produced the new
   `schema_version` value in `dashboard/manifest.json`
3. Add a row above and move older rows down; never delete history

For the schema version policy itself, see `schemas/VERSIONING.md`.
