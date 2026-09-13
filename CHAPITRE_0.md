<div align="center">

# RAPPORT DE STAGE / PROJET DE FIN D'ANNÉE (PFA)

<br>

**Sous le Thème :**
## ClarIA – Plateforme Intelligente de Restitution de Données par Génération Automatique de Visualisations en Langage Naturel

<br>
<hr style="width: 50%; margin: 20px auto;">
<br>

**Réalisé par :**<br>
OUSSAMA MOHAMED REDA

<br>

**Filière :**<br>
3ème Année Ingénierie Informatique et Réseaux (3IIR)

<br>

**Année universitaire :**<br>
2025 – 2026

<br>

**Encadré par :**<br>
Mme. BERRI Malak (Encadrante, SKATYS)

<br>

**Date de soutenance :**<br>
[JJ / MM / AAAA]

<br>

**École :**<br>
EMSI (École Marocaine des Sciences de l'Ingénieur)

<br>

**Organisme d'accueil (Stage) :**<br>
SKATYS

</div>

<div style="page-break-after: always;"></div>

# REMERCIEMENTS

Au terme de ce stage et de ce Projet de Fin d'Année, je tiens à exprimer ma profonde gratitude envers toutes les personnes qui ont contribué, de près ou de loin, à la réussite de ce travail et à l'aboutissement de la plateforme ClarIA.

J'adresse mes remerciements les plus sincères à mon encadrante, **Mme. BERRI Malak (SKATYS)**, pour sa disponibilité constante, ses conseils judicieux et son accompagnement rigoureux tout au long de la réalisation de ce projet. Son expertise en ingénierie logicielle, en architecture des systèmes distribués et en intelligence artificielle m'a permis de structurer ma démarche technique avec rigueur et d'aborder avec sérénité les nombreux défis inhérents à l'intégration de modèles de langage dans une application web de production.

Mes vifs remerciements s'adressent également au corps professoral et administratif de **l'École Marocaine des Sciences de l'Ingénieur (EMSI)** pour la qualité de l'enseignement dispensé durant mon cursus en **3ème Année Ingénierie Informatique et Réseaux (3IIR)**. Les compétences acquises en développement logiciel, en conception d'architectures distribuées et en bases de données ont constitué le fondement technique sur lequel la plateforme ClarIA a été entièrement construite.

Je tiens à exprimer ma reconnaissance envers les professionnels et les utilisateurs finaux qui ont accepté de tester les versions préliminaires de la plateforme et de me faire part de leurs retours. Leurs remarques sur la fluidité de l'interface, la pertinence des graphiques générés et la simplicité du parcours d'import de fichiers ont été déterminantes pour affiner les fonctionnalités et améliorer l'expérience utilisateur tout au long du développement.

J'adresse enfin mes remerciements les plus sincères à ma famille et à mes proches pour leur soutien moral indéfectible, leurs encouragements continus et leur patience durant ces mois de travail acharné. Ce projet est aussi le fruit de leur présence bienveillante.

<div style="page-break-after: always;"></div>

# RÉSUMÉ

La transformation numérique des organisations génère des volumes croissants de données tabulaires (fichiers CSV, feuilles Excel) dont l'exploitation analytique reste largement inaccessible aux équipes non techniques, faute d'outils simples et intuitifs. Dans ce contexte, ce rapport présente la conception, le développement et la validation de la plateforme **ClarIA**, une solution web intelligente permettant à tout utilisateur de générer automatiquement des visualisations graphiques interactives à partir de ses fichiers de données, en formulant simplement sa demande en langage naturel.

ClarIA est structurée autour d'une architecture en couches : le backend repose sur **FastAPI** (Python 3.11) avec **SQLAlchemy 2.0** pour la persistance des données — **SQLite** en développement, **PostgreSQL** en production — et quatre migrations **Alembic** pour la gestion de l'évolution du schéma. Le traitement asynchrone des requêtes est orchestré par **Celery** et **Redis** (broker et backend de résultats). L'interface utilisateur est développée en **React 18** avec **Vite** et **TypeScript strict**, structurée en cinq pages distinctes : la page d'accueil (Landing), l'import de fichiers (Upload), l'interface conversationnelle (Aski), le tableau de bord (Dashboard) et le panneau d'administration (Admin). L'authentification est assurée par **Keycloak 26** (realm `claria`) via des jetons JWT RS256 validés par cache JWKS (900 secondes).

Le cœur intelligent de la plateforme est le module **Aski**, une interface conversationnelle construite autour de **PandasAI** et de son extension **pandasai-litellm**. Par défaut, ClarIA utilise le modèle local **Ollama `qwen2.5-coder:7b`** hébergé sur l'infrastructure même, garantissant qu'aucune donnée ne quitte l'organisation. Un mécanisme de basculement automatique vers les APIs cloud (OpenAI, Anthropic, Google Gemini via **LiteLLM**) est déclenché si le serveur Ollama est indisponible. Chaque requête utilisateur passe par plusieurs services spécialisés : un classificateur d'intention LLM (`classify_data_intent`), un moteur de correspondance floue des colonnes (`rapidfuzz`, seuils configurables à 80% et 50%), un détecteur de type de graphique par mots-clés, et un constructeur de spécifications **Apache ECharts** (8 types : barres, lignes, aires, secteurs, nuages de points, histogrammes, cartes de chaleur, radar). Le résultat est transmis en temps réel via **WebSocket**. Un module complémentaire (`generate_explanation`) produit automatiquement une synthèse textuelle en français de deux phrases décrivant le graphique généré.

Les graphiques produits peuvent être épinglés sur un **Tableau de Bord** personnalisable par glisser-déposer (`react-grid-layout`) et persisté en base de données sous forme de configuration JSON (plafond de 500 Ko). Il est également possible de créer des **graphiques manuellement** (via un constructeur intégré traitant jusqu'à 10 000 lignes côté client) et d'ajouter des **indicateurs KPI** (somme, moyenne, comptage, minimum, maximum) depuis les données du fichier actif. La sécurité est renforcée par un limiteur de débit Redis (30 requêtes par utilisateur par heure) et une validation stricte des fichiers téléversés (libmagic, signature d'octets, limite à 10 Mo, 100 000 lignes maximum).

Les tests de validation automatisés démontrent que la plateforme ClarIA répond à l'ensemble des exigences fonctionnelles et non fonctionnelles définies dans le cahier des charges, avec une suite de **40 tests passant à 100%**.

**Mots-clés :** Intelligence Artificielle, Génération de Graphiques, Langage Naturel, PandasAI, LLM, Ollama, FastAPI, React, Keycloak, Tableau de Bord, Visualisation de Données, Celery, Redis, WebSocket.

<div style="page-break-after: always;"></div>

# ABSTRACT

The digital transformation of organizations generates growing volumes of tabular data (CSV files, Excel spreadsheets) whose analytical exploitation remains largely inaccessible to non-technical teams, due to the lack of simple and intuitive tools. Within this context, this report presents the design, development, and validation of the **ClarIA** platform, an intelligent web solution enabling any user to automatically generate interactive graphical visualizations from their data files, by simply formulating their request in natural language.

ClarIA is built on a layered architecture: the backend uses **FastAPI** (Python 3.11) with **SQLAlchemy 2.0** for data persistence — **SQLite** in development, **PostgreSQL** in production — and four **Alembic** migrations for schema lifecycle management. Asynchronous request processing is orchestrated by **Celery** and **Redis** (broker and result backend). The user interface is built in **React 18** with **Vite** and strict **TypeScript**, organized into five distinct pages: the landing page, file import (Upload), the conversational interface (Aski), the dashboard, and the administration panel. Authentication is managed by **Keycloak 26** (realm `claria`) via RS256 JWT tokens validated against a JWKS cache (900-second lifespan).

The intelligent core of the platform is the **Aski** module, a conversational interface built on **PandasAI** and its **pandasai-litellm** extension. By default, ClarIA uses the local **Ollama `qwen2.5-coder:7b`** model hosted on the same infrastructure, ensuring that no data leaves the organization. An automatic failover mechanism to cloud APIs (OpenAI, Anthropic, Google Gemini via **LiteLLM**) is triggered if the Ollama server is unavailable. Each user request passes through several specialized services: an LLM intent classifier (`classify_data_intent`), a fuzzy column matching engine (`rapidfuzz`, configurable thresholds at 80% and 50%), a keyword-based chart type detector, and an **Apache ECharts** specification builder (8 types: bar, line, area, pie, scatter, histogram, heatmap, radar). Results are delivered in real time via **WebSocket**. A complementary module (`generate_explanation`) automatically produces a two-sentence French-language textual summary describing each generated chart.

Generated charts can be pinned to a customizable drag-and-drop **Dashboard** (`react-grid-layout`), persisted in the database as a JSON configuration (500 KB cap). Users can also create **charts manually** (via a built-in builder processing up to 10,000 rows client-side) and add **KPI indicators** (sum, average, count, minimum, maximum) from the active file's data. Security is reinforced by a Redis rate limiter (30 requests per user per hour) and strict file upload validation (libmagic, byte signature, 10 MB limit, 100,000 rows maximum).

Automated validation testing demonstrates that the ClarIA platform meets all functional and non-functional requirements defined in the project specification, with a test suite of **40 tests passing at 100%**.

**Keywords:** Artificial Intelligence, Chart Generation, Natural Language Processing, PandasAI, LLM, Ollama, FastAPI, React, Keycloak, Dashboard, Data Visualization, Celery, Redis, WebSocket.

<div style="page-break-after: always;"></div>

# LISTE DES FIGURES

- **Figure 1 :** Organigramme de SKATYS — Structure organisationnelle par pôles de compétences.......... [Page X]
- **Figure 2 :** Positionnement de ClarIA dans le paysage des outils d'analyse de données............... [Page X]
- **Figure 3 :** Diagramme de Gantt prévisionnel du projet ClarIA........................................ [Page X]
- **Figure 4 :** Diagramme de Composants — Espace Utilisateur (UploadPage + Pipeline IA + WebSocket)... [Page X]
- **Figure 5 :** Diagramme de Composants — Espace Administrateur (AdminPage + KeycloakAdminClient)...... [Page X]
- **Figure 6 :** Diagramme de Cas d'Utilisation — Acteur Utilisateur (`user`)........................... [Page X]
- **Figure 7 :** Diagramme de Cas d'Utilisation — Acteur Administrateur (`admin`)........................ [Page X]
- **Figure 8 :** Diagramme de Classes — Entités métier (File, Prompt, Chart) et couche sécurité......... [Page X]
- **Figure 9 :** Diagramme de Classes — Couche Sécurité (User, get_current_user, require_admin)......... [Page X]
- **Figure 10 :** Diagramme de Séquence — Pipeline complet Upload → Aski → WebSocket → ECharts......... [Page X]
- **Figure 11 :** Diagramme de Séquence — Authentification Keycloak RS256 (JWKS + azp).................. [Page X]
- **Figure 12 :** Diagramme d'Activité — Validation et normalisation d'un fichier CSV/Excel.............. [Page X]
- **Figure 13 :** Diagramme d'Activité — Suppression en cascade d'un utilisateur (Keycloak → DB → disque) [Page X]
- **Figure 14 :** Diagramme d'État — Cycles de vie des entités File (4 états) et Prompt (5 états)...... [Page X]
- **Figure 15 :** Modèle Conceptuel de Données (MCD) — Entités File, Prompt, Chart...................... [Page X]
- **Figure 16 :** Diagramme de Déploiement — Infrastructure Docker Compose (8 services)................. [Page X]
- **Figure 17 :** Diagramme de Gantt — Phase de Développement & Rédaction (Juillet - Août 2026)................. [Page X]
- **Figure 18 :** Capture — Page d'accueil ClarIA (LandingPage)........................................... [Page X]
- **Figure 19 :** Capture — Interface d'import de fichiers avec prévisualisation (UploadPage)............ [Page X]
- **Figure 20 :** Capture — Interface conversationnelle Aski avec graphique généré (AskiPage)............ [Page X]
- **Figure 21 :** Capture — Tableau de bord personnalisable avec KPI Cards (DashboardPage)............... [Page X]
- **Figure 22 :** Capture — Panneau d'administration — gestion des utilisateurs Keycloak (AdminPage)..... [Page X]
- **Figure 23 :** Résultats de la suite de tests automatisés — 40 tests, 100% de réussite................ [Page X]

---

# LISTE DES TABLEAUX

- **Tableau 1 :** Fiche d'identité de l'organisme d'accueil — SKATYS................................... [Page X]
- **Tableau 2 :** Analyse comparative des solutions de visualisation de données existantes................ [Page X]
- **Tableau 3 :** Dictionnaire des données — Modèle Logique (entités File, Prompt, Chart)............... [Page X]
- **Tableau 4 :** Types de graphiques supportés, mots-clés de détection et cas d'usage recommandés....... [Page X]
- **Tableau 5 :** Stack technologique complet — Backend, Frontend, Infrastructure, Sécurité.............. [Page X]
- **Tableau 6 :** Matrice de validation des dépendances (PandasAI, Keycloak 26, Redis, ECharts 5).... [Page X]
- **Tableau 7 :** Résultats des tests automatisés par catégorie — 40 tests, répartition par module........... [Page X]
- **Tableau 8 :** Évaluation des performances du pipeline (latences mesurées par composant).............. [Page X]
- **Tableau 9 :** Limites et seuils configurables de la plateforme (taille, lignes, débit)............... [Page X]

---

# LISTE DES ABRÉVIATIONS

- **API** : Application Programming Interface
- **ASGI** : Asynchronous Server Gateway Interface
- **CDC** : Cahier des Charges
- **CORS** : Cross-Origin Resource Sharing
- **CSR** : Client-Side Rendering
- **HMR** : Hot Module Replacement
- **HTTP** : HyperText Transfer Protocol
- **IA** : Intelligence Artificielle
- **JWT** : JSON Web Token
- **JWKS** : JSON Web Key Set
- **KPI** : Key Performance Indicator (Indicateur Clé de Performance)
- **LLM** : Large Language Model (Grand Modèle de Langage)
- **MCD** : Modèle Conceptuel de Données
- **MLD** : Modèle Logique de Données
- **NLP** : Natural Language Processing (Traitement du Langage Naturel)
- **ORM** : Object-Relational Mapping
- **PFA** : Projet de Fin d'Année
- **RBAC** : Role-Based Access Control (Contrôle d'Accès Basé sur les Rôles)
- **RS256** : RSA Signature with SHA-256
- **SaaS** : Software as a Service
- **SPA** : Single Page Application
- **SSR** : Server-Side Rendering
- **TTL** : Time To Live
- **UML** : Unified Modeling Language
- **WS** : WebSocket

<div style="page-break-after: always;"></div>

# INTRODUCTION GÉNÉRALE

## Contexte général

À l'ère de la transformation numérique, les organisations de tous secteurs — entreprises commerciales, administrations, équipes projet, start-ups — produisent et accumulent des volumes croissants de données structurées. Ces données se matérialisent le plus souvent sous la forme de fichiers CSV ou de classeurs Excel : rapports de ventes, résultats d'enquêtes, tableaux de suivi financier, données opérationnelles, indicateurs de performance. Si la production de ces données est désormais quasi-automatique dans la majorité des systèmes d'information, leur exploitation analytique et leur restitution visuelle demeurent un processus long, technique et coûteux en ressources humaines.

En pratique, un responsable commercial souhaitant comprendre l'évolution de ses ventes par région, un chef de projet désirant visualiser la distribution de son budget par catégorie, ou un analyste opérationnel voulant identifier les tendances mensuelles de ses indicateurs, doit généralement solliciter un développeur ou un expert en Business Intelligence pour produire les graphiques correspondants. Cette intermédiation technique systématique constitue un goulot d'étranglement organisationnel majeur : elle ralentit la prise de décision, génère des dépendances inter-équipes coûteuses et décourage l'initiative analytique dans les équipes non techniques.

Les outils existants de Business Intelligence tels que Microsoft Power BI, Google Looker Studio ou Tableau apportent des réponses partielles à ce problème, mais leur utilisation efficace nécessite une formation initiale significative, une configuration technique préalable (connexion aux sources de données, modélisation du schéma) et une maîtrise de concepts analytiques avancés. Ces prérequis excluent de facto la grande majorité des utilisateurs professionnels non spécialisés.

L'essor des Grands Modèles de Langage (LLMs) — et notamment des modèles open-source comme **Qwen 2.5 Coder** disponibles via **Ollama** — ouvre une voie radicalement différente : celle de l'interaction directe en langage naturel avec des données tabulaires, sans aucune compétence technique requise de la part de l'utilisateur.

## Problématique

C'est précisément dans ce contexte que s'inscrit ce Projet de Fin d'Année. La problématique centrale que ce projet cherche à résoudre peut se formuler ainsi : **comment permettre à n'importe quel professionnel, sans compétences techniques particulières, d'importer ses propres fichiers de données et d'en obtenir des visualisations graphiques pertinentes et interactives, simplement en posant une question en français ?**

Cette problématique soulève cinq défis techniques et fonctionnels distincts, auxquels ClarIA apporte des réponses concrètes :

1. **Le défi de l'accessibilité** : l'interface doit être suffisamment simple et intuitive pour qu'un utilisateur puisse importer un fichier et formuler une première requête en moins d'une minute, sans aucune formation préalable. La plateforme doit également gérer de façon transparente la diversité des formats de fichiers réels : encodages variables (UTF-8, Latin-1), séparateurs décimaux français (virgule au lieu du point), formats de dates locaux (`dd/mm/yyyy`), fichiers Excel multi-feuilles.

2. **Le défi de la performance et de la réactivité** : l'analyse de fichiers pouvant contenir jusqu'à 100 000 lignes ne doit pas bloquer l'interface utilisateur. Le pipeline d'inférence LLM — dont la durée peut varier de quelques secondes à plusieurs minutes selon le modèle — doit être entièrement asynchrone, et le résultat restitué en temps réel dès qu'il est disponible.

3. **Le défi de la flexibilité des modèles de langage** : le marché des LLMs évolue rapidement. La plateforme doit pouvoir fonctionner avec différents fournisseurs (Ollama local, OpenAI, Anthropic, Google Gemini) sans modification du code applicatif, et basculer automatiquement vers un fournisseur de secours en cas d'indisponibilité du serveur local.

4. **Le défi de la confidentialité et de la sécurité** : les fichiers de données importés peuvent contenir des informations sensibles ou stratégiques. La plateforme doit garantir l'isolation stricte des données entre utilisateurs, un contrôle d'accès robuste, et une option d'exécution purement locale (sans transmission de données vers des APIs externes) pour les organisations soumises à des contraintes de confidentialité.

5. **Le défi de la persistance et de la réutilisabilité** : les visualisations produites ont de la valeur dans la durée. La plateforme doit permettre à chaque utilisateur de sauvegarder ses graphiques sur un tableau de bord personnel, de les réorganiser librement, et d'y associer des indicateurs de synthèse (KPI) pour constituer un espace de reporting réutilisable et évolutif.

## La solution : ClarIA

Pour répondre à l'ensemble de ces défis, j'ai conçu et développé **ClarIA** — une plateforme web SaaS (Software as a Service) de restitution intelligente de données. L'objectif de ClarIA est de supprimer la barrière technique entre un utilisateur et ses données, en remplaçant la complexité des outils de Business Intelligence traditionnels par une interface conversationnelle accessible à tous.

Le fonctionnement de ClarIA repose sur un pipeline structuré en cinq étapes :

**1. Import et préparation du fichier** — L'utilisateur téléverse un fichier CSV ou Excel depuis la page `Upload`. Le service `file_validator` valide le fichier (vérification par signature d'octets, limite de 10 Mo, maximum 100 000 lignes). Le service `locale_normalizer` normalise automatiquement les formats locaux français (nombres avec espaces et virgules, dates en `dd/mm/yyyy`). Pour les fichiers Excel multi-feuilles, un dialogue de sélection est présenté à l'utilisateur. Le fichier est stocké de manière persistante et ses métadonnées (nom, colonnes, aperçu) enregistrées en base de données.

**2. Formulation de la requête dans Aski** — L'utilisateur formule sa demande en langage naturel depuis la page `Aski` via le composant `PromptBar` (ex. : *"Montre-moi les ventes par trimestre sous forme de graphique à barres"*). Un limiteur de débit Redis garantit un maximum de 30 requêtes par utilisateur par heure.

**3. Traitement asynchrone par le pipeline IA** — La requête est transmise à un worker **Celery** via le broker **Redis**. Le pipeline exécute successivement : (a) la classification de l'intention (`classify_data_intent`) qui détermine si la question est pertinente au regard des données ; (b) la correspondance floue des colonnes (`fuzzy_matcher` avec `rapidfuzz`, seuils à 80% et 50%) pour identifier les colonnes impliquées ; (c) la détection du type de graphique souhaité par analyse des mots-clés de la requête ; (d) l'inférence via **PandasAI** sur un `pai.DataFrame()` construit à partir du fichier, en utilisant par défaut le modèle local **Ollama `qwen2.5-coder:7b`** (ou un fournisseur cloud de secours configuré via **LiteLLM**) ; (e) la construction de la spécification de graphique **Apache ECharts** par le service `chart_resolver`.

**4. Restitution en temps réel** — Le résultat est publié sur un canal **Redis** Pub/Sub (`ws:prompt:{id}`) et transmis immédiatement à l'interface via une connexion **WebSocket**. Le composant `ChartDisplay` affiche le graphique interactif ECharts. Un module `generate_explanation` produit simultanément une synthèse textuelle de deux phrases en français décrivant le graphique.

**5. Tableau de Bord, KPI et Constructeur Manuel** — L'utilisateur peut ajouter le graphique à son `DashboardPage` personnel. Le composant `DashboardView` offre une interface de glisser-déposer et redimensionnement (`react-grid-layout`). Outre les graphiques générés par l'IA, un **constructeur manuel** permet de créer des graphiques personnalisés (avec agrégation côté client limitée aux 10 000 premières lignes pour des raisons de performance) et d'ajouter des indicateurs `KPICard` (somme, moyenne, comptage, minimum, maximum sur n'importe quelle colonne numérique). L'ensemble de la configuration du tableau de bord est persistée en base de données en JSON (limite de 500 Ko).

Toutes ces fonctionnalités sont sécurisées par **Keycloak 26** (realm `claria`, client `claria-frontend`), qui gère l'authentification par jetons JWT RS256 validés par cache JWKS, l'isolation des données par utilisateur (`owner_id = current_user.sub`) et la séparation des rôles (`user` et `admin`). Le panneau d'administration (`AdminPage`) permet la gestion complète des comptes utilisateurs via l'API Keycloak Admin, avec suppression en cascade (Keycloak → base de données → disque).

## Méthodologie et organisation du rapport

La réalisation de ClarIA a suivi une méthodologie de développement itérative. L’architecture a été conçue pour être entièrement conteneurisée via **Docker Compose**, intégrant les services backend, worker Celery, Redis, Keycloak, PostgreSQL et Ollama, garantissant ainsi la reproductibilité parfaite des environnements de développement, de test et de production. Le schéma de base de données a évolué au travers de quatre migrations **Alembic** successives, reflétant les itérations fonctionnelles du projet.

Ce rapport est structuré en cinq chapitres :

- **Le Chapitre 1** présente le contexte du projet, l'organisme d'accueil SKATYS et l'analyse du besoin ayant justifié le développement de ClarIA.

- **Le Chapitre 2** détaille la présentation du projet : problématique, objectifs spécifiques, état de l'art des solutions de visualisation existantes, et cahier des charges fonctionnel et non fonctionnel.

- **Le Chapitre 3** traite la phase de conception : justification des choix technologiques (PandasAI, Ollama, Keycloak, React/Vite, Celery/Redis), modélisation UML (cas d'utilisation, classes, séquence, activité) et conception du schéma de données.

- **Le Chapitre 4** décrit la réalisation technique : architecture applicative, développement du backend FastAPI, du frontend React, du pipeline IA (PandasAI + orchestration multi-fournisseurs + chart_resolver), du tableau de bord dynamique, des mécanismes de sécurité, et des difficultés rencontrées avec les solutions adoptées.

- **Le Chapitre 5** dresse le bilan des tests : résultats de la suite de 40 tests automatisés, évaluation des performances du pipeline bout-en-bout, analyse des limites actuelles et perspectives d'amélioration.

Le rapport se conclut par une **Conclusion Générale** synthétisant les apports techniques et fonctionnels du projet, évaluant l'impact potentiel de ClarIA dans le contexte de la démocratisation de l'analyse de données, et traçant les perspectives d'évolution futures de la plateforme.

