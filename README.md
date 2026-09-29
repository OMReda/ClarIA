# Plateforme de Restitution Intelligente

> CSV/Excel → natural-language prompt → interactive ECharts chart — no code required.

## Architecture

```
nginx (80) → FastAPI (8000) → Celery worker → PandasAI + DockerSandbox
                                           ↘ Redis pub/sub → WebSocket
PostgreSQL / SQLite ← SQLAlchemy (async + sync)
Ollama (11434) — local LLM, data never leaves the server
```

## Tech Stack

### Frontend
- **Core:** React, TypeScript
- **Build Tool:** Vite
- **State Management:** Zustand
- **Data Validation:** Zod
- **Charts & Visualization:** ECharts (echarts-for-react)
- **Data Tables:** AG Grid Community
- **HTTP Client:** Axios
- **UI Layout:** React Grid Layout
- **Icons:** Lucide React
- **Excel Parsing:** SheetJS (xlsx)
- **Styling:** Tailwind CSS, PostCSS, Autoprefixer
- **Testing:** Vitest

### Backend
- **Runtime:** Python 3.11 (strictly required)
- **API Framework:** FastAPI, Uvicorn (ASGI)
- **Validation & Config:** Pydantic v2, pydantic-settings
- **Database ORM:** SQLAlchemy
- **Database Drivers:** asyncpg, psycopg2-binary, aiosqlite
- **Migrations:** Alembic
- **Task Queue:** Celery
- **Message Broker & Caching:** Redis
- **Data Processing:** Pandas, Numpy, DuckDB
- **File Parsing (Excel):** openpyxl, xlrd
- **Data Sniffing:** python-magic, chardet
- **String Matching:** rapidfuzz
- **Code Templating:** jinja2, astor
- **Fallback Charting:** matplotlib

### AI & LLM
- **LLM DataFrame Querying:** PandasAI
- **LLM Integration:** LiteLLM, pandasai-litellm, pandasai-openai
- **Local AI Server:** Ollama (Qwen 2.5 Coder 7B)
- **Machine Learning (Planned):** scikit-learn, xgboost, shap, prophet

### Infrastructure
- **Reverse Proxy:** Nginx
- **Databases:** PostgreSQL 16 (Production/Docker) / SQLite (Local dev)
- **Cache / PubSub:** Redis 7
- **Orchestration:** Docker & Docker Compose
- **Code Execution:** DockerSandbox

## How it works (The Pipeline)

The application's data processing pipeline is fully asynchronous to ensure the UI remains responsive and provides real-time feedback:

1. **Upload:** User uploads a CSV/Excel file via the frontend dropzone.
2. **File Processing:** The backend detects the MIME type (via magic bytes), sniffs the CSV encoding (`chardet`), normalizes French locales (numbers and dates), infers the schema, and saves the file. It returns a 20-row preview.
3. **Preview:** The frontend displays the interactive data table (`AG Grid`) and waits for user input.
4. **Prompting:** The user types a natural language question. The backend creates a pending prompt in the database (PostgreSQL/SQLite) and pushes a background task to **Celery**.
5. **Real-time Connection:** The frontend immediately opens a **WebSocket** connection. The backend subscribes to a Redis Pub/Sub channel to stream the background worker's progress to the UI.
6. **AI Processing (Celery Worker):**
   - The worker dynamically constructs an LLM prompt containing the user's question and the file's schema.
   - It sends the request to the LLM (e.g., local Ollama Qwen 2.5 Coder) via **PandasAI**.
   - The LLM writes Python code to aggregate the data.
   - The generated Python code is executed securely inside an isolated **DockerSandbox**.
   - A fuzzy matching algorithm (`rapidfuzz`) automatically corrects misspelled column names.
   - The resulting aggregated DataFrame is mapped to a chart specification.
7. **Rendering:** The worker publishes the final ECharts configuration to Redis. The WebSocket relays it to the frontend, which renders the beautiful, interactive SVG chart.

## Quick start

```bash
# 1. Copy env file
cp .env.example .env

# 2. Build and start everything
docker compose -f docker/docker-compose.yml up --build

# 3. Open the app
open http://localhost
```

> **First start**: Ollama will pull the `qwen2.5-coder:7b` model (~4.7 GB). This takes a few
> minutes. The worker service won't accept prompts until the Ollama healthcheck passes.

## Local development (backend)

```bash
# Requires Python 3.11 (pandasai 3.0.0 requires <3.12)
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
pip install -r tests/requirements-test.txt

# Start local infra (postgres + redis only)
docker compose -f docker/docker-compose.yml up postgres redis -d

# Run migrations
cd backend && alembic -c alembic.ini upgrade head && cd ..

# Start API
uvicorn backend.main:app --reload --port 8000

# Start worker (separate terminal)
celery -A backend.workers.celery_app worker --loglevel=info
```

## Local development (frontend)

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

Dev server proxies `/api` and `/ws` to `localhost:8000`.

## Run tests

```bash
# Unit + integration tests (in-memory SQLite, no Docker needed)
pytest --cov=backend --cov-report=term-missing
```

## Configuration

All settings are in `.env`. Key options:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `local` | `local` \| `openai` \| `anthropic` \| `google` |
| `LLM_MODEL` | `ollama/qwen2.5-coder:7b` | LiteLLM model string |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API base |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `GOOGLE_API_KEY` | — | Required when `LLM_PROVIDER=google` |
| `MAX_FILE_SIZE_MB` | `10` | Upload limit |
| `MAX_ROWS` | `100000` | Row limit per file |
| `RATE_LIMIT_PROMPTS_PER_HOUR` | `30` | Per-session hourly prompt limit |
| `FUZZY_HIGH_THRESHOLD` | `80` | Score ≥ 80 → silent column correction |
| `FUZZY_MID_THRESHOLD` | `50` | Score 50–79 → "did you mean?" question |
| `KEYCLOAK_SERVER_URL` | `http://localhost:8080` | Keycloak server URL |
| `KEYCLOAK_REALM` | `claria` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | `claria-frontend` | Frontend OIDC client ID |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | — | Admin service account secret |

## Privacy

- **`LLM_PROVIDER=local`** (default): PandasAI passes up to 10 sample rows to
  Ollama. Ollama runs on the same server — **data never leaves the host**.
- **`LLM_PROVIDER=openai` / `anthropic`**: sample rows are sent to the external
  API. Operator consent required. A warning is logged on startup.

## Security notes

- Authentication is handled by **Keycloak** (OpenID Connect / JWT). All API routes
  require a valid Bearer token. The `require_admin` dependency gates administrative
  endpoints to users with the `admin` realm role.
- File and prompt access is enforced by owner-id checks on every endpoint.
- The Celery worker mounts `/var/run/docker.sock` for `DockerSandbox`. In
  production, use a dedicated Docker daemon (Sysbox or rootless Docker) to
  reduce blast radius.
- **`LLM_PROVIDER=local`** (default): data never leaves the host.
- **Cloud providers (openai / anthropic / google)**: sample rows are sent to
  the external API. Operator consent required.

## Supported chart types

| Type | Keywords (FR/EN) |
|---|---|
| Bar | barre, bar, par région, par catégorie |
| Line | évolution, tendance, par date, par mois |
| Area | aire, cumulé |
| Pie | camembert, proportion, pourcentage |
| Scatter | corrélation, nuage de points, vs |
| Histogram | distribution, histogramme, fréquence |
| Radar | radar, toile d'araignée, spider |
| Heatmap | heatmap, carte de chaleur, matrice de corrélation |
