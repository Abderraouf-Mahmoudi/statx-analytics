# StatX Player Media and Tunisian Club Sync — Design

## Intent

Transform the Release 1 roster from a manually populated list into a club-first workspace. Immediately after the administrator account is created, the administrator selects a Tunisian club, imports its current squad and recent competition data from API-Football, and lands on a visual roster of player cards. StatX must still support manual players and club-owned corrections because provider coverage can be incomplete or delayed.

Every player can receive a portrait from the device camera, the tablet gallery, or the configured provider. StatX processes the portrait locally, removes its background, stores an original plus a transparent cutout, and presents the player as a touch-friendly branded card.

## Goals

- Select a Tunisian club during the post-account onboarding wizard.
- Import the club, current squad, player portraits, fixtures, results and standings using a quota-conscious provider adapter.
- Keep API credentials on the backend only and never expose them to the browser, logs, database exports, source control or generated reports.
- Cache imported data in SQLite so the application remains usable without Internet.
- Preserve manual player creation, local corrections and club-specific players.
- Capture a portrait from the tablet camera or gallery.
- Remove the background locally and produce an optimized transparent PNG.
- Replace the roster list with responsive player cards inspired by the supplied shield-card reference without copying that artwork literally.
- Show provenance and synchronization state for every imported or locally entered player.

## Non-goals

- Treat API-Football as an authoritative legal source for image publication rights.
- Automatically merge players by name.
- Synchronize every Tunisian competition or club on every page load.
- Spend requests on individual player statistics during initial onboarding.
- Remove the manual workflow.
- Perform image inference on the tablet; processing runs on the local StatX backend hosted by the club PC.

## Anti-goals

- Committing the API key or returning it in any frontend response.
- Calling the provider directly from React.
- Re-downloading the complete squad on each navigation.
- Overwriting a club-edited portrait or identity field during synchronization.
- Publishing an imported player portrait when its rights/consent status is unknown.
- Blocking player creation when the provider is unavailable or the daily quota is exhausted.

## Constraints

- API-Football free plan: 100 calls per day.
- Tunisia coverage and individual feature coverage vary by competition and season.
- Provider images are identification assets; publication rights remain the club's responsibility.
- Background removal must work locally after the segmentation model has been installed once.
- Tablet touch targets remain at least 48 px and the grid must work at 1024 × 768 and portrait widths.
- The existing organization isolation, RBAC, CSRF and consent rules remain binding.

## Approaches considered

### A. API-only roster

Fastest initial setup, but fails for academy/reserve players, transfers not yet synchronized, incomplete Tunisian coverage and provider outages. It also makes StatX dependent on a third party for the club's core roster. Rejected.

### B. Hybrid provider sync plus manual ownership — selected

API-Football seeds the organization and refreshes provider-owned facts. Manual creation remains available, local edits have precedence, imported records retain provenance and all operational data is cached locally. This satisfies fast onboarding without surrendering club ownership or offline operation.

### C. Manual roster plus CSV import

Cheapest and legally simplest, but does not deliver the requested team selection, photos, results or automatic refresh. Retained as a future bulk fallback, not the primary path.

## External provider boundary

Create an `ApiFootballClient` behind a provider protocol. Only the backend knows:

- `API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io`
- `API_FOOTBALL_KEY` as a secret setting
- connection/read timeouts
- internal daily request ceiling, default 90 to preserve 10 emergency calls

The client sends `x-apisports-key`, validates provider envelopes and captures quota headers when present. It never logs request headers or the key. HTTP failures become typed integration errors and never partially commit a synchronization run.

A persistent per-day counter and a database-backed refresh lock prevent concurrent tablets from spending the same quota twice. Cached requests are keyed by provider endpoint plus normalized parameters. The provider's remaining-quota header wins when available; otherwise StatX applies its own conservative counter.

### Quota-conscious initial workflow

1. Load Tunisia's current competitions from a local cache; refresh through `/leagues?country=Tunisia&current=true` only when stale.
2. Load teams for the selected league/season once.
3. Import the selected club's current squad with one `/players/squads?team={id}` call.
4. Import current-season fixtures/results with one filtered fixtures call.
5. Import standings with one standings call when the league reports that coverage.

The expected initial synchronization is approximately five provider calls. Club and squad caches live for seven days; fixtures/results use a shorter explicit refresh policy. No provider call occurs merely because a user opens a screen. The squad endpoint supplies the fast current-roster profile; optional height, weight, birth date and season statistics are enriched later through paginated player-statistics calls only when requested and when quota permits.

## Data model

### Organization and team selection

- Add a nullable `primary_team_id` to `organizations` after the selected provider team has been imported.
- Keep `teams` organization-scoped.
- Add provider provenance fields to teams: `source`, `provider`, `provider_id`, `provider_updated_at`, `logo_source_url`, `logo_local_path`.
- Enforce a unique provider identity per organization.

### Player identity

Add to `players`:

- `source`: `manual | api_football | club`
- `provider`: nullable
- `provider_id`: nullable string
- `provider_updated_at`: nullable timestamp
- `nationality`, `height_cm`, `weight_kg`: nullable provider facts
- `provider_photo_url`: nullable
- `local_override`: boolean, preventing synchronization from replacing club-owned identity fields

Provider IDs, not names, drive upserts. A manual record can later be explicitly linked by an administrator; StatX never performs a destructive name-based merge.

### Player media

Create `player_photos`:

- `id`, `public_id`, `player_id`
- `source`: `camera | gallery | api_football`
- `original_path`, `cutout_path`
- `mime_type`, `sha256`, `width`, `height`
- `processing_status`: `pending | ready | failed`
- `rights_status`: `unknown | club_authorized | provider_identification_only`
- `created_at`, `processed_at`

Only relative paths are stored. Files live under `data/player_photos/{organization_public_id}/{player_public_id}/`. Originals are private; processed cutouts are exposed through an authenticated media endpoint, not a public static directory.

### Synchronization records

Create `provider_sync_runs` with organization/team/provider, start/end timestamps, status, call count, remaining quota when known, error summary and a sanitized result summary. This supports diagnostics without retaining secrets or oversized raw responses.

## Image workflow

React presents two explicit touch actions:

- **Prendre une photo**: file input with `accept="image/*"` and `capture="user"`.
- **Choisir dans la galerie**: file input with `accept="image/jpeg,image/png,image/webp"` and no capture hint.

The browser shows a local preview before upload. The backend:

1. accepts JPEG, PNG or WebP up to 10 MB;
2. decodes the image with Pillow, applies EXIF orientation, strips metadata and rejects decompression bombs;
3. normalizes size and color space;
4. stores a content-hashed original;
5. uses `rembg` with a portrait/human segmentation model and a reused inference session;
6. crops/pads the cutout into a consistent card portrait canvas;
7. stores an optimized transparent PNG;
8. lets the user accept the cutout, retry with a different image, or keep the original when segmentation is poor.

The segmentation model is downloaded during installation or an explicit administrator preparation step, never unexpectedly during a match workflow.

The media inference stack is isolated in `requirements-media.txt` so ordinary API development does not reinstall the large ONNX dependencies. The installation command prepares the selected model under `DATA_ROOT/models`, which is included in operational backups when offline reinstallation is required.

## API surface

All routes are under `/api/v1` and preserve current RBAC/CSRF behavior.

- `GET /integrations/api-football/status` — configured state, cache age and quota information; never the key.
- `GET /integrations/api-football/tunisia/clubs` — cached selectable clubs and competition/season metadata.
- `POST /integrations/api-football/select-club` — admin-only selection and initial sync; the organization is derived exclusively from the current actor.
- `POST /integrations/api-football/sync` — explicit admin refresh for the selected club.
- `GET /integrations/api-football/sync-runs/{id}` — progress/result summary.
- `POST /players/{player_id}/photo` — multipart upload and local processing.
- `GET /players/{player_id}/photo` — authenticated processed portrait response with ETag.
- `DELETE /players/{player_id}/photo` — removes the current club-owned portrait and audit-logs the action.

Long-running photo processing and provider synchronization use persisted job status rather than FastAPI in-memory `BackgroundTasks`, so failures and restarts are visible and recoverable.

## Onboarding and frontend experience

The existing first-run organization/admin form remains atomic. Immediately after it succeeds, the authenticated wizard opens a **Choisir votre club** step:

1. show cached Tunisia competitions and clubs;
2. search by club name;
3. preview club crest, competition and season;
4. confirm selection;
5. display synchronization progress and exact imported counts;
6. allow **Continuer sans import** when the provider is unavailable.

The roster becomes a card grid:

- 4 columns on wide desktop, 3 around tablet landscape, 2 in portrait and 1 on narrow phones;
- shield-inspired dark card with an original StatX geometry and emerald outline;
- large transparent cutout, player number, full name, position and preferred foot;
- badges for `API`, `Club`, `Manuel`, consent/publication and sync freshness;
- touch action to open the existing player detail/consent workspace;
- skeleton, empty, stale-cache, quota-exhausted and synchronization-conflict states.

The card never presents provider data as club-verified. Imported facts remain visually distinguishable until reviewed.

## Synchronization rules

- Provider IDs are immutable external references.
- New provider players are created and registered in the selected current season.
- Existing provider-linked players are updated only in non-overridden provider fields.
- Missing players are marked `provider_absent`; they are not deleted or silently unregistered.
- A squad refresh never revokes consent, deletes media or changes a club-entered registration.
- Photos uploaded by the club take precedence over provider photos.
- Every sync is one database transaction after the complete remote payload has been validated.

## Security and privacy

- The supplied API key is stored only in ignored `backend/.env` and should be rotated after development because it was shared in a chat message.
- Provider calls are server-to-server with strict hostname allowlisting and timeouts.
- Image contents are validated by decoding, not trusted from filename or `Content-Type` alone.
- EXIF metadata is stripped to remove device/location information.
- Photo access is organization-scoped and authenticated.
- Consent and rights badges are independent: a player can have consent while a provider image remains identification-only.
- Upload, deletion, provider link and synchronization actions are audit logged.

## Failure handling

- Missing key: manual workflows remain available and UI shows integration disabled.
- Provider timeout/error: retain cached data, report staleness and allow retry.
- Quota below safety reserve: block nonessential refreshes and show next reset information when available.
- Partial/invalid provider response: roll back the entire sync.
- Background-removal failure: preserve the validated original, mark processing failed and allow retry/fallback.
- Duplicate provider identity: fail with a visible conflict; never guess a merge.

## Verification and acceptance

- Migration preserves every existing organization, team, player, registration and consent.
- No API key appears in frontend bundles, logs, API responses, commits or test snapshots.
- A selected Tunisian club imports using a bounded number of provider calls and remains visible with the provider offline.
- Re-running the same squad sync is idempotent and creates no duplicate players.
- Local player edits and club-uploaded photos survive synchronization.
- Camera and gallery inputs work at tablet dimensions.
- JPEG/PNG/WebP validation, size limits, EXIF stripping and cross-organization access are tested.
- Background removal produces a transparent PNG and failure leaves the original recoverable.
- Roster cards meet 48 px touch requirements, portrait/landscape layouts and RTL direction rules.
- Manual player creation remains fully operational with no provider key or Internet connection.
