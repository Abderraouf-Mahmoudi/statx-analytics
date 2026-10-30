# StatX Analytics — Google Stitch Prompt Pack

## How to use this pack

1. Create a new Stitch project.
2. Upload `C:\Users\MSI\Downloads\SVG Master Lockup.png` as the official brand reference.
3. Paste the **Master Prompt** first.
4. Ask Stitch to create the **Design System + App Shell** before generating all product screens.
5. Generate the screen batches in order with the follow-up prompts below.
6. Keep every screen in the same project so Stitch reuses the same design language.
7. Export the final project, frontend assets and `DESIGN.md`.

Do not ask Stitch to redesign the logo. The attached lockup is the source of truth.

---

## Master Prompt — paste this first

```text
You are a senior product designer and design systems lead specializing in professional sports analytics, touch-first data applications, offline workflows, and bilingual French/Arabic interfaces.

Design a complete high-fidelity product UI/UX system for “StatX Analytics — Football Data Lab”. This is a real football analysis application used by club analysts, coaches and administrators. It is not a marketing website, landing page, fantasy football product, betting product, gaming dashboard, or futuristic AI demo.

BRAND ASSET
Use the attached “Stat X — Football Data Lab” logo as the official logo and visual reference. Preserve its proportions, spacing, white wordmark and bright green geometric accents. Never redraw, distort, recolor or add effects to the logo. Provide lockup usage on dark backgrounds and a compact icon treatment derived only from the existing square symbol.

PRODUCT PURPOSE
StatX Analytics transforms local club data into verified tactical analysis and certified player passports without requiring Internet access. The main workflow is:
Club and roster → Match and lineup → Local video import → Manual touch tagging → Review and validation → Versioned analytics → Player passport → Certified QR and PDF report.

Automatic YOLO tracking and automatic player identification are experimental future features. Do not make AI tracking the primary navigation or the main product story.

USERS
1. Club administrator: users, roles, seasons, teams, licence, backups and restore.
2. Analyst: match preparation, video, tagging, validation, analysis and reports.
3. Coach: tactical analysis, reports and player profiles.
4. Read-only user: authorized viewing only.

PLATFORMS AND FRAMES
Create responsive high-fidelity screens for:
- Desktop analyst console: 1440 × 1024.
- Tablet landscape tagging mode: 1024 × 768.
- Tablet portrait management/profile mode: 820 × 1180.
Do not design a phone-first application.

DESIGN DIRECTION
Create a premium, professional, credible football intelligence product. The visual tone should feel precise, calm, operational and trustworthy — closer to elite club performance software than esports or crypto dashboards.

Use a dark “Pitch Intelligence” visual system:
- App canvas: #070B12 or #0B0F19.
- Sidebar/deep surface: #080D15.
- Primary cards: #111827.
- Elevated surfaces: #162033.
- Borders/dividers: #263244.
- Primary text: #F8FAFC.
- Secondary text: #94A3B8.
- Brand highlight: #4ADE80.
- Main action green: #10B981.
- Informational cyan: #22D3EE.
- Warning amber: #F59E0B.
- Critical red: #EF4444.

Use the green deliberately for main actions, selected navigation, confirmed data and positive status. Do not flood every card with green. Never rely only on green versus red to communicate meaning; also use icons, text and patterns.

TYPOGRAPHY
- Use Inter or an equivalent highly legible sans-serif for the main interface.
- Use a compact monospaced font such as JetBrains Mono only for telemetry, timestamps and technical identifiers.
- Strong hierarchy, tabular numerals for scores and statistics, readable minimum text size.
- Avoid tiny labels and excessive all-caps text.

LAYOUT AND COMPONENT LANGUAGE
- 8 px spacing grid.
- 12–16 px card radius; no excessive pill-shaped containers.
- 1 px low-contrast borders with restrained shadows.
- Dense but calm desktop information layout.
- Touch targets at least 48 × 48 px on tablet.
- No action available only through hover.
- Persistent desktop sidebar and contextual top bar.
- Tablet uses simplified contextual navigation and a bottom navigation when useful.
- Keep the active match, score, synchronization state and user role visible.

CORE NAVIGATION
- Vue club
- Effectif
- Match Center
- Analyses
- Passeports
- Imports physiques
- Administration

MATCH CENTER WORKFLOW
Make Match Center a clear step-based workspace:
1. Contexte du match
2. Composition
3. Vidéo
4. Tagging
5. Validation
6. Analyse
7. Publication

The analyst must always know which step is complete, blocked, in progress or needs validation.

TOUCH TAGGING EXPERIENCE
The tablet landscape tagging screen is a flagship screen. It must include:
- Match score and period.
- Local video player with large controls.
- Large player selector with jersey number and position.
- Large event actions: Passe, Tir, Récupération, Perte, Faute and More.
- Two-tap maximum for the most common event.
- Football pitch location input after choosing the event when required.
- Event timeline with large scrub handle.
- Undo action available for five seconds.
- Explicit states: saved locally, waiting for synchronization, synchronized, conflict.
- No hidden destructive gestures.

ANALYTICS PRINCIPLES
Every number must look traceable rather than magical. Show:
- Source/provenance level A, B or C.
- Calculation version.
- Number of underlying events or denominator where relevant.
- Confidence or availability state.
- “xG indisponible” instead of displaying 0 when no approved xG source/model exists.

Tactical insight cards should separate normal, offensive and defensive analysis. Provide evidence links from an insight back to source events or video clips.

BILINGUAL AND RTL
The main screen set should use French UI copy. Also generate Arabic RTL variants for:
- Club dashboard.
- Tablet tagging screen.
- Player passport.
- PDF/report preview.

Mirror layout direction and text alignment in RTL, but do not automatically mirror football pitch coordinates, team attack direction or time-series meaning. Use realistic Arabic placeholders and leave terminology easy to replace after linguistic validation.

OFFLINE AND TRUST STATES
Design explicit visual states for:
- Online on local network.
- Working offline locally.
- Commands waiting to synchronize.
- Successful synchronization.
- Version conflict requiring analyst choice.
- Licence expired in read-only mode.
- Missing media.
- Long-running analysis or PDF generation.
- Backup progress and verified restore.

MOTION
Use functional motion only:
- 120–180 ms for control feedback.
- 220–300 ms for drawers, panels and step transitions.
- Clear progress motion for upload, processing and synchronization.
- No decorative looping animations.
- Include reduced-motion behavior.

ACCESSIBILITY
- WCAG AA contrast.
- Visible keyboard focus.
- Keyboard shortcuts on the desktop tagging workspace.
- Screen-reader labels for icon-only actions.
- Error messages next to the affected input.
- Do not communicate status through color alone.

DESIGN SYSTEM DELIVERABLE
Create a dedicated design system page containing:
- Brand usage and logo safe space.
- Color tokens and semantic colors.
- Typography scale.
- Spacing, radius, border and elevation tokens.
- Desktop sidebar, tablet bottom navigation and top bar.
- Buttons: primary, secondary, ghost, destructive and icon.
- Inputs, selects, date/time controls and search.
- Tables, filters, pagination and empty states.
- Badges: role, provenance, confidence, synchronization and job status.
- Cards: KPI, tactical insight, player, match and warning.
- Modal, confirmation dialog, drawer, tablet bottom sheet, toast and undo snackbar.
- Skeleton, spinner, progress bar and long-running job state.
- Video controls, event palette, timeline and pitch location selector.
- Charts with accessible legends, tooltips and no red/green-only distinction.
- Every component in default, hover, focus, pressed, disabled, loading, success and error states.

REQUIRED SCREENS
Generate the following product screens with realistic football data and French copy:
1. First-run setup wizard and local administrator creation.
2. Login and locked/read-only licence states.
3. Club dashboard.
4. Teams, seasons and roster list.
5. Player profile and registration history.
6. Player passport overview and version history.
7. Match list and filters.
8. Create Match / Match Setup wizard.
9. Lineup and substitutions editor.
10. Local video import and clip trimming.
11. Desktop Match Center tagging workspace.
12. Tablet landscape tagging workspace.
13. Validation queue and event revision comparison.
14. Match analytics overview.
15. Tactical insights: normal, offensive and defensive tabs.
16. Shot map, pass map and heatmap detail.
17. Sensor data import: preview, column mapping, validation and commit.
18. Passport builder: sources, confidence and certification.
19. One-page report preview in French and Arabic.
20. Administration: users, roles, audit, licence, backup and restore.

FOR EACH IMPORTANT SCREEN
Provide at least the relevant states among:
- populated/default;
- loading/skeleton;
- empty;
- validation error;
- permission denied;
- offline/pending synchronization;
- conflict;
- read-only licence;
- long-running job;
- success.

CONTENT RULES
- Use realistic club, player, score and match content rather than lorem ipsum.
- Use French labels and concise operational language.
- Do not invent cloud synchronization, social feeds, betting, scouting marketplace or fan features.
- Do not present experimental computer vision as complete or certified.
- Do not use fake percentages without showing the supporting sample size.

AVOID
- Generic SaaS dashboard appearance.
- Cyberpunk, gaming HUD, glowing neon overload or glassmorphism everywhere.
- Excessive gradients.
- Tiny telemetry text.
- Huge empty hero areas.
- Marketing copy inside the operational product.
- Phone-style cards stretched across desktop.
- Important controls hidden in kebab menus.
- Decorative football imagery that competes with operational data.

OUTPUT EXPECTATIONS
Create one coherent product, not disconnected concepts. Reuse the same components, tokens and spacing across all screens. Use Auto Layout/responsive constraints. Name layers and components semantically. Produce a clickable prototype for the primary flow:
Roster → Match Setup → Video Import → Tagging → Validation → Analytics → Passport → Certified Report.

At the end, export:
- All desktop and tablet screens.
- Design system and reusable components.
- Clickable primary flow.
- Frontend assets.
- Generated frontend code where available.
- DESIGN.md with tokens, component rules, responsive behavior and motion guidelines.
```

---

## Follow-up 1 — Design system and shell

```text
Using the approved StatX master brief and attached official logo, generate only the design system page and responsive application shell first.

Show:
- Desktop 1440 px shell with sidebar, top bar, match context and synchronization status.
- Tablet landscape and portrait shells.
- French LTR and Arabic RTL shell variants.
- All navigation states and role-aware navigation.
- Brand tokens, semantic colors, typography, spacing and component states.

Do not generate feature screens yet. Keep the visual language professional, restrained and operational. Make sure the logo remains unchanged and clearly readable.
```

## Follow-up 2 — Foundation and roster screens

```text
Continue with the exact same StatX design system. Generate screens 1–6:
first-run setup, login/licence states, club dashboard, teams/seasons/roster, player profile, and player passport history.

Include populated, empty, loading, permission and validation-error states. Include a minor player with visible consent status. Create desktop and relevant tablet portrait variants. Add Arabic RTL variants for the club dashboard and player passport.
```

## Follow-up 3 — Match Center and touch tagging

```text
Continue with the exact same StatX design system. Generate screens 7–13:
match list, match setup wizard, lineup editor, local video import/trim, desktop tagging workspace, tablet landscape tagging workspace, and validation/revision comparison.

This is the most important workflow. Optimize the tablet tagging screen for fingers, 48 px minimum touch targets, two taps maximum for common events, visible undo, large timeline controls and explicit offline/sync/conflict states. The desktop screen may be denser and must include keyboard shortcut hints.

Create a clickable flow from match creation through validated events. Also create an Arabic RTL version of the tablet tagging screen without mirroring pitch coordinates.
```

## Follow-up 4 — Analytics and tactical insights

```text
Continue with the exact same StatX design system. Generate screens 14–16:
match analytics overview, tactical insights with Normal/Offensif/Défensif modes, and detailed shot map/pass map/heatmap views.

Every insight must expose evidence: provenance grade, confidence, denominator, calculation version, and a link back to events or clips. Show “xG indisponible” when there is no approved source. Use accessible charts and never rely on red versus green alone.
```

## Follow-up 5 — Imports, passport, reports and administration

```text
Continue with the exact same StatX design system. Generate screens 17–20:
sensor import and column mapping, passport builder and certification, one-page report preview, and administration for users/roles/audit/licence/backup/restore.

Show long-running jobs, recoverable errors, backup verification, read-only licence state and certification confirmation. Create French and Arabic RTL report previews. The passport QR area must communicate local verification and document fingerprint without implying a public cloud verification service.
```

## Final audit prompt

```text
Audit the complete StatX project for consistency and production readiness.

Check and correct:
- Logo integrity and brand consistency.
- Shared components and token reuse.
- Desktop/tablet responsiveness.
- 48 px minimum touch targets.
- French and Arabic RTL behavior.
- WCAG AA contrast and visible focus.
- Offline, pending sync, conflict and read-only states.
- Loading, empty, error and success states.
- Consistent chart legends and data provenance.
- Functional motion and reduced-motion behavior.
- Semantic layer/component naming and Auto Layout.

Remove generic SaaS, gaming, neon-HUD and decorative elements that do not help analysts. Then update and export DESIGN.md with the final tokens, component rules, responsive breakpoints, RTL rules and motion specifications.
```

## Files to return from Stitch

Request the following from the final project:

- Exported screen images at full resolution.
- Editable design/Figma export when available.
- Project ZIP with generated frontend assets and code.
- `DESIGN.md`.
- Logo assets used without alteration.
- Component inventory.
- Token inventory.
- Desktop/tablet prototype link or exported flow.

When these files are available, add them to the StatX design handoff so implementation can be planned against concrete UI references rather than screenshots alone.

