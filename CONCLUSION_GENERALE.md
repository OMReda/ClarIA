# CONCLUSION GÉNÉRALE ET PERSPECTIVES

---

## Synthèse des réalisations

Ce Projet de Fin d'Année avait pour objectif de concevoir et de développer une plateforme web intelligente permettant à tout professionnel, indépendamment de ses compétences techniques, d'interroger ses propres fichiers de données en langage naturel et d'en obtenir des visualisations graphiques interactives. La plateforme ClarIA, réalisée dans le cadre d'un stage de un mois au sein de **SKATYS** — SAP Gold Partner basé à Casablanca — sous l'encadrement de **Mme. BERRI Malak** (juillet 2026), répond intégralement à cet objectif.

Sur le plan technique, ClarIA est une application web full-stack de production, architecturée autour de cinq briques technologiques majeures et parfaitement intégrées :

**Le backend FastAPI** constitue le cœur applicatif de la plateforme. Il expose **5 routeurs** (`files`, `prompts`, `provider`, `websocket` et `admin` — ce dernier monté sous le préfixe `/api/v1/platform-users`), un endpoint de santé `/api/v1/health`, et un gestionnaire d'exceptions global qui masque systématiquement les traces de pile vers le client pour des raisons de sécurité. L'application impose dès le démarrage un guard Python (`main.py`) : PandasAI 3.0.0 requiert Python ≥ 3.10 et < 3.12 — toute version hors de cette plage est détectée et signalée. Les **4 migrations Alembic** — `001_initial`, `12a6875_drop_session_and_add_owner_id`, `795420f_add_preview_rows_column`, `3f8c1a2b_expand_chart_type_constraint` — témoignent d'une évolution maîtrisée du schéma de données au fil des itérations de développement.

**La sécurité Keycloak 26** assure l'authentification de chaque utilisateur via des jetons JWT RS256 signés. Le module `security.py` implémente une validation par suffixe d'issuer (`iss.endswith(f"/realms/{keycloak_realm}")`) qui rend la plateforme indépendante du nom d'hôte de déploiement — compatible aussi bien avec `localhost`, une IP LAN, un tunnel Cloudflare ou Ngrok. Le cache JWKS est configuré avec un `lifespan=900` secondes (15 minutes) pour minimiser les appels au serveur Keycloak tout en garantissant la fraîcheur des clés de signature. La vérification de l'`azp` (Authorized Party) remplace la vérification standard de l'`aud`. Le RBAC à deux niveaux — rôle `user` (accordé automatiquement à tout utilisateur authentifié sans rôle explicite) et rôle `admin` (vérifié strictement par `require_admin`) — protège l'intégralité des endpoints sensibles.

**Le pipeline IA asynchrone Celery** constitue la contribution technique la plus ambitieuse du projet. La tâche `process_prompt` dans `workers/tasks.py` orchestre les **8 étapes** suivantes : *(1)* marquage du prompt en `processing` et notification WebSocket immédiate ; *(2)* configuration dynamique de PandasAI par requête avec notification si Ollama est hors ligne et qu'un fallback cloud est utilisé ; *(3)* détection d'intention — LLM-based pour les fournisseurs cloud (Google, OpenAI, Anthropic), fallback par mots-clés pour Ollama local (afin d'éviter une double latence) ; *(4)* remplacement fuzzy haute-confiance des références de colonnes dans le texte utilisateur ; *(5)* détection du type de graphique via `detect_chart_type()` — heuristiques de mots-clés français/anglais + types de colonnes ; *(6)* chargement du fichier, construction du prompt d'ingénierie et appel PandasAI (avec ou sans `DockerSandbox` selon disponibilité) ; *(7)* conversion du DataFrame résultant en spécification ECharts via `build_chart_spec()` ; *(8)* persistance en base et publication de l'événement WebSocket `completed`. Le `DockerSandbox` (`pandasai-docker`) est démarré une seule fois par processus worker (`worker_init` signal) et stoppé proprement à l'arrêt (`worker_shutdown`). Le rate limiter Redis, implémenté via un script **Lua atomique** (INCR + EXPIRE conditionnelle en une seule exécution serveur), garantit la stabilité et l'équité du service à **30 requêtes/heure/utilisateur**, sans risque de race condition sur les nouvelles clés.

**Le frontend React 18** offre une expérience utilisateur fluide et moderne, structurée en **5 pages** distinctes (`LandingPage`, `UploadPage`, `AskiPage`, `DashboardPage`, `AdminPage`) et **3 stores Zustand** (`index.ts` — état principal, `datasetStore.ts` — gestion des datasets, `providerStore.ts` — statut du fournisseur LLM actif). L'interface de tableau de bord, bâtie sur `react-grid-layout`, permet à chaque utilisateur de composer son espace de reporting personnel de manière intuitive. Les **13 composants React** (`ChartDisplay`, `ClarificationDialog`, `DashboardView`, `Icon`, `KPICard`, `PreviewPanel`, `PromptBar`, `ProviderStatusBadge`, `SettingsPanel`, `SheetSelector`, `StatusToast`, `UploadZone`, `UserMenu`) couvrent l'ensemble des interactions utilisateur, de l'upload à la visualisation en passant par la gestion des préférences LLM.

**L'architecture Docker Compose** garantit la reproductibilité complète de l'environnement de déploiement en **8 services** interdépendants : `nginx` (reverse proxy — route `/api/` vers le backend et `/` vers le frontend), `frontend` (build Vite React servi en production), `api` (FastAPI), `worker` (Celery — monte `/var/run/docker.sock` pour le `DockerSandbox`), `redis` (Redis 7-alpine), `postgres` (PostgreSQL 16-alpine), `keycloak` (v26.0.0 avec import automatique du realm `claria`) et `ollama` (modèle `qwen2.5-coder:7b` auto-téléchargé). Un neuvième conteneur éphémère `migrate` exécute `alembic upgrade head` au démarrage avant l'API, garantissant que le schéma est toujours à jour. Quatre volumes Docker nommés (`pgdata`, `redisdata`, `ollamadata`, `filestore`) assurent la persistance des données entre les redémarrages.

---

## Objectifs atteints

Au terme du développement, la confrontation des réalisations avec le cahier des charges initial est entièrement positive :

| Exigence initiale | Réalisé |
| :--- | :---: |
| Import CSV / Excel avec validation stricte | ✅ |
| Normalisation automatique des formats français | ✅ |
| Sélection de feuille pour les fichiers Excel multi-onglets | ✅ |
| Requête en langage naturel (français) | ✅ |
| 8 types de graphiques ECharts (bar, line, pie, scatter, histogram, area, radar, heatmap) | ✅ |
| Explication textuelle en français | ✅ |
| Tableau de bord personnalisable (drag-and-drop) | ✅ |
| Indicateurs KPI dynamiques et graphiques manuels | ✅ |
| Authentification Keycloak JWT RS256 + RBAC (user/admin) | ✅ |
| Panneau d'administration complet | ✅ |
| Rate limiting Redis 30 req/h (Lua atomique) | ✅ |
| Confidentialité : exécution locale Ollama `qwen2.5-coder:7b` | ✅ |
| Fallback multi-fournisseurs LLM (Google, OpenAI, Anthropic via LiteLLM) | ✅ |
| Déploiement Docker Compose reproductible (8 services) | ✅ |
| Tests automatisés (40 tests Pytest, 100%) | ✅ |

---

## Apports personnels et retour d'expérience

Ce stage au sein de SKATYS a représenté une expérience formatrice à plusieurs niveaux. Sur le plan technique, il m'a permis d'approfondir de nombreux domaines abordés en cours de formation — architecture des applications web, gestion des identités, programmation asynchrone Python — en les confrontant aux exigences et aux contraintes d'un projet réel, avec des données imparfaites, des dépendances de bibliothèques complexes, et des problèmes d'intégration imprévus.

La gestion de la contrainte Python 3.10–3.11 imposée par PandasAI 3.0.0 (détectée dès `main.py` pour un signalement précoce), la résolution de la race condition du rate limiter Redis par un script Lua atomique (l'ancienne approche pipeline pouvait perdre l'EXPIRE en cas de coupure réseau post-INCR), la mise au point du mécanisme de validation d'issuer par suffixe dans `security.py` pour supporter Cloudflare/Ngrok sans hardcoder les hostnames, ou encore la détection duale d'intention (LLM pour le cloud, mots-clés pour Ollama local pour éviter la double latence) — autant de problèmes techniques non triviaux qui m'ont conduit à lire de la documentation de bas niveau, à déboguer des comportements concurrents, et à concevoir des solutions robustes et testées.

Sur le plan professionnel, ce projet m'a initié aux pratiques de l'ingénierie logicielle en entreprise au sein d'une entreprise de conseil de haut niveau : la rédaction d'un cahier des charges, la modélisation UML, la gestion des versions par branches, et la documentation technique. Il m'a également appris à prioriser les fonctionnalités dans un délai contraint, à accepter les imperfections d'une première version, et à documenter les limitations identifiées pour les équipes futures.

---

## Limites actuelles

Malgré la complétude fonctionnelle de la plateforme, plusieurs limitations ont été identifiées et méritent d'être documentées honnêtement :

1. **Dépendance au modèle LLM** : La qualité des graphiques générés dépend directement des capacités du modèle. Sur des jeux de données complexes, `qwen2.5-coder:7b` peut produire du code incorrect ou déclencher une `NoResultFoundError`. Un mécanisme de retry automatique avec reformulation du prompt constituerait une amélioration significative.

2. **Absence de support multi-fichiers** : La version actuelle ne permet d'interroger qu'un seul fichier à la fois. Les requêtes croisant plusieurs sources de données ne sont pas supportées.

3. **Limitation de la détection comparative** : Le `chart_resolver` supporte les comparaisons à deux termes via `_is_comparison_prompt()`, mais les comparaisons portant sur trois périodes ou plus ne sont pas systématiquement détectées.

4. **Pas de gestion optimisée des séries temporelles** : Les séries temporelles sont générées, mais sans détection automatique du format de date comme axe X temporel ni zoom ECharts natif.

5. **Interface mono-langue** : L'interface est entièrement en français. L'internationalisation vers l'anglais ou l'arabe n'a pas été implémentée.

6. **Dépendance au Docker socket** : Le `DockerSandbox` nécessite le montage de `/var/run/docker.sock` dans le conteneur worker. En production à grande échelle, il conviendrait d'utiliser Sysbox ou un daemon Docker dédié.

7. **Intégration spécifique à Ollama pour le mode local** : La sonde de disponibilité (`probe_ollama`) interroge l'endpoint `/api/tags` propre à l'API Ollama. D'autres solutions d'inférence locale — vLLM, LocalAI, llama.cpp server — permettent également d'exécuter des LLMs sur des serveurs privés sans envoyer de données à l'extérieur, mais nécessiteraient une adaptation de cette sonde pour être pleinement supportées. Ollama reste la solution recommandée pour sa simplicité d'installation, mais n'est pas la seule voie pour un déploiement local et confidentiel.

---

## Perspectives et évolutions futures

Les travaux réalisés posent des fondations solides sur lesquelles plusieurs évolutions peuvent être envisagées :

**Court terme (Évolutions Fonctionnelles) :**
- Retry intelligent avec reformulation du prompt en cas de `NoResultFoundError`
- Support des comparaisons multi-termes (> 2 groupes) dans `_is_comparison_prompt()`
- Ajout du type *treemap* pour les données hiérarchiques
- Internationalisation de l'interface (EN / AR)
- Détection automatique des séries temporelles avec zoom natif ECharts
- **Support d'autres serveurs d'inférence locale** : vLLM, LocalAI ou llama.cpp server pour les organisations disposant d'infrastructures GPU dédiées — l'architecture LiteLLM rend cette évolution réalisable sans refonte majeure du code.

**Moyen terme (ClarIA Entreprise) :**

- **Connexion aux bases de données décisionnelles** : Permettre une connexion directe aux bases relationnelles (PostgreSQL, MySQL), aux entrepôts de données (BigQuery, Snowflake, Azure Synapse) et, dans le contexte de SKATYS, aux exports SAP Analytics Cloud — sans étape d'export/import manuel.

- **Pipeline RAG (Retrieval-Augmented Generation)** : Enrichir dynamiquement le prompt `build_aggregation_prompt()` avec des documents de contexte récupérés par similarité sémantique — glossaires métier, dictionnaires de données, exemples SAP — augmentant la précision sur des domaines spécialisés.

- **Modèle d'embeddings local `bge-m3`** : Disponible via Ollama, multilingue (FR/EN/AR). Chaîne complète : *requête → `bge-m3` → ChromaDB/pgvector → contexte enrichi → PandasAI + `qwen2.5-coder:7b`*. 100% local, aucune donnée ne quittant l'infrastructure.

- **Support PDF/Word** : Via OCR (Tesseract/PaddleOCR) + pipeline RAG, interroger des rapports SAP PDF ou bilans financiers Word en langage naturel.

- **Rapports automatisés** : Celery Beat pour des analyses récurrentes (quotidiennes/hebdomadaires) avec alertes conditionnelles sur KPIs.

- **Tableau de bord collaboratif** : Partage de dashboards entre membres d'équipe avec niveaux de permission distincts.

- **Mode Hybride Graphique ↔ Chat** : Enrichir le classificateur d'intention d'une dimension *"graphique ou texte ?"* pour transformer ClarIA en assistant analytique conversationnel complet.

**Long terme (Vision Finale) :**

- **ClarIA Entreprise** : Interface universelle en langage naturel pour toute source de données — BigQuery, Snowflake, Kafka, Metabase/Superset via API.
- **Interface vocale** : Intégration Whisper (disponible via Ollama en local).
- **Observabilité LLM** : Métriques Prometheus/Grafana (taux de succès PandasAI, scores fuzzy, temps d'inférence).
- **Agent IA autonome** : RAG + mémoire conversationnelle + data warehouse = agent analytique planifiant et exécutant une série d'analyses à partir d'un objectif en une phrase.

---

## Mot de conclusion

La démocratisation de l'analyse de données est un enjeu organisationnel et sociétal majeur. Dans un monde où la donnée est omniprésente — notamment dans les systèmes ERP SAP qu'exploitent les clients de SKATYS — mais où les compétences pour l'exploiter restent rares et coûteuses, les interfaces en langage naturel représentent une rupture technologique dont l'impact potentiel est considérable. ClarIA est une première réponse concrète à cet enjeu : une réponse **technique rigoureuse** (architecture full-stack de production, pipeline IA asynchrone en 8 étapes, sécurité JWT RS256 éprouvée), une réponse **fonctionnelle complète** (22 exigences fonctionnelles toutes satisfaites, 40 tests passés à 100%), et une réponse **éthique** — celle d'une plateforme conçue pour que les données restent sous le contrôle de ceux qui les produisent, hébergées localement via Ollama, traitées confidentiellement, sans dépendance à un fournisseur cloud externe.

Le contexte dans lequel ce projet a été réalisé — un mois de stage intensif au sein de **SKATYS**, SAP Gold Partner reconnu, encadré par **Mme. BERRI Malak** — a imposé des contraintes de délai réelles qui ont elles-mêmes été une source d'apprentissage. Prioriser les fonctionnalités, accepter une première version imparfaite, documenter rigoureusement les anomalies et les limitations pour les équipes futures : autant de réflexes professionnels que ce projet a contribué à forger.

Les perspectives décrites — connexion aux data warehouses SAP, pipeline RAG avec `bge-m3`, alertes planifiées Celery Beat, tableau de bord collaboratif, interface vocale Whisper — ne sont pas de vagues ambitions, mais des évolutions techniquement réalisables sur la base de l'architecture existante, sans refonte majeure. ClarIA est conçue pour être étendue : son architecture modulaire, ses couches d'abstraction (LiteLLM pour les LLMs, SQLAlchemy pour les bases de données, Celery pour l'asynchronisme), et son système de configuration centralisé via `pydantic-settings` sont précisément pensés pour accueillir ces évolutions avec un minimum de friction.

Ce Projet de Fin d'Année constitue à la fois l'aboutissement de trois années de formation en Ingénierie Informatique et Réseaux à l'EMSI, et le point de départ d'un parcours professionnel que j'entends poursuivre résolument dans le domaine de l'intelligence artificielle appliquée au développement logiciel.
