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

