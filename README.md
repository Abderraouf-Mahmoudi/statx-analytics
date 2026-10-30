# StatX Analytics

StatX Analytics est une plateforme locale d’analyse football destinée aux clubs, analystes et staffs techniques. La Release 1 fournit le socle exploitable du produit : initialisation sécurisée du club, authentification locale, gestion des saisons, équipes, joueurs, inscriptions et consentements, avec journal d’audit et isolation stricte des organisations.

L’interface React est pensée pour une utilisation tactile sur tablette : navigation latérale, cibles d’au moins 48 px, français par défaut et prise en charge de l’arabe en RTL. Les ressources visuelles sont embarquées afin que le cœur du produit reste utilisable sur le réseau local sans dépendance à un CDN.

## Périmètre de la Release 1

- configuration initiale du club et création du premier administrateur ;
- session locale protégée par cookie, RBAC et jeton CSRF ;
- saisons, équipes, joueurs et inscriptions d’effectif ;
- consentements avec règles spécifiques aux joueurs mineurs ;
- journal d’audit et cloisonnement des données par organisation ;
- application responsive desktop/tablette, français et arabe RTL.

Les anciens prototypes vidéo, vision et analytics sont conservés pour expérimentation, mais ne font pas partie du chemin critique ni de la navigation principale de cette release.

## Architecture

- `backend/` — FastAPI, SQLAlchemy, Alembic et SQLite ;
- `frontend/` — React, TypeScript, Vite, TanStack Query et i18next ;
- `data/` — médias et exports locaux non versionnés ;
- `docs/` — conception, plans et procédures d’exploitation.

## Prérequis

- Windows 10/11 avec PowerShell ;
- Python 3.12 ;
- Node.js 20+ et npm ;
- Git.

## Démarrage local sous Windows

Les commandes suivantes n’activent pas l’environnement virtuel. Elles fonctionnent donc même lorsque PowerShell bloque `Activate.ps1` ou `npm.ps1`.

### 1. Backend

Depuis la racine du dépôt :

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

L’API est disponible sur `http://127.0.0.1:8000`, sa documentation sur `http://127.0.0.1:8000/docs` et son contrôle de santé sur `http://127.0.0.1:8000/health`.

### 2. Frontend

Dans un second terminal, depuis la racine du dépôt :

```powershell
cd frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Ouvrez `http://127.0.0.1:5173`. Au premier lancement, l’assistant demande les informations du club et crée le compte administrateur local.

## Vérification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -v

cd ..\frontend
npm.cmd run test:run
npm.cmd run build
npm.cmd run test:e2e
```

## Exploitation et sauvegarde

Par défaut, les services écoutent uniquement sur `127.0.0.1`. Ne remplacez l’hôte par `0.0.0.0` que pour un déploiement volontaire sur un réseau local maîtrisé. Avant toute sauvegarde, arrêtez l’API puis copiez ensemble la base SQLite configurée par `DATABASE_URL` et le dossier `data/`. Conservez la copie dans un emplacement chiffré et testez régulièrement sa restauration.

La procédure complète de migration, sauvegarde, restauration et dépannage se trouve dans [docs/operations/release-1-foundation.md](docs/operations/release-1-foundation.md).

## Dépôt

Le dépôt de référence est [Abderraouf-Mahmoudi/statx-analytics](https://github.com/Abderraouf-Mahmoudi/statx-analytics).
