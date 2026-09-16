# CHAPITRE 2 : PRÉSENTATION DU PROJET

---

**Introduction du chapitre**

Le chapitre précédent a posé le cadre contextuel du projet en présentant l'organisme d'accueil, le problème de l'exploitation des données tabulaires par les utilisateurs non techniques, et les limitations des solutions de Business Intelligence existantes. Ce deuxième chapitre se consacre à la présentation formelle et détaillée du projet ClarIA. Ce chapitre reformule la problématique centrale de manière précise et technique, dresse un état de l'art des technologies sur lesquelles repose la solution, définit le positionnement de ClarIA, ses objectifs généraux et spécifiques, et traduit l'ensemble de ces éléments en un cahier des charges structuré. Ce chapitre se conclut par la présentation du planning prévisionnel qui a rythmé le développement du projet.

---

## 2.1 Problématique

La problématique centrale de ce projet, introduite dans le chapitre précédent, peut être reformulée de manière formelle et technique de la façon suivante :

> **Comment concevoir et déployer une plateforme web capable d'interpréter une requête formulée en langue naturelle (français), de l'exécuter de manière asynchrone sur un fichier de données tabulaires (CSV, Excel) via un Grand Modèle de Langage, de restituer le résultat sous forme de visualisation graphique interactive, et de garantir simultanément la confidentialité des données, la sécurité des accès et la persistance des visualisations — sans aucun prérequis technique de la part de l'utilisateur ?**

Cette problématique se distingue des approches de Business Intelligence classiques par quatre caractéristiques fondamentales qui la rendent techniquement ambitieuse :

1. **L'interprétation sémantique libre :** Contrairement aux requêtes SQL ou aux formules Excel, une requête en langage naturel peut être formulée de mille façons différentes pour exprimer la même intention. Le système doit comprendre le sens de la requête, pas seulement sa syntaxe.

2. **L'adaptation dynamique aux données :** Le système ne dispose d'aucun schéma fixe ou modèle de données préconfiguré. Il doit analyser le fichier de l'utilisateur à la volée, comprendre la sémantique de ses colonnes (y compris en cas d'orthographe approximative), et les mapper correctement à la requête.

3. **La robustesse aux données imparfaites :** Les fichiers réels comportent des imperfections (encodages variables, formats locaux français, classeurs multi-feuilles) que le système doit absorber de manière transparente, sans intervention de l'utilisateur.

4. **La confidentialité by design :** Le traitement doit pouvoir être effectué entièrement en local, sans transmission de données à des tiers, grâce à l'utilisation de modèles LLM open-source hébergés sur l'infrastructure de l'utilisateur.

---

## 2.2 État de l'Art Technique

### 2.2.1 L'émergence de l'interaction en langage naturel avec les données tabulaires

L'idée de permettre à des utilisateurs non techniques d'interroger des bases de données en langage naturel (Natural Language to SQL, ou NL2SQL) n'est pas nouvelle. Des systèmes comme NLIDB (Natural Language Interface to DataBase) ont été étudiés dès les années 1970. Cependant, ces approches étaient limitées à des grammaires rigides et nécessitaient un schéma de base de données précis et bien documenté.

L'essor des LLMs (Large Language Models) à partir de 2020 — et particulièrement l'apparition de modèles spécialisés dans la génération de code (Codex, Code Llama, Qwen 2.5 Coder) — a radicalement changé la donne. Ces modèles sont capables de comprendre une instruction en langue naturelle et de générer du code Python ou SQL valide pour l'exécuter sur des données réelles, avec une flexibilité et une tolérance aux variations de formulation sans précédent.

### 2.2.2 PandasAI — La bibliothèque pivot de ClarIA

**PandasAI** est une bibliothèque Python open-source qui constitue le cœur du pipeline intelligent de ClarIA. Elle permet de connecter un LLM à un `DataFrame` Pandas, offrant ainsi la capacité de répondre à des questions en langage naturel sur des données tabulaires.

Son fonctionnement peut être résumé en quatre étapes :
1. L'utilisateur formule une question en langage naturel.
2. PandasAI construit un prompt structuré contenant les métadonnées du DataFrame (noms des colonnes, types, échantillon de données) et la question de l'utilisateur.
3. Le LLM configuré génère un snippet de code Python (Pandas) répondant à la question.
4. PandasAI exécute ce code dans un environnement sécurisé et retourne le résultat (DataFrame, valeur scalaire, graphique).

La version 3.0.0 de PandasAI, utilisée dans ClarIA, introduit une architecture modulaire avec `pandasai-litellm` qui permet de connecter n'importe quel fournisseur LLM via l'interface unifiée LiteLLM.

*Tableau 1 : Comparatif des bibliothèques d'interaction LLM-données tabulaires*

| Bibliothèque | Approche | LLM supportés | Exécution locale | Maturité |
| :--- | :--- | :--- | :--- | :--- |
| **PandasAI** | Code Python généré + exécuté | Ollama, OpenAI, Anthropic, Google | ✅ Oui | ✅ Production |
| LangChain (CSV Agent) | Agent ReAct sur outils Pandas | OpenAI, HuggingFace | ✅ Oui (limité) | ⚠️ Complexe |
| LlamaIndex | Index sémantique sur documents | Ollama, OpenAI | ✅ Oui | ⚠️ Orienté RAG |
| vanna.ai | NL2SQL via RAG | OpenAI, Mistral | ✅ Oui | ⚠️ SQL only |

**Avantage de PandasAI pour ClarIA :** Il opère directement sur des DataFrames Pandas (format naturel des fichiers CSV/Excel) sans nécessiter de base de données relationnelle, et son architecture v3 avec LiteLLM permet un basculement transparent entre Ollama local et APIs cloud.

### 2.2.3 Ollama — Le moteur d'exécution locale des LLMs

**Ollama** est un serveur open-source permettant d'exécuter des modèles de langage de grande taille (LLMs) en local sur l'infrastructure de l'utilisateur. Il expose une API REST compatible avec l'API OpenAI, facilitant son intégration dans des systèmes existants.

Dans le contexte de ClarIA, Ollama joue un rôle fondamental : il garantit que **aucune donnée ne quitte le réseau de l'organisation**. Le modèle par défaut configuré est **`qwen2.5-coder:7b`**, un modèle open-source de Alibaba Cloud spécialisé dans la génération de code, particulièrement performant pour la génération de code Python/Pandas à partir d'instructions en langage naturel.

### 2.2.4 LiteLLM — L'orchestration multi-fournisseurs LLM

**LiteLLM** est une bibliothèque Python qui fournit une interface unifiée pour interagir avec plus de 100 fournisseurs LLM différents (OpenAI, Anthropic, Google Gemini, Ollama, Mistral, etc.) via une API standardisée. Dans ClarIA, LiteLLM est utilisé via l'extension `pandasai-litellm` pour gérer le basculement automatique entre Ollama local (prioritaire) et les APIs cloud (secours), de manière totalement transparente pour l'utilisateur.

### 2.2.5 Apache ECharts — Le moteur de visualisation

**Apache ECharts** est une bibliothèque de visualisation de données open-source développée par Baidu et maintenant sous la gouvernance de la fondation Apache. Elle offre 8 types de graphiques interactifs (barres, lignes, aires, secteurs, nuages de points, histogrammes, cartes de chaleur, radar) avec une personnalisation fine et un rendu performant côté navigateur via Canvas. Son intégration dans React est assurée par la bibliothèque `echarts-for-react`.

---

## 2.3 Positionnement de ClarIA

ClarIA se positionne à l'intersection de trois domaines technologiques : la Business Intelligence (BI), le traitement du langage naturel (NLP), et les interfaces conversationnelles de données. Cette intersection définit une catégorie émergente que l'on peut nommer **"Conversational Business Intelligence"**.

Son positionnement peut être résumé ainsi :

- **Par rapport aux outils BI classiques (Power BI, Tableau) :** ClarIA ne remplace pas ces outils pour les équipes data professionnelles. Elle les complète en ciblant les utilisateurs métiers non formés qui n'ont pas accès ou le temps d'apprendre ces plateformes.

- **Par rapport aux assistants IA génériques (ChatGPT, Gemini) :** ClarIA ne demande pas à l'utilisateur de copier-coller ses données dans un chatbot. Elle intègre directement le fichier de l'utilisateur, maintient la confidentialité locale, et produit des graphiques interactifs persistants sur un tableau de bord.

- **Par rapport à PandasAI utilisé directement :** ClarIA est une couche d'orchestration complète autour de PandasAI, ajoutant la gestion des utilisateurs (Keycloak), la sécurité (JWT RS256), le traitement asynchrone (Celery/Redis), le temps réel (WebSocket), la normalisation des données (locale_normalizer), et la persistance (Dashboard PostgreSQL).

> [Figure 2 : Positionnement de ClarIA dans le paysage des outils d'analyse de données — À insérer ici]
> *(Légende suggérée : Figure 2 — Carte de positionnement illustrant ClarIA à l'intersection de la BI classique, du NLP et de la confidentialité des données.)*

---

## 2.4 Objectifs du Projet

### 2.4.1 Objectif général

L'objectif général de ClarIA est de **démocratiser l'analyse de données tabulaires** en mettant la puissance des Grands Modèles de Langage au service d'une interface accessible à tout professionnel, sans compétence technique, tout en garantissant la confidentialité des données par l'utilisation privilégiée de modèles LLM exécutés localement.

### 2.4.2 Objectifs spécifiques

De manière plus granulaire, la plateforme doit atteindre les objectifs suivants :

1. **Import et normalisation automatiques :** Déployer un pipeline de validation et de normalisation robuste (format numérique français, encodage UTF-8/Latin-1, classeurs multi-feuilles) capable de traiter des fichiers CSV et Excel jusqu'à 10 Mo et 100 000 lignes.

2. **Compréhension du langage naturel :** Implémenter un moteur d'interprétation des requêtes utilisateur utilisant PandasAI et un LLM local (Ollama `qwen2.5-coder:7b`), avec correspondance floue des colonnes (`rapidfuzz`) pour tolérer les erreurs de formulation.

3. **Génération de visualisations :** Produire automatiquement des spécifications de graphiques Apache ECharts (8 types) à partir de la requête utilisateur, sans aucune intervention manuelle.

4. **Traitement asynchrone et temps réel :** Exécuter l'intégralité du pipeline IA via Celery/Redis en arrière-plan, et restituer le résultat en temps réel au navigateur via WebSocket, garantissant que l'interface n'est jamais bloquée.

5. **Sécurité et isolation :** Assurer une authentification sécurisée via Keycloak 26 (JWT RS256), un contrôle d'accès basé sur les rôles (RBAC), et une isolation stricte des données entre utilisateurs (`owner_id` sur toutes les entités).

6. **Tableau de bord personnalisable :** Permettre à chaque utilisateur de sauvegarder ses graphiques sur un tableau de bord personnel avec disposition librement modifiable (glisser-déposer, redimensionnement), enrichi d'indicateurs KPI manuels.

---

## 2.5 Cahier des Charges

### 2.5.1 Acteurs et Besoins Utilisateurs

Le système identifie trois acteurs principaux interagissant avec la plateforme :

1. **L'Utilisateur Métier (`user`) :** Professionnel non technique disposant de fichiers de données. Il peut importer ses fichiers, formuler des requêtes en langage naturel, visualiser les graphiques générés, les épingler sur son tableau de bord, et y ajouter des indicateurs KPI. Il n'a accès qu'à ses propres données. Dans le cadre du déploiement chez SKATYS, ce profil correspond en premier lieu aux **consultants** de l'entreprise, qui analysent des exports de données clients (extractions SAP, fichiers Excel, rapports opérationnels) lors de leurs missions — sans avoir besoin de compétences en programmation ou en BI.

2. **L'Administrateur (`admin`) :** Responsable de la gestion de la plateforme. Il est dédié **exclusivement** aux fonctions de gestion des comptes utilisateurs via le panneau d'administration (`AdminPage`) : création, modification, désactivation et suppression des comptes via l'API Keycloak. Il ne participe pas à l'analyse de données et n'a pas accès aux fonctionnalités de l'espace utilisateur (import de fichiers, requêtes LLM, tableau de bord).

3. **Le Worker Asynchrone (Celery) :** Acteur système qui traite les requêtes longues (pipeline IA) en arrière-plan, sans blocage de l'API principale.

### 2.5.2 Exigences Fonctionnelles

Les fonctionnalités attendues du système sont les suivantes :

- **F-01 :** Authentification sécurisée via Keycloak 26, jetons JWT RS256, cache JWKS 900 secondes.
- **F-02 :** Import de fichiers CSV et Excel (`.xlsx`, `.xls`) avec validation par signature d'octets (magic bytes), limite à 10 Mo et 100 000 lignes.
- **F-03 :** Dialogue de sélection de feuille pour les classeurs Excel multi-feuilles.
- **F-04 :** Normalisation automatique des formats locaux français (virgules décimales, dates `dd/mm/yyyy`).
- **F-05 :** Prévisualisation des données importées : aperçu des premières lignes, types des colonnes, nombre de lignes.
- **F-06 :** Interface conversationnelle (Aski) : saisie de la requête en langage naturel, envoi asynchrone vers le pipeline IA.
- **F-07 :** Classification de l'intention LLM : détermination si la question est pertinente aux données importées.
- **F-08 :** Correspondance floue des colonnes (`rapidfuzz`, seuils à 80% et 50%) pour tolérer les fautes de frappe dans les noms de colonnes.
- **F-09 :** Détection du type de graphique souhaité par analyse des mots-clés de la requête (8 types).
- **F-10 :** Inférence LLM via PandasAI sur un `pai.DataFrame()`, avec modèle Ollama local par défaut.
- **F-11 :** Basculement automatique entre fournisseurs LLM (Ollama → OpenAI / Anthropic / Google Gemini via LiteLLM).
- **F-12 :** Construction de la spécification de graphique Apache ECharts par le service `chart_resolver`.
- **F-13 :** Restitution du résultat en temps réel via WebSocket (Redis Pub/Sub).
- **F-14 :** Génération d'une explication textuelle en français du graphique (opt-in, `generate_explanation`).
- **F-15 :** Tableau de bord personnalisable (glisser-déposer, redimensionnement) avec persistance en base de données.
- **F-16 :** Indicateurs KPI manuels (SUM, AVG, COUNT, MIN, MAX) sur les colonnes numériques.
- **F-17 :** Limiteur de débit Redis : 30 requêtes par utilisateur par heure (script Lua atomique).
- **F-18 :** Panneau d'administration : CRUD utilisateurs via Keycloak Admin API, suppression en cascade (base de données + disque).
- **F-19 :** Configuration des fournisseurs LLM à chaud (sans redémarrage) depuis le panneau de paramètres.
- **F-20 :** Nettoyage automatique des fichiers expirés (TTL 7 jours) via une tâche Celery planifiée.
- **F-21 :** Dialogue de clarification interactif : lorsque la requête est ambiguë, le pipeline passe en état `awaiting_clarification` et pose une question de précision à l'utilisateur avant de reprendre le traitement.
- **F-22 :** Constructeur manuel de graphiques : création de graphiques personnalisés directement depuis l'interface (sans LLM), avec agrégation côté client sur les 10 000 premières lignes du fichier actif.


### 2.5.3 Exigences Non Fonctionnelles

Pour garantir une qualité de service optimale, la plateforme doit respecter les contraintes suivantes :

- **Performance :** L'interface utilisateur ne doit jamais être bloquée lors de l'exécution d'une requête LLM. Le pipeline complet (upload → normalisation → validation) doit s'effectuer en moins de 5 secondes. L'inférence LLM est asynchrone, sans contrainte de durée côté interface.
- **Sécurité :** Aucun mot de passe n'est stocké dans l'application (délégué à Keycloak). Toutes les communications API sont protégées par JWT RS256. Aucune donnée d'un utilisateur n'est accessible à un autre (clause `owner_id` obligatoire sur toutes les requêtes métier).
- **Confidentialité :** En mode Ollama, aucune donnée ne quitte l'infrastructure de l'organisation, satisfaisant aux exigences RGPD des entreprises.
- **Disponibilité :** L'architecture doit supporter l'ajout de workers Celery supplémentaires pour distribuer la charge sans modification du code.
- **Maintenabilité :** L'architecture est entièrement conteneurisée via Docker Compose, garantissant la reproductibilité parfaite des environnements de développement et de production.

### 2.5.4 Périmètre du Projet

**Inclus dans la version actuelle :**
Gestion des fichiers (CSV/Excel), pipeline IA complet (normalisation → PandasAI → ECharts), 8 types de graphiques, tableau de bord personnalisable, indicateurs KPI, authentification Keycloak, RBAC (rôles user/admin), limiteur de débit Redis, panneau d'administration, nettoyage automatique des fichiers, support multi-fournisseurs LLM.

**Exclus de la version actuelle — Perspectives d'évolution futures :**
Connexion directe à des entrepôts de données (Data Warehouse : Snowflake, BigQuery, Redshift), export PDF/PowerPoint des tableaux de bord, modèles statistiques avancés (séries temporelles, clustering), application mobile native, pipeline RAG avec embeddings vectoriels (PGvector, `bge-m3`).

### 2.5.5 Environnement Technique

Afin de répondre à l'ensemble de ces exigences, la pile technologique suivante a été sélectionnée et justifiée :

*Tableau 2 : Stack technologique de la plateforme ClarIA*

| Couche | Technologie | Version | Justification |
| :--- | :--- | :--- | :--- |
| **API Backend** | FastAPI | ≥0.111.0 | ASGI natif, performances élevées, validation Pydantic intégrée |
| **ORM & Base de données** | SQLAlchemy + PostgreSQL / SQLite | 2.0 / 16 | Moteur asynchrone (`asyncpg`) en prod, SQLite en développement |
| **Migrations** | Alembic | ≥1.13 | 4 révisions — gestion des évolutions de schéma sans perte de données |
| **File de tâches** | Celery + Redis | ≥5.4 / ≥7.0 | Asynchronisme du pipeline IA ; Redis = broker + pub/sub WebSocket |
| **Core IA** | PandasAI + LiteLLM | 3.0.0 | Interface unifiée LLM sur DataFrames Pandas — nécessite Python 3.10–3.11 |
| **LLM local** | Ollama (`qwen2.5-coder:7b`) | 26+ | Exécution locale, confidentialité totale, API compatible OpenAI |
| **Authentification** | Keycloak 26 + python-jose | 26.0.0 | SSO, RBAC, JWT RS256, JWKS, portail admin intégré |
| **Frontend Framework** | React 18 + Vite 5 + TypeScript | 18.3 / 5.3 | SPA réactive, typage strict, HMR rapide |
| **Visualisation** | Apache ECharts | 5.5.0 | 8 types de graphiques, rendu Canvas performant, interactivité native |
| **Tableau de données** | AG Grid Community | 32.0 | Prévisualisation complète des CSV/Excel importés (jusqu'à 100k lignes) |
| **Tableau de bord** | react-grid-layout | 2.2.3 | Glisser-déposer + redimensionnement avec sérialisation JSON |
| **Réorganisation KPI** | @dnd-kit/sortable | 10.0 | Tri drag-and-drop des indicateurs KPI sur le tableau de bord |
| **État global** | Zustand | 4.5.2 | Store léger, sans boilerplate, 3 stores : app, dataset, provider |
| **Conteneurisation** | Docker + Docker Compose | — | Déploiement reproductible, isolation des services |

---

## 2.6 Planning et Répartition des Tâches

La réalisation de la plateforme ClarIA a été organisée selon une méthodologie de développement agile et itérative. Le **planning** ci-dessous a été établi en début de stage sur la base d’un développement intensif sur le mois de juillet 2026 (S1-S4), suivi de la rédaction du rapport et de la préparation à la soutenance en août (S5-S8). Le détail précis de l'exécution se trouve au Chapitre 3 (section 3.8).

*Tableau 3 : Planning de développement et répartition des tâches*

| Phase | Période | Activités principales |
| :--- | :--- | :--- |
| **S1** | Semaine 1 | Cahier des charges, étude de l'existant, choix technologiques, environnement de travail |
| **S2** | Semaine 2 | Conception UML (cas d'utilisation, classes, séquence, activité), modélisation MCD/MLD |
| **S3** | Semaine 3 | Développement backend : FastAPI, SQLAlchemy, Keycloak, intégration du pipeline IA |
| **S4** | Semaine 4 | Développement frontend (React), tests automatisés (44 tests), correction des bugs |
| **S5-S8**| Semaines 5–8 | Rédaction du rapport PFA, documentation technique, préparation de la soutenance |

> [Figure 3 : Diagramme de Gantt du projet ClarIA — À insérer ici]
> *(Légende suggérée : Figure 3 — Diagramme de Gantt illustrant les grandes phases de réalisation de la plateforme ClarIA.)*

---

**Conclusion du chapitre**

Ce deuxième chapitre a permis de présenter formellement le projet ClarIA dans toute sa dimension technique et fonctionnelle. La reformulation de la problématique a mis en évidence les quatre défis fondamentaux que la solution doit relever : l'interprétation sémantique libre, l'adaptation dynamique aux données, la robustesse aux imperfections des fichiers, et la confidentialité by design. L'état de l'art technique a justifié le choix de PandasAI, d'Ollama et de LiteLLM comme technologies pivot, tandis que le cahier des charges a formalisé les 22 exigences fonctionnelles et les contraintes non fonctionnelles qui encadrent le développement. Le chapitre suivant abordera la phase d'analyse et de conception, en traduisant ces exigences en modélisations UML concrètes qui ont servi de plan directeur à l'ensemble du développement.
