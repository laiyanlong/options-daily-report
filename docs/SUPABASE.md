# Supabase architecture (Phase 0)

Cross-repo doc — kept here in the public data repo because all three
repos read or write it. **Last updated**: 2026-04-25.

## What's there

A single Supabase project (`dappgo-options`, region: `East US`) holds:

| Table / View       | Type         | Written by             | Read by                                         |
|--------------------|--------------|------------------------|-------------------------------------------------|
| `events`           | table        | mobile app (anon)      | admin via SQL editor                            |
| `option_taps`      | table        | mobile app (anon)      | feeds `popular_options` view                    |
| `popular_options`  | matview      | scheduled cron         | mobile app, dashboard, marketing site, engine   |

Schema source: `dappgo-options-app/supabase/migrations/001_phase0_anonymous.sql`

## Who can do what

| Role             | Where it lives          | Capabilities                                |
|------------------|-------------------------|---------------------------------------------|
| `anon` (public)  | App + websites + engine | `INSERT` events / option_taps; `SELECT` popular_options |
| `authenticated`  | (Phase 1+)              | TBD when Apple Sign-In lands                |
| `service_role`   | Edge functions only     | Bypasses RLS — never embed in any client    |

The publishable key (`sb_publishable_…`) is **safe** to commit to public
repos and ship to mobile devices. RLS is the security layer; the key is
just the connection identifier.

## Each repo's relationship

### `dappgo-options-app` (private — primary writer)
- Generates `device_id` UUID at first launch (stored in iOS Keychain)
- Every `trackEvent()` writes to `events` (fire-and-forget, non-blocking)
- Matrix strike taps write to `option_taps`
- Dashboard "🔥 Hot Strikes" widget reads `popular_options`
- Env vars: `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_ANON_KEY`
  in `.env.local` (gitignored)

### `options-core` (private — analytical reader)
- `pipeline/popular_options.py` fetches `popular_options` and renders a
  markdown section appended to the daily report
- Workflow secrets: `SUPABASE_URL`, `SUPABASE_ANON_KEY`
- Section is silently skipped when secrets aren't set or the view is empty

### `options-daily-report` (public — passive reader)
- `dashboard/index.html` shows a "Hot Strikes" panel below AI Commentary
- URL + anon key are inlined in the HTML — public-safe by design

### `dappgo-website` (public — marketing reader)
- `options.html` shows a "Hot Strikes" section below the AI Commentary
  card as social proof
- Connects to Supabase via fetch; CSP `connect-src` whitelists the
  project URL

## Cron schedule

`refresh_popular_options()` runs every 30 min via `pg_cron`:
```sql
SELECT cron.schedule(
  'refresh-popular-options',
  '*/30 * * * *',
  $$SELECT refresh_popular_options()$$
);
```

Manual refresh:
```sql
SELECT refresh_popular_options();
```

## Phase 1 migration (planned)

When Apple Sign-In lands:
- `auth.users` table populated by Supabase Auth
- `events.user_id` + `option_taps.user_id` columns get filled via
  `claim-device` Edge function on login
- New `user_devices` join table linking historical anonymous data
- New RLS policies: authenticated users can `SELECT` their own rows

No Phase 0 schema changes required — the `user_id` column exists but
is NULL today.

## Cost reference

Free tier limits:
- Storage: 500 MB (Phase 0 typical use ~5 MB / month)
- Egress: 5 GB / month (typical use ~10 MB / month)
- API: unlimited
- MAU: 50K (Phase 0 has zero authenticated users)

At 100× current scale you're still under the storage limit. See
[`SECRETS.md`](https://github.com/laiyanlong/options-core/blob/main/docs/SECRETS.md) (private repo) for key rotation steps when ready.
