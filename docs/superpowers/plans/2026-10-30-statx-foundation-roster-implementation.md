# StatX Foundation and Roster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the prototype-only foundation with a migrated, authenticated, organization-scoped StatX application that manages seasons, teams, player identities, registrations and consent through the new desktop/tablet-ready App Shell.

**Architecture:** Preserve legacy integer primary keys during migration and add stable UUID `public_id` values exposed by `/api/v1`; this avoids destructive rewrites of existing match, event and tracking foreign keys. FastAPI routes delegate to module services, Alembic owns schema evolution, and the React/Vite frontend moves incrementally to TypeScript with the approved local design tokens.

**Tech Stack:** Python 3.11+, FastAPI 0.115, SQLAlchemy 2, Alembic, Pydantic v2, Argon2id via `pwdlib`, signed HTTP-only sessions via `itsdangerous`, SQLite WAL; React, TypeScript, Vite, React Router, TanStack Query, i18next, Zod, Tailwind, Vitest, Testing Library and Playwright.

**Spec:** `docs/superpowers/specs/2026-10-30-statx-mvp-foundation-design.md`

## Global Constraints

- Preserve all current user changes and legacy Team, Player, Match, Event and TrackingPoint rows.
- New public API is `/api/v1`; existing `/api` routes remain available until later releases migrate their consumers.
- SQLite foreign keys are ON, journal mode is WAL and busy timeout is 5,000 ms.
- Production assets and fonts are local; no Google Fonts, Tailwind CDN, Material Symbols CDN or remote logo URL.
- Official identity is “Stat X — Football Data Lab”; copy the provided logo to `frontend/src/assets/statx-lockup.png` without redesigning it.
- Default locale is French; Arabic uses real `dir="rtl"`, but football coordinates are never mirrored.
- Interactive controls are at least 48 × 48 CSS pixels; focus is visible and status never relies on color alone.
- Provenance is A=validated primary, B=derived/partially verified, C=legacy/estimated/unvalidated.
- No YOLO/tracking workflow appears in the primary Release 1 navigation.
- Never display an unapproved xG as zero; unavailable values are `null` and render as “xG indisponible”.

## Review Focus

- A legacy database containing teams, players, matches, events and tracking points migrates without changed IDs or lost rows — covered by Task 2 migration tests.
- Two concurrent first-run requests cannot create two organizations or two initial administrators — covered by Task 3 transaction test.
- Missing, expired or cross-organization sessions receive 401/403 without leaking whether a resource exists — covered by Tasks 3 and 4 API tests.
- A minor without active consent cannot be marked publishable, and consent revocation remains auditable — covered by Task 4 service tests.
- The built frontend makes no external asset requests and remains usable in French, Arabic RTL and 1024 × 768 touch viewport — covered by Tasks 5 and 7 tests.

---

## File Structure

### Backend platform

- `backend/alembic.ini` — migration configuration.
- `backend/alembic/env.py` — metadata and database URL wiring.
- `backend/alembic/versions/20261030_01_foundation.py` — additive legacy-safe migration.
- `backend/app/config.py` — cached application settings.
- `backend/app/db/database.py` — engine/session factory and SQLite pragmas.
- `backend/app/db/model_registry.py` — imports every ORM model for Alembic.
- `backend/app/db/models.py` — compatibility re-exports for existing routes.
- `backend/app/api/problems.py` — uniform `application/problem+json` responses.
- `backend/app/api/v1/router.py` — v1 router composition.

### Backend modules

- `backend/app/modules/organizations/{models,schemas,service,router}.py`
- `backend/app/modules/identity/{models,schemas,security,dependencies,service,router}.py`
- `backend/app/modules/roster/{models,schemas,service,router}.py`
- `backend/app/modules/platform/{models,audit}.py`
- `backend/app/modules/matches/models.py` — compatibility home for current Match/Event/TrackingPoint classes.

### Frontend

- `frontend/src/main.tsx`, `frontend/src/app/App.tsx`, `frontend/src/app/router.tsx`
- `frontend/src/app/providers.tsx`, `frontend/src/app/i18n.ts`
- `frontend/src/styles/tokens.css`, `frontend/src/styles/globals.css`
- `frontend/src/components/shell/*`
- `frontend/src/features/setup/*`, `auth/*`, `club/*`, `roster/*`
- `frontend/src/lib/api/{client,types}.ts`
- `frontend/src/locales/{fr,ar}.json`
- `frontend/src/assets/statx-lockup.png`

---

### Task 1: Testable Application Configuration and Alembic Baseline

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/app/db/model_registry.py`
- Modify: `backend/app/db/database.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_database_config.py`

**Interfaces:**
- Produces: `Settings`, `get_settings() -> Settings`, `create_engine_from_settings(settings) -> Engine`, `create_app(settings: Settings | None = None) -> FastAPI`.
- Produces: Alembic `upgrade head` as the only production schema creation path.

- [ ] **Step 1: Write failing SQLite configuration tests**

Test that a temporary settings object creates an engine whose connections report `foreign_keys=1`, `journal_mode=wal` and `busy_timeout=5000`; test that `create_app()` does not write to the default developer database when a test URL is supplied.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_database_config.py -v`  
Expected: FAIL because `Settings`, engine factory and app factory do not exist.

- [ ] **Step 3: Add configuration and dependencies**

Add `alembic`, `pydantic-settings`, `pwdlib[argon2]` and `itsdangerous` with compatible version bounds. Define `Settings` fields for `database_url`, `session_secret`, `session_ttl_seconds=28800`, `cors_origins`, `data_root`, `default_locale="fr"` and `sqlite_busy_timeout_ms=5000`.

- [ ] **Step 4: Refactor database and application factories**

Make `database.py` expose engine/session construction, apply all three SQLite pragmas on connect, and keep `get_db()` request-scoped. Make `main.py` expose `create_app()` while retaining module-level `app` for Uvicorn.

- [ ] **Step 5: Add the Alembic environment**

Wire the configured URL and `model_registry.Base.metadata`; do not create a revision yet.

- [ ] **Step 6: Run tests and static startup check**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_database_config.py -v`  
Run: `backend/.venv/Scripts/python.exe -c "from app.main import create_app; assert create_app().title == 'StatX Analytics API'"` from `backend`.  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/config.py backend/app/db backend/app/main.py backend/alembic.ini backend/alembic backend/requirements.txt backend/tests/test_database_config.py
git commit -m "feat: establish migrated application foundation"
```

### Task 2: Legacy-Safe Organization and Roster Schema

**Files:**
- Create: `backend/app/modules/organizations/models.py`
- Create: `backend/app/modules/identity/models.py`
- Create: `backend/app/modules/roster/models.py`
- Create: `backend/app/modules/platform/models.py`
- Create: `backend/app/modules/platform/audit.py`
- Create: `backend/app/modules/matches/models.py`
- Create: `backend/alembic/versions/20261030_01_foundation.py`
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/db/model_registry.py`
- Test: `backend/tests/migrations/test_foundation_migration.py`
- Test: `backend/tests/factories.py`

**Interfaces:**
- Produces ORM classes `Organization`, `User`, `Membership`, `Season`, `Team`, `TeamSeason`, `Player`, `PlayerRegistration`, `Consent`, `SystemState`, `AuditLog`, plus legacy `Match`, `Event`, `TrackingPoint`.
- Produces `write_audit(session, *, actor_id, organization_id, action, entity_type, entity_public_id, before=None, after=None) -> AuditLog`.
- All API roots expose `public_id: UUID`; legacy integer `id` remains internal.

- [ ] **Step 1: Build a failing legacy migration fixture**

Create a pre-migration SQLite file containing one Team, Player, Match, Event and TrackingPoint with fixed integer IDs. Assert after `alembic upgrade head` that row counts and IDs are unchanged, every migrated root has a unique UUID, and an “Imported season” registration reproduces the legacy team, shirt number, position and preferred foot.

- [ ] **Step 2: Run the migration test and confirm failure**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/migrations/test_foundation_migration.py -v`  
Expected: FAIL because the revision and models do not exist.

- [ ] **Step 3: Define modular ORM models**

Use integer internal PKs and `public_id` UUID columns. Add organization ownership, locale/timezone, user activity, membership role, season dates, team category/gender, player identity fields, registration dates/status, consent evidence, singleton system state and append-only audit rows. Keep legacy Player columns available to old routes during the transition.

- [ ] **Step 4: Implement the additive Alembic revision**

Use SQLite batch operations. Create a default imported organization and season only when legacy data exists; populate UUIDs; create registrations from current player rows; add indexes and uniqueness constraints. Never drop legacy columns or experimental tracking tables.

- [ ] **Step 5: Re-export compatibility models**

Make existing imports from `app.db.models` continue to resolve, so current `/api` tests remain runnable.

- [ ] **Step 6: Verify fresh and legacy databases**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/migrations/test_foundation_migration.py backend/tests/test_api.py -v`  
Expected: all migration tests and existing API tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/modules backend/app/db backend/alembic/versions backend/tests/migrations backend/tests/factories.py
git commit -m "feat: add organization and roster data model"
```

### Task 3: First-Run Setup, Local Authentication and RBAC

**Files:**
- Create: `backend/app/modules/identity/schemas.py`
- Create: `backend/app/modules/identity/security.py`
- Create: `backend/app/modules/identity/dependencies.py`
- Create: `backend/app/modules/identity/service.py`
- Create: `backend/app/modules/identity/router.py`
- Create: `backend/app/api/problems.py`
- Create: `backend/app/api/v1/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/v1/test_setup_auth.py`
- Test: `backend/tests/api/v1/test_rbac.py`

**Interfaces:**
- Produces: `hash_password(password: str) -> str`, `verify_password(password: str, encoded: str) -> bool`.
- Produces: `bootstrap_system(session, command: BootstrapCommand) -> BootstrapResult`.
- Produces dependencies `current_actor()` and `require_roles(*roles)`.
- Routes: `GET /api/v1/setup/status`, `POST /api/v1/setup`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/session`.

- [ ] **Step 1: Write failing setup/auth tests**

Assert bootstrap creates exactly one organization/admin membership, hashes the password, returns an authenticated session, rejects a second bootstrap with 409, and remains single under two competing transactions. Assert login failure is generic, cookies are HTTP-only/SameSite, logout clears them and an expired signature returns 401.

- [ ] **Step 2: Write failing RBAC and organization-isolation tests**

Assert admin-only dependency returns 403 for analyst/coach/viewer and that requesting another organization’s UUID returns 404 rather than revealing it.

- [ ] **Step 3: Run tests and confirm failure**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/api/v1/test_setup_auth.py backend/tests/api/v1/test_rbac.py -v`.

- [ ] **Step 4: Implement password/session security**

Use Argon2id, an `itsdangerous` timed serializer and an HTTP-only `statx_session` cookie. Resolve membership from the database on every request. Add a readable SameSite CSRF cookie and require matching `X-CSRF-Token` on authenticated mutations; setup and login are exempt.

- [ ] **Step 5: Implement bootstrap and auth routes**

Wrap first-run creation in one transaction guarded by a singleton bootstrap marker/unique constraint. Return `application/problem+json` errors with `code`, `detail` and `trace_id`.

- [ ] **Step 6: Compose `/api/v1` and run tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/api/v1/test_setup_auth.py backend/tests/api/v1/test_rbac.py -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/modules/identity backend/app/api backend/app/main.py backend/tests/api/v1
git commit -m "feat: add local setup authentication and roles"
```

### Task 4: Seasons, Teams, Players, Registrations and Consent API

**Files:**
- Create: `backend/app/modules/organizations/{schemas,service,router}.py`
- Create: `backend/app/modules/roster/{schemas,service,router}.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/modules/test_roster_service.py`
- Test: `backend/tests/api/v1/test_organization_roster.py`

**Interfaces:**
- Produces services `create_season`, `create_team`, `create_player`, `register_player`, `record_consent`, `revoke_consent`, `list_roster`.
- Routes: `/api/v1/seasons`, `/api/v1/teams`, `/api/v1/players`, `/api/v1/teams/{team_id}/registrations`, `/api/v1/teams/{team_id}/roster`, `/api/v1/players/{player_id}/consents`.

- [ ] **Step 1: Write failing domain service tests**

Test overlapping registration rejection, unique shirt number per team/season when active, age-at-signature minor detection, guardian requirement for minors, immutable consent evidence hash, revocation audit fields and `publishable=False` without active consent.

- [ ] **Step 2: Write failing API contract tests**

Test UUID responses, organization scoping, role permissions, pagination/filtering, 409 domain conflicts, 422 validation and unknown foreign UUIDs returning 404.

- [ ] **Step 3: Run tests and confirm failure**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/modules/test_roster_service.py backend/tests/api/v1/test_organization_roster.py -v`.

- [ ] **Step 4: Implement Pydantic contracts and services**

Keep transactions in service functions, never routers. Write the compatibility `name`, `team_id`, `jersey_number`, `position` and `preferred_foot` values needed by legacy routes while the transition remains active.

- [ ] **Step 5: Implement scoped routers**

Use the current actor organization and role dependencies; never accept `organization_id` from browser payloads.

- [ ] **Step 6: Run new and regression tests**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/modules backend/tests/api/v1 backend/tests/test_api.py -v`  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/modules/organizations backend/app/modules/roster backend/app/api/v1 backend/tests/modules backend/tests/api/v1
git commit -m "feat: add season and roster management API"
```

### Task 5: TypeScript Frontend Foundation and Approved App Shell

**Files:**
- Create: `frontend/tsconfig.json`, `frontend/tsconfig.node.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/{App,router,providers,i18n}.tsx`
- Create: `frontend/src/styles/{tokens,globals}.css`
- Create: `frontend/src/components/shell/{AppShell,SidebarNavigation,TopRuntimeBar,LocalRuntimeStatus}.tsx`
- Create: `frontend/src/assets/statx-lockup.png`
- Create: `frontend/src/locales/{fr,ar}.json`
- Create: `frontend/playwright.config.ts`
- Modify: `frontend/package.json`, `frontend/tailwind.config.js`, `frontend/index.html`
- Delete: `frontend/src/main.jsx`
- Test: `frontend/src/components/shell/AppShell.test.tsx`
- Test: `frontend/src/app/i18n.test.tsx`

**Interfaces:**
- Produces route shell with protected/public branches and layout variants `desktop | tablet-landscape | tablet-portrait`.
- Produces CSS tokens exactly matching `STATX_VISUAL_DIRECTION.md`.

- [ ] **Step 1: Add frontend test/tooling dependencies**

Add TypeScript, Vitest, jsdom, Testing Library, React Router, TanStack Query, i18next/react-i18next, Zod and Playwright. Add `test`, `test:run` and `test:e2e` scripts and configure isolated frontend/backend web servers.

- [ ] **Step 2: Write failing shell and localization tests**

Assert official brand text/logo alt, primary navigation order, 48 px navigation hit areas, no tracking item, visible local runtime state, Arabic `dir=rtl`, French `dir=ltr` and invariant pitch container direction.

- [ ] **Step 3: Run tests and confirm failure**

Run: `npm run test:run -- AppShell i18n` from `frontend`.

- [ ] **Step 4: Implement tokens and local assets**

Copy the supplied logo into the repository. Bundle font files or use the documented local system fallbacks without any remote request. Replace glow-heavy prototype styles with tonal surfaces and borders.

- [ ] **Step 5: Implement providers, routing and App Shell**

Use persistent desktop sidebar, top runtime bar and tablet navigation. Keep old JSX feature components unimported but untouched for later migration.

- [ ] **Step 6: Run tests and production build**

Run: `npm run test:run`  
Run: `npm run build`  
Expected: tests PASS and Vite build succeeds with no external font/image URL in generated assets.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig* frontend/index.html frontend/tailwind.config.js frontend/src
git commit -m "feat: add StatX product shell and design system"
```

### Task 6: First-Run Setup and Login Experience

**Files:**
- Create: `frontend/src/lib/api/{client,types}.ts`
- Create: `frontend/src/features/setup/{SetupPage,setupSchema,api}.ts*`
- Create: `frontend/src/features/auth/{LoginPage,SessionGate,api}.ts*`
- Modify: `frontend/src/app/router.tsx`
- Test: `frontend/src/features/setup/SetupPage.test.tsx`
- Test: `frontend/src/features/auth/LoginPage.test.tsx`
- Test: `frontend/e2e/setup-login.spec.ts`

**Interfaces:**
- Produces credentialed API client with CSRF header support and problem+json mapping.
- Produces setup routing: uninitialized → setup; initialized unauthenticated → login; authenticated → app.

- [ ] **Step 1: Write failing API client and page tests**

Assert cookies/credentials, CSRF propagation, field errors, generic login failure, password rules, loading/disabled state and successful route transitions.

- [ ] **Step 2: Run tests and confirm failure**

Run: `npm run test:run -- SetupPage LoginPage`.

- [ ] **Step 3: Implement the typed API client**

Expose `request<T>(path, options) -> Promise<T>` and `ProblemDetails`; use `/api/v1`, `credentials:"include"` and the CSRF cookie value for mutations.

- [ ] **Step 4: Implement setup, login and session gate**

Use French copy first, locale switch, accessible form errors and 48 px controls. Do not include licence activation yet; show it as a later setup step marked unavailable in Release 1.

- [ ] **Step 5: Add Playwright setup/login journey**

Test initial setup, logout, failed login and successful login against an isolated backend database.

- [ ] **Step 6: Run unit, E2E and build checks**

Run: `npm run test:run && npm run build`  
Run: `npx playwright test frontend/e2e/setup-login.spec.ts` from repository root with configured web servers.  
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib frontend/src/features/setup frontend/src/features/auth frontend/src/app frontend/e2e frontend/package.json frontend/package-lock.json
git commit -m "feat: add first-run setup and local login"
```

### Task 7: Club, Roster and Player Management UI

**Files:**
- Create: `frontend/src/features/club/{ClubDashboardPage,api}.ts*`
- Create: `frontend/src/features/roster/{RosterPage,PlayerDetailPage,PlayerForm,RegistrationForm,ConsentPanel,api,schemas}.ts*`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/locales/{fr,ar}.json`
- Test: `frontend/src/features/roster/RosterPage.test.tsx`
- Test: `frontend/src/features/roster/ConsentPanel.test.tsx`
- Test: `frontend/e2e/roster-rtl-touch.spec.ts`

**Interfaces:**
- Consumes Release 1 `/api/v1` organization and roster routes.
- Produces working club dashboard, roster filters, player identity view, seasonal registration and consent/revocation UI.

- [ ] **Step 1: Write failing roster/component tests**

Test loading, empty, populated, validation error, permission denied and conflict states. Assert minors show consent requirement, revoked consent is not publishable and provenance/status has text plus icon.

- [ ] **Step 2: Write failing RTL/touch E2E test**

At 1024 × 768, assert navigation and actions have at least 48 px hit boxes, Arabic changes document direction, roster order mirrors appropriately, and a marked pitch placeholder would retain LTR direction.

- [ ] **Step 3: Run tests and confirm failure**

Run: `npm run test:run -- RosterPage ConsentPanel`.

- [ ] **Step 4: Implement club and roster features**

Use TanStack Query for cache/invalidation, Zod for forms and the approved dense cards/tables. Keep tablet portrait lists touch-friendly and avoid hover-only controls.

- [ ] **Step 5: Run complete frontend verification**

Run: `npm run test:run`  
Run: `npm run build`  
Run: `npx playwright test frontend/e2e/setup-login.spec.ts frontend/e2e/roster-rtl-touch.spec.ts`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features/club frontend/src/features/roster frontend/src/app/router.tsx frontend/src/locales frontend/e2e
git commit -m "feat: add club and roster workspace"
```

### Task 8: Release 1 Regression, Offline Asset Audit and Handoff

**Files:**
- Modify: `README.md`
- Modify: `backend/.env.example`
- Modify: `frontend/.env.example`
- Create: `docs/operations/release-1-foundation.md`
- Create: `backend/tests/test_release1_regression.py`

**Interfaces:**
- Produces a reproducible Release 1 setup and verification command set.

- [ ] **Step 1: Write the release regression test**

Exercise setup → login → create season/team/player → register player → record and revoke consent → verify audit and organization isolation. Include an upgraded legacy database fixture.

- [ ] **Step 2: Run the regression test and fix only release blockers**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_release1_regression.py -v`.

- [ ] **Step 3: Audit production frontend assets**

Build and search `frontend/dist` for `http://`, `https://`, Google Fonts, Tailwind CDN and remote image hosts. Expected: none, excluding API URLs intentionally injected at runtime.

- [ ] **Step 4: Run the full retained test suite**

Run: `backend/.venv/Scripts/python.exe -m pytest backend/tests -v`  
Run: `npm run test:run && npm run build` from `frontend`  
Expected: all non-experimental tests PASS; experimental vision tests remain isolated but not deleted.

- [ ] **Step 5: Update operating documentation**

Document Windows commands that avoid PowerShell activation-policy issues by invoking `.venv\Scripts\python.exe` and `npm.cmd` directly. Document migrations, first-run setup, backup recommendation and how to disable LAN access.

- [ ] **Step 6: Commit**

```bash
git add README.md backend/.env.example frontend/.env.example docs/operations backend/tests/test_release1_regression.py
git commit -m "docs: complete foundation release handoff"
```

## Final Release 1 Verification

- [ ] `alembic upgrade head` succeeds on an empty database.
- [ ] `alembic upgrade head` preserves the legacy fixture and IDs.
- [ ] Backend full suite passes.
- [ ] Frontend unit suite and production build pass.
- [ ] Playwright setup/login and roster/RTL/touch journeys pass.
- [ ] No external assets exist in the production frontend bundle.
- [ ] Official logo, French default, Arabic RTL and 48 px touch constraints are visible.
- [ ] Primary navigation contains no computer-vision/tracking modules.
- [ ] Release 1 commits contain no unrelated pre-existing prototype changes.

