# StatX Account, Tunisian Club Import and Player Enrichment — Design

## Intent

Turn first launch into one coherent, professional setup journey: the creator identifies their football function, chooses a current Tunisian club from a simple provider-backed list, creates the local StatX workspace, and immediately receives a usable current-season club profile and roster. Imported data accelerates setup, while club-owned edits, academy players, portraits and operational decisions remain authoritative inside StatX.

This design extends the existing Release 1 foundation and the approved player-media/provider-sync design. It fixes the observed gap where the application was bootstrapped manually, no provider club was selected, no synchronization ran, and consequently no player photo record existed for the cards to display.

## Goals

- Ask for the creator's football function during first setup.
- Keep the creator technically capable of administering the installation.
- Present a simple list of teams participating in Tunisia's current covered competitions.
- Bind the selected provider club to the organization during setup.
- Import the current season, team identity, crest, squad, player portraits, fixtures, results and standings.
- Enrich squad members with the provider's season profile and statistics when quota permits.
- Display portraits and useful player attributes on responsive touch-friendly cards.
- Replace free-text position entry with a normalized selectable position list.
- Let authorized staff add, edit, deactivate and remove players without losing historical match integrity.
- Preserve offline operation, provenance, audit history and the 100-call free-plan budget.

## Non-goals

- Scrape Transfermarkt or treat its pages as a machine-readable source.
- Claim that API-Football supplies contracts, agents or market valuations.
- Make Internet access mandatory after setup.
- Delete historical player, registration, event or match references during roster cleanup.
- Let React call API-Football directly or receive the provider key.
- Download every possible player statistic during every login or page view.

## Anti-goals

- Conflating a person's football job with authorization privileges.
- Creating a non-admin first user who cannot manage the installation they created.
- Hiding import failures behind an apparently empty roster.
- Showing a broken image element when no portrait is ready.
- Overwriting a locally corrected field during provider refresh.
- Guessing player identity from a name match.
- Spending provider quota merely by reopening a page.

## Constraints

- API-Football free plan allows 100 calls per day; StatX keeps a configurable safety ceiling of 90.
- Tunisia and per-feature coverage vary by competition and season.
- Provider images are identification assets; club publication and consent remain separate decisions.
- Existing organization isolation, CSRF, local authentication, audit and consent rules remain binding.
- The app must remain usable at 1024 × 768 with 48 px minimum touch targets.
- The first setup must survive provider timeout, missing coverage or exhausted quota.
- Existing manually created organizations, seasons, teams and players must migrate without loss.

## Approaches considered

### A. Provider-owned product

Make API-Football the source of truth and prevent most local editing. This is operationally brittle for academy players, transfers, Tunisian coverage gaps and provider outages. Rejected.

### B. Hybrid provider seed with club-owned overrides — selected

API-Football seeds current public facts and seasonal data. StatX stores a durable local copy, marks provenance per field, and lets authorized staff override provider facts or add local players. Refreshes update only provider-owned fields. This matches the validated product direction.

### C. Transfermarkt-style scraping

Would appear richer initially, but creates licensing, stability, anti-bot and provenance risks and is unsuitable for a real club product. Rejected. Transfermarkt remains a reference for which facts users value, not a data source.

## Roles: authorization versus football function

The first creator receives:

- security role `admin` (displayed as **Propriétaire**), because they own the local installation;
- a separate required `job_title`: `director`, `coach`, `analyst`, `scout`, `medical`, `media`, or `other`.

Later users receive an explicit security role (`admin`, `coach`, `analyst`, `viewer`) and their independent football function. Authorization checks continue to use the security role only. The job title is profile and workflow context, never an implicit permission grant.

Add `users.job_title` and expose both `role` and `job_title` in the session view. Existing users migrate with `job_title = other` and retain their current role.

## First-run setup journey

The setup wizard is one visual flow with three persistent client steps and one final server command:

1. **Votre profil** — display name, email, password and football function.
2. **Votre club** — current Tunisian competition filter and a searchable/selectable team list with crest, name, competition and season.
3. **Confirmation** — selected role/function, club and season, plus a clear explanation of imported data and image rights.
4. **Créer et importer** — atomically create the organization, owner/admin membership and selected provider-team binding, then queue a persisted synchronization run.

Before bootstrap, the browser may call only a narrow installation endpoint:

- `GET /api/v1/setup/provider-catalog`

This endpoint works only while `system_state.bootstrapped` is false. It returns a sanitized cached Tunisia catalog. A cache refresh is protected by the existing quota counter and setup lock. It never exposes the provider key. After bootstrap it returns `409 setup_complete`.

The final setup command accepts the selected provider identifiers and current season metadata. Account creation remains successful if remote synchronization later fails. The authenticated user sees a retryable progress screen rather than losing the account.

If the integration is not configured or unavailable, the wizard offers **Créer sans import** with an explicit manual club name. Provider selection can be resumed later from Settings.

## Provider catalog and current season

The backend determines the current season from provider data, not from the calendar alone:

1. `/leagues?country=Tunisia&current=true`
2. retain current seasons whose competition type and coverage are usable;
3. `/teams?league={league_id}&season={season}` for each retained competition;
4. deduplicate teams by immutable provider team ID;
5. cache the resulting catalog for seven days.

The UI defaults to the highest covered domestic senior competition but lets the creator switch competition when multiple Tunisian leagues are available. It shows a simple list/grid; it does not ask the user to type provider IDs.

## Initial import pipeline

After selection, a persisted sync run performs bounded, observable stages:

1. selected team identity and crest;
2. current squad from `/players/squads?team={team_id}`;
3. current-season player profiles/statistics from paginated `/players?team={team_id}&season={season}` when coverage and quota allow;
4. fixtures/results for the selected team, league and season;
5. standings when covered;
6. provider portrait queue for players without a club-owned portrait.

The fast squad import commits usable roster data even if optional statistical enrichment is unavailable. Each stage has `pending`, `running`, `completed`, `skipped` or `failed` status and a sanitized count. Required-stage validation remains atomic; optional enrichment never rolls back a valid squad.

No provider call occurs on ordinary roster navigation. Explicit refresh policies are:

- catalog, team, squad and profiles: seven days;
- fixtures and standings: thirty minutes when explicitly refreshed;
- completed historical fixtures: effectively immutable unless manually refreshed;
- portraits: once per provider URL change, unless retried after failure.

## Player model

### Identity and physical profile

Store normalized fields:

- `first_name`, `last_name`, `display_name`;
- `birth_date`, derived age in views only;
- `birth_place`, `birth_country`, `nationality`;
- `height_cm`, `weight_kg`;
- `preferred_foot` (`left`, `right`, `both`, `unknown`);
- `primary_position` and optional `secondary_positions`;
- provider identity, timestamps and absence state.

### Normalized positions

Use a controlled enum and select component:

- `GK` goalkeeper
- `RB`, `CB`, `LB` defenders
- `DM`, `CM`, `AM` midfielders
- `RW`, `LW`, `ST` attackers
- `OTHER` only when the source cannot be mapped

Provider position labels map centrally to these codes. Manual forms use a dropdown; no free-text position is accepted for new records.

### Seasonal registration and statistics

Registration remains the authority for team, season, shirt number, position and status. Add a versioned `player_season_snapshots` table for provider statistics rather than expanding the player identity row indefinitely. A snapshot contains:

- organization, player, team, season and provider identity;
- appearances, starts, minutes and rating;
- goals, assists, shots and shots on target;
- passes, key passes and pass accuracy;
- tackles, interceptions, duels and dribbles;
- fouls, cards and penalties;
- sanitized raw-provider payload for fields StatX does not yet visualize;
- capture timestamp and schema version.

The identity card shows only stable identity/registration facts. Detailed seasonal statistics live in the player workspace.

### Per-field provenance and overrides

Replace the coarse `local_override` behavior with field-level provenance. Add a `player_field_overrides` JSON object whose keys are editable field names and whose values contain source, editor, timestamp and optional note. Provider refresh updates fields not present in this override map.

Club-owned portraits always outrank provider portraits. Removing a club portrait reveals the latest ready provider identification portrait when available.

## Player lifecycle

- **Add:** create manual identity plus seasonal registration; portrait is optional and retryable.
- **Edit:** admin/coach updates selected fields and records field-level override provenance.
- **Deactivate:** end or deactivate the current registration while preserving identity and history.
- **Remove from current roster:** soft operation on registration, never destructive deletion.
- **Hard delete:** allowed only for an unused mistaken identity with no registration history, events, media or audit dependency; admin-only and explicitly confirmed.
- **Provider absence:** mark `provider_absent`; never auto-delete or auto-deactivate a club-confirmed registration.

## Portrait state and card behavior

The observed empty portraits are explained by database state: two manual players exist and `player_photos` contains zero rows. The card correctly renders a silhouette because it only requests media when `photo_status == ready`.

Improve the experience so the cause is visible:

- `no_photo`: silhouette plus **Ajouter une photo** action;
- `pending` or `processing`: preview/skeleton plus progress badge and polling;
- `failed`: original-safe preview when authorized, error badge and retry action;
- `ready`: authenticated cutout endpoint with ETag;
- provider portrait: identification-rights badge;
- club portrait: club-authorized badge and priority.

After manual player creation, the result explicitly says whether the player was created and whether portrait upload/processing was queued. A failed portrait upload never reports the entire player creation as failed.

## API surface

### Setup and session

- `GET /api/v1/setup/status`
- `GET /api/v1/setup/provider-catalog`
- `POST /api/v1/setup/bootstrap` extended with `job_title` and optional selected-club command
- `GET /api/v1/session` returns security role and football function

### Provider operations

- existing status, catalog, selection, refresh and sync-run routes remain authenticated after setup;
- sync-run view gains per-stage state and imported/skipped/failed counts;
- add an explicit `POST /integrations/api-football/enrich-players` admin action when optional enrichment was skipped for quota.

### Player management

- `PATCH /api/v1/players/{player_id}` for controlled editable fields and override provenance;
- `POST /api/v1/players/{player_id}/registrations` or existing team registration route for seasonal moves;
- `DELETE /api/v1/players/{player_id}/registrations/{registration_id}` performs roster removal/deactivation;
- `DELETE /api/v1/players/{player_id}` exists only for safe unused identities and returns a conflict otherwise;
- existing authenticated photo routes remain.

Every mutation derives organization from the authenticated actor and writes an audit record.

## UI surfaces

### Setup wizard

- compact three-step progress header;
- function dropdown;
- competition selector and searchable club list;
- selected-club summary;
- import scope and rights explanation;
- offline/manual fallback;
- touch targets of at least 48 px.

### Roster

- default current primary team and current provider season;
- filters for position, registration status, source and portrait state;
- cards show portrait, shirt number, name, primary position, preferred foot and provenance;
- card action opens player workspace;
- clear add-player action remains available.

### Player workspace

- identity and physical profile;
- current and historical registrations;
- portrait management;
- provider-vs-club provenance indicators;
- season statistics snapshot;
- edit, deactivate and safe-delete actions according to permissions.

## Transfermarkt reference boundary

Use Transfermarkt only as a product-reference checklist: users expect coherent identity, club, position, nationality, birth, physical profile, registration history and seasonal performance. StatX does not copy its layout, scrape its pages, reuse its images or claim unsupported values such as market valuation. Provider-sourced values come from API-Football and are labeled; club-entered values remain club-owned.

## Security, privacy and data rights

- Rotate the API key previously shared in chat before enabling live import.
- Store the new key only in ignored `backend/.env` as a secret setting.
- Keep pre-bootstrap catalog access disabled after installation and rate limited before installation.
- Never serialize provider headers, secrets or unbounded raw responses.
- Keep portraits organization-scoped and authenticated.
- Strip image metadata and preserve the existing validation/segmentation pipeline.
- Separate provider identification rights, club authorization and player consent.
- Audit setup selection, sync, field override, portrait, registration and deletion actions.

## Migration and compatibility

- Add nullable `users.job_title`, backfilled to `other`.
- Add new player identity/profile columns without changing existing public IDs.
- Migrate existing `position` values through the normalized mapping; unmapped values become `OTHER` while preserving the original in audit/provenance data.
- Add `secondary_positions` and `player_field_overrides` JSON defaults.
- Add `player_season_snapshots` and sync-stage persistence.
- Existing manual team, season and players remain valid.
- Existing first installation is not forced back through setup; Settings exposes **Associer un club API-Football** to run the same club-selection/import flow.

## Failure handling

- Missing/rotated key: manual setup and roster remain usable; show configuration action to admin.
- No current Tunisia coverage: offer manual club and season creation with a visible provider-coverage message.
- Provider timeout/quota exhaustion: use valid cache; otherwise create account without import and keep a retryable queued action.
- Optional profile pagination failure: retain squad and mark enrichment incomplete.
- Portrait download/segmentation failure: retain player and provider URL, expose retry, never show a broken image.
- Duplicate provider ID: fail the affected required stage without guessing a merge.
- Local/provider conflict: preserve override and show the incoming provider value for review.

## Verification and acceptance

- Existing databases migrate with the current admin, organization and two manual players intact.
- First setup captures football function and still creates an owner/admin security role.
- Before bootstrap, the provider catalog is sanitized, quota-bound and unavailable after setup.
- Club selection uses a list; no provider ID or free-text position is requested from the user.
- Current provider season drives the imported season.
- Required initial import is idempotent and produces no duplicate teams, players or registrations.
- Player enrichment is paginated, cached and safely skippable near the quota reserve.
- Provider and manual portraits reach a visible ready/pending/failed card state.
- Local field overrides and club portraits survive refresh.
- Add, edit, deactivate and safe-delete behavior is organization-scoped and audited.
- Provider outage does not prevent account creation or manual roster work.
- Frontend unit tests cover wizard state, normalized positions, card photo states and CRUD errors.
- Backend tests cover migrations, authorization, quota, pagination, idempotency, per-field overrides and deletion guards.
- Playwright covers setup → role → current league/team selection → import progress → roster cards on tablet.

