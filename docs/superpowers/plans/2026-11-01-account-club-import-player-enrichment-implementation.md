# Account, Tunisian Club Import and Player Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-run wizard that captures the creator's football function, selects a current Tunisian club, imports and enriches its current-season roster, and provides audited player editing, lifecycle and portrait states.

**Architecture:** Extend the existing local-first `/api/v1` modular monolith. API-Football remains behind the backend cache/quota boundary; setup stores immutable provider identifiers and queues persisted stages, while SQLite remains the operational source of truth with per-field club overrides. React renders a touch-first three-step setup and consumes only sanitized StatX APIs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, SQLite, Pydantic v2, httpx, React 19, TypeScript, TanStack Query, Zod, Vitest, Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-01-account-club-import-player-enrichment-design.md`

## Global Constraints

- Preserve every existing public UUID and historical row during schema migration.
- Keep API-Football secrets backend-only; never serialize keys or provider headers.
- Reserve 10 of the free plan's 100 daily calls by retaining the default ceiling of 90.
- Determine current seasons from `/leagues?country=Tunisia&current=true`, not calendar arithmetic.
- Never call API-Football merely because a user opens a screen.
- Security role and football function are independent; the first creator is security `admin` and displayed as owner.
- New positions are controlled values: `GK`, `RB`, `CB`, `LB`, `DM`, `CM`, `AM`, `RW`, `LW`, `ST`, `OTHER`.
- Local field overrides and club-owned portraits survive provider refresh.
- Removing a player from a roster is non-destructive; hard delete is admin-only and blocked by dependencies.
- Provider portraits remain `provider_identification_only`; publication consent is separate.
- All touch actions are at least 48 px and work at 1024 × 768.
- The user-authorized local reset runs only after the new flow is verified and first creates a recoverable backup.

## Review Focus

- Two concurrent pre-bootstrap catalog requests must spend quota once and return one consistent catalog; Task 3 adds the concurrency/cache test.
- A provider player transferred between clubs in one season must not duplicate identity or overwrite club overrides; Task 5 adds the transfer/idempotency test.
- A club-edited value that becomes blank must still count as an intentional override; Task 6 tests explicit null/blank overrides.
- Portrait processing may finish after roster data is cached in the browser; Task 7 tests invalidation/polling from pending to ready.
- An existing installation must not re-enter first-run setup after migration, while a reset installation must; Task 9 adds both E2E states.

---

### Task 1: Provider-Enrichment Persistence and Migration

**Files:**
- Create: `backend/alembic/versions/20261101_03_account_club_player_enrichment.py`
- Create: `backend/app/modules/roster/statistics_models.py`
- Modify: `backend/app/modules/identity/models.py`
- Modify: `backend/app/modules/roster/models.py`
- Modify: `backend/app/modules/integrations/models.py`
- Modify: `backend/app/db/model_registry.py`
- Test: `backend/tests/migrations/test_account_club_player_enrichment_migration.py`

**Interfaces:**
- Consumes: existing `User`, `Player`, `ProviderSyncRun`, `Season`, organization-scoped public IDs.
- Produces: `User.job_title: str`; `Player.display_name`, `birth_place`, `birth_country`, `primary_position`, `secondary_positions`, and `player_field_overrides`; `PlayerSeasonSnapshot`; `ProviderSyncStage`; `ProviderRequestLease` unique on `(provider, scope_key)` for pre-bootstrap cache refresh serialization.

- [ ] **Step 1: Write migration tests for fresh and existing databases**

  Add `test_upgrade_adds_job_title_profile_overrides_snapshots_and_sync_stages` and `test_upgrade_preserves_existing_admin_and_manual_players`. Assert `job_title == "other"` for the legacy user, existing player public IDs remain unchanged, JSON defaults are usable, and new unique/index/check constraints exist.

- [ ] **Step 2: Run the migration tests and verify RED**

  Run: `python -m pytest backend/tests/migrations/test_account_club_player_enrichment_migration.py -v`  
  Expected: FAIL because revision `20261101_03` and new tables/columns do not exist.

- [ ] **Step 3: Add the migration and mapped models**

  Define `PlayerSeasonSnapshot` unique on `(organization_id, player_id, team_id, season_id, provider)` with versioned `statistics_json`, `raw_payload`, and `captured_at`. Define `ProviderSyncStage` unique on `(sync_run_id, name)` with status/count/error/timestamps. Add job-title and position check constraints and non-null JSON defaults using SQLite-safe batch operations.

- [ ] **Step 4: Run migration and model-registry tests**

  Run: `python -m pytest backend/tests/migrations backend/tests/test_database_config.py -q`  
  Expected: PASS.

- [ ] **Step 5: Commit persistence**

  ```bash
  git add docs/superpowers/specs/2026-11-01-account-club-import-player-enrichment-design.md docs/superpowers/plans/2026-11-01-account-club-import-player-enrichment-implementation.md backend/alembic/versions/20261101_03_account_club_player_enrichment.py backend/app/modules backend/app/db/model_registry.py backend/tests/migrations
  git commit -m "feat: add onboarding and player enrichment persistence"
  ```

### Task 2: Security Role and Football Function Contracts

**Files:**
- Modify: `backend/app/modules/identity/schemas.py`
- Modify: `backend/app/modules/identity/service.py`
- Modify: `backend/app/modules/identity/router.py`
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/features/setup/setupSchema.ts`
- Create: `frontend/src/features/setup/setupSchema.test.ts`
- Test: `backend/tests/api/v1/test_setup_auth.py`

**Interfaces:**
- Consumes: `User.job_title` from Task 1 and existing `bootstrap`, `authenticate`, `SessionView`.
- Produces: `FootballJobTitle`; `BootstrapCommand.job_title`; `SessionView.job_title`; first creator membership role fixed to `admin`.

- [ ] **Step 1: Write failing backend role/function tests**

  Add `test_bootstrap_keeps_owner_admin_role_and_records_job_title` with `job_title="coach"`; assert membership role `admin`, user job title `coach`, and session exposes both. Add table-driven rejection of unsupported functions.

- [ ] **Step 2: Run backend setup tests and verify RED**

  Run: `python -m pytest backend/tests/api/v1/test_setup_auth.py -v`  
  Expected: FAIL because `job_title` is absent.

- [ ] **Step 3: Implement the typed function contract**

  Add allowed values `director|coach|analyst|scout|medical|media|other`, persist the selected function, and keep authorization based only on membership role.

- [ ] **Step 4: Write and run the frontend schema test**

  Assert setup parsing requires one allowed function and rejects arbitrary values.  
  Run: `npm.cmd test -- --run src/features/setup/setupSchema.test.ts`  
  Expected: PASS; visual composition remains in Task 8.

- [ ] **Step 5: Run identity regression and commit**

  Run: `python -m pytest backend/tests/api/v1/test_setup_auth.py backend/tests/api/v1/test_rbac.py -q`  
  Expected: PASS.

  ```bash
  git add backend/app/modules/identity backend/tests/api/v1/test_setup_auth.py frontend/src/lib/api/types.ts frontend/src/features/setup/setupSchema.ts frontend/src/features/setup/setupSchema.test.ts
  git commit -m "feat: separate owner permissions from football function"
  ```

### Task 3: Safe Pre-Bootstrap Tunisian Club Catalog

**Files:**
- Create: `backend/app/modules/integrations/catalog.py`
- Create: `backend/app/modules/integrations/setup_router.py`
- Modify: `backend/app/modules/integrations/router.py`
- Modify: `backend/app/modules/integrations/schemas.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/api/v1/test_setup_provider_catalog.py`
- Test: `backend/tests/modules/integrations/test_provider_repository.py`

**Interfaces:**
- Consumes: `ProviderRepository.cached_request`, quota rows, `ProviderRequestLease` from Task 1, `SystemState.bootstrapped`, provider club schema.
- Produces: `GET /api/v1/setup/provider-catalog`; `TunisianClubCatalogService.current_catalog() -> ClubCatalog`; deduplicated `ProviderClub` entries containing competition and current season.

- [ ] **Step 1: Write catalog boundary tests**

  Cover cached success, multiple current competitions, provider-team deduplication, provider unavailable with cache, unavailable without cache, and `409 setup_complete` after bootstrap. Add the Review Focus concurrency test proving two callers produce one cache refresh/call set.

- [ ] **Step 2: Run catalog tests and verify RED**

  Run: `python -m pytest backend/tests/api/v1/test_setup_provider_catalog.py backend/tests/modules/integrations/test_provider_repository.py -v`  
  Expected: FAIL because the setup catalog route/service do not exist.

- [ ] **Step 3: Implement catalog service and route**

  Mount a dedicated `/setup` router from the v1 composition root; do not place the public route under the authenticated integration prefix. Reuse `/leagues?country=Tunisia&current=true` and cached `/teams` calls. Return only IDs, names, crest URL, competition, season, cache/stale metadata and quota summary. Guard refresh with `ProviderRequestLease` and bootstrap state.

- [ ] **Step 4: Run catalog, quota and security tests**

  Run: `python -m pytest backend/tests/api/v1/test_setup_provider_catalog.py backend/tests/modules/integrations/test_provider_repository.py backend/tests/api/v1/test_api_football_sync_security.py -q`  
  Expected: PASS and no secret serialization.

- [ ] **Step 5: Commit catalog**

  ```bash
  git add backend/app/modules/integrations backend/app/api/v1/router.py backend/tests/api/v1/test_setup_provider_catalog.py backend/tests/modules/integrations/test_provider_repository.py
  git commit -m "feat: expose safe tunisian setup catalog"
  ```

### Task 4: Atomic Setup Selection and Persisted Import Stages

**Files:**
- Modify: `backend/app/modules/identity/schemas.py`
- Modify: `backend/app/modules/identity/service.py`
- Modify: `backend/app/modules/identity/router.py`
- Modify: `backend/app/modules/integrations/service.py`
- Modify: `backend/app/modules/integrations/schemas.py`
- Modify: `backend/app/modules/integrations/worker.py`
- Test: `backend/tests/api/v1/test_setup_auth.py`
- Test: `backend/tests/modules/integrations/test_club_sync_service.py`

**Interfaces:**
- Consumes: `ProviderClub` from Task 3, `ProviderSyncStage` from Task 1, typed job title from Task 2.
- Produces: optional `BootstrapCommand.selected_club`; atomically created organization/user/admin membership plus queued `ProviderSyncRun`; stage view `name/status/count/error`.

- [ ] **Step 1: Write failing atomic-setup tests**

  Assert selected provider IDs are stored in the queued request, creator account survives later provider failure, duplicate bootstrap remains rejected, and manual fallback creates no provider run.

- [ ] **Step 2: Write failing sync-stage lifecycle tests**

  Assert `squad`, `profiles`, `fixtures`, `standings`, `portraits` stages transition independently and sanitized stage errors never contain request headers or keys.

- [ ] **Step 3: Run setup and sync tests to verify RED**

  Run: `python -m pytest backend/tests/api/v1/test_setup_auth.py backend/tests/modules/integrations/test_club_sync_service.py -v`  
  Expected: FAIL on selected-club and stage contracts.

- [ ] **Step 4: Implement atomic queueing and stage persistence**

  Queue the provider command in the same database transaction as bootstrap. Keep provider I/O exclusively in the worker after commit. Required squad failure marks the run failed; optional stage failure records `failed` or `skipped` without deleting the valid account.

- [ ] **Step 5: Run tests and commit**

  Run: `python -m pytest backend/tests/api/v1/test_setup_auth.py backend/tests/modules/integrations/test_club_sync_service.py -q`  
  Expected: PASS.

  ```bash
  git add backend/app/modules/identity backend/app/modules/integrations backend/tests/api/v1/test_setup_auth.py backend/tests/modules/integrations/test_club_sync_service.py
  git commit -m "feat: bind club selection to first setup"
  ```

### Task 5: Paginated Player Profile and Season-Statistics Enrichment

**Files:**
- Create: `backend/app/modules/integrations/player_enrichment.py`
- Modify: `backend/app/modules/integrations/repository.py`
- Modify: `backend/app/modules/integrations/service.py`
- Modify: `backend/app/modules/integrations/worker.py`
- Modify: `backend/app/modules/roster/models.py`
- Test: `backend/tests/modules/integrations/test_player_enrichment.py`
- Test: `backend/tests/modules/integrations/test_club_sync_service.py`

**Interfaces:**
- Consumes: provider envelope pagination, quota reserve, selected team/season, `PlayerSeasonSnapshot`, field overrides.
- Produces: `ProviderRepository.cached_pages(endpoint, params, ttl, *, max_pages) -> list[dict]`; `PlayerEnrichmentService.apply(team, season, rows) -> EnrichmentSummary`.

- [ ] **Step 1: Write failing pagination and mapping tests**

  Use literal two-page provider fixtures. Assert birth facts, nationality, height/weight parsing, foot/position mapping, statistics snapshot values, and sanitized raw payload. Assert quota reserve stops before a page call and marks enrichment incomplete.

- [ ] **Step 2: Add idempotency, transfer and malformed-profile tests**

  Cover the Review Focus transfer case: provider ID remains one identity, a new registration may be created, and field overrides survive. Reject duplicate provider IDs and impossible measurements without damaging the squad.

- [ ] **Step 3: Run enrichment tests and verify RED**

  Run: `python -m pytest backend/tests/modules/integrations/test_player_enrichment.py backend/tests/modules/integrations/test_club_sync_service.py -v`  
  Expected: FAIL because paginated enrichment is absent.

- [ ] **Step 4: Implement bounded cached pagination and enrichment**

  Parse provider heights/weights into nullable integers, map provider positions centrally, store one versioned season snapshot, and update only non-overridden player fields. Set stage counts for imported/skipped/malformed profiles.

- [ ] **Step 5: Run integration suite and commit**

  Run: `python -m pytest backend/tests/modules/integrations backend/tests/api/v1/test_api_football_integration.py -q`  
  Expected: PASS.

  ```bash
  git add backend/app/modules/integrations backend/app/modules/roster backend/tests/modules/integrations
  git commit -m "feat: enrich imported player profiles and statistics"
  ```

### Task 6: Audited Player Editing, Registration Lifecycle and Safe Deletion

**Files:**
- Create: `backend/app/modules/roster/positions.py`
- Modify: `backend/app/modules/roster/schemas.py`
- Modify: `backend/app/modules/roster/service.py`
- Modify: `backend/app/modules/roster/router.py`
- Test: `backend/tests/modules/test_roster_service.py`
- Test: `backend/tests/api/v1/test_organization_roster.py`
- Test: `backend/tests/api/v1/test_player_lifecycle.py`

**Interfaces:**
- Consumes: normalized player profile and field overrides from Task 1; current RBAC/audit services.
- Produces: `normalize_position(value: str) -> PositionCode`; `update_player`; `deactivate_registration`; `safe_delete_player`; PATCH and DELETE routes from the spec.

- [ ] **Step 1: Write failing normalized-position tests**

  Cover provider synonyms and all controlled codes; manual commands reject arbitrary free text and accept `OTHER` explicitly.

- [ ] **Step 2: Write failing lifecycle and authorization tests**

  Assert admin/coach edit permissions, viewer rejection, organization isolation, registration deactivation, dependency-blocked hard delete, and successful hard delete only for an unused mistaken identity.

- [ ] **Step 3: Add field-override tests**

  Assert changed fields record actor/time/source. Include the Review Focus case where an intentional blank optional value remains an override and is not repopulated on sync.

- [ ] **Step 4: Run roster tests and verify RED**

  Run: `python -m pytest backend/tests/modules/test_roster_service.py backend/tests/api/v1/test_organization_roster.py backend/tests/api/v1/test_player_lifecycle.py -v`  
  Expected: FAIL on new commands/routes.

- [ ] **Step 5: Implement minimal lifecycle services and routes**

  Keep hard-delete dependency checks in the service, use registration status/end date for roster removal, and write before/after audit payloads without private media bytes.

- [ ] **Step 6: Run roster/RBAC tests and commit**

  Run: `python -m pytest backend/tests/modules/test_roster_service.py backend/tests/api/v1/test_organization_roster.py backend/tests/api/v1/test_player_lifecycle.py backend/tests/api/v1/test_rbac.py -q`  
  Expected: PASS.

  ```bash
  git add backend/app/modules/roster backend/tests/modules/test_roster_service.py backend/tests/api/v1/test_organization_roster.py backend/tests/api/v1/test_player_lifecycle.py
  git commit -m "feat: add audited player lifecycle management"
  ```

### Task 7: Reliable Portrait States and Provider Portrait Priority

**Files:**
- Modify: `backend/app/modules/media/worker.py`
- Modify: `backend/app/modules/media/service.py`
- Modify: `backend/app/modules/roster/service.py`
- Modify: `frontend/src/features/roster/PlayerCard.tsx`
- Modify: `frontend/src/features/roster/PlayerCard.test.tsx`
- Modify: `frontend/src/features/roster/PlayerPhotoPicker.tsx`
- Modify: `frontend/src/features/roster/api.ts`
- Test: `backend/tests/modules/media/test_media_service.py`
- Test: `backend/tests/api/v1/test_player_photos.py`

**Interfaces:**
- Consumes: imported `provider_photo_url`, existing `PlayerPhoto`, authenticated photo API.
- Produces: roster photo states `no_photo|pending|processing|failed|ready`; local portrait priority; retry/status APIs; frontend polling/invalidation behavior.

- [ ] **Step 1: Write backend portrait-priority tests**

  Assert provider portrait queues only without club media, club media wins, removing club media reveals the latest ready provider photo, and failed provider download never breaks player import.

- [ ] **Step 2: Write frontend card-state tests**

  Assert no-photo action, processing badge, failed retry and ready authenticated image. Add the Review Focus test that a pending query invalidates and renders the ready image without reloading the page.

- [ ] **Step 3: Run tests and verify RED**

  Run: `python -m pytest backend/tests/modules/media/test_media_service.py backend/tests/api/v1/test_player_photos.py -q` and `npm.cmd test -- --run src/features/roster/PlayerCard.test.tsx src/features/roster/PlayerPhotoPicker.test.tsx`  
  Expected: FAIL on explicit states/priority/polling.

- [ ] **Step 4: Implement portrait selection and status behavior**

  Return explicit photo state in roster items, keep all media authenticated, and invalidate the roster query when processing completes. Never emit a provider CDN URL directly from a card.

- [ ] **Step 5: Run media/roster tests and commit**

  Run both commands from Step 3.  
  Expected: PASS.

  ```bash
  git add backend/app/modules/media backend/app/modules/roster frontend/src/features/roster backend/tests/modules/media backend/tests/api/v1/test_player_photos.py
  git commit -m "feat: make player portrait states reliable"
  ```

### Task 8: Touch-First Setup Wizard and Enriched Roster Workspace

**Files:**
- Create: `frontend/src/features/setup/SetupWizard.tsx`
- Create: `frontend/src/features/setup/ProfileStep.tsx`
- Create: `frontend/src/features/setup/ClubStep.tsx`
- Create: `frontend/src/features/setup/ConfirmationStep.tsx`
- Create: `frontend/src/features/setup/providerCatalogApi.ts`
- Create: `frontend/src/features/roster/PlayerEditForm.tsx`
- Create: `frontend/src/features/roster/PositionSelect.tsx`
- Create: `frontend/src/features/integrations/ClubAssociationPanel.tsx`
- Create: `frontend/src/features/integrations/ClubAssociationPanel.test.tsx`
- Modify: `frontend/src/features/setup/SetupPage.tsx`
- Modify: `frontend/src/features/setup/api.ts`
- Modify: `frontend/src/features/auth/SessionGate.tsx`
- Modify: `frontend/src/features/onboarding/SyncProgress.tsx`
- Modify: `frontend/src/features/roster/RosterPage.tsx`
- Modify: `frontend/src/features/roster/PlayerDetailPage.tsx`
- Modify: `frontend/src/features/roster/PlayerForm.tsx`
- Modify: `frontend/src/features/roster/schemas.ts`
- Modify: `frontend/src/styles/globals.css`
- Test: `frontend/src/features/setup/SetupWizard.test.tsx`
- Test: `frontend/src/features/roster/PlayerEditForm.test.tsx`
- Test: `frontend/src/features/roster/RosterPage.test.tsx`

**Interfaces:**
- Consumes: setup catalog and bootstrap contracts from Tasks 2–4; lifecycle and portrait contracts from Tasks 6–7.
- Produces: three-step setup wizard; controlled position list; enriched card filters; edit/deactivate/safe-delete player workspace.

- [ ] **Step 1: Write failing setup-wizard tests**

  Assert function selection, competition/team list, no provider-ID fields, confirmation summary, manual fallback, selected-club bootstrap payload and import progress. Assert 48 px controls and keyboard labels. Assert an already-bootstrapped admin can open `ClubAssociationPanel` to run the same provider selection without re-entering setup.

- [ ] **Step 2: Write failing roster-management tests**

  Assert position dropdown, edit payload, source/photo/status filters, deactivation, safe-delete conflict message and season-statistics rendering.

- [ ] **Step 3: Run frontend tests and verify RED**

  Run: `npm.cmd test -- --run src/features/setup src/features/roster`  
  Expected: FAIL because wizard/edit components do not exist.

- [ ] **Step 4: Implement the wizard state machine**

  Keep unsent wizard state in React, load the catalog once, make back/next transitions explicit, and submit one bootstrap command. Existing installations bypass the wizard and use authenticated club-association settings.

- [ ] **Step 5: Implement roster management UI**

  Use `PositionSelect` in create/edit flows, show mutation errors without discarding form state, and refresh only affected queries.

- [ ] **Step 6: Run frontend suite and production build**

  Run: `npm.cmd test -- --run` and `npm.cmd run build`  
  Expected: all tests PASS and build exit 0.

- [ ] **Step 7: Commit frontend experience**

  ```bash
  git add frontend/src/features frontend/src/lib/api frontend/src/styles/globals.css
  git commit -m "feat: add club-first setup and roster management"
  ```

### Task 9: End-to-End Acceptance, Operations and Authorized Local Reset

**Files:**
- Create: `frontend/e2e/setup-club-import.spec.ts`
- Create: `frontend/e2e/player-lifecycle.spec.ts`
- Modify: `frontend/playwright.config.ts`
- Modify: `frontend/e2e/setup-login.spec.ts`
- Modify: `docs/operations/release-1-foundation.md`
- Modify: `README.md`
- Test: `backend/tests/test_release1_regression.py`

**Interfaces:**
- Consumes: complete setup/import/player workflow from Tasks 1–8.
- Produces: tablet acceptance coverage, operator instructions, recoverable reset evidence and a fresh active installation ready for real setup.

- [ ] **Step 1: Write E2E setup/import and player-lifecycle journeys**

  Use deterministic provider fixtures: function → current competition → club → bootstrap → staged import → cards with photo states → edit/deactivate. Add the Review Focus existing-vs-reset setup-gate cases.

- [ ] **Step 2: Run E2E and verify RED before final UI wiring**

  Run: `npm.cmd run test:e2e -- setup-club-import.spec.ts player-lifecycle.spec.ts`  
  Expected: FAIL until all routes and selectors are integrated; repair only product gaps identified by the journeys.

- [ ] **Step 3: Run full automated verification**

  Run: `python -m pytest backend/tests -q`, `npm.cmd test -- --run`, `npm.cmd run build`, and `npm.cmd run test:e2e`.  
  Expected: all suites PASS; record exact counts.

- [ ] **Step 4: Run secret/runtime audit**

  Assert zero high-entropy `API_FOOTBALL_KEY` assignments in tracked files, zero provider-key markers in `frontend/dist`, and zero tracked `.env`, database, WAL/SHM, player media or model files.

- [ ] **Step 5: Commit acceptance and operations**

  ```bash
  git add frontend/e2e frontend/playwright.config.ts backend/tests/test_release1_regression.py docs/operations/release-1-foundation.md README.md
  git commit -m "test: verify club-first onboarding and roster lifecycle"
  ```

- [ ] **Step 6: Back up and deactivate the authorized legacy installation**

  Resolve the exact active database path first. Stop only the verified StatX backend process. Copy the database plus consistent WAL contents through SQLite backup API to `data/backups/pre-onboarding-reset-<UTC timestamp>.db`; verify `PRAGMA integrity_check` and expected counts (one user, two players) in the backup. Never recursively delete a broad directory.

- [ ] **Step 7: Create and migrate the fresh active database**

  Move the old active database files to a timestamped recoverable archive, run `alembic upgrade head` against a new `statx.db`, and assert `bootstrapped == false`, zero users and zero players. This fulfills the user's explicit deletion request while preserving recovery evidence.

- [ ] **Step 8: Start the verified branch and check PC/tablet access**

  Start backend on `0.0.0.0:8000` and frontend on `0.0.0.0:5173`; verify `/health`, the first-run wizard on PC and LAN URL, and that no default credentials exist. Do not enter a new provider key until the user supplies a rotated value.

## Final Verification

- [ ] Fresh SQLite migration and legacy migration both pass.
- [ ] Existing public IDs and historical records are preserved by migrations.
- [ ] First creator is owner/admin with a separate football function.
- [ ] Current Tunisia competitions and teams appear as a selectable list.
- [ ] Initial import and enrichment are idempotent, staged and quota-bounded.
- [ ] Player positions are controlled values.
- [ ] Local overrides survive refresh, including explicit blank optional values.
- [ ] Portrait cards expose no-photo, pending, failed and ready states.
- [ ] Add/edit/deactivate/safe-delete flows are audited and tenant-scoped.
- [ ] Tablet E2E passes at 1024 × 768.
- [ ] No API secret or runtime media/database artifact is tracked or bundled.
- [ ] The previous active database is recoverably archived and the new active database is empty and unbootstrapped.

