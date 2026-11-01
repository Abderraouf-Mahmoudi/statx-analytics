# API-Football free-plan season fallback

## Intent

Keep club-first onboarding usable with an API-Football free-plan key without presenting historical data as current. The provider currently exposes Tunisia's current competitions but rejects their 2025–2026 team data on the free plan, whose accessible window ends in 2024.

## Goals

- Try each competition's current season first.
- Fall back to season 2024 only when API-Football explicitly reports a plan-access restriction for the current season.
- Show the actual season on every club choice and clearly label fallback results as historical data.
- Preserve manual setup when neither current nor historical provider data is available.
- Resume current-season behavior automatically when the configured API plan allows it.

## Non-goals

- Do not infer or fabricate a current roster from the 2024 response.
- Do not hide provider errors unrelated to plan access, such as invalid credentials, transport failures, or exhausted quota.
- Do not scrape Transfermarkt or another third-party website.

## Selected approach

The catalog service will keep the current-season request as the primary path. When the provider returns its explicit free-plan season error, it will retry that competition with the configured historical fallback season, initially 2024. Clubs returned by that request retain `season=2024`; the API catalog will additionally expose whether historical fallback was used so the frontend can display an unambiguous warning.

Alternative approaches considered:

- Paid-plan-only current data: most accurate, but blocks onboarding with the user's current plan.
- Manual-only current roster: accurate when maintained by the club, but discards the useful provider catalog and adds avoidable setup work.

The selected hybrid keeps onboarding operational now and upgrades naturally when the provider subscription changes.

## Acceptance criteria

- A current-season response succeeds without a fallback request or warning.
- The documented API-Football plan restriction triggers a bounded retry for season 2024.
- Other provider failures remain visible and do not trigger a misleading fallback.
- The club picker displays `Données historiques — saison 2024` for fallback results.
- Selecting a historical club stores and synchronizes the actual 2024 season.
- Manual setup remains available if the fallback also fails.
- Backend and frontend regression suites remain green.
