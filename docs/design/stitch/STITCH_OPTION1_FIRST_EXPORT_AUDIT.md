# Audit — Premier export Google Stitch StatX

**Date :** 30 octobre 2026  
**Fichiers audités :** `stitch_tactical_football_analytics_dashboard.zip`, `DESIGN.md`  
**Décision :** révision obligatoire avant génération des autres écrans

## Inventaire reçu

Le ZIP contient uniquement :

- `screen.png` — un écran desktop de 1600 × 1495 ;
- `code.html` — une page HTML statique ;
- `DESIGN.md` — une première base de tokens et de règles.

Il ne contient pas encore :

- le Design System sous forme d’écran ;
- le format desktop demandé 1440 × 1024 ;
- le shell tablette paysage ;
- le shell tablette portrait ;
- un véritable écran arabe RTL ;
- le passeport joueur ;
- le rapport FR/AR ;
- les variantes loading, erreur, conflit et lecture seule ;
- un prototype cliquable ;
- un inventaire de composants exportés ;
- les assets locaux du logo et des images.

## Éléments satisfaisants

- La palette sombre correspond globalement à l’identité StatX.
- La hiérarchie de la navigation latérale est claire.
- Le workflow Match Center en sept étapes est visible.
- Le contexte du match et le score restent accessibles.
- La palette d’événements est compréhensible.
- La timeline et l’annulation rapide sont présentes.
- La file de validation est une bonne traduction du modèle métier.
- Les badges de provenance sont visibles.
- La densité convient à une console analyste desktop.

Ces éléments peuvent être conservés après correction.

## Écarts bloquants

### 1. Identité de marque incorrecte

- Le logo ne se charge pas dans le rendu reçu.
- Le produit est renommé « StatX Pro — Tactical Intelligence ».
- La marque validée est « Stat X — Football Data Lab ».
- Le HTML référence le logo par une URL Google distante au lieu d’un asset local.

### 2. Livrable incomplet

Un seul écran desktop a été généré. Il ne représente ni le Design System complet ni les cinq écrans pivots de l’Option 1.

### 3. Format et viewport incorrects

L’image mesure 1600 × 1495, au lieu de 1440 × 1024. Les commandes principales ne sont donc pas validées dans le viewport cible et la page est beaucoup trop haute.

### 4. Dépendances Internet

Le HTML dépend de :

- Tailwind CDN ;
- Google Fonts ;
- Material Symbols distants ;
- trois images Google distantes.

Cela ne peut pas servir de référence d’implémentation offline. Les assets exportés doivent être locaux.

### 5. Provenance A/B/C incompatible

Le `DESIGN.md` Stitch définit :

- A = tracking optique/GPS ;
- B = scout manuel/vidéo ;
- C = agrégateur tiers.

Le modèle StatX validé définit :

- A = donnée validée par un analyste identifié ou import capteur signé et mappé ;
- B = donnée dérivée exclusivement de sources A ou import partiellement vérifié ;
- C = donnée héritée, estimée, incomplète ou non validée.

La définition métier StatX doit remplacer celle de Stitch.

### 6. xG inventé

L’écran affiche « modèle local v2.4 » et `xG 0.38` sans modèle approuvé ni source. Le MVP doit afficher `xG indisponible` tant qu’une source importée ou un modèle documenté n’est pas configuré.

### 7. Vision automatique trop dominante

La vidéo montre des overlays de tracking, heatmap et identification automatique. Ces fonctionnalités sont expérimentales et ne doivent pas représenter le parcours principal du MVP.

### 8. Promesses techniques incorrectes

- L’écran annonce une base SQLite chiffrée AES-256, alors que la conception valide le chiffrement des sauvegardes, pas une promesse SQLCipher.
- L’interface indique « Mode hybride » et utilise une icône cloud, alors que le produit est offline-first avec accès tablette sur LAN local.
- La licence est affichée active jusqu’au 30/06/2026 alors que la date d’audit est postérieure.

### 9. RTL non livré

Un bouton arabe est présent, mais le HTML ne contient aucun `dir="rtl"` ni écran RTL réel.

### 10. Cibles tactiles incohérentes

Le Design System impose 48 px, mais le HTML utilise encore plusieurs cibles de 44 px dans la navigation.

### 11. Export non interactif

La page est essentiellement statique : liens `href="#"`, absence de prototype fonctionnel et absence de composants React réutilisables.

### 12. `DESIGN.md` encore incomplet

La base de couleurs et typographies est exploitable, mais il manque notamment :

- tokens de motion ;
- comportement reduced-motion ;
- états complets des composants ;
- règles d’erreur, loading et conflit ;
- exceptions RTL pour terrain et graphiques ;
- composants vidéo, timeline et pitch selector détaillés ;
- patterns de graphiques accessibles ;
- règles d’assets offline ;
- inventaire des composants et des variantes.

## Prompt correctif à envoyer à Stitch

```text
Revise the current StatX Option 1 export before generating any additional product screens.

The current visual direction is promising, especially the dark palette, persistent sidebar, seven-step Match Center workflow, event palette, timeline and validation queue. Preserve those strengths, but correct every issue below.

1. BRAND IDENTITY
- Use the attached official logo as a local embedded asset.
- The exact brand is “Stat X — Football Data Lab”.
- Remove “StatX Pro” and “Tactical Intelligence” as replacement brand names.
- Never generate or redraw a different logo.

2. TARGET FRAME
- Rebuild the desktop Match Center at exactly 1440 × 1024.
- Keep the essential video, event actions, active player, timeline and validation queue usable inside that viewport.
- Use internal panel scrolling when necessary instead of a 1495 px page.

3. OFFLINE ASSETS
- Do not depend on Tailwind CDN, Google Fonts CDN, Material Symbols CDN or remote Google image URLs in the export.
- Export logo, icons, images and fonts as local assets or provide explicit local fallbacks.

4. PROVENANCE — USE THIS EXACT BUSINESS DEFINITION
- Provenance A: data entered and validated by an identified analyst, or a signed sensor import with confirmed player mapping.
- Provenance B: data derived exclusively from A sources using a versioned algorithm, or a partially verified import.
- Provenance C: legacy, estimated, incomplete or unvalidated data.
- Replace the current Optical/GPS = A and Manual = B mapping.

5. XG INTEGRITY
- Remove “local model v2.4” and the invented xG 0.38 value.
- Display “xG indisponible” with an explanatory unavailable state unless a documented imported source or approved model exists.

6. MVP SCOPE
- Remove automatic tracking, player identification, computer-vision overlays and heatmap overlays from the main video.
- Show a clean local match video with manual tagging controls.
- Computer vision may appear only as a disabled or experimental future capability, never as validated production data.

7. OFFLINE-FIRST LANGUAGE
- Remove “Mode hybride”, cloud-sync language and cloud icons.
- Use these states instead: Poste local, Tablette LAN appairée, Hors-ligne local, Synchronisation en attente, Synchronisé, Conflit.

8. TECHNICAL CLAIMS
- Do not claim that the active SQLite database is AES-256 encrypted.
- Only encrypted backup archives use AES-256-GCM.
- Use a logically valid licence date, or explicitly render the read-only expired licence state.

9. TOUCH AND ACCESSIBILITY
- Every interactive target must be at least 48 × 48 px, including sidebar navigation, language selector, timeline handles and icon buttons.
- Maintain WCAG AA contrast, visible focus and non-color status cues.

10. REAL RTL OUTPUT
- Create an actual Arabic RTL frame, not only an Arabic toggle.
- Use logical start/end spacing.
- Do not mirror football pitch coordinates, team attack direction or time-series meaning.

11. COMPLETE THE OPTION 1 DELIVERABLE
After correcting the Design System and desktop Match Center, generate:
- Design System screen and component inventory.
- Desktop app shell 1440 × 1024.
- Tablet landscape app shell 1024 × 768.
- Tablet portrait app shell 820 × 1180.
- Arabic RTL shell.
- Tablet tagging workspace.
- Player passport and certification.
- One-page French report preview.
- One-page Arabic RTL report preview.
- Loading, empty, offline, pending-sync, conflict, error and read-only variants where relevant.

12. DESIGN.MD
Update DESIGN.md with:
- the corrected A/B/C provenance model;
- motion and reduced-motion tokens;
- all component states;
- responsive breakpoints and exact frame sizes;
- RTL exceptions;
- offline asset rules;
- chart accessibility rules;
- component and variant inventory.

Export the revised screens, local assets, DESIGN.md, editable design/Figma artifact and clickable flow. Do not proceed to the administrative Option 2 screens until this corrected Option 1 is reviewed.
```

## Décision

Le concept visuel peut être conservé comme point de départ, mais le livrable ne doit pas encore être annexé comme référence UI finale. Une nouvelle exportation conforme est requise.

