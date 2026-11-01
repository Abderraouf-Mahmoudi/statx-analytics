# API-Football Free-Plan Season Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Tunisian club onboarding usable on API-Football's free plan by falling back from a provider-restricted current season to clearly labelled historical season 2024 data.

**Architecture:** Classify the provider's plan restriction at the HTTP boundary without exposing its raw payload, then let the catalog service perform one bounded historical retry. Extend the catalog response with explicit fallback metadata and render that metadata in the existing tactile setup wizard while preserving the selected club's actual season through bootstrap and sync.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy repository cache, HTTPX, pytest, React, TypeScript, Vitest, Testing Library.

**Spec:** `docs/superpowers/specs/2026-11-01-api-football-free-plan-fallback-design.md`

## Global Constraints

- Current-season provider data always has priority.
- Historical fallback is allowed only for API-Football's explicit plan-access season restriction.
- The fallback season is configurable and defaults to `2024`.
- Historical data must always display its actual season and must never be presented as current.
- Invalid credentials, transport errors, quota exhaustion, and unrelated provider errors remain visible failures.
- Manual setup remains available if both provider paths fail.
- Provider credentials and raw provider errors must never appear in API responses, logs, tests, or commits.

## Review Focus

- A generic provider error must not trigger a historical retry; Task 1 and Task 2 pin this branch.
- A failed historical retry must remain a sanitized provider failure and leave manual setup available; Task 2 pins it.
- Duplicate clubs returned by competitions with different seasons must retain the newest accessible season; Task 2 pins it.
- A successful current-season catalog must not display a historical warning; Task 3 pins it.
- Selecting a historical club must send season `2024`, not the current year, to bootstrap; Task 3 pins it.

---

### Task 1: Classify the provider's season-plan restriction

**Files:**
- Modify: `backend/app/modules/integrations/api_football.py`
- Test: `backend/tests/modules/integrations/test_api_football_client.py`

**Interfaces:**
- Consumes: API-Football's HTTP 200 error envelope with `errors.plan`.
- Produces: `ProviderSeasonRestricted(ProviderUnavailable)` for the explicit inaccessible-season plan response; all other error envelopes continue to produce `ProviderUnavailable`.

- [ ] **Step 1: Write the failing transport-boundary tests**

Add `test_client_classifies_free_plan_season_restriction_without_exposing_provider_text` and extend the generic-envelope test. Assert that the documented `errors.plan` response raises `ProviderSeasonRestricted`, while token/generic errors raise exactly `ProviderUnavailable`; assert neither exception contains the API key or raw provider text.

- [ ] **Step 2: Run the focused tests and verify RED**

Run from `backend`: `..\..\..\backend\.venv\Scripts\python.exe -m pytest tests/modules/integrations/test_api_football_client.py -q`

Expected: FAIL because `ProviderSeasonRestricted` does not exist and the plan envelope is not classified.

- [ ] **Step 3: Implement the minimal exception classification**

In `api_football.py`, add `class ProviderSeasonRestricted(ProviderUnavailable)` and a private predicate that recognizes only a mapping with a `plan` message containing both the inaccessible-season and allowed-range markers. Raise the typed exception with a constant sanitized message; keep the existing generic behavior for every other non-empty `errors` value.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the Step 2 command. Expected: all tests in the file PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/integrations/api_football.py backend/tests/modules/integrations/test_api_football_client.py
git commit -m "fix: classify provider season restrictions"
```

### Task 2: Add the bounded historical catalog fallback

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/app/modules/integrations/catalog.py`
- Modify: `backend/app/modules/integrations/schemas.py`
- Modify: `backend/app/modules/integrations/setup_router.py`
- Modify: `backend/app/modules/integrations/router.py`
- Test: `backend/tests/api/v1/test_setup_provider_catalog.py`
- Test: `backend/tests/test_database_config.py`

**Interfaces:**
- Consumes: `ProviderSeasonRestricted` from Task 1 and `Settings.api_football_free_plan_fallback_season`.
- Produces: `ClubCatalog.historical_fallback: bool`, `ClubCatalog.historical_season: int | None`, and clubs whose `season` is the season actually queried.

- [ ] **Step 1: Write failing catalog and configuration tests**

Add tests proving: current data returns with `historical_fallback=False`; an explicit restriction for season 2026 retries the same league once with season 2024 and returns `historical_fallback=True`, `historical_season=2024`; generic unavailability performs no retry; a failed fallback propagates the sanitized failure; duplicate clubs keep the greater season. Add a settings test asserting the default fallback season is `2024`.

- [ ] **Step 2: Run the focused backend tests and verify RED**

Run from `backend`: `..\..\..\backend\.venv\Scripts\python.exe -m pytest tests/api/v1/test_setup_provider_catalog.py tests/test_database_config.py -q`

Expected: FAIL because the fallback configuration, response fields, and retry branch do not exist.

- [ ] **Step 3: Implement the fallback setting and catalog behavior**

Add `api_football_free_plan_fallback_season: int = Field(default=2024, ge=2000, le=2200)` and document `API_FOOTBALL_FREE_PLAN_FALLBACK_SEASON=2024` in `.env.example`. Give `TunisianClubCatalogService.__init__` a keyword-only `historical_fallback_season: int = 2024`. For each current competition, catch only `ProviderSeasonRestricted`, retry `/teams` once with the fallback season, and record fallback metadata. When deduplicating provider team IDs, replace an older-season club with a newer-season club.

- [ ] **Step 4: Extend the API contract and route wiring**

Add the two response fields to `ClubCatalog`, defaulting to `False` and `None`. Pass `settings.api_football_free_plan_fallback_season` to the catalog service from both public setup and authenticated integration routes.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all focused tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/.env.example backend/app/config.py backend/app/modules/integrations backend/tests/api/v1/test_setup_provider_catalog.py backend/tests/test_database_config.py
git commit -m "feat: fall back to accessible provider season"
```

### Task 3: Label historical data in the tactile setup flow

**Files:**
- Modify: `frontend/src/features/setup/providerCatalogApi.ts`
- Modify: `frontend/src/features/integrations/apiFootballApi.ts`
- Modify: `frontend/src/features/setup/ClubStep.tsx`
- Modify: `frontend/src/features/setup/SetupWizard.test.tsx`

**Interfaces:**
- Consumes: `historical_fallback` and `historical_season` from Task 2.
- Produces: a visible `Données historiques — saison 2024` warning and a bootstrap payload that retains the chosen club's actual season.

- [ ] **Step 1: Write the failing setup-wizard tests**

Add a historical catalog fixture and test that Step 2 displays `Données historiques — saison 2024`, each club still displays its league and actual season, and selecting the club submits `selected_club.season === 2024`. Add an assertion to the existing current-season test that the historical warning is absent.

- [ ] **Step 2: Run the focused frontend test and verify RED**

Run from `frontend`: `npm.cmd run test:run -- src/features/setup/SetupWizard.test.tsx`

Expected: FAIL because the warning and typed metadata do not exist.

- [ ] **Step 3: Implement the typed warning**

Extend both catalog interfaces with `historical_fallback: boolean` and `historical_season?: number | null`. In `ClubStep`, render a tactile-safe warning using the existing `status-badge warning` styling only when `historical_fallback` is true, with the exact text `Données historiques — saison 2024`. Keep the existing club card and selection payload behavior so the provider season remains authoritative.

- [ ] **Step 4: Run the focused frontend test and verify GREEN**

Run the Step 2 command. Expected: all tests in `SetupWizard.test.tsx` PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/setup frontend/src/features/integrations/apiFootballApi.ts
git commit -m "feat: label historical provider catalog data"
```

### Task 4: Verify regression safety and the real free-plan flow

**Files:**
- Modify only if a verification failure exposes a covered defect.

**Interfaces:**
- Consumes: completed Tasks 1–3 and the locally configured API-Football key.
- Produces: test, build, and live-response evidence that the setup screen can list Tunisian clubs without mislabelling season 2024.

- [ ] **Step 1: Run the complete backend suite**

Run from `backend`: `..\..\..\backend\.venv\Scripts\python.exe -m pytest -q`

Expected: all backend tests PASS.

- [ ] **Step 2: Run the complete frontend suite**

Run from `frontend`: `npm.cmd run test:run`

Expected: all frontend tests PASS.

- [ ] **Step 3: Build the frontend**

Run from `frontend`: `npm.cmd run build`

Expected: exit code 0.

- [ ] **Step 4: Restart only the backend and verify the live catalog**

Restart Uvicorn with the repository's complete virtual environment, request `/api/v1/setup/provider-catalog`, and assert HTTP 200, at least one Tunisian club, `historical_fallback=true`, `historical_season=2024`, and every fallback club's visible season is 2024. Do not print the provider key or raw upstream payload.

- [ ] **Step 5: Verify the tablet URL**

Request the frontend and backend through the LAN address and expect HTTP 200, then open Step 2 on the tablet and confirm the historical warning and club cards are visible.

- [ ] **Step 6: Commit any verification-only fixtures if required**

If no files changed, make no empty commit. Otherwise commit only the minimal covered fix after repeating its RED/GREEN cycle.

