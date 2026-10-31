# Player Media and Tunisian Club Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a StatX administrator select a Tunisian club, import and refresh its operational roster safely within the API-Football quota, and manage touch-friendly player cards with locally processed portraits from camera or gallery.

**Architecture:** Keep API-Football behind a backend-only adapter with typed errors, persistent cache/quota records, and organization-scoped transactional upserts. Run provider sync and portrait segmentation as persisted, restart-recoverable jobs observed by the API; React only polls sanitized job state and reads cached SQLite data. Preserve the current manual roster path and make club-owned edits and photos override provider facts.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, SQLite, httpx, Pillow, rembg/ONNX Runtime, Pydantic Settings, React 19, TypeScript, TanStack Query, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-31-player-media-provider-sync-design.md`

## Global Constraints

- API-Football free plan is limited to 100 calls per day; StatX's configurable default ceiling is 90.
- The API key stays in ignored `backend/.env`; it must never reach frontend code, responses, logs, database snapshots, reports, fixtures, or commits.
- All provider and media routes use `/api/v1`, current session authentication, CSRF enforcement, RBAC, organization isolation, and audit logging.
- Initial club synchronization uses at most five provider calls: current Tunisia leagues, teams, squad, fixtures, and standings when covered.
- Provider IDs drive idempotent upserts; names never trigger automatic merges.
- Club-owned identity edits, registrations, consent records, and uploaded portraits survive every refresh.
- Missing provider players become `provider_absent`; they are never deleted automatically.
- JPEG, PNG, and WebP uploads are limited to 10 MiB, decoded rather than trusted by extension, EXIF-oriented, metadata-stripped, and stored as relative paths.
- The processed player cutout is a transparent PNG; failed segmentation retains the validated original and exposes retry/fallback actions.
- Touch targets remain at least 48 px; the card grid supports 1024 × 768 landscape, tablet portrait, narrow phone, French, and Arabic RTL.
- Manual player creation continues to work with no provider key and no Internet connection.

## Review Focus

- Two administrators start a refresh simultaneously: only one lease spends quota and both clients receive a stable, observable run state; covered in Task 3 concurrency tests.
- A provider payload is truncated, malformed, or contains duplicate external IDs: the run fails atomically without partial roster changes; covered in Task 3 transaction tests.
- A forged upload contains invalid bytes/excessive dimensions/EXIF GPS, or a provider portrait redirects outside the approved media host: reject or sanitize it without unsafe files while keeping the player usable; covered in Task 4 processor and service tests.
- An authenticated user requests another organization's portrait or sync run: return the same not-found response used for absent resources and reveal no metadata; covered in Tasks 3 and 4 API tests.
- A refresh occurs after a club user edits a player or uploads a portrait: provider facts update only where permitted and the local override remains authoritative; covered in Tasks 3, 4, and 6 tests.

---

### Task 1: Provider-aware persistence and configuration

**Files:**
- Create: `backend/alembic/versions/20261031_02_player_media_provider_sync.py`
- Create: `backend/app/modules/integrations/__init__.py`
- Create: `backend/app/modules/integrations/models.py`
- Create: `backend/app/modules/media/__init__.py`
- Create: `backend/app/modules/media/models.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/modules/organizations/models.py`
- Modify: `backend/app/modules/matches/models.py`
- Modify: `backend/app/modules/roster/models.py`
- Modify: `backend/app/db/model_registry.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/migrations/test_player_media_provider_migration.py`
- Test: `backend/tests/test_database_config.py`

**Interfaces:**
- Consumes: Existing `Base`, organization/team/player IDs, Alembic revision `20261030_01`, and `Settings` loading from `backend/.env`.
- Produces: `Settings.api_football_key: SecretStr | None`, `api_football_base_url`, timeout/cache/ceiling settings, media limits/model settings; ORM models `ProviderCacheEntry`, `ProviderQuotaDay`, `ProviderSyncLease`, `ProviderSyncRun`, `ProviderStandingSnapshot`, and `PlayerPhoto`; provider/provenance columns on `Organization`, `Season`, `Team`, `Player`, and `Match`.

- [ ] **Step 1: Write migration and settings tests that fail before the new schema exists**

  Assert upgrade from both an empty and Release 1 database; existing rows remain; `organizations.primary_team_id`, season/team/player/match provider fields, `player_photos`, standings-snapshot, cache/quota/lease/sync-run tables, indexes, foreign keys, checks, and per-organization provider uniqueness exist. Assert a secret loaded from environment is a `SecretStr`, default ceiling is `90`, upload limit is `10 * 1024 * 1024`, and serialized settings never expose the secret value.

- [ ] **Step 2: Run the focused tests and confirm the expected missing-column/model failures**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/migrations/test_player_media_provider_migration.py backend/tests/test_database_config.py -q`

  Expected: FAIL because the revision and settings do not exist.

- [ ] **Step 3: Add the migration and focused ORM models**

  Define provenance values as checked strings (`manual`, `api_football`, `club`), photo status (`pending`, `processing`, `ready`, `failed`) and rights status (`unknown`, `club_authorized`, `provider_identification_only`). Store only relative media paths. Make provider identity unique on `(organization_id, provider, provider_id)` and change team-name uniqueness from global to organization scope without losing Release 1 data.

- [ ] **Step 4: Add validated backend-only settings**

  Use `SecretStr` for `API_FOOTBALL_KEY`; allow only the exact HTTPS API-Football host and explicit provider-media hosts; add connect/read timeout, daily ceiling `90`, cache TTLs, maximum upload bytes, maximum decoded pixels, media model name, and worker polling interval. Document placeholders only in `.env.example`.

- [ ] **Step 5: Run migration and settings tests**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/migrations/test_player_media_provider_migration.py backend/tests/test_database_config.py -q`

  Expected: PASS.

- [ ] **Step 6: Commit the approved spec and persistence slice**

  Run: `git add docs/superpowers/specs/2026-10-31-player-media-provider-sync-design.md docs/superpowers/plans/2026-10-31-player-media-provider-sync-implementation.md backend/alembic/versions/20261031_02_player_media_provider_sync.py backend/app/config.py backend/app/db/model_registry.py backend/app/modules/integrations backend/app/modules/media backend/app/modules/organizations/models.py backend/app/modules/matches/models.py backend/app/modules/roster/models.py backend/.env.example backend/tests/migrations/test_player_media_provider_migration.py backend/tests/test_database_config.py`

  Run: `git commit -m "feat: add provider and player media persistence"`

### Task 2: Quota-safe API-Football adapter and persistent cache

**Files:**
- Create: `backend/app/modules/integrations/api_football.py`
- Create: `backend/app/modules/integrations/repository.py`
- Create: `backend/app/modules/integrations/schemas.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/modules/integrations/test_api_football_client.py`
- Test: `backend/tests/modules/integrations/test_provider_repository.py`

**Interfaces:**
- Consumes: `Settings` and persistence records from Task 1.
- Produces: `ApiFootballClient.get(path: str, params: Mapping[str, Scalar]) -> ProviderEnvelope`, `ProviderRepository.cached_request(...)`, `QuotaSnapshot`, `IntegrationDisabled`, `ProviderUnavailable`, `QuotaReserved`, and sanitized provider DTOs for leagues, clubs, squad, fixtures, and standings.

- [ ] **Step 1: Write failing adapter contract tests with an injected `httpx.MockTransport`**

  Test exact base host, `x-apisports-key` presence at transport boundary, normalized query parameters, envelope validation, timeout and 4xx/5xx mapping, quota-header parsing, and redacted exception/log representations. Add a source scan assertion that the supplied secret value cannot appear in API responses or captured logs.

- [ ] **Step 2: Run adapter tests and verify they fail because the client is absent**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/modules/integrations/test_api_football_client.py -q`

  Expected: FAIL on import.

- [ ] **Step 3: Implement the minimal typed client and response parsers**

  Add `httpx>=0.28,<1` and inject the transport/client in tests. Never include headers in exceptions. Reject redirects and any hostname other than `v3.football.api-sports.io`.

- [ ] **Step 4: Write failing repository tests for TTL cache, persistent daily quota, and reserve behavior**

  Verify cache hits consume zero calls, stale entries refresh once, counters survive repository recreation, provider remaining headers override the conservative local value, and call 91 is blocked when the ceiling is 90.

- [ ] **Step 5: Implement `ProviderRepository.cached_request` and atomic quota accounting**

  Use endpoint plus canonical JSON parameters as the cache key. Increment quota in the same short SQLite transaction that reserves a call; store only sanitized response JSON and hashes, never headers or credentials.

- [ ] **Step 6: Run both provider test modules**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/modules/integrations/test_api_football_client.py backend/tests/modules/integrations/test_provider_repository.py -q`

  Expected: PASS.

- [ ] **Step 7: Commit the provider boundary**

  Run: `git add backend/app/modules/integrations backend/requirements.txt backend/tests/modules/integrations`

  Run: `git commit -m "feat: add quota-safe api football client"`

### Task 3: Transactional club synchronization and observable jobs

**Files:**
- Create: `backend/app/modules/integrations/service.py`
- Create: `backend/app/modules/integrations/router.py`
- Create: `backend/app/modules/integrations/worker.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/modules/matches/models.py`
- Modify: `backend/app/modules/organizations/models.py`
- Modify: `backend/app/modules/roster/schemas.py`
- Modify: `backend/app/modules/roster/service.py`
- Test: `backend/tests/modules/integrations/test_club_sync_service.py`
- Test: `backend/tests/api/v1/test_api_football_integration.py`
- Test: `backend/tests/api/v1/test_api_football_sync_security.py`

**Interfaces:**
- Consumes: Adapter/repository DTOs and errors from Task 2; current `Actor`, RBAC, audit, Team/Season/Player/Registration/Match models.
- Produces: `ClubSyncService.queue_initial_sync(actor, command) -> ProviderSyncRun`, `execute_run(run_public_id: str) -> SyncSummary`, `run_pending_syncs_once() -> int`; endpoints `GET /integrations/api-football/status`, `GET /integrations/api-football/tunisia/clubs`, `POST /integrations/api-football/select-club`, `POST /integrations/api-football/sync`, and `GET /integrations/api-football/sync-runs/{run_id}`.

- [ ] **Step 1: Write failing service tests for a five-call initial import and idempotent refresh**

  Use recorded synthetic provider envelopes, not live Internet. Assert one club, current season, squad registrations, provider portrait URLs, fixtures/results, and standings snapshot are persisted; a second identical run creates no duplicates; missing squad members become `provider_absent`; and local overrides remain unchanged.

- [ ] **Step 2: Add atomicity and concurrency failure tests**

  Assert malformed/duplicate provider identities roll back all domain changes, two queued refreshes acquire one database lease, stale leases can be recovered, and a failed/restarted worker leaves a visible retryable run rather than a false success.

- [ ] **Step 3: Run service tests and verify missing service failures**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/modules/integrations/test_club_sync_service.py -q`

  Expected: FAIL on import.

- [ ] **Step 4: Implement validation-first transactional upserts and the durable polling worker**

  Fetch and validate the complete remote set before opening the domain transaction. Upsert exclusively by provider ID, set `Organization.primary_team_id`, create the current `TeamSeason`, and write a sanitized `SyncSummary` with imported/updated/absent counts. The lifespan worker claims persisted queued runs through leases and resumes abandoned runs after the configured timeout; do not use `BackgroundTasks`.

- [ ] **Step 5: Write failing API tests for RBAC, CSRF, organization scoping, offline cache, and sanitized status**

  Admin can select/refresh; reader roles can read status but cannot mutate. Cross-organization run IDs return 404. Missing key returns `configured: false` and keeps manual routes usable. Provider outage returns cached clubs with `stale: true`. No response contains a key or secret representation.

- [ ] **Step 6: Implement integration schemas and routes, then compose them under `/api/v1`**

  Mutation responses return HTTP 202 plus `run_id`, `status`, and polling URL. The status route returns only configured state, cache timestamps, safe quota counts, selected team, and last-run summary.

- [ ] **Step 7: Run service and API integration tests**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/modules/integrations/test_club_sync_service.py backend/tests/api/v1/test_api_football_integration.py backend/tests/api/v1/test_api_football_sync_security.py -q`

  Expected: PASS.

- [ ] **Step 8: Commit synchronization**

  Run: `git add backend/app/modules/integrations backend/app/api/v1/router.py backend/app/main.py backend/app/modules/matches/models.py backend/app/modules/organizations/models.py backend/app/modules/roster backend/tests/modules/integrations backend/tests/api/v1/test_api_football_integration.py backend/tests/api/v1/test_api_football_sync_security.py`

  Run: `git commit -m "feat: synchronize tunisian club data"`

### Task 4: Secure player portrait processing and media API

**Files:**
- Create: `backend/requirements-media.txt`
- Create: `backend/app/modules/media/image_processor.py`
- Create: `backend/app/modules/media/service.py`
- Create: `backend/app/modules/media/router.py`
- Create: `backend/app/modules/media/worker.py`
- Create: `backend/scripts/prepare_media_model.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/modules/roster/schemas.py`
- Modify: `backend/app/modules/roster/service.py`
- Test: `backend/tests/modules/media/test_image_processor.py`
- Test: `backend/tests/modules/media/test_media_service.py`
- Test: `backend/tests/api/v1/test_player_photos.py`

**Interfaces:**
- Consumes: `PlayerPhoto`, organization/player scope, audit writer, data-root settings, and persisted worker lifecycle from Task 3.
- Produces: `ImageProcessor.validate_and_normalize(source: BinaryIO) -> NormalizedImage`, `remove_background(image: NormalizedImage) -> ProcessedPortrait`, `queue_photo(...) -> PlayerPhoto`, `queue_provider_portrait(player_id: int, url: str) -> PlayerPhoto`, `run_pending_photos_once() -> int`; `POST`, `GET`, and `DELETE /players/{player_id}/photo` plus retry/fallback commands.

- [ ] **Step 1: Write failing pure processor tests**

  Cover valid JPEG/PNG/WebP, bad bytes with a valid filename, 10 MiB boundary, decompression-bomb pixel limit, EXIF rotation, GPS/metadata removal, RGB normalization, transparent output, deterministic crop/pad canvas, and mocked rembg failure retaining the normalized original.

- [ ] **Step 2: Run processor tests and verify they fail on missing implementation**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/modules/media/test_image_processor.py -q`

  Expected: FAIL on import.

- [ ] **Step 3: Implement validation/normalization with Pillow and segmentation behind a protocol**

  Put Pillow in base requirements and `rembg`, `onnxruntime` in `requirements-media.txt`. Reuse one portrait-model session per process. Write to a unique temporary file, fsync, then atomically replace the final file; on Windows, close every handle before replace. Hash content and store `original` and `cutout` under `data/player_photos/{organization_public_id}/{player_public_id}/`.

- [ ] **Step 4: Write failing service and API tests**

  Assert queued → processing → ready/failed transitions survive service recreation, club upload overrides provider media, original remains recoverable on failure, ETag/304 works, delete is audited, unauthorized roles cannot mutate, and cross-organization reads return 404. Test provider portrait ingestion with strict HTTPS/media-host allowlisting, redirects disabled, streamed byte limits, `provider_identification_only` rights, and no failure of the player import when the portrait cannot be downloaded.

- [ ] **Step 5: Implement media service, worker claim/recovery, and authenticated streaming routes**

  Upload returns HTTP 202 with photo status. GET returns cutout when ready and an explicit authorized original fallback only after user confirmation. DELETE removes database association first and schedules safe file cleanup; never accept a client-supplied path. After a successful squad sync, enqueue provider portraits only for players without a club-owned photo; the media worker downloads and processes them independently so a CDN failure cannot roll back roster data.

- [ ] **Step 6: Add the explicit model preparation script**

  `backend/.venv/Scripts/python.exe backend/scripts/prepare_media_model.py` downloads/warms the configured human-segmentation model into `DATA_ROOT/models` and exits nonzero with actionable diagnostics if preparation fails. It must not run implicitly during match workflows.

- [ ] **Step 7: Run all media tests**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/modules/media backend/tests/api/v1/test_player_photos.py -q`

  Expected: PASS.

- [ ] **Step 8: Commit portrait processing**

  Run: `git add backend/requirements.txt backend/requirements-media.txt backend/scripts/prepare_media_model.py backend/app/modules/media backend/app/api/v1/router.py backend/app/main.py backend/app/modules/roster backend/tests/modules/media backend/tests/api/v1/test_player_photos.py`

  Run: `git commit -m "feat: process secure player portraits"`

### Task 5: Post-account Tunisian club onboarding

**Files:**
- Create: `frontend/src/features/integrations/apiFootballApi.ts`
- Create: `frontend/src/features/onboarding/ClubSelectionPage.tsx`
- Create: `frontend/src/features/onboarding/ClubSelectionPage.test.tsx`
- Create: `frontend/src/features/onboarding/SyncProgress.tsx`
- Modify: `frontend/src/features/auth/SessionGate.tsx`
- Modify: `frontend/src/features/setup/SetupPage.tsx`
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/locales/fr.json`
- Modify: `frontend/src/locales/ar.json`

**Interfaces:**
- Consumes: Task 3 status, clubs, selection, and sync-run APIs; existing authenticated session and request helper.
- Produces: `getIntegrationStatus`, `getTunisianClubs`, `selectClub`, `getSyncRun`, `refreshClub`; onboarding state `checking | choose | syncing | ready | manual` and a touch-first club selector.

- [ ] **Step 1: Write failing component tests for the onboarding state machine**

  Test cached club search, crest/league/season preview, confirmation, 202 polling through success/failure, exact imported counts, retry, quota-disabled state, and **Continuer sans import**. Assert setup credentials are never resubmitted and the API key never appears in props, storage, or rendered DOM.

- [ ] **Step 2: Run the focused frontend test**

  Run: `npm.cmd run test:run -- src/features/onboarding/ClubSelectionPage.test.tsx`

  Working directory: `frontend`

  Expected: FAIL because the page is absent.

- [ ] **Step 3: Implement typed integration API calls and the selection/progress UI**

  After atomic setup returns an authenticated session, `SessionGate` checks integration status and opens club selection when `primary_team` is absent. Never call the provider from React. Poll only a queued run; stop polling on terminal state or unmount.

- [ ] **Step 4: Add French and Arabic copy with accessible status announcements**

  Use visible stale-cache, offline, quota, failed-run, and manual-continuation messages. Preserve logical CSS properties and direction-independent pitch language.

- [ ] **Step 5: Run onboarding and existing auth/setup tests**

  Run: `npm.cmd run test:run -- src/features/onboarding/ClubSelectionPage.test.tsx src/features/setup/SetupPage.test.tsx src/features/auth/LoginPage.test.tsx`

  Working directory: `frontend`

  Expected: PASS.

- [ ] **Step 6: Commit onboarding**

  Run: `git add frontend/src/features/integrations frontend/src/features/onboarding frontend/src/features/auth/SessionGate.tsx frontend/src/features/setup/SetupPage.tsx frontend/src/lib/api/types.ts frontend/src/locales`

  Run: `git commit -m "feat: add tunisian club onboarding"`

### Task 6: Shield-inspired roster cards and camera/gallery workflow

**Files:**
- Create: `frontend/src/features/roster/PlayerCard.tsx`
- Create: `frontend/src/features/roster/PlayerCard.test.tsx`
- Create: `frontend/src/features/roster/PlayerPhotoPicker.tsx`
- Create: `frontend/src/features/roster/PlayerPhotoPicker.test.tsx`
- Modify: `frontend/src/features/roster/RosterPage.tsx`
- Modify: `frontend/src/features/roster/RosterPage.test.tsx`
- Modify: `frontend/src/features/roster/PlayerForm.tsx`
- Modify: `frontend/src/features/roster/api.ts`
- Modify: `frontend/src/lib/api/client.ts`
- Modify: `frontend/src/styles/globals.css`
- Modify: `frontend/src/locales/fr.json`
- Modify: `frontend/src/locales/ar.json`

**Interfaces:**
- Consumes: Task 4 photo endpoints/status and enriched `RosterItem` fields from Tasks 1–4.
- Produces: responsive `PlayerCard`, `PlayerPhotoPicker`, multipart-aware `request`, photo preview/upload/poll/retry/fallback actions, and a card-grid roster while retaining manual create/register/detail flows.

- [ ] **Step 1: Write failing card tests**

  Assert name, number, position, preferred foot, provider/club/manual source, verification/rights, publication state, freshness, accessible image fallback, and one 48 px **Gérer** action render without relying on color alone. Local photo must win over provider photo.

- [ ] **Step 2: Write failing camera/gallery picker tests**

  Assert separate inputs: camera has `accept="image/*"` and `capture="user"`; gallery accepts JPEG/PNG/WebP and has no capture attribute. Test local preview URL cleanup, 10 MiB client warning, multipart upload without forced JSON content type, processing progress, retry, and keep-original fallback.

- [ ] **Step 3: Run the new and current roster tests**

  Run: `npm.cmd run test:run -- src/features/roster/PlayerCard.test.tsx src/features/roster/PlayerPhotoPicker.test.tsx src/features/roster/RosterPage.test.tsx`

  Working directory: `frontend`

  Expected: FAIL because cards and picker are absent.

- [ ] **Step 4: Implement multipart support, photo API types, cards, and photo picker**

  Allow `FormData` through `request` without setting `Content-Type`. Append an optional photo after successful manual player creation so identity creation remains recoverable when image processing fails. Poll only pending/processing photos.

- [ ] **Step 5: Replace `.roster-list` with the responsive card grid and original StatX geometry**

  Use CSS (`clip-path`/pseudo-elements) rather than copying the supplied card artwork. Target four columns wide, three at tablet landscape, two in portrait, one on narrow phones; maintain 48 px actions, visible focus, reduced-motion behavior, and RTL logical alignment.

- [ ] **Step 6: Run roster tests and TypeScript build**

  Run: `npm.cmd run test:run -- src/features/roster`

  Run: `npm.cmd run build`

  Working directory: `frontend`

  Expected: all tests PASS and Vite build succeeds.

- [ ] **Step 7: Commit roster media UX**

  Run: `git add frontend/src/features/roster frontend/src/lib/api/client.ts frontend/src/styles/globals.css frontend/src/locales`

  Run: `git commit -m "feat: add player cards and portrait capture"`

### Task 7: Tablet, RTL, offline, and end-to-end acceptance

**Files:**
- Create: `frontend/e2e/club-import-player-cards.spec.ts`
- Create: `frontend/e2e/player-photo-touch.spec.ts`
- Modify: `frontend/e2e/roster-rtl-touch.spec.ts`
- Modify: `frontend/playwright.config.ts`
- Modify: `backend/tests/test_release1_regression.py`
- Modify: `docs/operations/release-1-foundation.md`

**Interfaces:**
- Consumes: Completed backend and frontend user paths.
- Produces: automated acceptance proof for club import, offline cache, manual fallback, camera/gallery controls, player cards, tablet breakpoints, and RTL.

- [ ] **Step 1: Add a deterministic fake-provider mode for E2E only**

  Inject synthetic API-Football responses at the backend adapter boundary through test configuration; never add live credentials or network dependence to Playwright.

- [ ] **Step 2: Write failing 1024 × 768 and portrait workflows**

  Cover setup → club search → import → card roster; manual player creation while provider is unavailable; camera/gallery affordances; card detail; 48 px hit areas; three landscape/two portrait columns; and no horizontal overflow.

- [ ] **Step 3: Extend RTL and reduced-motion assertions**

  Verify Arabic reading order, logical alignment, source/status text, shield/card controls, and functional navigation under `prefers-reduced-motion: reduce`.

- [ ] **Step 4: Run E2E tests and confirm initial failures**

  Run: `npm.cmd run test:e2e -- club-import-player-cards.spec.ts player-photo-touch.spec.ts roster-rtl-touch.spec.ts`

  Working directory: `frontend`

  Expected: FAIL until all fixtures, selectors, and responsive states are connected.

- [ ] **Step 5: Make the smallest production/fixture corrections required by the failing journeys**

  Do not weaken assertions or add test-only branches to UI components. Keep fake data behind backend dependency injection.

- [ ] **Step 6: Document installation, secret rotation, model preparation, quota use, backup, and tablet access**

  Include `requirements-media.txt` installation, `.env` variables without values, `prepare_media_model.py`, Alembic upgrade, worker behavior, quota reset/retry, data directories, and provider image-rights warning. Explicitly instruct rotating the key shared during development.

- [ ] **Step 7: Run acceptance E2E and Release 1 regression**

  Run: `npm.cmd run test:e2e -- club-import-player-cards.spec.ts player-photo-touch.spec.ts roster-rtl-touch.spec.ts`

  Working directory: `frontend`

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_release1_regression.py -q`

  Working directory: repository root

  Expected: PASS.

- [ ] **Step 8: Commit acceptance coverage and operations**

  Run: `git add frontend/e2e frontend/playwright.config.ts backend/tests/test_release1_regression.py docs/operations/release-1-foundation.md`

  Run: `git commit -m "test: cover club import and player media journeys"`

### Task 8: Full verification, security scan, and branch handoff

**Files:**
- Modify only if verification reveals a defect in files owned by Tasks 1–7.

**Interfaces:**
- Consumes: All implementation tasks.
- Produces: migration, backend, frontend, E2E, and secret-safety evidence suitable for branch review.

- [ ] **Step 1: Upgrade a copied Release 1 database and inspect preservation**

  Run Alembic against a disposable copy, then assert existing organization/team/player/registration/consent counts and IDs are unchanged and the new revision is current.

- [ ] **Step 2: Run the complete backend suite**

  Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -q`

  Expected: all tests PASS.

- [ ] **Step 3: Run complete frontend unit tests and production build**

  Run: `npm.cmd run test:run`

  Run: `npm.cmd run build`

  Working directory: `frontend`

  Expected: all tests PASS and production build succeeds.

- [ ] **Step 4: Run the complete Playwright suite**

  Run: `npm.cmd run test:e2e`

  Working directory: `frontend`

  Expected: all projects PASS at desktop, tablet landscape, and tablet portrait viewports.

- [ ] **Step 5: Scan tracked source and built frontend for credential leakage**

  Search tracked files, test snapshots, logs generated by tests, and `frontend/dist` for `x-apisports-key`, `API_FOOTBALL_KEY=` with a non-placeholder value, and the development key fingerprint. Expected: no secret value and no backend header in the browser bundle.

- [ ] **Step 6: Verify clean source control scope**

  Run: `git status --short`

  Expected: no `.env`, SQLite WAL/SHM, `.run`, model weights, uploaded photos, provider cache dumps, or generated media staged/tracked.

- [ ] **Step 7: Use the verification and branch-finishing skills**

  Invoke `superpowers:verification-before-completion`, then `superpowers:requesting-code-review`, and finally `superpowers:finishing-a-development-branch`. Fix any review findings with focused tests before presenting integration options.
