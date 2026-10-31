# StatX Analytics Delivery Roadmap

**Spec:** `docs/superpowers/specs/2026-10-30-statx-mvp-foundation-design.md`  
**Visual reference:** `docs/design/stitch/STATX_VISUAL_DIRECTION.md`

The MVP is divided into four independently testable releases. Each release receives its own implementation plan before execution.

## Release 1 — Product Foundation and Roster

Delivers a real installable application foundation: Alembic migrations, organizations, local users, roles, seasons, teams, player identities, registrations, consent, the visual App Shell, first-run setup, login, club dashboard and roster management.

Plan: `docs/superpowers/plans/2026-10-30-statx-foundation-roster-implementation.md`

## Release 2 — Match Workspace and Validated Tagging

Delivers match creation, lineup and participation, local video assets, clips, desktop/tablet tagging, offline command queue, immutable event revisions, analyst validation and audit evidence.

Exit criterion: a club analyst can prepare and validate one match without Internet, including a tablet disconnection and duplicate-free synchronization.

## Release 3 — Analytics, Passports and Reports

Delivers versioned analysis runs, metric provenance, tactical evidence, visualizations, passport versions, certification, local QR verification and one-page FR/AR reports.

Exit criterion: every published metric links to validated source revisions and a certified passport/report can be verified locally.

## Release 4 — Physical Data and Operational Hardening

Delivers sensor import/mapping, persistent long jobs, offline licence verification, encrypted backup/restore, diagnostic bundle, Windows packaging and the pilot-club acceptance suite.

Exit criterion: an administrator installs, licenses, backs up, restores and operates the complete product on the pilot hardware.

## Deferred Experimental Track

YOLO, ByteTrack, homography and automatic player identification remain isolated behind experimental flags. They do not block any MVP release and cannot feed certified output unless later promoted through the same provenance and validation contracts.

