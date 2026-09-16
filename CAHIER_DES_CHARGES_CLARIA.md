# CAHIER DES CHARGES — CLARIA
## Plateforme Intelligente de Restitution de Données

---

## Table des Matières

1. [Contexte et Objectifs du Projet](#1-contexte-et-objectifs-du-projet)
   - 1.1 Contexte
   - 1.2 Problématique
   - 1.3 Objectifs
   - 1.4 Analyse de l’Existant et Positionnement
2. [Périmètre du Projet](#2-périmètre-du-projet)
   - 2.1 Inclus dans la version 1.0
   - 2.2 Exclus de la version actuelle — Perspectives d'Évolution futures
3. [Acteurs et Besoins Utilisateurs](#3-acteurs-et-besoins-utilisateurs)
   - 3.1 Acteurs
   - 3.2 Besoins Utilisateurs
   - 3.3 Types de Données Supportés et Cas d’Usage
4. [Exigences Fonctionnelles](#4-exigences-fonctionnelles)
   - 4.1 Fonctions Principales
   - 4.2 Scénario d’Utilisation Principal
5. [Exigences Non Fonctionnelles](#5-exigences-non-fonctionnelles)
6. [Environnement Technique](#6-environnement-technique)
7. [Analyse des Risques](#7-analyse-des-risques)
8. [Planning et Livrables](#8-planning-et-livrables)
9. [Glossaire](#9-glossaire)

---

## 1. Contexte et Objectifs du Projet

### 1.1 Contexte
Dans un environnement où la prise de décision est de plus en plus dirigée par les données (data-driven), de nombreuses entreprises et professionnels disposent de vastes quantités de données structurées (fichiers CSV, Excel). Cependant, l'exploitation de ces données nécessite souvent des compétences techniques (SQL, Python, outils BI complexes) dont les utilisateurs métiers sont dépourvus, créant ainsi un goulot d'étranglement analytique.

### 1.2 Problématique
Comment démocratiser l'analyse de données et la génération de tableaux de bord interactifs pour les utilisateurs non techniques, en leur permettant d'interroger leurs propres fichiers (CSV, Excel) en langage naturel, tout en garantissant la sécurité et la confidentialité des informations téléversées ?

### 1.3 Objectifs
- Permettre le téléversement (upload) intuitif de fichiers de données volumineux.
- Interroger ces données via des requêtes en langage naturel (français supporté) grâce à l'intégration d'un grand modèle de langage (LLM).
- Générer automatiquement des requêtes pandas et des graphiques interactifs (ECharts) sans aucune intervention manuelle.
- Fournir un tableau de bord personnalisable (Dashboard) permettant de regrouper les visualisations clés.
- Assurer une authentification sécurisée et une isolation stricte des données par utilisateur
- Supporter plusieurs fournisseurs LLM (local via Ollama, cloud via OpenAI / Anthropic / Google Gemini)

> ⚠️ **ClarIA est un outil d’aide à l’analyse et ne remplace pas le jugement métier ou l’expertise d’un analyste de données.**

### 1.4 Analyse de l’Existant et Positionnement

Plusieurs outils de Business Intelligence et d’analyse de données existent sur le marché. L’analyse comparative ci-dessous justifie le développement de ClarIA :

| Critère | Microsoft Power BI | Google Looker Studio | Tableau | **ClarIA** |
|---|---|---|---|---|
| Compétence requise | Élevée | Moyenne | Élevée | **Aucune** |
| Interaction en langage naturel | Partielle | Non | Partielle | **Oui (NLP natif)** |
| Import CSV/Excel direct | Oui | Limité | Oui | **Oui + normalisation FR** |
| LLM local (données privées) | Non | Non | Non | **Oui (Ollama)** |
| Gratuit / Open Source | Non (licences) | Freemium | Non (licences) | **Oui** |
| Déploiement on-premise | Limité | Non | Limité | **Oui (Docker)** |
| Tableau de bord personnalisable | Oui | Oui | Oui | **Oui (glisser-déposer)** |
| Multi-fournisseurs LLM | Non | Non | Non | **Oui (Ollama/OpenAI/Gemini)** |

**Conclusion :** ClarIA se positionne comme une solution complémentaire aux outils BI classiques, en ciblant spécifiquement les utilisateurs non techniques qui ont besoin d’analyser rapidement leurs propres fichiers de données, sans formation ni infrastructure lourde. Son différenciant principal est la **confidentialité garantie par le mode LLM local** et **l’absence totale de prérequis technique** pour l’utilisateur final.

---

## 2. Périmètre du Projet

### 2.1 Inclus dans la version 1.0

| Module | Fonctionnalités |
|---|---|
| Gestion des Fichiers | Upload CSV/Excel, normalisation locale (virgules décimales), validation des types, gestion du TTL |
| Interaction IA | Interface conversationnelle, analyse du prompt, fuzzy matching des colonnes |
| Pipeline LLM | Génération de code via PandasAI, gestion des erreurs, repli (fallback) entre providers |
| Visualisation | Rendu dynamique ECharts, support de 8 types de graphiques, thèmes clair/sombre |
| Tableau de bord | Grille draggable/resizable, enregistrement du layout, cartes de métriques (KPI) |
| Administration | Gestion des utilisateurs (via Keycloak) |
| Sécurité | Authentification JWT (RS256), isolation des données par utilisateur (owner_id) |
| Rate limiting | 30 requêtes par utilisateur par heure (Redis Lua) |
| Nettoyage automatique | Suppression des fichiers expirés après 7 jours (Celery beat) |

### 2.2 Exclus de la version actuelle — Perspectives d'Évolution futures

Les fonctionnalités suivantes sont volontairement hors périmètre de la version actuelle et constituent la **roadmap d'évolution** de ClarIA :

| Exclusion | Justification | Évolution future prévue |
|---|---|---|
| Connexion directe Data Warehouse | Complexité JDBC/ODBC, hors périmètre | Connecteurs natifs Snowflake, BigQuery, Redshift, PostgreSQL externe |
| Export PDF / PowerPoint | Dépendances système (WeasyPrint, python-pptx) | Export multi-formats des graphiques et du tableau de bord |
| Modèles statistiques avancés | Hors périmètre actuel (scikit-learn commenté) | Prévisions, séries temporelles (Prophet), clustering |
| Application mobile native | Non prévu | Application React Native ou PWA |

#### Perspectives Techniques futures — Architecture RAG

La prochaine version de ClarIA intégrera un pipeline **RAG (Retrieval-Augmented Generation)** adapté aux données tabulaires, permettant d'améliorer significativement la qualité et la pertinence des analyses :

**1. Remplacement du Fuzzy Matching par la Recherche Sémantique**

L'actuel service `fuzzy_matcher` (basé sur `rapidfuzz`) sera enrichi d'une couche de **correspondance sémantique par embeddings**. Au lieu de comparer des chaînes de caractères, le système comparera les représentations vectorielles de la requête utilisateur avec les descriptions sémantiques des colonnes du fichier.

Modèles d'embedding envisagés (disponibles localement via **Ollama**) :
- **`nomic-embed-text`** — Modèle léger, haute qualité, optimisé pour la recherche sémantique en texte court (noms de colonnes, en-têtes)
- **`bge-m3` (BAAI/bge-m3)** — Modèle multilingue de référence, excellent pour le français — idéal pour ClarIA dont les requêtes sont formulées en français

**2. Base de Données Vectorielle**

Les embeddings des colonnes et des métadonnées de fichiers seront stockés dans une base vectorielle :
- **PGvector** *(option privilégiée)* — Extension PostgreSQL native, zéro infrastructure supplémentaire puisque ClarIA utilise déjà PostgreSQL en production. Permet des requêtes de similarité cosinus directement en SQL.
- **ChromaDB** *(alternative)* — Base vectorielle autonome, plus simple à déployer en développement

**3. Connexion directe aux Bases Décisionnelles**

Au lieu d'importer un fichier CSV/Excel, l'utilisateur pourra connecter ClarIA directement à son **entrepôt de données (Data Warehouse)** :
- Sources supportées : PostgreSQL externe, Snowflake, Google BigQuery, AWS Redshift, DuckDB
- Le pipeline RAG récupérera automatiquement le schéma (tables, colonnes, types) et construira un index vectoriel des métadonnées
- L'utilisateur pourra alors poser une question en langage naturel qui sera traduite en requête SQL optimisée, sans aucun téléversement manuel

**Architecture future simplifiée :**
```
[Requête NL] → [Embedding bge-m3 / nomic-embed-text via Ollama]
     → [Recherche sémantique PGvector / ChromaDB]
     → [Contexte pertinent récupéré (colonnes, lignes-clés)]
     → [PandasAI + LLM → ECharts]
```

> 💡 Cette évolution permettra à ClarIA de dépasser la limite actuelle de 100 000 lignes et de traiter des datasets de plusieurs millions de lignes en ne transmettant au LLM que les fragments sémantiquement pertinents.

---

## 3. Acteurs et Besoins Utilisateurs

### 3.1 Acteurs

| Acteur | Rôle Système | Droits et Accès |
|---|---|---|
| **Utilisateur Métier** | `user` | Peut uploader des fichiers, générer des graphiques, gérer son tableau de bord personnel. Ne voit que ses propres données. |
| **Administrateur** | `admin` | Accès exclusif à la console d'administration pour gérer les utilisateurs de la plateforme. Ne participe pas à l'analyse de données. |
| **Worker Asynchrone** | Système (Celery) | Tâche de fond traitant les requêtes longues (IA) sans bloquer l'interface web. |

### 3.2 Besoins Utilisateurs
- Obtenir des graphiques interactifs en moins d'une minute à partir d'un fichier brut.
- Pouvoir poser des questions "naturelles" sans utiliser un jargon de base de données.
- Ne pas être bloqué par des erreurs de formatage (nombres avec virgules à la française, dates).
- Disposer d'un tableau de bord personnalisable (épingler, redimensionner, organiser).

### 3.3 Types de Données Supportés et Cas d’Usage
- **Ventes & Commerce** : CA par région, évolution des ventes par mois.
- **Ressources Humaines** : Répartition des effectifs, moyenne des salaires par département.
- **Marketing** : Performance des campagnes, trafic web par canal.
- **Limites techniques** : 10 Mo par fichier, environ 100 000 lignes maximum.

---

## 4. Exigences Fonctionnelles

### 4.1 Fonctions Principales

| ID | Fonction | Description | Priorité | Critère d'acceptation |
|---|---|---|---|---|
| F-01 | Authentification sécurisée | Login via Keycloak 26 (realm `claria`) — JWT RS256, cache JWKS 900s | 🔴 Essentielle | Un utilisateur non authentifié ne peut accéder à aucune page ni endpoint |
| F-02 | Import de fichiers | CSV / Excel (.xlsx, .xls), validation magic bytes, limite 10 Mo / 100 000 lignes | 🔴 Essentielle | Un fichier valide est accepté ; un fichier corrompu ou > 10 Mo est rejeté avec message d'erreur |
| F-03 | Sélection de feuille Excel | Dialogue de sélection (SheetSelector) pour classeurs multi-feuilles | 🟡 Importante | Un classeur multi-feuilles affiche le dialogue ; un classeur à feuille unique le saute |
| F-04 | Normalisation locale | Correction automatique des formats numériques et dates français | 🟡 Importante | Un fichier avec virgules décimales et dates dd/mm/yyyy est lu correctement |
| F-05 | Prévisualisation des données | Aperçu des premières lignes et métadonnées colonnes (PreviewPanel) | 🟡 Importante | Les colonnes, types et aperçu sont affichés après upload |
| F-06 | Requête en langage naturel | Saisie de la question dans la PromptBar, envoi asynchrone | 🔴 Essentielle | La soumission d'une requête déclenche le pipeline sans bloquer l'interface |
| F-07 | Correspondance floue des colonnes | fuzzy_matcher (rapidfuzz) — seuils 80% (haut) / 50% (moyen) | 🟡 Importante | Une colonne mal orthographiée dans la requête est mappée à la colonne réelle |
| F-08 | Classification de l'intention | classify_data_intent — détecte si la question est pertinente aux données | 🟡 Importante | Une question hors-sujet retourne un message d'aide, pas un graphique vide |
| F-09 | Détection du type de graphique | Analyse mots-clés de la requête — 8 types supportés | 🔴 Essentielle | "barres", "secteurs", "radar" dans la requête produisent le graphique correspondant |
| F-10 | Inférence LLM via PandasAI | `pai.DataFrame().chat()` — modèle Ollama qwen2.5-coder:7b par défaut | 🔴 Essentielle | Une requête valide produit un DataFrame exploitable transmis à build_chart_spec |
| F-11 | Basculement automatique LLM | Ollama indisponible → OpenAI / Anthropic / Google Gemini via LiteLLM | 🟡 Importante | Si Ollama est arrêté, le système bascule sur le fournisseur cloud configuré et notifie l'utilisateur |
| F-12 | Construction du graphique ECharts | build_chart_spec() → spécification Apache ECharts (8 types) | 🔴 Essentielle | Le graphique s'affiche avec axes, légendes et données correctes |
| F-13 | Résultat en temps réel | Redis Pub/Sub (`ws:prompt:{id}`) → WebSocket → ChartDisplay | 🔴 Essentielle | Le graphique apparaît sans rechargement de page dès que le worker Celery termine |
| F-14 | Explication textuelle | generate_explanation() — synthèse en français (opt-in) | 🟢 Optionnelle | Quand activé, une synthèse en français s'affiche sous le graphique |
| F-15 | Dialogue de clarification | ClarificationDialog si colonne ambiguë détectée | 🟡 Importante | Si une colonne est ambiguë, une question de clarification est posée avant génération |
| F-16 | Tableau de bord | DashboardView — glisser-déposer + redimensionnement (react-grid-layout) | 🔴 Essentielle | L'utilisateur peut déplacer et redimensionner librement les widgets |
| F-17 | Persistance du tableau de bord | Configuration JSON sauvegardée en base de données (plafond 500 Ko) | 🔴 Essentielle | Après rechargement de page, la disposition du tableau de bord est identique |
| F-18 | Indicateurs KPI | KPICard — agrégations (SUM, AVG, COUNT, MIN, MAX) sur colonnes numériques | 🟡 Importante | Un KPI ajouté affiche la valeur agrégée correcte de la colonne sélectionnée |
| F-19 | Rate limiting | 30 requêtes/heure/utilisateur — script Lua Redis (atomique) | 🔴 Essentielle | Après 30 requêtes en 1 heure, la 31e est rejetée avec message explicite |
| F-20 | Panneau d'administration | AdminPage — CRUD utilisateurs Keycloak, suppression en cascade | 🟡 Importante | Un admin peut créer, modifier et supprimer un utilisateur ; ses données sont effacées en cascade |
| F-21 | Configuration LLM | SettingsPanel — changement de fournisseur / modèle / clé API à chaud | 🟡 Importante | Après changement de fournisseur, la prochaine requête utilise le nouveau fournisseur sans redémarrage |
| F-22 | Nettoyage automatique | cleanup_expired_files() — fichiers > 7 jours supprimés (Celery beat) | 🟢 Optionnelle | Les fichiers > 7 jours sont supprimés du disque et de la base lors de l'exécution planifiée |

### 4.2 Scénario d'Utilisation Principal (Happy Path)

1. L'utilisateur se connecte et téléverse un fichier (ex: `ventes_2025.csv`).
2. Le backend valide le fichier, normalise les données et affiche un aperçu.
3. L'utilisateur pose la question : *"Montre moi le chiffre d'affaires total par région en graphique à barres"*.
4. La requête est transmise au backend qui l'envoie en file d'attente (Redis) via Celery.
5. L'interface affiche un indicateur de chargement et écoute un canal WebSocket.
6. Le worker Celery exécute l'inférence via le LLM (Ollama).
7. Le résultat est retourné, formaté en configuration ECharts, et publié sur le canal WebSocket.
8. L'interface reçoit la configuration et rend le graphique interactif.
9. L'utilisateur épingle le graphique à son tableau de bord.

---

## 5. Exigences Non Fonctionnelles

### 5.1 Performance
- **Temps de réponse LLM** : L'intégration avec Ollama local doit répondre en moins de 30 secondes pour une requête standard sur une machine adéquate.
- **Asynchronisme** : L'interface utilisateur ne doit jamais être bloquée pendant l'exécution d'une analyse LLM.
- **Scalabilité** : L'architecture doit pouvoir supporter l'ajout de nouveaux workers Celery pour distribuer la charge.

### 5.2 Sécurité & Confidentialité
- Les mots de passe ne sont jamais stockés dans l'application (gérés par Keycloak).
- Les communications API frontend/backend doivent être sécurisées via JWT (durée de vie courte + renouvellement).
- Aucun fichier de données ou contenu de requête n'est partagé entre utilisateurs. Les clauses `WHERE owner_id = :user_id` sont obligatoires sur toutes les tables métiers.
- En mode Ollama, **aucune donnée ne quitte le réseau de l'entreprise**, satisfaisant aux normes strictes de confidentialité (RGPD).

### 5.3 Ergonomie
- L'interface doit être "Responsive" pour un usage sur tablette et ordinateur (l'usage smartphone n'est pas la cible principale mais l'interface ne doit pas être cassée).
- Les retours d'erreurs IA (ex: "Je ne comprends pas la question") doivent être affichés clairement, en français, avec des suggestions.

---

## 6. Environnement Technique

### 6.1 Backend
- **Framework** : FastAPI (**Python 3.11 strictement recommandé** — PandasAI 3.0.0 requiert ≥ 3.10 et < 3.12 ; une vérification est effectuée au démarrage dans `main.py`)
- **ORM & Base de Données** : SQLAlchemy 2.0 avec PostgreSQL (Production) / SQLite (Développement). Alembic pour les migrations.
- **Gestion des tâches** : Celery couplé à Redis (Broker & Result Backend).
- **Core IA** : PandasAI, LiteLLM, Ollama (Modèle par défaut : `qwen2.5-coder:7b`).
- **Authentification** : `PyJWT[crypto]` pour la vérification JWT asynchrone des jetons Keycloak (`jwt.PyJWKClient` avec cache JWKS 900s).

### 6.2 Frontend
- **Framework** : React 18 avec Vite et TypeScript.
- **Visualisation** : Apache ECharts (`echarts` et `echarts-for-react`).
- **Composants d'interface** : CSS Natif (Design System sur-mesure), Lucide React (Icônes).
- **Gestion d'état** : Zustand.
- **Tableau de bord** : `react-grid-layout`.
- **Authentification client** : `keycloak-js`.

### 6.3 Infrastructure
- Conteneurisation complète via **Docker** et **Docker Compose** (PostgreSQL, Redis, Keycloak, Backend, Worker, Frontend).

---

## 7. Analyse des Risques

| # | Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | **Qualité des graphiques LLM** : le modèle local Ollama produit un code Python incorrect ou un DataFrame mal formaté | Moyenne | Élevé | Gestion d’erreurs multicouche (NoResultFoundError, exc_type, clarification dialog) + fallback cloud |
| R-02 | **Indisponibilité d’Ollama** : le serveur local est hors ligne | Faible | Moyen | Basculement automatique vers Google Gemini / OpenAI / Anthropic via LiteLLM + notification utilisateur |
| R-03 | **Fichiers mal formatés** : encodage non détecté, séparateur inhabituel, dates incohérentes | Moyenne | Moyen | locale_normalizer + chardet + python-magic + messages d’erreur explicites |
| R-04 | **Dépassement de la limite de tokens LLM** : fichier trop large à représenter en prompt | Faible | Moyen | PandasAI n’envoie que 10 lignes d’échantillon + métadonnées colonnes au LLM |
| R-05 | **Sécurité** : accès non autorisé aux données d’un autre utilisateur | Très faible | Très élevé | owner_id obligatoire sur chaque entité + JWT RS256 vérifié à chaque requête + RBAC Keycloak |
| R-06 | **Surcharge du système** : trop de requêtes simultanées | Faible | Moyen | Rate limiter Redis (30 req/h/user) + Celery worker asynchrone |
| R-07 | **Perte de données** : crash lors du traitement | Très faible | Élevé | try/except/finally sur tous les workers Celery + rollback SQLAlchemy + état persistant en base |
| R-08 | **Compatibilité Python** : PandasAI incompatible avec Python ≥ 3.12 | Contrôlé | Élevé | Contrainte déclarée dans requirements.txt + vérification au démarrage dans main.py |

## 8. Planning et Livrables

### 8.1 Planning Prévisionnel

| Sprint | Semaines | Activités |
|---|---|---|
| S1 | S1 – S2 | Cahier des charges, étude de l'existant, choix technologiques |
| S2 | S3 – S4 | Conception UML (cas d'utilisation, classes, séquence, activité), MCD |
| S3 | S5 – S6 | Développement backend : FastAPI, modèles, migrations Alembic, Keycloak |
| S4 | S6 – S7 | Développement pipeline IA : PandasAI, fuzzy_matcher, chart_resolver, Celery |
| S5 | S7 – S8 | Développement frontend : pages React, WebSocket, ECharts, Dashboard, KPI |
| S6 | S8 – S9 | Tests automatisés (44 tests), correction des bugs, validation end-to-end |
| S7 | S9 – S10 | Conteneurisation Docker, documentation technique, rapport final, soutenance |

### 8.2 Livrables

| Livrable | Statut | Description |
|---|---|---|
| Cahier des charges | ✅ | Ce document — périmètre, exigences, architecture |
| Application web complète | ✅ | Frontend React 18 + Backend FastAPI + Docker Compose |
| Pipeline IA | ✅ | PandasAI + Ollama + LiteLLM + chart_resolver (8 types) |
| API REST + WebSocket | ✅ | Endpoints fichiers, prompts, dashboard, admin, provider |
| Tableau de bord interactif | ✅ | DashboardView + KPICard + react-grid-layout |
| Sécurité complète | ✅ | Keycloak 26 + JWT RS256 + RBAC + rate limiting Redis |
| Suite de tests | ✅ | 44 tests automatisés — 100% de réussite |
| Documentation technique | ✅ | Production Readiness Report + Deep Dive Report |
| Rapport final (PFA) | 🔄 | CHAPITRE_0 (Introduction) + Chapitres 1 à 5 + Conclusion |
| Présentation PPTX | 🔜 | Diaporama de soutenance |

---

## 9. Glossaire

| Terme | Définition |
|---|---|
| **LLM** | Large Language Model — Grand modèle de langage (ex: GPT-4, Gemini, Qwen) |
| **NLP** | Natural Language Processing — Traitement automatique du langage naturel |
| **PandasAI** | Bibliothèque Python connectant un LLM à un DataFrame pour répondre à des questions en langage naturel |
| **Ollama** | Serveur local permettant d'exécuter des LLMs open-source sur l'infrastructure de l'organisation |
| **LiteLLM** | Bibliothèque unifiant les APIs de plusieurs fournisseurs LLM (OpenAI, Anthropic, Google...) |
| **ECharts** | Bibliothèque de visualisation interactive open-source Apache, moteur graphique de ClarIA |
| **FastAPI** | Framework Python pour la création d'APIs REST haute performance (ASGI) |
| **Celery** | Système de file de tâches asynchrones — traite les requêtes LLM sans bloquer le serveur |
| **Redis** | Base de données en mémoire : broker Celery + Pub/Sub WebSocket + rate limiter |
| **Keycloak** | Serveur d'identité open-source gérant authentification SSO, rôles et permissions |
| **JWT** | JSON Web Token — Standard de jeton d'authentification signé numériquement |
| **RS256** | RSA avec SHA-256 — algorithme de signature des JWT Keycloak |
| **JWKS** | JSON Web Key Set — Ensemble de clés publiques pour valider les JWT |
| **RBAC** | Role-Based Access Control — Contrôle d'accès basé sur les rôles utilisateur |
| **WebSocket** | Protocole de communication bidirectionnel temps réel entre navigateur et serveur |
| **fuzzy matching** | Correspondance approximative de chaînes de caractères (ex: "chifre" → "chiffre") |
| **SPA** | Single Page Application — Application web sans rechargement de page |
| **ORM** | Object-Relational Mapping — Couche d'abstraction entre Python et la base de données SQL |
| **Alembic** | Outil de migrations de schéma de base de données pour SQLAlchemy |
| **KPI** | Key Performance Indicator — Indicateur clé de performance (agrégation sur colonne) |
| **RGPD** | Règlement Général sur la Protection des Données — réglementation européenne sur la vie privée |
| **SaaS** | Software as a Service — Application web sans installation locale |
| **TTL** | Time To Live — Durée de vie d'un fichier avant suppression automatique |
| **Docker Compose** | Outil d'orchestration de conteneurs multi-services pour déploiement reproductible |

---

*Document rédigé dans le cadre du Rapport de Stage / Projet de Fin d'Année — EMSI, filière 3IIR*
*ClarIA — Plateforme de Restitution Intelligente de Données — SKATYS — 2025–2026*
