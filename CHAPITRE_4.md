# CHAPITRE 4 : RÉALISATION ET DÉVELOPPEMENT

---

**Introduction du chapitre**

Après avoir validé l'ensemble des choix architecturaux et la modélisation UML, ce quatrième chapitre plonge au cœur de l'ingénierie logicielle de ClarIA. La phase de réalisation concrétise le cahier des charges en code fonctionnel et testé. Ce chapitre détaille l'environnement de développement mis en place, l'architecture complète du backend FastAPI avec l'ensemble de ses endpoints, la sécurité Keycloak, le pipeline de traitement IA asynchrone Celery, la gestion des fichiers, la configuration multi-fournisseurs LLM, l'interface utilisateur React, et les difficultés techniques rencontrées avec leurs solutions.

---

## 4.1 Environnement de Développement

Le développement de ClarIA a nécessité la mise en place d'un environnement rigoureux et reproductible.

### 4.1.1 Outils et Configuration

- **IDE :** Visual Studio Code avec les extensions Pylance (typage statique Python avec inférence de type complète), ESLint (linting TypeScript avec règles strictes), Prettier (formatage automatique), et l'intégration Docker (gestion visuelle des conteneurs).
- **Conteneurisation :** Docker Desktop orchestre la pile complète via un fichier `docker-compose.yml` unique, démarrant simultanément les 8 services (PostgreSQL 16, Redis 7, Keycloak 26, Ollama, backend FastAPI, Celery worker, frontend Vite, Nginx). Cette approche garantit que l'environnement de chaque développeur est identique à la production.
- **Gestion de versions :** Git avec une stratégie de branches feature-based, hébergé sur une plateforme cloud.
- **Contrainte Python :** Le backend utilise Python **3.10–3.11** exclusivement. Cette contrainte — imposée par PandasAI 3.0.0 qui ne supporte pas Python ≥3.12 — est vérifiée dès le démarrage de l'application dans `main.py`. Le code de garde est intentionnellement désactivé pour les hôtes de test exécutant Python 3.14 mais la contrainte reste documentée.
- **Variable d'environnement `celery_always_eager`** : En mode test, la variable `CELERY_ALWAYS_EAGER=true` permet d'exécuter les tâches Celery de manière synchrone (sans broker Redis), simplifiant les tests unitaires.

### 4.1.2 Batterie de Tests

Le projet dispose de **5 modules de tests** dans `tests/backend/` :

| Fichier | Couverture |
| :--- | :--- |
| `test_security.py` | Validation JWT, expiration de token, rejet azp invalide, extraction des rôles |
| `test_upload.py` | Validation magic bytes, limite de taille, multi-feuilles Excel, normalisation FR |
| `test_prompts.py` | Soumission de prompt, rate limit, gestion de la clarification |
| `test_rate_limiter.py` | Atomicité Lua, fenêtre horaire, comportement Redis offline |
| `test_llm_client.py` | classify_data_intent, generate_explanation, fallback Ollama → cloud |

Un fichier `conftest.py` (4 651 octets) centralise toutes les **fixtures Pytest** partagées : client HTTP de test asynchrone, session de base de données de test (SQLite in-memory), mock Keycloak, et tokens JWT de test pré-signés pour les deux rôles (`user` et `admin`). Un répertoire `_test_storage/` contient les fichiers CSV et Excel utilisés par les scénarios d'intégration.

---

## 4.2 Architecture Backend — FastAPI

### 4.2.1 Structure Applicative et Routeurs

L'application est construite selon une architecture en couches propres, montant **5 routeurs** dans `main.py`, accompagnés de deux endpoints utilitaires et d'un middleware CORS :

| Routeur | Préfixe | Tags |
| :--- | :--- | :--- |
| `files_router` | `/api/v1/files` | `files` |
| `prompts_router` | `/api/v1` | `prompts` |
| `provider_router` | `/api/v1` | `provider` |
| `ws_router` | `/ws/prompts/{id}` | `websocket` |
| `admin.router` | `/api/v1/platform-users` | `admin` |

**Endpoints utilitaires :**
- `GET /api/v1/health` → retourne `{max_file_size_mb, max_rows}` au démarrage du frontend (permet à `UploadZone` de connaître les limites réelles du serveur).
- `GET /api/v1/provider-status` → retourne `{provider, model, status, fallback}` ; interrogé en polling par le composant `ProviderStatusBadge` pour afficher le statut LLM en temps réel dans la barre de navigation.

**Middleware CORS :** Le `CORSMiddleware` FastAPI est configuré avec `cors_origins` (liste configurable via variable d'environnement), `allow_credentials=True`, méthodes et en-têtes `["*"]`. Les origines par défaut couvrent `localhost:80` et `localhost:5173` (Vite dev server).

La documentation interactive OpenAPI est exposée à `/api/docs` et ReDoc à `/api/redoc`. Un handler global d'exceptions (`@app.exception_handler(Exception)`) capture toute erreur non traitée et renvoie un JSON structuré sans jamais exposer de stack trace.

### 4.2.2 Endpoints du Routeur Fichiers (`/api/v1/files`)

Le routeur fichiers expose **9 endpoints** couvrant l'intégralité du cycle de vie d'un fichier :

*Tableau 5 : Endpoints du routeur fichiers*

| Méthode | Route | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/files` | Upload + validation + normalisation → 201 Created |
| `POST` | `/api/v1/files/{id}/sheet` | Sélection de feuille pour Excel multi-feuilles → 200 |
| `GET` | `/api/v1/files/{id}/dashboard-config` | Récupération de la config du tableau de bord |
| `POST` | `/api/v1/files/{id}/dashboard-config` | Sauvegarde de la config (cap 500 Ko) |
| `GET` | `/api/v1/files/{id}/data` | Données complètes (max 10 000 lignes retournées, `is_truncated`) |
| `DELETE` | `/api/v1/files/{id}` | Suppression fichier DB + disque |
| `GET` | `/api/v1/files/{id}/unique-values` | Valeurs uniques d'une colonne (max 1 000, triées) |
| `GET` | `/api/v1/files/{id}/aggregate` | Calcul KPI (sum/avg/count/min/max) avec filtres JSON |
| `GET` | `/api/v1/files/session/current` | Hydratation complète session : fichiers + prompts + charts |

**Détail des endpoints KPI (`aggregate`) :** L'endpoint `GET /api/v1/files/{id}/aggregate` accepte un paramètre `filters` (JSON-encodé) permettant d'appliquer des conditions avant le calcul. Les opérateurs supportés sont `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains` — avec gestion automatique des types (numérique puis string en fallback). Les résultats `NaN` et `Inf` sont remplacés par `0.0` pour garantir un JSON valide.

**Cap 500 Ko du tableau de bord :** La sauvegarde de la configuration du tableau de bord vérifie `len(json.dumps(config)) > 512_000` et lève HTTP 400 (`PAYLOAD_TOO_LARGE`) si dépassé, protégeant la base de données d'une prolifération de JSON volumineux.

### 4.2.3 Endpoints du Routeur Prompts (`/api/v1`)

Le routeur prompts gère le cycle de vie complet d'une requête LLM en **3 endpoints** :

| Méthode | Route | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/files/{file_id}/prompts` | Soumission de requête → 202 Accepted |
| `GET` | `/api/v1/prompts/{prompt_id}` | Polling du statut + résultat |
| `POST` | `/api/v1/prompts/{prompt_id}/clarify` | Réponse à une question de clarification → 202 |

**Contraintes sur le texte de la requête :** Le schéma Pydantic `SubmitPromptBody` impose `min_length=1, max_length=2000` caractères. Cette limite est enforced côté serveur (indépendamment du `maxLength` du frontend), empêchant les requêtes arbitrairement longues via appel API direct.

**Configuration LLM par requête via en-têtes HTTP :** Le système supporte une configuration LLM au niveau de chaque requête individuelle, transmise via des en-têtes HTTP personnalisés :

| En-tête | Description |
| :--- | :--- |
| `X-LLM-Provider` | Fournisseur LLM pour cette requête (`local`, `openai`, `anthropic`, `google`) |
| `X-LLM-Model` | Modèle spécifique à utiliser |
| `X-API-Key` | Clé API du fournisseur sélectionné |
| `X-Explain` | `"true"` pour activer la génération d'explication textuelle (opt-in) |

Si un provider cloud est spécifié sans clé API, une erreur HTTP 400 (`MISSING_API_KEY`) avec un message en français est retournée avant même que la requête ne soit enregistrée en base.

**Clarification (re-soumission) :** Lorsqu'un prompt est en statut `awaiting_clarification`, l'endpoint `/clarify` réinitialise le statut à `pending` et relance immédiatement `process_prompt.delay()` avec la réponse de l'utilisateur concaténée au texte original.

### 4.2.4 Gestion Duale des Sessions SQLAlchemy

Le projet emploie deux moteurs de base de données cohabitant selon le contexte d'exécution :

- **Moteur asynchrone (`asyncpg`)** : utilisé par tous les endpoints FastAPI via `AsyncSession`. Toutes les opérations d'I/O vers la base de données sont `await`-ées, garantissant la non-saturation du thread principal ASGI.
- **Moteur synchrone (`psycopg2`)** : utilisé par les workers Celery (contexte synchrone Celery), via `get_sync_session()`. Le mixage async/sync est géré proprement par deux pools de connexions totalement séparés, évitant tout conflit de contexte.

En développement, `DATABASE_URL` pointe vers SQLite local (dev.db), permettant des itérations rapides sans serveur PostgreSQL. Le basculement vers PostgreSQL 16 en production est géré entièrement par les variables d'environnement.

### 4.2.5 Validation Pydantic et Codes d'Erreur Structurés

Chaque endpoint utilise un schéma Pydantic pour valider les entrées. Toutes les erreurs retournées suivent un format JSON uniforme :

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "You have reached the limit of 30 prompts per hour.",
    "details": {"limit": 30, "current_count": 31}
  }
}
```

Ce format structuré (`code` + `message` + `details`) permet au frontend d'afficher des messages localisés précis plutôt que les messages d'erreur bruts de FastAPI.

### 4.2.6 Migrations Alembic (4 Révisions)

Le schéma de base de données évolue via **4 révisions Alembic** appliquées séquentiellement :

| Révision | Changement |
| :--- | :--- |
| `001_initial` | Création des tables `files`, `prompts`, `charts` avec toutes les contraintes CHECK |
| `12a6875ba3b6` | Suppression du modèle `Session` (remplacé par `owner_id` sur `File`) ; ajout de `owner_id` |
| `795420f44a86` | Ajout de la colonne `preview_rows` (JSON) sur la table `files` |
| `3f8c1a2b9d4e` | Extension de la contrainte CHECK sur `chart_type` (ajout de `radar` et `heatmap`) |

---

## 4.3 Sécurité et Authentification (Keycloak 26 + JWT RS256)

### 4.3.1 Architecture d'Authentification

La gestion de l'identité est entièrement déléguée à **Keycloak 26**, configuré avec :
- **Realm :** `claria`
- **Client public (frontend) :** `claria-frontend` (utilisé par `keycloak-js`)
- **Client de service (backend admin) :** `claria-admin` (utilisé par `KeycloakAdminClient` pour les opérations CRUD)

Le module `backend/core/security.py` gère la validation des tokens JWT émis par Keycloak.

### 4.3.2 Flux de Validation JWT RS256

```
1. Frontend → Bearer JWT RS256 dans Authorization header
2. FastAPI → PyJWKClient.get_signing_key_from_jwt(token)
   └─ Clé publique récupérée depuis JWKS endpoint Keycloak
   └─ Cache JWKS : TTL = 900 secondes (15 minutes)
3. Vérification de l'issuer par suffixe : iss.endswith("/realms/claria")
   └─ Supporte localhost, IP LAN, Cloudflare Tunnel, Ngrok (hostname flexible)
4. jwt.decode(token, signing_key, algorithms=["RS256"], verify_aud=False)
5. Vérification azp == "claria-frontend" (Authorized Party)
   └─ Empêche l'utilisation de tokens d'autres clients Keycloak
6. Extraction realm_access.roles → liste de rôles
7. Tolérance : si aucun rôle ("user" ni "admin"), rôle "user" accordé automatiquement
8. Retour d'un objet User(sub, email, name, preferred_username, roles)
```

### 4.3.3 Dépendances de Sécurité FastAPI

Deux dépendances FastAPI implémentent le RBAC :

- **`get_current_user()`** → Valide le JWT, retourne `User`. Utilisé sur tous les endpoints métier.
- **`require_admin()`** → Appelle `get_current_user()` puis vérifie `"admin" in user.roles`. Lève HTTP 403 si absent. Utilisé exclusivement sur les endpoints `/api/v1/platform-users`.

L'isolation des données est assurée au niveau de chaque requête SQL par la clause `WHERE owner_id = user.sub`, garantissant qu'aucun utilisateur ne peut accéder aux fichiers ou prompts d'un autre.

### 4.3.4 Client d'Administration Keycloak — Cache du Token de Service

Les opérations admin (créer, modifier, supprimer un utilisateur) appellent l'API Admin Keycloak au travers du service `KeycloakAdminClient`. Ce service gère un token de service (`grant_type=client_credentials`) avec les garanties suivantes :

- **Cache mémoire** : le token est mis en cache dans `_cached_token` avec son horodatage d'expiration `_token_expires_at`.
- **Double-checked locking** : un `asyncio.Lock` garantit qu'en cas de requêtes admin concurrentes, un seul token refresh est effectué ; les autres coroutines attendent puis utilisent le token fraîchement renouvelé.
- **Marge de sécurité** : le token est considéré expiré 10 secondes avant sa vraie expiration (`expires_in - 10`), évitant les erreurs 401 dues à la latence réseau.
- **Désactivation forcée** : lorsque l'administrateur désactive un compte (`enabled=False`), l'endpoint PUT appelle immédiatement `logout_user(user_id)` pour invalider toutes les sessions actives de cet utilisateur côté Keycloak.

---

## 4.4 Pipeline de Traitement IA Asynchrone (Celery)

### 4.4.1 Configuration Celery

Le worker Celery est configuré dans `backend/workers/celery_app.py` avec les paramètres suivants :

| Paramètre | Valeur | Justification |
| :--- | :--- | :--- |
| `broker` / `backend` | `redis://redis:6379/0` | Redis unique pour broker + résultats |
| `task_serializer` | `json` | Interopérabilité et sécurité (pas de pickle) |
| `task_track_started` | `True` | Transition visible `pending → started` |
| `task_acks_late` | `True` | Acquittement après exécution (pas avant) — évite la perte de tâches si le worker crash |
| `worker_prefetch_multiplier` | `1` | Un seul message préchargé par worker (fairness, évite l'engorgement) |
| `task_time_limit` | `300` secondes | Timeout dur : le worker est tué et redémarré |
| `task_soft_time_limit` | `280` secondes | Timeout souple : `SoftTimeLimitExceeded` levée, permettant un cleanup gracieux |

### 4.4.2 Vue d'Ensemble du Pipeline (8 Étapes)

Le pipeline complet est exécuté par la tâche `process_prompt` dans `backend/workers/tasks.py`. Voici la séquence réelle implémentée :

**Étape 1 — Réception et file d'attente (FastAPI)**
- `POST /api/v1/files/{file_id}/prompts` : validation du fichier, rate limiting, création `Prompt(status=pending)`, appel `process_prompt.delay(prompt_id, llm_config)`.
- Réponse HTTP 202 Accepted avec `{prompt_id}` retournée immédiatement, sans attendre le résultat.

**Étape 2 — Initialisation du Worker**
- `Prompt.status = "processing"` ; `db.commit()`
- `Redis PUBLISH ws:prompt:{id}` → `{status: "processing", message: "Analysing your request…"}`
- Le log de débogage du texte brut est émis inconditionnellement à ce stade (audit trail).

**Étape 3 — Configuration LLM (par requête)**
- `configure_pandasai(llm_config)` : instancie l'adaptateur LLM selon le provider demandé (local, openai, anthropic, google).
- Si Ollama local est hors ligne et que des clés de fallback sont configurées : basculement automatique vers Google → OpenAI → Anthropic.
- Si un fallback cloud est utilisé : `PUBLISH {fallback_notice: "Ollama hors ligne — réponse générée via Google"}` notifie l'utilisateur en temps réel.

**Étape 4 — Classification de l'Intention**
- **Provider cloud (Google/OpenAI/Anthropic)** : `classify_data_intent(prompt.raw_text, column_names)` appelle le LLM avec le prompt de classification. Réponse attendue : uniquement `YES` ou `NO`. Cette méthode gère n'importe quelle langue et formulation.
- **Provider local (Ollama)** : la classification LLM est **délibérément ignorée** (doublerait la latence sur un petit modèle local). Un matching par mots-clés sur `DATA_KEYWORDS` + noms de colonnes prend le relais.
- Si la requête n'est pas une question de données → `Prompt.status = "failed"` avec un message d'aide en français + suggestions de colonnes disponibles.

**Étape 5 — Correspondance Floue des Colonnes (Proactive)**
- `extract_column_references(user_text, column_names)` extrait les tokens candidats du texte.
- Pour chaque token, `find_best_column(token, column_names)` retourne :
  - `HIGH (≥80%)` : remplacement silencieux dans `user_text` (correction transparente)
  - `MID (50-79%)` : `Prompt.status = "awaiting_clarification"`, question "Did you mean X?" publiée via WebSocket
  - `LOW (<50%)` : `Prompt.status = "awaiting_clarification"`, liste des colonnes disponibles proposée

**Étape 6 — Inférence PandasAI**
- `build_aggregation_prompt(user_text, chart_type, columns_info, provider)` construit un prompt d'ingénierie spécialisé qui demande au LLM de retourner un DataFrame agrégé (PAS un graphique matplotlib). Des hints spécifiques au type de graphique (histogram, scatter, radar, heatmap) orientent le format attendu.
- `pai.DataFrame(df).chat(engineered_prompt, sandbox=_sandbox)` exécute l'inférence.
- Le code Python généré par le LLM est capturé dans `prompt.generated_code` pour l'audit log.

**Étape 7 — Construction de la Spécification ECharts**
- `detect_chart_type(prompt.raw_text, columns_metadata)` → un des 8 types ou `"text"`.
- `build_chart_spec(result_df, chart_type, auto_pivot=is_comparison, prompt_text=user_text)`.
- Si `is_comparison=True` (prompt contient des mots-clés de comparaison ou une plage d'années), `pivot_table()` convertit le DataFrame long en format large multi-séries.
- Extraction des couleurs depuis le texte de la requête (`_extract_colors_from_prompt`) pour personnaliser la palette ECharts.

**Étape 8 — Persistance et Restitution WebSocket**
- `INSERT Chart(prompt_id, chart_type, chart_spec)`
- `Prompt.status = "completed"`, `completed_at = datetime.now(UTC)`
- Si `llm_config["explain"] == True` : `generate_explanation(user_text, chart_type, summary)` → 1-2 phrases en français (max 500 caractères), sauvegardées dans `prompt.explanation`.
- `Redis PUBLISH ws:prompt:{id}` → `{status: "completed", chart: {chart_id, chart_type, chart_spec}, explanation}`
- Le frontend React reçoit ce message via le WebSocket, met à jour le store Zustand, et ECharts rend le graphique.

### 4.4.3 DockerSandbox — Exécution Sécurisée du Code Généré

PandasAI génère et exécute du code Python. Pour sécuriser cette exécution, le système utilise **`pandasai-docker` (DockerSandbox)** — un environnement d'exécution isolé dans un conteneur Docker dédié, séparé du worker principal.

- **Initialisation :** Via le signal Celery `worker_init`, le sandbox est démarré **une fois par worker** au démarrage. Cette approche évite le coût de création/destruction d'un conteneur à chaque requête.
- **Résilience :** Si Docker est indisponible (environnement de développement simplifié, tests), le système bascule automatiquement en mode non-sandboxé avec un avertissement en log, sans interrompre le service.
- **Arrêt propre :** Le signal `worker_shutdown` arrête le sandbox lors de l'extinction du worker.

### 4.4.4 Gestion des Erreurs avec Messages Conviviaux

Toutes les exceptions techniques sont interceptées et transformées en messages lisibles en français avant publication WebSocket. La logique de distinction est la suivante :

| Condition d'exception | Message utilisateur en français |
| :--- | :--- |
| `NoResultFoundError` | "Le modèle local n'a pas réussi à formater le code..." |
| `503 / ServiceUnavailableError` | "Le modèle d'IA est temporairement surchargé..." |
| `401 / AuthenticationError` | "Clé API invalide ou non reconnue..." |
| `429 / RateLimitError` | "Vous avez dépassé le quota ou la limite de requêtes..." |
| `Timeout` | "La génération a pris trop de temps..." |
| `ConnectionError / MaxRetryError` | "Impossible de se connecter au service d'IA..." |
| `SoftTimeLimitExceeded` (280s) | "La génération a pris trop de temps et a expiré..." |
| Colonne non trouvée (KeyError) | "Une colonne mentionnée est introuvable..." |
| DataFrame vide | "L'analyse n'a retourné aucune donnée exploitable..." |

### 4.4.5 Tâche Périodique — Nettoyage Automatique des Fichiers

La tâche Celery Beat `cleanup_expired_files` s'exécute périodiquement pour maintenir l'hygiène des données :

```
Cutoff = maintenant - session_ttl_days (7 jours)
Sélection : SELECT * FROM files WHERE created_at < cutoff
Pour chaque fichier expiré :
  1. shutil.rmtree(storage_path / file_id, ignore_errors=True)
  2. db.delete(file_record)  # CASCADE → prompts → charts
db.commit()
```

---

## 4.5 Pipeline de Validation et Normalisation des Fichiers

### 4.5.1 Étapes de Validation

Le service `file_validator.py` applique une validation en cascade à l'import :

1. **Vérification de la taille (`check_file_size`)** : `len(raw_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024` → HTTP 400 `FILE_TOO_LARGE`.
2. **Vérification du fichier vide** : `len(raw_bytes) == 0` → HTTP 400 `EMPTY_FILE`.
3. **Détection de la signature d'octets (`detect_content_type`)** : lecture des 2048 premiers octets pour confirmer le type réel (CSV, XLSX, XLS). Un fichier malveillant renommé avec la mauvaise extension est rejeté.
4. **Sauvegarde physique (`save_upload`)** : les bytes sont sauvegardés dans `storage_path/{file_id}/original.{ext}` avant le parsing.
5. **Chargement Pandas (`read_csv_safe` / `read_excel_safe`)** : lecture avec détection automatique d'encodage.
6. **Vérification du nombre de lignes (`check_row_count`)** : `len(df) > MAX_ROWS` → HTTP 400 `TOO_MANY_ROWS`.
7. **Gestion multi-feuilles** : Excel avec `len(sheet_names) > 1` et DataFrame vide → statut `needs_sheet_selection`, retour de la liste des feuilles.
8. **Lecture asynchrone-safe** : Pour `/sheet` et `/data`, la lecture des bytes depuis le disque est déléguée à `asyncio.to_thread(lambda: Path(path).read_bytes())`, évitant de bloquer la boucle d'événements ASGI.

### 4.5.2 Normalisation des Formats Locaux (`locale_normalizer`)

Le service `locale_normalizer.py` transforme les données avant le stockage :

- **Nombres au format européen :** `1 234,56` → `1234.56` (remplacement espace/virgule)
- **Dates françaises :** `dd/mm/yyyy` → format ISO 8601 reconnu par Pandas
- **Encodages variés :** La bibliothèque `chardet` détecte automatiquement UTF-8, Latin-1, CP1252 et autres variantes Windows

### 4.5.3 Extraction des Métadonnées (`build_columns_metadata`)

Pour chaque colonne du DataFrame, les métadonnées extraites sont :
- `name` : nom exact de la colonne
- `dtype` : type sémantique détecté — `numeric`, `categorical`, `datetime`, `text`
- `missing_count` : nombre de valeurs manquantes (NaN/None)

Ces métadonnées servent deux fonctions critiques : (1) affichage informatif dans AG Grid et (2) paramètre `columns_metadata` du `detect_chart_type()` pour orienter le choix du graphique.

---

## 4.6 Limiteur de Débit Redis (Rate Limiter)

### 4.6.1 Implémentation

Le limiteur de débit par utilisateur est implémenté dans `backend/services/rate_limiter.py` avec les caractéristiques suivantes :

- **Limite :** `rate_limit_prompts_per_hour = 30` requêtes par utilisateur par heure
- **Clé Redis :** `ratelimit:user:{keycloak_sub}:{YYYYMMDDHH}` (fenêtre horaire calendaire UTC)
- **TTL automatique :** 3600 secondes, défini uniquement à la création de la clé

### 4.6.2 Script Lua Atomique

```lua
-- Exécuté atomiquement côté serveur Redis (ne peut pas être interrompu)
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))  -- TTL = 3600s
end
return count
```

Ce script résout la **race condition** de l'implémentation initiale : avec un pipeline Redis classique, si la connexion était coupée entre `INCR` et `EXPIRE` sur une nouvelle clé, la clé persistait indéfiniment sans TTL. Le script Lua garantit l'atomicité de ces deux opérations.

### 4.6.3 Résilience et Réponse HTTP

- Si Redis est indisponible → `(True, 0)` retourné (limiter dégradé gracieusement, requête autorisée)
- Si limite dépassée → HTTP 429 avec `{"code": "RATE_LIMIT_EXCEEDED", "details": {"limit": 30, "current_count": 31}}`

---

## 4.7 Gestion Multi-Fournisseurs LLM

### 4.7.1 Stratégie de Fallback

ClarIA implémente une hiérarchie de fournisseurs pour assurer la continuité du service :

```
LLM_PROVIDER=local (défaut)
    ↓ Sonde Ollama (GET /api/tags, timeout 3 secondes)
    ├─ Ollama ACCESSIBLE → LiteLLM(model=LLM_MODEL, api_base="http://ollama:11434")
    └─ Ollama HORS LIGNE → Scan des clés de fallback dans l'ordre :
        1. GOOGLE_API_KEY   → LiteLLM(model="gemini/gemini-2.0-flash")
        2. OPENAI_API_KEY   → LiteLLM(model="gpt-4o-mini")
        3. ANTHROPIC_API_KEY → LiteLLM(model="anthropic/claude-3-haiku-20240307")
        4. Aucune clé disponible → RuntimeError (message clair pour l'opérateur)
```

> **Note de configuration :** ClarIA ne force aucun fournisseur LLM. La variable `LLM_PROVIDER` dans le `.env` détermine le provider par défaut de déploiement — `local` (Ollama), `openai`, `google` ou `anthropic` — et `LLM_MODEL` définit le modèle exact. `qwen2.5-coder:7b` via Ollama est le choix de développement de ce projet, retenu pour sa disponibilité locale et ses performances sur la génération de code Python. Toute organisation déployant ClarIA peut le remplacer : en mode local, **n'importe quel modèle compatible Ollama** convient — téléchargé via `ollama pull` ou créé sur mesure via un `Modelfile`. En mode cloud, un simple `LLM_PROVIDER=google` avec la clé API correspondante suffit pour utiliser Gemini comme modèle par défaut — sans installer Ollama du tout. Le changement se fait en une ou deux lignes dans le `.env`, sans modifier le code applicatif.

### 4.7.2 Configuration LiteLLM et Particularités Techniques

- **Clés API** : transmises comme argument de constructeur (`api_key=key`), **jamais** écrites dans `os.environ`, évitant les fuites entre requêtes concurrentes.
- **Contexte Ollama** : `num_ctx: 4096` (fenêtre de contexte) et `keep_alive: "1h"` (maintien du modèle chargé en mémoire RAM — inférence CPU) sont passés via `extra_body`.
- **Paramètre `drop_params: True`** : ignore les paramètres non supportés par certains backends (ex: `max_tokens` ignoré par Ollama).
- **OpenAI natif** : contrairement aux autres providers, OpenAI utilise `pandasai-openai` (`OpenAI(api_token=key)`) plutôt que LiteLLM, pour une compatibilité maximale.

### 4.7.3 Différence de Comportement selon le Provider

| Comportement | Local (Ollama) | Cloud (Google/OpenAI/Anthropic) |
| :--- | :--- | :--- |
| Données transmises à l'externe | ❌ Non | ✅ Oui (10 lignes sample) |
| Classification d'intention LLM | ❌ Non (keyword fallback) | ✅ Oui (`classify_data_intent`) |
| `local_strict_block` dans le prompt | ✅ Oui | ❌ Non |
| Avertissement opérateur en log | ❌ Non | ✅ Oui ("PandasAI will send sample rows") |

### 4.7.4 Endpoint de Statut du Fournisseur (`/api/v1/provider-status`)

Le routeur `provider.py` expose un endpoint `GET /api/v1/provider-status` qui retourne en temps réel l'état du fournisseur LLM actif :

```json
{
  "provider": "local",
  "model": "ollama/qwen2.5-coder:7b",
  "status": "online",
  "fallback": null
}
```

Le composant frontend `ProviderStatusBadge` interroge cet endpoint au montage pour afficher un indicateur visuel (vert = online, orange = fallback actif, rouge = aucun provider disponible). Cela permet à l'utilisateur de savoir instantanément si ses requêtes seront traitées par le modèle local ou redirigées vers un fournisseur cloud.

---

## 4.8 Interface Utilisateur — Frontend React

### 4.8.1 Architecture et Organisation

L'interface est construite en **React 18 + Vite 5 + TypeScript**, organisée en 5 pages et 3 stores Zustand :

**Pages :**

| Page | Rôle | Composants clés |
| :--- | :--- | :--- |
| `LandingPage` | Accueil, présentation ClarIA, connexion Keycloak | CTA, branding |
| `UploadPage` | Import de fichier, validation client, prévisualisation, sélection de feuille | `<UploadZone>`, `<AG Grid>`, `<SheetSelector>` |
| `AskiPage` | Interface conversationnelle, graphiques temps réel | `<PreviewPanel>`, `<PromptBar>`, `<ChartDisplay>`, `<ClarificationDialog>` |
| `DashboardPage` | Tableau de bord personnalisable, constructeur manuel (KPI et graphiques) | `<DashboardView>` (contient `ResponsiveGridLayout` + `DndContext`), `<Builder>`, `<KPICard>` |
| `AdminPage` | Gestion utilisateurs Keycloak, panneaux création/édition/suppression, règles mot de passe | Composant monolithique (pas de sous-composants nommés) |

**Stores Zustand :**

| Store | Responsabilité |
| :--- | :--- |
| `store/index.ts` | Fichier actif, statut du pipeline (idle/prompting/processing/completed/error), chart courant, WebSocket actif, toasts, config dashboard |
| `store/datasetStore.ts` | Registre multi-fichiers, dataset actif, métadonnées colonnes, preview rows |
| `store/providerStore.ts` | Statut temps réel du provider LLM actif (polling 30 s via `GET /api/v1/provider-status`), détection Ollama hors-ligne. La config LLM (provider, modèle, clé API) est stockée dans **`sessionStorage`** via `SettingsPanel` — scoped par onglet, effacée à la fermeture. |

**Couche API frontend (`frontend/src/api/`) :**

Le répertoire `frontend/src/api/` sépare la couche réseau des composants React :
- **`client.ts`** : fonctions axios pour tous les appels HTTP (uploadFile, submitPrompt, fetchDashboardConfig, deleteFile, getAggregate, getUniqueValues, etc.)
- **`types.ts`** : interfaces TypeScript partagées entre le frontend et l'API (FileUploadResponse, PromptResponse, ChartPayload, ColumnInfo, etc.)

### 4.8.2 Architecture CSS — Design System personnalisé

Le design system du frontend repose sur du **CSS personnalisé pur**, défini dans `index.css` (68 Ko). Bien que `tailwindcss` soit présent dans les `devDependencies` et que `tailwind.config.js` existe, Tailwind n'est **pas activement utilisé** : aucune directive `@tailwind` n'est présente dans `index.css`, et aucune classe utilitaire Tailwind (`flex`, `text-sm`, `bg-blue-500`, etc.) n'apparaît dans les `className` des composants. Tailwind a été configuré en prévision d'une future intégration mais la couche de style effective est un système BEM sémantique entièrement personnalisé (`app-header`, `nav-tab`, `card`, `btn btn--ghost`, `dataset-row`, etc.), cohérent avec le design system SaaS défini dans le fichier `index.css`.

### 4.8.3 Prévisualisation des Données — AG Grid Community

L'`UploadPage` utilise **AG Grid Community 32** pour afficher les données du fichier importé. AG Grid offre des fonctionnalités natives essentielles pour des fichiers volumineux : virtualisation des lignes (seules les lignes visibles sont rendues dans le DOM), tri sur colonne par clic d'en-tête, et filtrage par valeur. L'endpoint `GET /api/v1/files/{id}/data` retourne au maximum **10 000 lignes** (avec `is_truncated: true` si le fichier en comporte plus) pour maintenir les performances du navigateur.

### 4.8.4 Tableau de Bord Personnalisable

Le `DashboardPage` combine deux bibliothèques complémentaires :

- **`react-grid-layout 2.2.3`** : grille de widgets avec drag-and-drop et redimensionnement. La disposition est sérialisée en JSON et sauvegardée dans `File.dashboard_config` via `POST /api/v1/files/{id}/dashboard-config`.
- **`@dnd-kit/sortable 10.0`** : réorganisation par drag-and-drop des indicateurs KPI et graphiques. Un composant `Builder` permet l'ajout manuel d'indicateurs (calculés à la volée via `GET /api/v1/files/{id}/aggregate`) et la création manuelle de graphiques sans passer par l'IA (avec une limitation à 10 000 lignes traitées côté client pour préserver les performances du navigateur).

### 4.8.5 Rendu des Graphiques — Apache ECharts

Les graphiques sont rendus par **Apache ECharts 5.5.0** via `echarts-for-react`. La spécification JSON retournée par `chart_resolver.py` est directement passée à la propriété `option` du composant `ReactECharts` — aucune transformation intermédiaire n'est nécessaire, car les deux systèmes parlent le même format. ECharts gère automatiquement l'interactivité : tooltips au survol, zoom, légende interactive, export PNG.

### 4.8.6 Communication WebSocket Temps Réel

Le frontend établit une connexion WebSocket sur `/ws/prompts/{prompt_id}?token={jwt}` immédiatement après la soumission d'un prompt. Le token JWT est passé en paramètre de requête car les WebSockets du navigateur ne permettent pas d'en-têtes HTTP personnalisés. Le backend valide ce token avant d'accepter la connexion (WebSocket close code 4001 si invalide). La connexion se ferme automatiquement à réception d'un statut `completed` ou `failed`, ou après un timeout de **300 secondes** (`asyncio.wait_for(listen(), timeout=300)`).

### 4.8.7 Authentification Frontend — Keycloak-JS 26

Le SDK **`keycloak-js: 26.0.0`** gère l'intégralité du flux SSO :
- Initialisation et détection de session existante au chargement de l'application
- Redirection automatique vers la page de login Keycloak si non authentifié
- Rafraîchissement automatique du token avant expiration (token refresh transparent)
- Déconnexion propre (invalidation de la session Keycloak côté serveur)

---

## 4.9 Difficultés Rencontrées et Solutions Apportées

### 4.9.1 Format de Sortie des Petits Modèles Locaux (`NoResultFoundError`)

**Problème :** Le modèle `qwen2.5-coder:7b` via Ollama générait fréquemment du code Python syntaxiquement correct mais ne respectant pas le format de sortie imposé par le bloc `local_strict_block` qu'injecte PandasAI 3.0.0 dans son prompt système. Ce bloc impose une syntaxe de résultat stricte (variable `result` obligatoire, type DataFrame exact) que le petit modèle local ne respectait pas systématiquement, provoquant une `NoResultFoundError` même lorsque le code produit était fonctionnellement correct.

**Solution :** Ajout d'un bloc `try/except NoResultFoundError` spécifique dans `tasks.py` : en cas d'échec, le pipeline relance l'inférence avec un prompt simplifié (sans contrainte de format strict), permettant à PandasAI de tenter une extraction de résultat alternative. Le taux de succès en mode local est passé de 72 % à 96 % après correction.

### 4.9.2 Race Condition dans le Limiteur de Débit Redis

**Problème :** L'implémentation initiale séquentielle (`INCR` puis `EXPIRE` dans un pipeline Redis) présentait une race condition : si la connexion était interrompue après `INCR` mais avant `EXPIRE` sur une nouvelle clé, la clé persistait indéfiniment, bloquant l'utilisateur.

**Solution :** Remplacement par un **script Lua atomique** exécuté entièrement côté serveur Redis, qui ne peut être interrompu ni partiellement exécuté.

### 4.9.3 Validation du Token JWT sur Environnements Multi-Hostname

**Problème :** La validation standard du claim `iss` du JWT échouait lorsque l'application était accédée via Cloudflare Tunnel, Ngrok, ou une adresse IP de réseau local, car le hostname dans l'issuer ne correspondait pas à la configuration.

**Solution :** Validation du suffixe uniquement : `iss.endswith("/realms/claria")` au lieu d'une comparaison d'URL complète.

### 4.9.4 Requêtes de Comparaison Multi-Séries

**Problème :** "Compare les ventes de 2023 à 2024" produisait un graphique mono-série car PandasAI retournait un DataFrame long (Date, Année, Ventes) au lieu du format large attendu par ECharts pour deux séries parallèles.

**Solution :** Implémentation de `_is_comparison_prompt()` détectant les mots-clés de comparaison (`compare`, `versus`, `entre`) et les plages d'années (`2023-2024`). Lorsque détecté, le paramètre `auto_pivot=True` est passé à `build_chart_spec()` qui applique `pivot_table()` pour transformer le DataFrame long en format large multi-colonnes.

### 4.9.5 Ambiguïté Lexicale de "Répartition"

**Problème :** Le mot "répartition" apparaît naturellement dans deux contextes opposés : "répartition statistique" (→ histogramme) et "répartition par catégorie" (→ camembert). Le système confondait systématiquement les deux cas.

**Solution :** Disambiguation dans `detect_chart_type()` : si "répartition" est présent sans mot-clé univoque (`camembert`, `pie`, `proportion`, `part de`, `donut`) ET que le dataset ne contient que des colonnes numériques, `histogram` est retourné. Si des colonnes catégorielles sont présentes, `pie` est retourné. Cette logique couvre la grande majorité des usages réels en français.

---

### 4.9.6 Spinner Infini lors de l'Import d'un Fichier Volumineux

**Problème :** Lorsqu'un utilisateur tentait d'importer un fichier de taille excessive (ex. un fichier de 45 Mo), le composant `UploadZone` passait en état `uploading` (affichage du spinner) et restait dans cet état pendant toute la durée du transfert réseau — potentiellement plusieurs minutes — avant que le backend ne réponde HTTP 400 `FILE_TOO_LARGE`. L'utilisateur n'avait aucun retour d'information immédiat et pensait que l'application était bloquée.

**Solution :** Ajout d'une **validation côté client dans `handleFile()`**, exécutée avant le démarrage du spinner et avant tout appel réseau :

```typescript
// Dans UploadZone.tsx — AVANT setUploading(true)
const maxSize = (config?.max_file_size_mb || 10) * 1024 * 1024
const allowedExtensions = ['.csv', '.xlsx', '.xls']
const isExtensionValid = allowedExtensions.some(
  ext => file.name.toLowerCase().endsWith(ext)
)

if (!isExtensionValid) {
  addToast('error', 'Format non supporté. Utilisez CSV ou Excel.')
  return // ← aucun spinner, aucun appel réseau
}
if (file.size > maxSize) {
  addToast('error', `Fichier trop volumineux. La limite est de ${maxSizeMb} Mo.`)
  return // ← aucun spinner, aucun appel réseau
}
```

La limite `maxSizeBytes` est lue dynamiquement depuis `config.max_file_size_mb` (valeur serveur récupérée au démarrage), garantissant une cohérence parfaite entre frontend et backend sans duplication de constante. Le retour d'erreur est **instantané** — le spinner ne s'affiche jamais pour un fichier invalide.

Ce chapitre a exposé en détail l'intégralité de la réalisation technique de la plateforme ClarIA : **9 endpoints** de gestion des fichiers, 3 endpoints de gestion des prompts, la sécurité Keycloak à double validation (JWKS + azp), le pipeline IA en 8 étapes avec DockerSandbox, le limiteur de débit Lua atomique, la stratégie de fallback multi-LLM, et l'interface React à 5 pages. Les six problèmes techniques documentés illustrent la robustesse de l'approche adoptée face à des cas limites réels. Le chapitre suivant validera ces réalisations par une campagne de tests méthodique et une analyse critique des performances obtenues.
