# ClarIA — Plateforme de Restitution Intelligente

> Upload a CSV or Excel file, ask a question in plain French, get an interactive chart — no code required.

ClarIA is a self-hosted data visualisation platform built for non-technical users. It combines a local-first LLM (Ollama), a secure task queue (Celery), and a modern React frontend to turn raw spreadsheet data into interactive ECharts graphs through natural-language prompts.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Quick start (Docker)](#quick-start-docker)
- [Local development](#local-development)
- [Configuration](#configuration)
- [Supported chart types](#supported-chart-types)
- [Privacy & security](#privacy--security)
- [Known limitations & feedback](#known-limitations--feedback)
- [License](#license)

---

## Features

- **Drag-and-drop file upload** — CSV and Excel (`.xlsx`, `.xls`), up to 10 MB / 100 k rows by default
- **Multi-sheet Excel support** — pick the sheet you want before prompting
- **Natural-language prompts** — ask in French (primary) or English; the backend fuzzy-matches column names automatically
- **8 chart types** — bar, line, area, pie, scatter, histogram, radar, heatmap
- **Dashboard builder** — drag, resize, and persist multiple charts per dataset using a grid layout
- **KPI cards** — manual aggregation cards (sum, average, min, max, count) with optional column filters
- **AI explanation mode** — opt-in explanations generated alongside the chart (cloud providers only)
- **Clarification loop** — if the model can't resolve a column reference, it asks the user before retrying
- **Multi-provider LLM** — Ollama (local, default), OpenAI, Anthropic, Google Gemini; switchable per request from the settings panel
- **Automatic Ollama fallback** — if Ollama is unreachable the backend silently falls back to the first configured cloud key
- **Keycloak authentication** — OpenID Connect / JWT; admin role gates the user-management panel
- **Rate limiting** — 30 prompts / hour / user (Redis-backed, atomic Lua counter)
- **Real-time updates** — WebSocket streaming via Redis pub/sub; progress and fallback notices appear live
- **Export** — PNG, CSV, Excel, Power BI–ready `.xlsx` from any chart
- **Session restore** — page reload restores the last active dataset and chart result

---

## Architecture

```
Browser
  │
  ├─ HTTPS (dev: Vite + basicSsl / prod: nginx :80)
  │
nginx :80
  ├─ /api/        → FastAPI :8000  (async, Uvicorn)
  ├─ /ws/         → FastAPI :8000  (WebSocket)
  └─ /realms/ … → Keycloak :8080  (OIDC)

FastAPI
  ├─ POST /files              — upload, validate, persist
  ├─ POST /files/{id}/prompts — enqueue Celery task → 202
  ├─ WS   /ws/prompts/{id}    — Redis pub/sub → client
  ├─ GET  /files/{id}/…       — data, preview, dashboard config
  └─ /platform-users/…        — admin CRUD (Keycloak Admin API)

Celery worker (sync)
  ├─ load DataFrame (pandas)
  ├─ fuzzy-match column refs (rapidfuzz)
  ├─ detect chart type (keywords + LLM classify)
  ├─ call PandasAI → LLM generates aggregation code
  ├─ execute code in DockerSandbox
  ├─ build ECharts spec
  └─ publish result to Redis → WebSocket → browser

PostgreSQL 16  ← SQLAlchemy (async API + sync worker)
Redis 7        ← Celery broker + WebSocket pub/sub + rate-limit counters
Ollama :11434  ← local LLM (qwen2.5-coder:7b default)
```

---

## Tech stack

### Backend
| Concern | Library |
|---|---|
| API framework | FastAPI, Uvicorn |
| Auth | python-jose / PyJWT, Keycloak OIDC |
| ORM | SQLAlchemy (async + sync) |
| Migrations | Alembic |
| Task queue | Celery, Redis |
| Data | Pandas, NumPy, DuckDB |
| File parsing | openpyxl, xlrd, python-magic, chardet |
| String matching | rapidfuzz |
| LLM / AI | PandasAI, LiteLLM, pandasai-litellm, pandasai-openai |
| Code sandbox | pandasai-docker (DockerSandbox) |
| Validation | Pydantic v2, pydantic-settings |

### Frontend
| Concern | Library |
|---|---|
| Framework | React 18, TypeScript |
| Build | Vite |
| State | Zustand |
| Validation | Zod |
| Charts | Apache ECharts (echarts-for-react) |
| Data table | AG Grid Community |
| Grid layout | React Grid Layout |
| HTTP | Axios |
| Auth | keycloak-js |
| Icons | Lucide React |
| Excel export | SheetJS (xlsx) |

### Infrastructure
| Service | Image |
|---|---|
| Reverse proxy | nginx (alpine) |
| Database | postgres:16-alpine |
| Cache / broker | redis:7-alpine |
| Auth server | quay.io/keycloak/keycloak:26.0.0 |
| Local LLM | ollama/ollama:latest \u2014 any model from [ollama.com/library](https://ollama.com/library) |

---

## Quick start (Docker)

**Requirements:** Docker Engine 24+, Docker Compose v2, ~6 GB free disk (model download).

```bash
# 1. Clone
git clone <your-repo-url>
cd plateforme-restitution

# 2. Configure environment
cp .env.example .env
# Edit .env — at minimum set KC_ADMIN_PASSWORD and POSTGRES_PASSWORD

# 3. Build and start
docker compose -f docker/docker-compose.yml up --build

# 4. Open
http://localhost
```

> **First start:** Ollama will pull whichever model is set in `LLM_MODEL`. The default in `.env.example` is `qwen2.5-coder:7b` (~4.7 GB) — this is just a pre-filled starting point, **not a requirement**. You can use any model available on [ollama.com/library](https://ollama.com/library): pull it with `ollama pull <model>` and update `LLM_MODEL` accordingly. The worker will not accept prompts until the Ollama healthcheck passes (`start_period: 120s`).

> **On model choice:** `qwen2.5-coder:7b` is a personal preference that worked well during development of this project. Results on your hardware and data will vary. Larger models (14B+) tend to produce more reliable aggregations; smaller ones are faster but more error-prone. The app works with any Ollama-compatible model — experiment and find what suits your setup.

### Default credentials

The Keycloak realm (`claria`) is imported automatically from `infra/keycloak/claria-realm.json`.  
Set your admin password via `KC_ADMIN_PASSWORD` in `.env` before the first start.

---

## Local development

### Backend

> **Python 3.11 is strictly required.** PandasAI 3.x is not compatible with Python 3.12+.

```bash
# Create virtualenv
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
pip install -r tests/requirements-test.txt

# Start backing services only (postgres + redis)
docker compose -f docker/docker-compose.yml up postgres redis keycloak -d

# Run migrations
alembic -c backend/alembic.ini upgrade head

# Start API
uvicorn backend.main:app --reload --port 8000

# Start worker (separate terminal)
celery -A backend.workers.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # https://localhost:5173 (self-signed cert via @vitejs/plugin-basic-ssl)
```

The Vite dev server proxies `/api`, `/ws`, `/realms`, `/resources`, `/admin`, and `/js` to the local backend and Keycloak.

### Tests

```bash
# Unit + integration (in-memory SQLite, no Docker or Ollama needed)
pytest tests/ -q

# With coverage
pytest tests/ --cov=backend --cov-report=term-missing
```

All 141 tests run against an in-memory SQLite database. No external services are required.

---

## Configuration

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `changeme` | PostgreSQL password (Docker only) |
| `KC_ADMIN_PASSWORD` | `changeme` | Keycloak bootstrap admin password |
| `LLM_PROVIDER` | `local` | `local` \| `openai` \| `anthropic` \| `google` |
| `LLM_MODEL` | `ollama/qwen2.5-coder:7b` | LiteLLM model string — any Ollama model works here |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API base URL |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `GOOGLE_API_KEY` | — | Required when `LLM_PROVIDER=google` |
| `LLM_TIMEOUT_SECONDS` | `300` | Max wait for LLM response |
| `MAX_FILE_SIZE_MB` | `10` | Upload size limit |
| `MAX_ROWS` | `100000` | Maximum rows per file |
| `SESSION_TTL_DAYS` | `7` | Days before files are auto-deleted |
| `RATE_LIMIT_PROMPTS_PER_HOUR` | `30` | Per-user hourly prompt cap |
| `FUZZY_HIGH_THRESHOLD` | `80` | Score ≥ 80 → silent column correction |
| `FUZZY_MID_THRESHOLD` | `50` | Score 50–79 → clarification question |
| `KEYCLOAK_SERVER_URL` | `http://localhost:8080` | Keycloak base URL (backend-to-server) |
| `KEYCLOAK_REALM` | `claria` | Realm name |
| `KEYCLOAK_CLIENT_ID` | `claria-frontend` | OIDC client ID |
| `KEYCLOAK_ADMIN_CLIENT_ID` | `claria-admin` | Admin service account client ID |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | — | Admin service account secret |

---

## Supported chart types

| Type | Example prompts (FR) |
|---|---|
| **Bar** | "Ventes par région", "Montant par catégorie" |
| **Line** | "Évolution des ventes par mois", "Tendance sur 2024" |
| **Area** | "Cumul des revenus", "Surface sous la courbe" |
| **Pie** | "Répartition par type", "Part de marché en %" |
| **Scatter** | "Corrélation entre prix et quantité", "Nuage prix vs revenu" |
| **Histogram** | "Distribution des âges", "Fréquence des montants" |
| **Radar** | "Comparaison radar des indicateurs", "Toile d'araignée" |
| **Heatmap** | "Matrice de corrélation", "Carte de chaleur par jour/heure" |

Chart type detection uses keyword matching for local models and an LLM classification call for cloud providers.

---

## Privacy & security

### Data privacy
- **`LLM_PROVIDER=local`** (default): PandasAI sends up to 10 sample rows to Ollama. Ollama runs on the same server — **data never leaves the host**.
- **`LLM_PROVIDER=openai` / `anthropic` / `google`**: sample rows are transmitted to the external API. This requires explicit operator acknowledgment. A warning is logged on every affected request.

### Authentication
- All API and WebSocket endpoints require a valid Keycloak Bearer token (RS256-signed JWT).
- JWT issuer is validated by realm suffix (not hostname) so the platform works behind any proxy, tunnel, or custom domain.
- The `admin` realm role is required for all `/platform-users/` endpoints.

### Code execution
- PandasAI-generated Python code runs inside a **DockerSandbox** container when available, isolating execution from the host.
- The worker container mounts `/var/run/docker.sock`. In production, consider a dedicated Docker daemon (Sysbox, rootless Docker) to reduce blast radius.

---

## Future perspectives

This is an early-stage project. Planned directions include:

- **Conversation history** — multi-turn prompts that reference previous charts ("now break that down by region")
- **Scheduled reports** — generate and email a dashboard snapshot on a cron schedule
- **Multi-dataset joins** — prompt across two uploaded files simultaneously
- **Custom chart templates** — save and reuse ECharts configurations as named templates
- **Role-based dataset access** — share specific datasets between users without giving full admin access
- **Improved local model support** — better prompt engineering and structured output parsing to reduce failures on smaller models
- **i18n** — multi-language UI (the backend is language-agnostic; only the frontend messages need translation)
- **Audit log** — per-user prompt and export history for compliance use cases

None of these are guaranteed or on a fixed timeline — this list reflects directions being considered.

---

## Known limitations & feedback

This project is functional and tested, but it is still in active development. Here are the honest rough edges:

- **Local LLM quality varies.** Ollama worked well during development of this project, but results depend heavily on the model you choose and your data shape. `qwen2.5-coder:7b` is simply what was used while building the app — **you are not tied to it**. If you find it struggling with your data, try a larger model (14B+) or switch to a cloud provider (Gemini Flash, GPT-4o-mini) from the settings panel. Cloud providers consistently produce better structured outputs.

- **PandasAI v3 edge cases.** PandasAI 3.x is relatively new. Some data shapes (deeply nested columns, mixed-type columns, non-standard date formats) may produce unexpected results or silent failures.

- **Chart type detection on local models.** For Ollama, chart type is detected via keyword matching rather than an LLM call (to avoid doubling latency). Edge cases and ambiguous prompts may be misclassified.

- **French-first UI.** The frontend and error messages are primarily in French. There is no i18n system in place.

- **Keycloak initial setup.** A pre-configured realm JSON is included (`infra/keycloak/claria-realm.json`), but you will need to configure your own client secrets, redirect URIs, and SMTP settings for a production deployment.

- **Docker socket security.** The DockerSandbox requires the Docker socket, which grants elevated host access. This is a known trade-off — see the security notes above.

- **No horizontal scaling.** The current architecture assumes a single worker and single API instance. Celery supports multiple workers, but the file storage volume and session design have not been tested in a multi-node setup.

**Feedback is very welcome.** If you encounter a bug, an incorrect chart output, a failed migration, or anything unexpected, please open an issue with:
- The file type and approximate row/column count
- The prompt you used
- The LLM provider and model
- The error message or incorrect output

This helps prioritise fixes and improve the prompt engineering and chart detection logic. Pull requests are also welcome.

---

## License

MIT
