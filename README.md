# MiroFishPro（基于 MiroFishOpt 的进一步优化版）

本项目目录为 `MiroFishPro`，在 `MiroFishOpt` 本地化存储方案的基础上，进一步提升系统的工业级稳定性、计费精确度与仿真效率，覆盖 Step 1–5 全流程的健壮性与可观测性。

## 项目来源

- 上游项目：`https://github.com/jwc19890114/MiroFishOpt`
- 上游核心依赖：OASIS 模拟引擎（用于社媒多智能体模拟）
- 本优化版目标：在 MiroFishOpt 已完成本地化存储（Neo4j + Qdrant）的基础上，进一步解决工业场景中的计费精确度、仿真稳定性与 UI 可靠性问题；新增 Mock 测试服务器、AI 驱动的实体筛选、上下文摘要 Token 压缩等生产级特性，使全流程（Step 1–5）均达到可观测、可审计、可续跑的工业级标准。

## 做了哪些优化（重点变更点）

### 1) Mock 服务器自动化集成（零成本测试模式）

- **一键开启 Mock 模式**：在 `.env` 中配置 `USE_MOCK_LLM=true`，启动后端时会**自动拉起内置 Mock 服务器**，无需消耗真实 Token 即可完整测试 Step 1–5 的所有流程。
- **智能阶段识别**：Mock 服务器能自动识别调用者所处阶段（本体生成、实体抽取、人设生成、模拟行为、报告大纲/章节等）并返回对应格式的模拟数据。
- **可配置 Mock 地址**：通过 `MOCK_LLM_URL` 灵活指定 Mock 服务器监听地址（默认 `http://localhost:5099`），方便在复杂网络环境下自定义部署。
- **优雅退出**：后端通过 `atexit` 钩子在退出时自动关闭 Mock 子进程，避免端口残留。

### 2) AI 驱动的动态实体过滤（智能 Agent 筛选）

- **动态标签识别**：利用 LLM 根据模拟目标动态分析图谱标签，自动识别哪些实体标签应转化为社交 Agent（如"学生"、"官方机构"），并排除与本次模拟完全无关的实体类型。
- **个人 / 群体智能区分**：将识别出的标签分为"个人账号"与"机构账号"两类，驱动不同风格的人设生成策略，使仿真角色更加真实立体。

### 3) 社会关系强耦合（图谱中心度驱动）

- **连接度加权影响力**：Agent 的粉丝数、发帖频率、社交地位等参数与知识图谱中该实体的出度（Degree Centrality）挂钩——图谱中连接越多的实体，在模拟世界里的社会影响力就越高，实现了图谱知识与仿真世界的物理对齐。

### 4) 模拟轮次上下文摘要优化（大规模 Token 节省）

- **历史动态智能压缩**：重构了 OASIS 的 `SocialEnvironment.get_posts_env`。超过最近 10 条帖子的历史内容，会通过 LLM 生成 ≤500 字的"历史摘要"并缓存；每轮只向所有 Agent 广播一份摘要 + 最近 10 条全文，大幅降低每轮 Context 长度与 Token 消耗。
- **Agent-First 采样算法**：摘要生成时优先采样每个角色的最近 2 条动态 + 高互动帖子，确保摘要全面覆盖各方立场，不偏科。
- **轮次级缓存**：以"当前总帖数"为键做缓存，同一轮次内所有 Agent 共享同一份摘要，实现按轮次精确失效。

### 5) OASIS 引擎幂等补丁（续跑可靠性）

- **幂等建表 (Patch 1)**：修改 OASIS 的 `create_db()`，将 `CREATE TABLE` 改为 `CREATE TABLE IF NOT EXISTS`，解决续跑时因数据库已存在而崩溃的问题。
- **幂等注册 (Patch 2)**：修改 `Platform.sign_up()`，注册前先检查用户是否已存在，已存在则跳过而非抛出主键冲突，使模拟在异常退出后可安全续跑。

### 6) 后端驱动的物理级 Token 计费

- **账本唯一事实来源**：将统计权从前端收回到后端 `usage.json`，解决了多进程、异构环境下 Token 丢失的问题。
- **环节隔离分账 (Zero-Based Analytics)**：精准隔离 Step 1 到 Step 5 的每项开销，确保"报告生成费（step4）"与"交互对话费（step5）"互不占用。
- **子进程计费穿透**：修复了模拟子进程因环境隔离导致无法记费的 Bug（绝对导入修正 + 环境变量持久化），实现全链路 Token 零遗漏。

### 7) 算法护栏与死循环根治

- **指针强制位移保证**：在 `file_parser.py` 分块逻辑中引入安全阈值，根治了处理大文件或极端分块参数时 LLM 陷入无限循环的风险。
- **API 防御性校验**：在图谱构建入口 `graph.py` 引入参数强约束，从源头拦截 `chunk_size <= overlap` 等可能导致资源枯竭的非法配置。

### 8) 仿真与 IPC 通信加固

- **故障透明化反馈**：重构采访指令的响应机制，后端日志能反馈具体失败原因（如"Agent ID 不匹配"），而非模糊的 `failed`。
- **框架深度适配**：修正了对 `oasis` 库 `AgentGraph` 属性的非法引用（`.agents` → `.agent_mappings.values()`），解决了 Step 5 批量采访导致进程崩溃的顽疾。

### 9) 全链路 UI 韧性提升

- **解耦式计费仪表盘**：重构 `TokenDashboard`，在拿到 `simulationId` 后即刻启动轮询，无需等待三级 API 链加载完成，且能在 API 404（报告生成中）时静默重试。
- **鲁棒的报告导航**：通过 URL query 参数传递 `projectId`/`simulationId`，确保页面刷新或报告生成中间态时仍能正确定位数据。

---

## 数据存储位置（如何查阅历史项目）

### 项目元数据与上传文件（本地文件）

项目会以 `project_id` 持久化在后端 `uploads` 目录中：
- 项目目录：`MiroFishOpt/backend/uploads/projects/<project_id>/`
- 元数据：`MiroFishOpt/backend/uploads/projects/<project_id>/project.json`
- 原始文件：`MiroFishOpt/backend/uploads/projects/<project_id>/files/`
- 抽取文本：`MiroFishOpt/backend/uploads/projects/<project_id>/extracted_text.txt`

查看历史项目有两种方式：
- 前端：打开 `http://localhost:3000/projects`
- 后端 API：`GET /api/graph/project/list`

### 图谱与向量（本地服务）

- 图谱：Neo4j（容器默认暴露 `bolt://localhost:7687`，浏览器 `http://localhost:7474`）
- 向量：Qdrant（默认 `http://localhost:6333`）
- Qdrant collection：由 `.env` 的 `QDRANT_COLLECTION_CHUNKS` 控制（默认 `mirofish_chunks`）

## 如何运行（Linux / macOS / Windows）

### 0) 前置依赖

- Node.js 18+
- Python 3.11+
- `uv`（Python 依赖管理）
- Docker（推荐，用于一键启动 Neo4j/Qdrant）

### 1) 启动本地依赖（Neo4j + Qdrant）

```bash
docker compose -f docker-compose.local.yml up -d
```

默认 Neo4j 账号密码在 `docker-compose.local.yml` 中写死为：
- 用户：`neo4j`
- 密码：`mirofish`

对应 `.env` 里需要保持一致：`NEO4J_PASSWORD=mirofish`

### 2) 配置环境变量

```bash
cp .env.example .env
```

至少需要配置：

```env
# OpenAI-compatible LLM
LLM_API_KEY=你的key
LLM_BASE_URL=你的base_url
LLM_MODEL_NAME=你的模型名

# 本地化存储
GRAPH_BACKEND=local
VECTOR_BACKEND=qdrant

# Neo4j（与 compose 一致）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mirofish

# Qdrant
QDRANT_URL=http://localhost:6333
```

可选项（强烈建议了解）：

```env
# 抽取专用 LLM：解决 data_inspection_failed 等审核问题
# EXTRACT_API_KEY=...
# EXTRACT_BASE_URL=...
# EXTRACT_MODEL_NAME=...

# 报告专用 LLM：报告生成触发 data_inspection_failed 时使用
# REPORT_API_KEY=...
# REPORT_BASE_URL=...
# REPORT_MODEL_NAME=...

# Embeddings：如果你的提供方支持 embeddings，建议配置；不支持则可 VECTOR_BACKEND=none
# EMBEDDING_MODEL_NAME=...
# EMBEDDING_BASE_URL=...
# EMBEDDING_API_KEY=...

# Mock 模式（零 Token 测试，配置后自动拉起mock服务器用于模拟测试）
# USE_MOCK_LLM=true
# MOCK_LLM_URL=http://localhost:5099
```

### 3) 安装依赖

在项目根目录执行：

```bash
npm run setup:all
```

如果你不想使用 `uv`，也可以用原生 `venv + pip`（仅安装后端 Python 依赖）：

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

### 4) 启动服务

```bash
npm run dev
```

访问：
- 前端：`http://localhost:3000`
- 后端：`http://localhost:5001`

## 如何驱动（推荐使用流程）

1. Step1 图谱构建：上传材料 → 生成本体 → 构图（本地写入 Neo4j，可选写入 Qdrant）
2. Step2 环境准备：基于图谱实体生成 Agent Profiles（写入 `backend/uploads/simulations/<simulation_id>/...`）
3. Step3 启动模拟：启动并行模拟（Twitter + Reddit），本地模式会自动关闭"图谱记忆实时回写"；需要中途停止时可点击页面右上角「暂停模拟」
4. Step4 生成报告：ReportAgent 调用本地工具（图 + 向量 + 采访）生成报告
5. Step5 交互：对报告与模拟世界进行交互式查询；若采访不可用/超时，会自动降级为"人设 + 图谱/向量检索"回答

## 报告导出

- 报告生成完成后支持导出为 Markdown：
  - 页面 Step4 右侧有「导出报告（MD）」按钮
  - 或直接访问：`GET /api/report/<report_id>/download`
- 本地文件也会落盘在：`backend/uploads/reports/<report_id>/full_report.md`

## 常见问题（Troubleshooting）

- 报错 `400 data_inspection_failed / inappropriate content`：
  - 如果发生在"构图/抽取"阶段：使用 `EXTRACT_*` 把"抽取模型"单独切换到更合适的提供方/模型。
  - 如果发生在"报告生成"阶段：使用 `REPORT_*` 把"报告模型"单独切换到更合适的提供方/模型（后端也会自动尝试安全模式降级，但报告会更抽象）。
- 启动模拟 `HTTP 400: 未准备好，请先 prepare`：
  - Step3 已增加自动 prepare；如果仍发生，请确认你启动的是 `MiroFish-Optimize` 这套后端（端口 5001）。
- 报错 `interview_agents ... env 未运行或已关闭`：
  - 采访工具需要模拟环境仍在运行；不要提前关闭环境（或先重新启动模拟）。
- 交互阶段采访 `HTTP 400/504` 超时：
  - 这是 IPC 未收到模拟进程响应；当前版本已自动降级为"人设 + 图谱/向量检索"兜底回答。
- 图谱里同名多节点：
  - 这是"类型抖动"引起的；本优化版已对 Person/Organization/Product/Location 做归一，需**重建图谱**后生效。
- Token 仪表盘显示 0：
  - 请确保 `usage.json` 存在于对应 Simulation 目录；新建项目后将自动生成。如需重置计费数据，删除该文件即可。

## License

遵循上游 MiroFish 的开源许可证（仓库根目录 `LICENSE`）。
