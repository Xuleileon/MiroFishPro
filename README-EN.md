<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

简洁通用的群体智能引擎，预测万物
</br>
<em>A Simple and Universal Swarm Intelligence Engine, Predicting Anything</em>

<a href="https://www.shanda.com/" target="_blank"><img src="./static/image/shanda_logo.png" alt="666ghj%2MiroFish | Shanda" height="40"/></a>

[![GitHub Stars](https://img.shields.io/github/stars/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/stargazers)
[![GitHub Watchers](https://img.shields.io/github/watchers/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/watchers)
[![GitHub Forks](https://img.shields.io/github/forks/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/network)
[![GitHub Issues](https://img.shields.io/github/issues/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/pulls)

[![GitHub License](https://img.shields.io/github/license/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/blob/main/LICENSE)
[![Version](https://img.shields.io/badge/version-v0.1.0-green.svg?style=flat-square)](https://github.com/666ghj/MiroFish)

[English](./README-EN.md) | [中文文档](./README.md)

</div>

## ⚡ Overview

**MiroFish** is a next-generation AI prediction engine powered by multi-agent technology. By extracting seed information from the real world (such as breaking news, policy drafts, or financial signals), it automatically constructs a high-fidelity parallel digital world. Within this space, thousands of intelligent agents with independent personalities, long-term memory, and behavioral logic freely interact and undergo social evolution. You can inject variables dynamically from a "God's-eye view" to precisely deduce future trajectories — **rehearse the future in a digital sandbox, and win decisions after countless simulations**.

> You only need to: Upload seed materials (data analysis reports or interesting novel stories) and describe your prediction requirements in natural language</br>
> MiroFish will return: A detailed prediction report and a deeply interactive high-fidelity digital world

### Our Vision

MiroFish is dedicated to creating a swarm intelligence mirror that maps reality. By capturing the collective emergence triggered by individual interactions, we break through the limitations of traditional prediction:

- **At the Macro Level**: We are a rehearsal laboratory for decision-makers, allowing policies and public relations to be tested at zero risk
- **At the Micro Level**: We are a creative sandbox for individual users — whether deducing novel endings or exploring imaginative scenarios, everything can be fun, playful, and accessible

From serious predictions to playful simulations, we let every "what if" see its outcome, making it possible to predict anything.

## 🎬 Demo Videos

<div align="center">
<a href="https://www.bilibili.com/video/BV1VYBsBHEMY/" target="_blank"><img src="./static/image/武大模拟演示封面.png" alt="MiroFish Demo Video" width="75%"/></a>

Click the image to watch the complete demo video for prediction using BettaFish-generated "Wuhan University Public Opinion Report"
</div>

> More demo videos coming soon: "Dream of the Red Chamber" ending simulation, financial prediction examples...

## 🔄 Workflow

1. **Graph Building**: Seed extraction & Individual/collective memory injection & GraphRAG construction
2. **Environment Setup**: Entity relationship extraction & Persona generation & Agent configuration injection
3. **Simulation**: Dual-platform parallel simulation & Auto-parse prediction requirements & Dynamic temporal memory updates
4. **Report Generation**: ReportAgent with rich toolset for deep interaction with post-simulation environment
5. **Deep Interaction**: Chat with any agent in the simulated world & Interact with ReportAgent. If interviews are unavailable/timeout, it falls back to persona + graph/vector retrieval.

---

# MiroFishPro (Further Optimization Based on MiroFishOpt)

`MiroFishPro` builds on `MiroFishOpt`'s local storage foundation, further improving industrial-grade stability, billing accuracy, and simulation efficiency across the full Step 1–5 pipeline.

## Project Origin

- Upstream: `https://github.com/jwc19890114/MiroFishOpt` (local storage version, based on `https://github.com/666ghj/MiroFish`)
- Core dependency: OASIS simulation engine (for social multi-agent simulation)
- Goal: On top of MiroFishOpt's completed local storage (Neo4j + Qdrant), further resolve billing accuracy, simulation stability, and UI reliability issues in production scenarios. Adds Mock test server, AI-driven entity filtering, context-summary Token compression, and other production-grade features — making the full Step 1–5 pipeline observable, auditable, and resumable.

## What's New (Key Changes)

### 1) Mock Server Auto-Integration (Zero-Cost Testing Mode)

- **One-click Mock mode**: Set `USE_MOCK_LLM=true` in `.env` — the backend **automatically starts the built-in Mock server** when launched. Test the full Step 1–5 pipeline without consuming real Tokens.
- **Intelligent stage detection**: The Mock server automatically identifies the calling stage (ontology generation, entity extraction, persona generation, simulation actions, report outline/sections, etc.) and returns appropriately formatted mock data.
- **Configurable Mock URL**: Use `MOCK_LLM_URL` to specify the Mock server address (default `http://localhost:5099`) for custom deployments in complex network environments.
- **Graceful shutdown**: The backend registers an `atexit` hook to automatically terminate the Mock subprocess on exit, preventing orphaned port bindings.

### 2) AI-Driven Dynamic Entity Filtering (Smart Agent Selection)

- **Dynamic label recognition**: Uses LLM to analyze graph labels against the simulation goal, automatically identifying which entity types should become social Agents (e.g., "Student", "Government Agency") and excluding irrelevant types (e.g., "Auto Parts" in a medical simulation).
- **Individual / Group classification**: Splits recognized labels into "individual accounts" and "institutional accounts", driving different persona generation strategies for more realistic and dimensional simulation characters.

### 3) Social Graph Coupling (Degree Centrality Driven)

- **Degree-weighted influence**: Agent follower counts, posting frequency, and social status are tied to the entity's out-degree (Degree Centrality) in the knowledge graph — the more connected an entity is in the graph, the higher its social influence in the simulation, achieving physical alignment between graph knowledge and the simulated world.

### 4) Simulation Round Context Summary Optimization (Large-Scale Token Savings)

- **Intelligent history compression**: Refactored OASIS's `SocialEnvironment.get_posts_env`. Posts beyond the most recent 10 are summarized by LLM into a ≤500-word "history summary" and cached; each round broadcasts one summary + the last 10 posts in full, dramatically reducing per-round context length and Token consumption.
- **Agent-First sampling algorithm**: When generating summaries, the algorithm prioritizes the 2 most recent posts from each agent + high-engagement posts, ensuring the summary covers all perspectives without bias.
- **Round-level caching**: Uses "total post count" as the cache key; all agents within the same round share a single summary, with precise per-round invalidation.

### 5) OASIS Engine Idempotency Patches (Resume Reliability)

- **Idempotent table creation (Patch 1)**: Patches OASIS's `create_db()` to use `CREATE TABLE IF NOT EXISTS`, fixing crashes on resume when the database already exists.
- **Idempotent sign-up (Patch 2)**: Patches `Platform.sign_up()` to check if a user already exists before inserting, skipping rather than throwing a primary key conflict, enabling safe resume after abnormal exit.

### 6) Backend-Driven Physical Token Billing

- **Single source of truth**: Moves billing authority from the frontend to the backend `usage.json`, resolving Token loss in multi-process and heterogeneous environments.
- **Stage-isolated accounting (Zero-Based Analytics)**: Precisely isolates costs for Step 1 through Step 5, ensuring "report generation (step4)" and "interactive chat (step5)" fees never overlap.
- **Subprocess billing passthrough**: Fixes a bug where simulation subprocesses couldn't record fees due to environment isolation (via absolute import correction + environment variable persistence), achieving zero Token loss across the full chain.

### 7) Algorithmic Guardrails & Infinite Loop Prevention

- **Mandatory pointer advancement**: Introduces a safety threshold in `file_parser.py` chunking logic, eliminating the risk of LLM infinite loops when processing large files or extreme chunking parameters.
- **Defensive API validation**: Adds strict parameter constraints at the graph build entry point `graph.py`, blocking illegal configurations like `chunk_size <= overlap` that could exhaust resources.

### 8) Simulation & IPC Communication Hardening

- **Transparent failure feedback**: Refactored interview command response mechanism — backend logs now report specific failure reasons (e.g., "Agent ID mismatch") instead of a generic `failed`.
- **Framework deep adaptation**: Fixed illegal attribute access on the `oasis` library's `AgentGraph` (`.agents` → `.agent_mappings.values()`), resolving the Step 5 batch interview process crash.

### 9) Full-Stack UI Resilience

- **Decoupled billing dashboard**: Refactored `TokenDashboard` to start polling immediately upon receiving `simulationId`, without waiting for a three-level API chain to complete. Silently retries on API 404 (report still generating).
- **Robust report navigation**: Passes `projectId`/`simulationId` via URL query parameters, ensuring correct data retrieval on page refresh or during report generation intermediate states.

---

## Data Storage (How to Access Historical Projects)

### Project Metadata & Uploaded Files (Local Files)

Projects are persisted in the backend `uploads` directory by `project_id`:
- Project folder: `MiroFishOpt/backend/uploads/projects/<project_id>/`
- Metadata: `MiroFishOpt/backend/uploads/projects/<project_id>/project.json`
- Raw files: `MiroFishOpt/backend/uploads/projects/<project_id>/files/`
- Extracted text: `MiroFishOpt/backend/uploads/projects/<project_id>/extracted_text.txt`

Two ways to view historical projects:
- Frontend: `http://localhost:3000/projects`
- Backend API: `GET /api/graph/project/list`

### Graph & Vector (Local Services)

- Graph: Neo4j (container exposes `bolt://localhost:7687`, browser `http://localhost:7474`)
- Vector: Qdrant (default `http://localhost:6333`)
- Qdrant collection: controlled by `QDRANT_COLLECTION_CHUNKS` in `.env` (default `mirofish_chunks`)

## 🚀 How to Run (Linux / macOS / Windows)

### 0) Prerequisites

- Node.js 18+
- Python 3.11+
- `uv` (Python dependency manager)
- Docker (recommended, for one-click Neo4j/Qdrant startup)

### 1) Start Local Dependencies (Neo4j + Qdrant)

```bash
docker compose -f docker-compose.local.yml up -d
```

Default Neo4j credentials hardcoded in `docker-compose.local.yml`:
- User: `neo4j`
- Password: `mirofish`

Must match `.env`: `NEO4J_PASSWORD=mirofish`

### 2) Configure Environment Variables

```bash
cp .env.example .env
```

Minimum required configuration:

```env
# OpenAI-compatible LLM
LLM_API_KEY=your_api_key
LLM_BASE_URL=your_base_url
LLM_MODEL_NAME=your_model_name

# Local storage
GRAPH_BACKEND=local
VECTOR_BACKEND=qdrant

# Neo4j (must match compose)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mirofish

# Qdrant
QDRANT_URL=http://localhost:6333
```

Optional (strongly recommended to review):

```env
# Extraction-specific LLM: resolves data_inspection_failed review issues
# EXTRACT_API_KEY=...
# EXTRACT_BASE_URL=...
# EXTRACT_MODEL_NAME=...

# Report-specific LLM: used when report generation triggers data_inspection_failed
# REPORT_API_KEY=...
# REPORT_BASE_URL=...
# REPORT_MODEL_NAME=...

# Embeddings: configure if your provider supports it; otherwise set VECTOR_BACKEND=none
# EMBEDDING_MODEL_NAME=...
# EMBEDDING_BASE_URL=...
# EMBEDDING_API_KEY=...

# Mock mode (zero Token testing — auto-starts mock server when enabled)
# USE_MOCK_LLM=true
# MOCK_LLM_URL=http://localhost:5099
```

### 3) Install Dependencies

From the project root:

```bash
npm run setup:all
```

If you prefer not to use `uv`, use native `venv + pip` (backend Python dependencies only):

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4) Start Services

```bash
npm run dev
```

Access:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:5001`

## Recommended Usage Flow

1. **Step 1 — Graph Building**: Upload materials → Generate ontology → Build graph (writes to Neo4j locally, optionally to Qdrant)
2. **Step 2 — Environment Setup**: Generate Agent Profiles from graph entities (written to `backend/uploads/simulations/<simulation_id>/...`)
3. **Step 3 — Launch Simulation**: Start parallel simulation (Twitter + Reddit); local mode auto-disables "live graph memory sync". Click "Pause Simulation" in the top-right to stop mid-run.
4. **Step 4 — Generate Report**: ReportAgent uses local tools (graph + vector + interview) to generate the report
5. **Step 5 — Interact**: Query the report and simulated world interactively; if interviews are unavailable/timeout, automatically falls back to persona + graph/vector retrieval

## Report Export

- After generation, export as Markdown:
  - Click the "Export Report (MD)" button on the right side of the Step 4 page
  - Or: `GET /api/report/<report_id>/download`
- File is also saved locally: `backend/uploads/reports/<report_id>/full_report.md`

## Troubleshooting

- **`400 data_inspection_failed / inappropriate content`**:
  - During graph building/extraction: Use `EXTRACT_*` to switch the extraction model to a more permissive provider.
  - During report generation: Use `REPORT_*` to switch the report model (the backend also auto-attempts safe-mode fallback, but the report will be more abstract).
- **`HTTP 400: Not ready, please prepare first` on simulation start**:
  - Step 3 now includes auto-prepare; if this still occurs, confirm you're running the `MiroFishPro` backend (port 5001).
- **`interview_agents ... env not running or closed`**:
  - The interview tool requires the simulation environment to still be running. Don't close the environment prematurely (or restart the simulation first).
- **Interview `HTTP 400/504` timeout in Step 5**:
  - IPC received no response from the simulation process; the current version auto-falls back to persona + graph/vector retrieval.
- **Duplicate nodes with the same name in the graph**:
  - Caused by "type jitter"; this version normalizes Person/Organization/Product/Location types — requires **rebuilding the graph** to take effect.
- **Token dashboard showing 0**:
  - Ensure `usage.json` exists in the corresponding Simulation directory — it is auto-created for new projects. Delete the file to reset billing data.

## 📄 Acknowledgments

**MiroFish has received strategic support and incubation from Shanda Group!**

MiroFish's core simulation engine is powered by **[OASIS (Open Agent Social Interaction Simulations)](https://github.com/camel-ai/oasis)**. OASIS is a high-performance social media simulation framework developed by the [CAMEL-AI](https://github.com/camel-ai) team, supporting million-scale agent interaction simulations, providing a solid technical foundation for MiroFish's swarm intelligence emergence. We sincerely thank the CAMEL-AI team for their open-source contributions!

## License

Follows the upstream MiroFish open-source license (see `LICENSE` in the repository root).
