# StatX Analytics — Direction visuelle retenue

**Statut :** référence de conception pour l’implémentation  
**Origine :** second export Stitch fourni le 30 octobre 2026  
**Règle :** le visuel Stitch sert d’inspiration ; le code HTML et les affirmations métier de Stitch ne sont pas repris tels quels.

## 1. Intention

L’interface StatX doit ressembler à un outil opérationnel utilisé par un analyste de club pendant un match : dense, stable, rapide à lire et dépourvu d’ornements inutiles. Elle ne doit évoquer ni un jeu vidéo, ni une plateforme de paris, ni un produit crypto, ni un tableau de bord SaaS générique.

La direction retenue combine :

- une console sombre et structurée ;
- une hiérarchie visuelle basée sur les surfaces et bordures ;
- un vert de marque réservé aux actions et confirmations ;
- un cyan réservé aux informations et données dérivées ;
- un ambre réservé aux attentes et anomalies ;
- un rouge réservé aux erreurs et conflits ;
- une typographie monospacée limitée aux mesures et identifiants.

## 2. Éléments retenus du visuel Stitch

- Sidebar persistante et compacte.
- Contexte de match visible dans le bandeau supérieur.
- État réseau/offline toujours visible.
- Workflow Match Center en sept étapes.
- Organisation en trois zones : effectif, vidéo/tagging, validation.
- Vidéo comme élément central du Match Center.
- Palette d’événements directement sous la vidéo.
- Annulation rapide après une action.
- Saisie spatiale sur un terrain séparé de la vidéo.
- Inspecteur de validation affichant provenance, auteur et état.
- Barre d’exploitation locale en bas de l’écran.
- Surfaces très sombres, bordures précises et faible usage des ombres.

## 3. Éléments explicitement non retenus

- HTML généré par Stitch.
- Dépendances CDN ou assets distants.
- Logo généré ou redessiné.
- Tracking automatique au centre de la vidéo.
- Valeurs xG non sourcées.
- Promesse de chiffrement direct de SQLite.
- Mode cloud ou « hybride ».
- Dimensions et débordements du screenshot Stitch.
- Dates, scores, licences et contenus métier fictifs considérés comme règles.
- Composants trop petits ou texte de télémétrie illisible.

## 4. Identité

- Logo officiel : « Stat X — Football Data Lab ».
- Le lockup officiel est utilisé sans modification.
- Le symbole carré peut servir d’icône compacte uniquement à partir du vrai fichier vectoriel.
- Fond principal très sombre afin de préserver le contraste du logo blanc et vert.
- Aucun halo, glow ou dégradé appliqué au logo.

## 5. Tokens visuels

### 5.1 Couleurs

| Token | Valeur | Usage |
|---|---|---|
| `canvas` | `#070B12` | fond racine |
| `shell` | `#0B0F19` | espace principal |
| `sidebar` | `#080D15` | navigation et système |
| `surface` | `#111827` | cartes et tableaux |
| `surface-elevated` | `#162033` | overlays et inspecteurs |
| `border` | `#263244` | séparateurs et contours |
| `text-primary` | `#F8FAFC` | titres et données critiques |
| `text-secondary` | `#94A3B8` | métadonnées |
| `text-muted` | `#475569` | états désactivés |
| `brand` | `#4ADE80` | accent StatX |
| `action` | `#10B981` | action principale et succès |
| `info` | `#22D3EE` | information et provenance B |
| `warning` | `#F59E0B` | attente et avertissement |
| `danger` | `#EF4444` | erreur et conflit |

### 5.2 Typographie

- Interface : `Geist`, fournie localement, avec fallback système.
- Mesures : `JetBrains Mono`, fournie localement, avec fallback monospace.
- Chiffres tabulaires pour scores, temps et métriques.
- Taille minimale recommandée : 13 px sur desktop, 14 px sur tablette.
- Les labels 10–11 px sont réservés aux métadonnées non critiques et ne sont jamais le seul moyen de comprendre une action.

### 5.3 Formes et espacements

- Grille de 8 px, demi-pas de 4 px pour les micro-alignements.
- Contrôles : rayon 4–8 px.
- Cartes : rayon 8–12 px.
- Bordure 1 px, sans glow.
- Cible interactive minimale : 48 × 48 px.
- Ombre uniquement pour les modales et panneaux flottants.

## 6. Shell desktop 1440 × 1024

```text
┌──────────────┬──────────────────────────────────────────────────────────────┐
│ Sidebar      │ Top bar : match · statut local · langue · utilisateur      │
│ 240 px       ├──────────────────────────────────────────────────────────────┤
│              │ Stepper Match Center — 7 étapes                            │
│              ├──────────────┬───────────────────────────┬───────────────────┤
│              │ Effectif     │ Vidéo + timeline          │ Validation        │
│              │ 280–300 px   │ largeur fluide            │ 320–360 px        │
│              │              │ Palette événements        │ scroll interne    │
│              │              │ Terrain de saisie         │                   │
│              ├──────────────┴───────────────────────────┴───────────────────┤
│              │ Barre locale : licence · sauvegarde · diagnostic            │
└──────────────┴──────────────────────────────────────────────────────────────┘
```

Règles :

- aucun overflow global ;
- vidéo et actions critiques visibles au-dessus de la ligne de flottaison ;
- scroll uniquement dans l’effectif, la validation et les panneaux secondaires ;
- sidebar réductible à 64 px ;
- raccourcis clavier visibles sans encombrer la palette tactile.

## 7. Adaptation tablette

### 7.1 Paysage 1024 × 768

- Vidéo dans la partie supérieure.
- Joueur actif et score toujours visibles.
- Palette d’événements en grille 2 × 3.
- Timeline avec poignée large.
- Terrain de saisie dans un panneau/bottom sheet.
- Validation accessible comme mode séparé, pas dans une troisième colonne étroite.
- Navigation contextuelle inférieure.

### 7.2 Portrait 820 × 1180

- Utilisé pour effectif, profil, passeport, imports et administration.
- Sections empilées avec navigation par onglets.
- Tableaux remplacés par listes structurées lorsque nécessaire.
- Actions primaires fixes en bas sans masquer le contenu.

## 8. Motion

| Token | Durée | Usage |
|---|---:|---|
| `motion-fast` | 140 ms | pression, focus, sélection |
| `motion-standard` | 200 ms | toast, validation, changement d’état |
| `motion-panel` | 280 ms | drawer, bottom sheet, changement d’étape |

- Courbe standard : `cubic-bezier(0.2, 0, 0, 1)`.
- Pas d’animation décorative en boucle.
- Le statut « synchronisation en attente » peut pulser doucement.
- `prefers-reduced-motion` supprime translation et scale, tout en conservant les changements de couleur et de texte.

## 9. Composants structurants

- `AppShell`
- `SidebarNavigation`
- `TopMatchContext`
- `LocalRuntimeStatus`
- `MatchWorkflowStepper`
- `VideoWorkspace`
- `VideoTimeline`
- `ActivePlayerSelector`
- `EventActionPalette`
- `PitchLocationPicker`
- `UndoSnackbar`
- `ValidationInspector`
- `ProvenanceBadge`
- `ConfidenceIndicator`
- `JobProgress`
- `SyncConflictResolver`
- `TabletBottomNavigation`
- `TabletBottomSheet`

Tous possèdent les états nécessaires : défaut, hover desktop, focus, pressed, disabled, loading, success, error et read-only lorsque pertinent.

## 10. Provenance

- **A :** donnée validée par un analyste identifié ou import capteur signé avec mapping joueur confirmé.
- **B :** donnée dérivée de sources A par un algorithme versionné ou import partiellement vérifié.
- **C :** donnée héritée, estimée, incomplète ou non validée.

Le badge ne suffit jamais seul : la source, l’auteur, la date ou la version restent consultables.

## 11. Offline et synchronisation

États visibles :

- Poste local actif.
- Tablette LAN appairée.
- Hors-ligne local.
- Synchronisation en attente avec compteur.
- Synchronisé.
- Conflit.
- Lecture seule.

Les sauvegardes peuvent être chiffrées AES-256-GCM. L’interface ne prétend pas que SQLite est chiffrée si SQLCipher n’est pas réellement implémenté.

## 12. RTL

- Navigation, texte, panneaux et ordre des colonnes suivent `dir="rtl"`.
- Le terrain, les coordonnées, le sens d’attaque et les séries temporelles restent invariants.
- Les chiffres du score et les unités restent lisibles et tabulaires.
- Les composants doivent être testés dans de vrais écrans arabes, pas uniquement par un bouton de langue.

## 13. Accessibilité

- Contraste WCAG AA.
- Focus clavier visible.
- Aucun statut uniquement par couleur.
- Labels accessibles pour les boutons icônes.
- Navigation clavier complète sur desktop.
- Zones tactiles de 48 px minimum.
- Erreurs proches du contrôle concerné.

## 14. Source de vérité

Cette direction visuelle complète la conception consolidée du MVP. En cas de conflit :

1. les règles métier de la conception consolidée prévalent ;
2. ce document fixe l’expérience et le langage visuel ;
3. le screenshot Stitch est seulement une inspiration de composition ;
4. le code généré par Stitch n’est jamais copié directement dans le produit.

