# Exploitation — Release 1 Foundation & Roster

Ce guide décrit une installation locale reproductible de StatX Analytics sur Windows. La Release 1 privilégie la confidentialité : la base, les consentements et les données d’effectif restent sur la machine ou le réseau contrôlé du club.

## 1. Installation initiale

Exécuter depuis la racine du dépôt :

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Modifier ensuite `backend/.env` et remplacer `SESSION_SECRET` par une valeur aléatoire d’au moins 32 caractères. Ne jamais versionner ce fichier.

Pour activer l’import des clubs tunisiens, ajouter également la clé au fichier local ignoré :

```dotenv
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
API_FOOTBALL_KEY=remplacer-localement
API_FOOTBALL_DAILY_CEILING=90
API_FOOTBALL_MEDIA_HOSTS=media.api-sports.io
```

La clé ne doit jamais être saisie dans le frontend. Toute clé partagée dans une messagerie de développement doit être renouvelée depuis le tableau de bord API-Football avant une utilisation réelle.

Le plan gratuit autorise 100 requêtes quotidiennes ; StatX bloque les appels non essentiels à 90 afin de préserver une réserve. Les clubs et effectifs sont mis en cache sept jours. L’ouverture d’une page ne déclenche pas automatiquement une synchronisation.

Préparer la base et lancer l’API :

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Dans un second terminal :

```powershell
cd frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Ouvrir `http://127.0.0.1:5173`, choisir la fonction football du créateur, sélectionner le club tunisien puis confirmer. Le créateur reçoit toujours le rôle de sécurité `admin`, indépendamment de sa fonction. Ce bootstrap n’est possible qu’une fois. En cas d’indisponibilité du fournisseur, le bouton **Continuer sans import** conserve un démarrage entièrement manuel.

L’import s’exécute après le commit du compte et affiche cinq phases indépendantes : effectif, profils, matchs, classement et portraits. Une panne du fournisseur ne supprime jamais le compte ni un effectif déjà validé. Les champs corrigés par le club restent prioritaires lors des synchronisations suivantes.

## 1.1 Traitement local des portraits

Le backend standard accepte et normalise les images. La suppression d’arrière-plan utilise un environnement média séparé :

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-media.txt
.\.venv\Scripts\python.exe scripts\prepare_media_model.py
```

Cette préparation télécharge explicitement le modèle humain dans `DATA_ROOT/models`. Elle doit être faite pendant l’installation, avec Internet, jamais juste avant un match. Les originaux et PNG transparents sont stockés sous `data/player_photos/` et doivent être inclus dans les sauvegardes chiffrées.

Les photos API-Football portent le statut **Identification uniquement** jusqu’à validation des droits par le club. Une photo prise ou choisie par le club prend toujours priorité sur la photo fournisseur.

## 2. Migrations de base de données

Appliquer les migrations avant chaque nouvelle version :

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

Contrôler la révision courante :

```powershell
.\.venv\Scripts\python.exe -m alembic -c alembic.ini current
```

Alembic est l’unique propriétaire des changements de schéma. Ne pas créer les tables manuellement sur une base d’exploitation.

## 3. Accès local et accès réseau

Le mode recommandé utilise `127.0.0.1` pour le backend et le frontend : seul le poste courant peut accéder aux services.

Pour une tablette sur le même LAN, utiliser explicitement `--host 0.0.0.0` pour les deux services, remplacer `VITE_API_URL` par l’adresse IPv4 du poste, puis ajouter l’origine exacte du frontend à `CORS_ORIGINS`. N’ouvrir le pare-feu Windows que sur un réseau privé maîtrisé.

Exemple pour un PC `192.168.1.20` :

```dotenv
# backend/.env
CORS_ORIGINS=["http://127.0.0.1:5173","http://192.168.1.20:5173"]

# frontend/.env
VITE_API_URL=http://192.168.1.20:8000/api/v1
```

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd ..\frontend
npm.cmd run dev -- --host 0.0.0.0 --port 5173
```

Pour désactiver à nouveau l’accès LAN :

1. arrêter les deux processus ;
2. remettre `VITE_API_URL=http://127.0.0.1:8000/api/v1` ;
3. limiter `CORS_ORIGINS` à localhost et 127.0.0.1 ;
4. relancer avec `--host 127.0.0.1` ;
5. supprimer toute règle de pare-feu créée pour les ports 5173 et 8000.

## 4. Sauvegarde et restauration

Une sauvegarde cohérente contient la base SQLite et le dossier `data/` de la même date.

### Sauvegarde

1. arrêter l’API afin d’éviter une écriture pendant la copie ;
2. copier le fichier indiqué par `DATABASE_URL` ;
3. copier le dossier indiqué par `DATA_ROOT` ;
4. chiffrer l’archive et la stocker hors du poste ;
5. enregistrer la version de l’application et la révision Alembic.

### Restauration

1. arrêter l’application ;
2. conserver une copie de sécurité de l’état actuel ;
3. restaurer la base et `data/` ensemble ;
4. exécuter `alembic upgrade head` ;
5. lancer les contrôles de santé et vérifier un joueur, une inscription et un consentement.

Tester la restauration périodiquement sur une copie, jamais directement sur la base active.

## 5. Vérification de release

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -v

cd ..\frontend
npm.cmd run test:run
npm.cmd run build
npm.cmd run test:e2e
```

Le bundle de production doit rester autonome. Après le build, les fichiers HTML et CSS ne doivent contenir aucune police, image ou feuille de style distante :

```powershell
Get-ChildItem dist -Recurse -Include *.html,*.css | Select-String -Pattern 'https?://|fonts\.googleapis|cdn\.tailwindcss'
```

Une sortie vide est attendue.

Vérifier aussi qu’aucun secret fournisseur n’a été suivi par Git :

```powershell
git grep -n "API_FOOTBALL_KEY=" -- ':!backend/.env.example'
git status --short
```

La première commande ne doit afficher aucune valeur et `.env`, `data/player_photos`, les modèles ONNX, bases SQLite, WAL/SHM et dossiers `.run` ne doivent jamais être ajoutés au commit.

## 6. Dépannage Windows

### `Activate.ps1` ou `npm.ps1` est bloqué

Il n’est pas nécessaire de modifier la stratégie d’exécution PowerShell. Utiliser directement `.\.venv\Scripts\python.exe` et `npm.cmd`, comme dans les commandes de ce guide.

### `ModuleNotFoundError`

Vérifier que l’installation a utilisé le Python de l’environnement :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Base verrouillée

S’assurer qu’une seule instance d’administration est active, attendre la fin des écritures et conserver `SQLITE_BUSY_TIMEOUT_MS=5000` ou une valeur supérieure. Ne pas synchroniser la base SQLite active avec un outil de cloud drive.

### Synchronisation fournisseur échouée ou quota réservé

Les données SQLite déjà importées restent disponibles. Consulter l’état de synchronisation dans l’onboarding, attendre la remise à zéro du quota ou relancer explicitement plus tard. Ne pas augmenter le plafond au-delà de 90 avec un abonnement gratuit. Un joueur absent de la dernière réponse est marqué comme absent ; il n’est pas supprimé.

### Portrait bloqué en traitement

Vérifier que `requirements-media.txt` est installé et que `prepare_media_model.py` a réussi. L’original normalisé reste conservé si la segmentation échoue. Réessayer avec une photo plus nette, sans réinstaller l’ensemble du backend.

### Le frontend ne joint pas l’API

Vérifier `/health`, `VITE_API_URL`, les origines CORS et l’usage cohérent de `localhost` ou `127.0.0.1`. Après modification d’un fichier `.env`, redémarrer le serveur concerné.

## 7. Limites de cette release

Le tracking vidéo, la computer vision, les métriques avancées et les rapports automatiques historiques restent des modules expérimentaux. Ils sont exclus de la navigation et des garanties opérationnelles de la Release 1. Le socle certifié couvre l’identité locale, les organisations, les effectifs, les consentements et leur audit.
