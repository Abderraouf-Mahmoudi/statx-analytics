# StatX Analytics

**StatX Analytics** est un assistant d’analyse tactique et de performance pour le football. La plateforme vise à transformer les données de match en informations directement exploitables par les analystes, les entraîneurs et les équipes de recrutement : visualisations du terrain, analyse d’événements, rapports et indicateurs de performance.

## Architecture

Le projet suit une architecture monorepo :

- `backend/` — API Python basée sur FastAPI, traitement des données avec pandas et NumPy, visualisations avec Matplotlib et mplsoccer, génération de rapports PDF.
- `frontend/` — interface web Vite avec Tailwind CSS.
- `docs/` — documentation fonctionnelle et technique.
- `data/` — données locales et exports générés, exclus de Git lorsqu’ils sont volumineux ou produits automatiquement.

## Prérequis

- Python 3.11 ou version ultérieure
- Node.js 20 ou version ultérieure
- npm 10 ou version ultérieure
- Git

## Installation locale

Clonez le dépôt puis placez-vous dans le projet :

```bash
git clone https://github.com/Abderraouf-Mahmoudi/statx-analytics.git
cd statx-analytics
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

Sous Windows PowerShell, activez l’environnement avec :

```powershell
.venv\Scripts\Activate.ps1
```

Installez les dépendances et préparez la configuration :

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

L’API est disponible sur `http://localhost:8000`, sa documentation interactive sur `http://localhost:8000/docs` et le contrôle de santé sur `http://localhost:8000/health`. La base SQLite `backend/statx.db` et ses tables sont créées automatiquement au démarrage.

Les principales routes sont :

- `POST /api/teams`
- `POST /api/players`
- `POST /api/matches`
- `POST /api/matches/{match_id}/events`
- `GET /api/matches/{match_id}/analytics?player_id={player_id}`
- `GET /api/matches/{match_id}/pdf`

Les coordonnées d’événements suivent le terrain StatsBomb (`x` de 0 à 120 et `y` de 0 à 80). La possession exposée par la première version du moteur correspond à la part des passes enregistrées par équipe.

### Module vidéo

Le backend expose `POST /api/video/upload`, `POST /api/video/trim` et `GET /api/video/stream/{clip_id}`. Le découpage utilise en priorité `FFMPEG_BINARY`, puis FFmpeg dans le `PATH`, puis le binaire fourni par `imageio-ffmpeg`. Les vidéos sources et les clips exportés sont stockés dans les dossiers ignorés `data/raw_videos/` et `data/exports/clips/`.

Le tracking IA se lance avec `POST /api/video/track/{clip_id}`. L’API répond `202` avec un `job_id`; l’état et les trajectoires finales sont disponibles sur `GET /api/video/track/jobs/{job_id}`. Le modèle par défaut est `yolov8n.pt` et peut être remplacé via `VISION_MODEL_PATH`. Pour une projection terrain fiable, transmettez quatre `source_points` ordonnés bas-gauche, bas-droite, haut-droite, haut-gauche; sans calibration, les coins de l’image sont projetés sur le terrain 105 × 68 m.

### Pipeline d’ingestion SQLite

Une fois le job Vision terminé, ses trajectoires peuvent être enregistrées avec `POST /api/matches/{match_id}/ingest-tracking`. Les identifiants ByteTrack étant temporaires, `player_mapping` associe chaque piste au joueur enregistré en base :

```json
{
  "job_id": "identifiant-du-job-vision",
  "player_mapping": {
    "1": 12,
    "2": 18
  }
}
```

L’endpoint accepte également un tableau `tracking_data` direct. Les points sont insérés par lots dans une transaction SQLite, les doublons `(match, joueur, timestamp)` sont mis à jour et la vitesse est calculée automatiquement lorsqu’elle est absente. `GET /api/matches/{match_id}/tracking-status` renvoie le total persisté affiché par le module Data Pipeline du frontend.

### Insights tactiques automatisés

`GET /api/matches/{match_id}/tactical-insights` analyse les coordonnées SQLite du match depuis la perspective de l’équipe à domicile. Le paramètre optionnel `team_id` permet de changer de perspective. La réponse contient la répartition adverse entre le flanc gauche (`x < 35`), l’axe (`35 ≤ x ≤ 70`) et le flanc droit (`x > 70`), les alertes de surcharge au-delà de 60 %, ainsi que la distance et la vitesse maximale calculées pour chaque joueur.

Ces informations alimentent les cartes du dashboard et la section « Avis Tactique StatX » du rapport PDF. Le rapport reste limité à une page A4 et inclut la répartition spatiale, l’alerte prioritaire et les trois principaux profils télémétriques.

Pour générer la visualisation de démonstration :

```bash
python -m app.core.pitch
```

L’image est enregistrée dans `data/exports/test_pitch.png` à la racine du monorepo.

Pour installer les outils de développement et exécuter les tests d’intégration :

```bash
pip install -r requirements-dev.txt
pytest
```

### Frontend

Dans un second terminal :

```bash
cd frontend
npm install
npm run dev
```

L’interface de développement est alors disponible sur `http://localhost:5173`.

Le frontend utilise `VITE_API_BASE_URL` (valeur par défaut : `http://localhost:8000/api`). Le backend autorise par défaut les origines Vite `http://localhost:5173` et `http://127.0.0.1:5173`; elles peuvent être modifiées avec `CORS_ORIGINS`.

## Commandes Git d’initialisation

```bash
git init -b main
git add .
git commit -m "feat: initialisation du projet StatX Analytics"
git remote add origin https://github.com/Abderraouf-Mahmoudi/statx-analytics.git
```

## Licence

Le choix de la licence du projet reste à définir.

