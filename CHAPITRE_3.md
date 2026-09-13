# CHAPITRE 3 : ANALYSE ET CONCEPTION DU SYSTÈME

---

**Introduction du chapitre**

La phase d'analyse et de conception constitue l'étape charnière entre les exigences fonctionnelles définies dans le cahier des charges et l'implémentation technique réelle. Ce troisième chapitre traduit les besoins de la plateforme ClarIA en un ensemble de modélisations formelles. Ce chapitre justifie les choix technologiques effectués, en expliquant pourquoi chaque composant de la pile a été préféré à ses alternatives. Il présente ensuite l'architecture globale du système, puis l'ensemble des diagrammes UML (Unified Modeling Language) qui ont servi de plan directeur au développement : diagrammes de composants, de cas d'utilisation, de classes, de séquence, d'activité, et le diagramme de déploiement. Ce chapitre se conclut par le Diagramme de Gantt retraçant le planning du projet.

---

## 3.1 Choix Technologiques Justifiés

Le choix de chaque technologie dans la pile de ClarIA a fait l'objet d'une analyse comparative rigoureuse. Cette section justifie les décisions les plus structurantes.

### 3.1.1 FastAPI plutôt que Flask ou Django

**FastAPI** a été sélectionné comme framework backend pour deux raisons déterminantes. Premièrement, il repose nativement sur l'architecture ASGI (*Asynchronous Server Gateway Interface*), permettant l'utilisation de coroutines `async/await` sans configuration additionnelle. Cette caractéristique est critique pour ClarIA : toutes les opérations d'accès à la base de données et de validation de fichiers s'exécutent de manière asynchrone, sans bloquer le thread principal. Deuxièmement, FastAPI intègre la validation automatique des entrées via **Pydantic**, garantissant l'intégrité de chaque requête HTTP entrante sans code défensif manuel.

Flask aurait nécessité des extensions tierces (Flask-Async, Marshmallow) pour atteindre un niveau équivalent, ajoutant de la complexité de configuration. Django, bien que plus complet, impose un paradigme synchrone en MVC et une surcharge liée à son ORM propre qui aurait été redondante avec SQLAlchemy.

### 3.1.2 SQLAlchemy 2.0 (moteur asynchrone) plutôt qu'un ORM synchrone

**SQLAlchemy 2.0** a été préféré à des alternatives comme Tortoise ORM ou Databases pour sa maturité, la richesse de son système de migrations (Alembic), et sa gestion native des deux paradigmes (asynchrone via `asyncpg` pour les endpoints FastAPI, synchrone via `psycopg2` pour les workers Celery). Le type personnalisé `GUID` garantit une représentation des UUID identique sur SQLite (développement) et PostgreSQL (production), évitant tout problème de compatibilité lors du déploiement.

### 3.1.3 Keycloak 26 plutôt qu'une authentification maison

La gestion de l'identité et des accès est un domaine où les implémentations personnalisées introduisent systématiquement des vulnérabilités. **Keycloak 26** externalise entièrement cette responsabilité vers une solution éprouvée et auditée. Il fournit nativement la gestion des utilisateurs, l'authentification JWT RS256, le RBAC, le portail d'administration, et la rotation des clés cryptographiques. L'application ne stocke jamais de mot de passe — Keycloak est le seul point de vérité pour l'identité.

### 3.1.4 Celery + Redis plutôt qu'une file de tâches maison

L'inférence LLM via Ollama peut prendre entre 5 et 30 secondes selon la complexité de la requête. Exécuter ce traitement dans un endpoint FastAPI synchrone bloquerait le thread et rendrait l'API inutilisable sous charge. **Celery** avec **Redis** comme broker résout ce problème en déléguant le pipeline entier (`classify_data_intent` → `fuzzy_matcher` → `chart_resolver` → `generate_explanation`) à des workers isolés. Redis sert simultanément de broker de messages et de canal de publication Pub/Sub pour la restitution WebSocket en temps réel.

### 3.1.5 React 18 + Vite plutôt que Next.js

**Next.js** aurait apporté le Server-Side Rendering (SSR), adapté aux applications nécessitant un bon référencement (SEO). ClarIA étant une plateforme SaaS à accès restreint (authentification obligatoire), le SEO n'est pas une priorité. **Vite** a donc été préféré pour sa vélocité en développement (HMR quasi-instantané), sa configuration zéro, et son build optimisé. Le résultat est une **Single Page Application** (SPA) légère et réactive, sans surcoût du framework Next.js.

### 3.1.6 PandasAI + LiteLLM plutôt qu'un agent LangChain

**PandasAI** opère directement sur des DataFrames Pandas, format natif des fichiers CSV/Excel chargés par ClarIA. Il n'exige pas de base de données vectorielle, de pipeline RAG, ni d'index sémantique préalable — il génère du code Python à la volée à partir des métadonnées du DataFrame. **LiteLLM** via l'extension `pandasai-litellm` fournit l'interface unifiée vers tous les fournisseurs LLM (Ollama, OpenAI, Anthropic, Google), permettant de basculer de fournisseur par simple variable d'environnement, sans modifier le code applicatif.

---

## 3.2 Architecture Globale et Diagrammes de Composants

L'architecture de ClarIA est organisée selon une séparation stricte des responsabilités entre cinq couches fonctionnelles : présentation (React SPA), API (FastAPI), traitement asynchrone (Celery workers), persistance (PostgreSQL) et identité (Keycloak).

### 3.2.1 Vue d'ensemble de l'architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  NAVIGATEUR (React 18 + Vite)                                    │
│  LandingPage │ UploadPage │ AskiPage │ DashboardPage │ AdminPage  │
│  Zustand (3 stores) — ECharts — AG Grid — react-grid-layout      │
│  ProviderStatusBadge (poll /provider-status)                     │
└──────────────────────┬───────────────────────────────────────────┘
                       │ HTTP/WebSocket (JWT RS256)
┌──────────────────────▼───────────────────────────────────────────┐
│  FASTAPI (Uvicorn/ASGI)                                          │
│  Routeurs: files │ prompts │ provider │ websocket │ platform-users│
│  Endpoints utilitaires:                                          │
│    GET /api/v1/health          → {max_file_size_mb, max_rows}    │
│    GET /api/v1/provider-status → {provider, model, status, fallback}│
│  Middleware: CORS (cors_origins) │ Global exception handler 500  │
│  Services: file_validator │ locale_normalizer │ keycloak_admin   │
└──────────┬──────────────────────────────────┬────────────────────┘
           │ Pub/Sub (Redis)                  │ SQLAlchemy async
┌──────────▼──────────────┐       ┌───────────▼────────────────────┐
│  CELERY WORKER          │       │  POSTGRESQL (Production)        │
│  Pipeline IA :          │       │  Tables: files, prompts, charts  │
│  ├─ classify_intent     │       │  Migrations: 4 révisions Alembic │
│  ├─ fuzzy_matcher       │       └────────────────────────────────┘
│  ├─ PandasAI         │
│  ├─ chart_resolver      │       ┌────────────────────────────────┐
│  └─ generate_explanation│       │  KEYCLOAK 26                   │
│                         │       │  Realm: claria                 │
│  LLM: Ollama (local)    │       │  Clients: claria-frontend       │
│  Fallback: Google /     │       │  Rôles: user, admin             │
│  OpenAI / Anthropic     │       └────────────────────────────────┘
└─────────────────────────┘
```

### 3.2.2 Diagramme de Composants — Espace Utilisateur

> [Figure 4 : Diagramme de Composants (Espace Utilisateur) — À insérer ici]
> *(Légende suggérée : Figure 4 — Interaction entre le navigateur (UploadPage + AskiPage), le router FastAPI, le service file_validator, le worker Celery (pipeline PandasAI), et le canal WebSocket Redis Pub/Sub.)*

### 3.2.3 Diagramme de Composants — Espace Administrateur

> [Figure 5 : Diagramme de Composants (Espace Administrateur) — À insérer ici]
> *(Légende suggérée : Figure 5 — Interaction entre l'AdminPage, le router platform-users, le service KeycloakAdminClient, et la suppression en cascade Keycloak → PostgreSQL → disque.)*

---

## 3.3 Diagrammes des Cas d'Utilisation

Les fonctionnalités de ClarIA ont été réparties en deux espaces distincts selon le rôle de l'acteur.

### 3.3.1 Cas d'Utilisation — Acteur Utilisateur (`user`)

L'acteur `user` peut effectuer les actions suivantes :
- **S'authentifier** via Keycloak (SSO) *(prérequis à toutes les autres actions)*
- **Importer un fichier** (CSV, Excel) *(inclut : valider le format, normaliser les données FR, sélectionner une feuille si multi-feuilles)*
- **Consulter la prévisualisation** du fichier importé (colonnes, types, aperçu des données)
- **Formuler une requête en langage naturel** sur le fichier actif *(inclut : classification d'intention, correspondance floue des colonnes, inférence LLM)*
- **Visualiser le graphique généré** en temps réel via WebSocket
- **Lire l'explication** textuelle du graphique (générée automatiquement en français)
- **Épingler un graphique** sur son tableau de bord
- **Personnaliser le tableau de bord** (glisser-déposer, redimensionner les widgets)
- **Ajouter / Supprimer un indicateur KPI** (somme, moyenne, comptage, min, max)
- **Configurer le fournisseur LLM** actif (Ollama, OpenAI, Anthropic, Google)

> [Figure 6 : Diagramme de Cas d'Utilisation — Acteur Utilisateur — À insérer ici]

### 3.3.2 Cas d'Utilisation — Acteur Administrateur (`admin`)

L'acteur `admin` est dédié exclusivement aux fonctions de gestion des comptes. Il ne participe pas à l'analyse de données. **Important :** les rôles (`user`, `admin`) sont attribués directement dans Keycloak — il n'existe pas d'endpoint applicatif pour modifier le rôle d'un utilisateur. De plus, le compte administrateur lui-même est strictement verrouillé côté applicatif : il ne peut être modifié que directement dans la console d'administration native de Keycloak (Realm claria).

- **Consulter la liste des utilisateurs** de la plateforme (`GET /api/v1/platform-users/users`)
- **Créer un nouveau compte utilisateur** (`POST /api/v1/platform-users/users`) — politique de mot de passe enforced : 8+ caractères, majuscule + minuscule + chiffre + caractère spécial
- **Modifier les informations d'un utilisateur non-admin** (`PUT /api/v1/platform-users/users/{id}`) — email, prénom, nom, activation/désactivation ; *toute modification d'un compte administrateur est bloquée dans l'application web (doit être faite dans Keycloak)*
- **Désactiver un compte utilisateur** (champ `enabled: false`) — *impossible sur un compte admin ; le logout Keycloak est forcé immédiatement après désactivation*
- **Réinitialiser le mot de passe d'un utilisateur** (`PUT /api/v1/platform-users/users/{id}/password`) — *impossible sur son propre compte*
- **Supprimer un utilisateur** en cascade (`DELETE /api/v1/platform-users/users/{id}`) — Keycloak → PostgreSQL (prompts, charts) → fichiers physiques sur disque ; *impossible sur son propre compte ; protégé si au moins 1 utilisateur non-admin doit rester*

> [Figure 7 : Diagramme de Cas d'Utilisation — Acteur Administrateur — À insérer ici]

---

## 3.4 Diagrammes de Classes

La modélisation orientée objet du domaine métier de ClarIA est structurée autour de trois entités principales et d'une couche de sécurité.

### 3.4.1 Diagramme de Classes — Domaine Métier

Les trois entités persistées en base de données ont les attributs suivants, directement issus des modèles SQLAlchemy :

**Classe `File` (table `files`)**
```
+ id            : UUID (PK)
+ owner_id      : String(36)     [index]
+ original_filename : String
+ file_type     : Enum('csv','xlsx','xls')
+ size_bytes    : Integer
+ row_count     : Integer?
+ sheet_name    : String?
+ storage_path  : String
+ columns_metadata : JSON?
+ preview_rows  : JSON?
+ dashboard_config : JSON?
+ status        : Enum('uploaded','needs_sheet_selection','validated','error')
+ error_message : String?
+ created_at    : DateTime
────────────────────────────────
+ prompts       : List<Prompt>  [1..*]
```

**Classe `Prompt` (table `prompts`)**
```
+ id                   : UUID (PK)
+ file_id              : UUID (FK → files.id, CASCADE)  [index]
+ raw_text             : String
+ status               : Enum('pending','processing','awaiting_clarification','completed','failed')
+ clarification_question : String?
+ clarification_answer   : String?
+ explanation            : String?
+ generated_code         : String?
+ error_message          : String?
+ created_at             : DateTime
+ completed_at           : DateTime?
────────────────────────────────
+ file   : File          [*..1]
+ chart  : Chart?        [0..1]
```

**Classe `Chart` (table `charts`)**
```
+ id          : UUID (PK)
+ prompt_id   : UUID (FK → prompts.id, CASCADE) [unique, index]
+ chart_type  : Enum('bar','line','pie','scatter','histogram','area','radar','heatmap')
+ chart_spec  : JSON
+ created_at  : DateTime
────────────────────────────────
+ prompt : Prompt  [*..1]
```

**Relations :** `File` 1→* `Prompt` 1→0..1 `Chart`. Toutes les suppressions sont en cascade (`ondelete="CASCADE"`).

> [Figure 8 : Diagramme de Classes — Entités Métier (File, Prompt, Chart) — À insérer ici]
> *(Légende suggérée : Figure 8 — Diagramme de classes UML illustrant les trois entités métier avec leurs attributs exacts, leurs types et leurs relations de composition.)*

### 3.4.2 Diagramme de Classes — Couche Sécurité

La couche de sécurité est gérée par le module `backend/core/security.py`, qui expose deux structures :

**Classe `User` (objet de session — non persisté)**
```
+ sub        : String   [identifiant Keycloak unique]
+ email      : String
+ username   : String
+ roles      : List<String>
+ is_admin   : Boolean
```

**Dépendances FastAPI :**
- `get_current_user(token)` → valide le JWT RS256 via cache JWKS, retourne un `User`
- `require_admin(user)` → lève HTTP 403 si `is_admin == False`

> [Figure 9 : Diagramme de Classes — Couche Sécurité (User, get_current_user, require_admin) — À insérer ici]
> *(Légende suggérée : Figure 9 — Diagramme de classes UML illustrant la couche sécurité : l'objet de session `User`, la dépendance `get_current_user()` avec validation JWKS, et `require_admin()` avec rejet HTTP 403.)*

### 3.4.3 Modèle Conceptuel et Logique de Données (MCD / MLD)

**Modèle Conceptuel de Données**

Le MCD de ClarIA s'articule autour de trois entités métier liées par des associations de composition :

- **FILE** contient **0..N PROMPT** (un fichier peut avoir de nombreux historiques de requêtes)
- **PROMPT** génère **0..1 CHART** (une requête produit au plus un graphique)
- La suppression d'un **FILE** déclenche en cascade la suppression de tous ses **PROMPT** et **CHART** associés

> [Figure 15 : Modèle Conceptuel de Données (MCD) — Entités File, Prompt, Chart — À insérer ici]

**Modèle Logique de Données (MLD)**

*Tableau 4 : Dictionnaire des données — Modèle Logique de ClarIA*

| Table | Colonne | Type | Contrainte | Description |
| :--- | :--- | :--- | :--- | :--- |
| **files** | `id` | UUID | PK | Identifiant unique du fichier |
| | `owner_id` | VARCHAR(36) | NOT NULL, INDEX | `sub` Keycloak du propriétaire |
| | `original_filename` | TEXT | NOT NULL | Nom original du fichier uploadé |
| | `file_type` | VARCHAR(10) | CHECK(csv/xlsx/xls) | Format détecté par magic bytes |
| | `size_bytes` | INTEGER | NOT NULL | Taille en octets |
| | `row_count` | INTEGER | NULLABLE | Nombre de lignes après chargement |
| | `sheet_name` | TEXT | NULLABLE | Feuille sélectionnée (Excel) |
| | `storage_path` | TEXT | NOT NULL | Chemin absolu sur le disque |
| | `columns_metadata` | JSON | NULLABLE | Noms + types des colonnes |
| | `preview_rows` | JSON | NULLABLE | 5 premières lignes (aperçu) |
| | `dashboard_config` | JSON | NULLABLE | Config tableau de bord (≤500Ko) |
| | `status` | VARCHAR(30) | CHECK(...) | uploaded/needs_sheet_selection/validated/error |
| | `error_message` | TEXT | NULLABLE | Message d'erreur si status=error |
| | `created_at` | TIMESTAMPTZ | NOT NULL | Horodatage de création |
| **prompts** | `id` | UUID | PK | Identifiant unique de la requête |
| | `file_id` | UUID | FK→files(id) CASCADE | Fichier associé |
| | `raw_text` | TEXT | NOT NULL | Texte brut de la question |
| | `status` | VARCHAR(30) | CHECK(...) | pending/processing/awaiting_clarification/completed/failed |
| | `clarification_question` | TEXT | NULLABLE | Question de clarification du LLM |
| | `clarification_answer` | TEXT | NULLABLE | Réponse de l'utilisateur |
| | `explanation` | TEXT | NULLABLE | Synthèse textuelle FR du graphique |
| | `generated_code` | TEXT | NULLABLE | Code Python généré par PandasAI |
| | `error_message` | TEXT | NULLABLE | Message d'erreur si status=failed |
| | `created_at` | TIMESTAMPTZ | NOT NULL | Horodatage de soumission |
| | `completed_at` | TIMESTAMPTZ | NULLABLE | Horodatage de complétion |
| **charts** | `id` | UUID | PK | Identifiant unique du graphique |
| | `prompt_id` | UUID | FK→prompts(id) CASCADE, UNIQUE | Prompt source (1-1) |
| | `chart_type` | VARCHAR(20) | CHECK(bar/line/pie/...) | Type ECharts (8 valeurs) |
| | `chart_spec` | JSON | NOT NULL | Spécification ECharts complète |
| | `created_at` | TIMESTAMPTZ | NOT NULL | Horodatage de génération |

---

## 3.5 Diagrammes de Séquence

### 3.5.1 Diagramme de Séquence — Pipeline Complet (Upload → Aski → WebSocket → ECharts)

Ce diagramme illustre le flux nominal complet depuis l'import d'un fichier jusqu'à l'affichage du graphique.

```
Utilisateur    Frontend (React)     FastAPI           Redis/Celery        Ollama LLM
    │                │                  │                   │                  │
    │─ Upload CSV ──►│                  │                   │                  │
    │                │─ POST /files ───►│                   │                  │
    │                │                  │─ file_validator() │                  │
    │                │                  │─ locale_normalizer()                 │
    │                │                  │─ INSERT files (status=uploaded)      │
    │                │◄─ 201 {file_id} ─│                   │                  │
    │                │                  │                   │                  │
    │─ Question NL ─►│                  │                   │                  │
    │                │─ POST /prompts ─►│                   │                  │
    │                │                  │─ rate_limiter.check()                │
    │                │                  │─ INSERT prompts (status=pending)     │
    │                │                  │─ celery.delay(task) ──────────────►  │
    │                │◄─ 202 {prompt_id}│                   │                  │
    │                │                  │                   │                  │
    │                │─ WS /ws/prompts/{id} ────────────────►                  │
    │                │                  │                   │─ classify_intent()►│
    │                │                  │                   │◄─ YES/NO ─────────│
    │                │                  │                   │─ fuzzy_matcher()  │
    │                │                  │                   │─ detect_chart_type()
    │                │                  │                   │─ PandasAI.chat() ─►│
    │                │                  │                   │◄─ DataFrame ──────│
    │                │                  │                   │─ build_chart_spec()
    │                │                  │                   │─ generate_explanation()►│
    │                │                  │                   │◄─ texte FR ───────│
    │                │                  │                   │─ Redis PUBLISH {chart_spec, explanation}
    │                │◄─ WS message {chart_spec, explanation, status=completed} │
    │◄─ Graphique ──►│                  │                   │                  │
```

> [Figure 10 : Diagramme de Séquence — Pipeline complet Upload → Aski → WebSocket → ECharts — À insérer ici]

### 3.5.2 Diagramme de Séquence — Authentification Keycloak (JWT RS256)

```
Utilisateur    Keycloak 26         FastAPI           Cache JWKS
    │               │                  │                  │
    │─ Login ──────►│                  │                  │
    │◄─ JWT RS256 ──│                  │                  │
    │               │                  │                  │
    │─ GET /api/v1/files (Bearer JWT) ►│                  │
    │               │                  │─ PyJWKClient.get_signing_key() ──────►│
    │               │                  │◄─ clé publique (TTL 900s) ────────────│
    │               │                  │─ jwt.decode(token, RS256)             │
    │               │                  │─ Vérifier issuer, azp, expiry        │
    │               │                  │─ extract roles → User object         │
    │◄─ 200 (données utilisateur) ─────│                  │                  │
```

> [Figure 11 : Diagramme de Séquence — Authentification Keycloak RS256 (JWKS + azp) — À insérer ici]

---

## 3.6 Diagrammes d'Activité

### 3.6.1 Diagramme d'Activité — Validation et Normalisation d'un Fichier

Ce diagramme formalise la logique du service `file_validator` + `locale_normalizer` lors de l'import d'un fichier.

```
[Début] → Réception du fichier (multipart/form-data)
    ↓
Vérifier la taille : size > MAX_FILE_SIZE (10 Mo) ?
    → OUI : HTTP 400 FILE_TOO_LARGE → [Fin]
    ↓ NON
Vérifier la signature d'octets (magic bytes) : type réel = csv/xlsx/xls ?
    → NON : HTTP 400 INVALID_FILE_TYPE → [Fin]
    ↓ OUI
Détecter l'encodage (chardet) : UTF-8 ? Latin-1 ? Autre ?
    ↓
Charger avec Pandas (encoding détecté)
    ↓
Normaliser les nombres français (1 234,56 → 1234.56)
Normaliser les dates françaises (dd/mm/yyyy → ISO 8601)
    ↓
Compter les lignes : row_count > MAX_ROWS (100 000) ?
    → OUI : HTTP 400 TOO_MANY_ROWS → [Fin]
    ↓ NON
Fichier Excel multi-feuilles ?
    → OUI : status = 'needs_sheet_selection' → Retourner sheet_names → [Fin]
    ↓ NON
Extraire columns_metadata + preview_rows (5 premières lignes)
status = 'validated'
INSERT files en base de données
→ HTTP 201 {file_id, columns, preview_rows, row_count} → [Fin]
```

> [Figure 12 : Diagramme d'Activité — Validation et normalisation d'un fichier CSV/Excel — À insérer ici]

### 3.6.2 Diagramme d'Activité — Suppression en Cascade d'un Utilisateur (Administrateur)

Ce diagramme formalise la logique réelle de l'endpoint `DELETE /api/v1/platform-users/users/{id}`.

```
[Début] → Requête DELETE /api/v1/platform-users/users/{id}
    ↓
Valider le JWT → require_admin() : user est admin ?
    → NON : HTTP 403 FORBIDDEN → [Fin]
    ↓ OUI
id cible == admin.sub (auto-suppression) ?
    → OUI : HTTP 403 CANNOT_DELETE_SELF → [Fin]
    ↓ NON
Appeler Keycloak Admin API : lister les utilisateurs
    ↓
Compter les utilisateurs non-admin restants (username != 'adminuser'/'admin')
Si l'utilisateur cible est l'avant-dernier non-admin :
    → HTTP 400 (la plateforme doit conserver au moins un utilisateur) → [Fin]
    ↓
Collect Files : SELECT * FROM files WHERE owner_id = {id}
    ↓
Keycloak Admin API : DELETE /users/{id}  ← PRIORITAIRE
    → Erreur Keycloak : lever exception (DB non modifiée) → [Fin]
    ↓ Succès Keycloak
SQLAlchemy : DELETE charts WHERE prompt_id IN (SELECT id FROM prompts WHERE file_id IN [file_ids])
SQLAlchemy : DELETE prompts WHERE file_id IN [file_ids]
SQLAlchemy : DELETE files WHERE id IN [file_ids]
db.commit()
    ↓
Pour chaque file_id : shutil.rmtree(storage_path / file_id, ignore_errors=True)
    → HTTP 204 No Content → [Fin]
```

> [Figure 13 : Diagramme d'Activité — Suppression en cascade d'un utilisateur (Keycloak → DB → disque) — À insérer ici]

### 3.6.3 Diagramme d'État — Cycle de Vie des Entités

**États d'un Fichier (`File.status`)**

Un fichier transite par les états suivants au cours de son traitement :

```
[Importé] → uploaded
    ↓ (si Excel multi-feuilles)
needs_sheet_selection
    ↓ (après sélection de feuille)
    ↓ (si CSV ou Excel mono-feuille, directement)
validated ←—————————————————————————
    ↓ (si erreur de validation ou normalisation)
error  [état terminal]

[validated] = état nominal permettant la soumission de prompts
```

**États d'un Prompt (`Prompt.status`)**

Chaque requête utilisateur suit ce cycle de vie asynchrone :

```
[Soumis] → pending
    ↓ (Celery task démarre)
processing
    ↓                    ↓ (LLM demande clarification)
completed          awaiting_clarification
                         ↓ (réponse utilisateur reçue)
                    processing → completed
    ↓ (erreur à n'importe quelle étape)
failed  [état terminal]
```

> [Figure 14 : Diagramme d'État — Cycles de vie des entités File (4 états) et Prompt (5 états) — À insérer ici]

---

## 3.7 Diagramme de Déploiement

L'infrastructure de ClarIA est entièrement conteneurisée via **Docker Compose**. Elle s'articule autour de huit services isolés communiquant via un réseau Docker interne :

| Service | Image / Runtime | Rôle | Port exposé |
| :--- | :--- | :--- | :--- |
| **nginx** | `nginx:alpine` | Reverse proxy — route `/api/` → backend, `/` → frontend | 80, 443 |
| **frontend** | Node.js / Vite build | SPA React — interface utilisateur | 5173 (dev) |
| **backend** | Python 3.11 / Uvicorn | API FastAPI — 5 routers | 8000 |
| **celery_worker** | Python 3.11 / Celery | Pipeline IA asynchrone | — |
| **redis** | `redis:7-alpine` | Broker de messages + Pub/Sub WebSocket | 6379 |
| **postgres** | `postgres:16-alpine` | Persistance des données | 5432 |
| **keycloak** | `quay.io/keycloak/keycloak:26` | Serveur d'identité SSO | 8080 |
| **ollama** | `ollama/ollama` | Serveur LLM local (qwen2.5-coder:7b) | 11434 |

Au démarrage, le service `migrate` (Alembic `upgrade head`) s'exécute avant le backend pour garantir que le schéma est toujours à jour.

> [Figure 16 : Diagramme de Déploiement — Infrastructure Docker Compose de ClarIA — À insérer ici]
> *(Légende suggérée : Figure 16 — Diagramme de déploiement illustrant les 8 conteneurs Docker, leurs réseaux internes, les volumes persistants (PostgreSQL, stockage fichiers), et les flux de communication inter-services.)*

---

## 3.8 Diagramme de Gantt

Le diagramme de Gantt ci-dessous retrace le planning de développement du projet ClarIA sur les mois de **juillet et août 2026**. Le développement technique — de l'analyse à la correction de bugs — a été réalisé intégralement sur le mois de juillet (S1 à S4). La rédaction du rapport PFA a débuté fin juillet (S4) et s'est poursuivie sur le mois d'août (S5-S8). La date de la soutenance finale reste à confirmer (courant septembre).

*Tableau 5 : Diagramme de Gantt — Phase de Développement & Rédaction (Juillet - Août 2026)*

| Phase | Tâches / Livrables | S1 (juil.) | S2 (juil.) | S3 (juil.) | S4 (juil.) | S5–S8 (août) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Phase 1** | CDC, état de l'art, analyse besoins SKATYS | ████ | | | | |
| **Phase 2** | Architecture système, UML, modélisation BDD | ░███ | ████ | | | |
| **Phase 3** | FastAPI + Keycloak, Pipeline IA, Celery + Redis | | ░███ | ████ | | |
| **Phase 4** | Interface React, tests Pytest (40 tests), bug fixes | | | ░███ | ████ | |
| **Phase 5** | Rédaction du Rapport PFA & Documentation | | | | ░░██ | ████ |

*Légende : ████ = Phase active. ░ = Transition / chevauchement. S = Semaine.*
*(Soutenance finale : Date exacte à confirmer, prévue courant septembre 2026).*

**Détail des phases de développement :**

- **Phase 1 — Cadrage & Recherche (S1, 1–12 juil.)** : Prise en main de l'environnement SKATYS, rédaction du Cahier des Charges (CDC), recherche bibliographique (PandasAI vs LangChain, Keycloak vs Auth0, ECharts vs Plotly), analyse des besoins métier.

- **Phase 2 — Conception (S2, 8–18 juil.)** : Modélisation UML complète (14 diagrammes : composants, cas d'utilisation, classes, séquence, activité, état, déploiement, Gantt). Définition de l'architecture Docker et du schéma de base de données (File / Prompt / Chart).

- **Phase 3 — Développement Backend & IA (S3, 13–26 juil.)** : Implémentation du backend FastAPI (SQLAlchemy, 4 migrations Alembic, Keycloak JWT RS256, RBAC, rate limiter Redis Lua atomique). Intégration du pipeline IA : PandasAI, LiteLLM, fuzzy matcher, chart_resolver (8 types), DockerSandbox, WebSocket Pub/Sub.

- **Phase 4 — Frontend & Tests (S4, 20–31 juil.)** : Construction du frontend React 18 (UploadZone, AskiPage, Dashboard react-grid-layout, panneau Admin, keycloak-js). Campagne de tests (40 tests Pytest, 100%), correction des bugs critiques (NoResultFoundError, race condition Redis, spinner infini).

- **Phase 5 — Rédaction du Rapport (S4–S8, 25 juil. – fin août)** : Rédaction de la documentation technique, consolidation des chapitres 0 à 5, génération des diagrammes PlantUML.

> [Figure 17 : Diagramme de Gantt — Planning du Projet ClarIA — À insérer ici]

---

**Conclusion du chapitre**

Ce troisième chapitre a traduit les exigences fonctionnelles de ClarIA en une conception technique rigoureuse et documentée. Les choix technologiques — FastAPI asynchrone, SQLAlchemy 2.0, Keycloak 26, Celery/Redis, PandasAI + LiteLLM — ont été justifiés par rapport à leurs alternatives. L'ensemble des diagrammes UML produits — 2 diagrammes de composants, 2 cas d'utilisation, 3 classes (dont MCD/MLD), 2 de séquence, 3 d'activité (dont le diagramme d'état), 1 de déploiement — ainsi que le Diagramme de Gantt constituent le référentiel de conception sur lequel repose l'implémentation. Le chapitre suivant décrira la phase de réalisation technique, en montrant comment cette conception a été concrétisée en code fonctionnel.
