# AGENTS.md — 花卉识别 AI Agent 项目速览

给 AI 助手/新人的项目地图。10 分钟跑起来的全部信息。

## 这是什么

FastAPI + LangChain(1.x) + ChromaDB RAG + Streamlit 的全栈花卉识别/养护咨询应用。
支持：图片识别（qwen-vl-max）、文字问答（qwen-plus + RAG 检索）、知识库管理、语音输入。

## 快速启动（本地）

```bash
# 1. 依赖（版本已锁定 requirements.txt）
pip install -r requirements.txt

# 2. 配置 .env（复制 .env.example 填真实 Key）
cp .env.example .env

# 3. 初始化知识库（只首次）
python init_knowledge.py

# 4. 启动（两个终端）
python run_backend.py     # FastAPI @ :8000，docs 在 /docs
python run_frontend.py    # Streamlit @ :8501
```

Docker：`docker compose up --build`（前后端一个镜像两个容器）。

## 目录地图

```
backend/
  main.py             # FastAPI 入口：CORS、鉴权依赖（verify_api_token）、路由注册
  config.py           # pydantic-settings 配置（环境变量全部走这里）
  image_utils.py      # 图片压缩（Pillow，识别前归一化 JPEG）
  api/
    chat_router.py    # /api/chat/*：stream(SSE)/send/messages(持久化)/transcribe/history/sessions
    flower_router.py  # /api/flower/*：recognize(图片识别)/knowledge/*(知识库增删查)
  agent/
    flower_agent.py   # 核心 Agent：直连 LLM 快速路径(纯文字) + Agent 路径(有图)
    session_store.py  # SQLite 会话持久化（WAL，线程本地连接）
  rag/                # 知识库：loader → splitter → embedding → Chroma/FAISS
  tools/              # Agent 工具：flower_recognition / knowledge_search
  oss/oss_manager.py  # 阿里云 OSS 上传（失败时前端自动退回 base64）
frontend/
  app.py              # Streamlit 入口：st.navigation 路由 + 侧边栏会话管理
  app_pages/          # chat(聊天)/knowledge(搜索)/manage(管理)/about(关于)
  api.py              # 统一 HTTP 封装：错误结构 + Bearer Token
  assets/             # 会话侧边栏 CCv2 组件（html/css/js）
tests/                # pytest 全离线（FakeAgent + FakeEmbeddings，无需 API Key）
data/                 # SQLite 会话 + chroma_db（gitignored）
knowledge/processed/  # 知识库源 JSON
```

## 环境变量（.env）

| 变量 | 用途 | 必填 |
|---|---|---|
| DASHSCOPE_API_KEY | 阿里云百炼 Key（LLM/视觉/embedding/语音共用） | 是 |
| OSS_ACCESS_KEY_ID / SECRET / BUCKET / ENDPOINT | 图片 OSS 存储；缺省时走 base64 兜底 | 否 |
| API_TOKEN | **生产必填**：后端 /api/* Bearer 鉴权；为空则无鉴权（本地开发） | 生产是 |
| DEBUG | true 时 uvicorn reload + 全量日志 | 否 |
| KNOWLEDGE_FORCE_REINDEX | true 时启动强制重建向量索引（默认跳过，省 embedding 钱） | 否 |
| VECTOR_DB_TYPE / CHROMA_PERSIST_DIR | 向量库类型与目录 | 否 |
| LLM_MODEL_NAME / VISION_MODEL_NAME / EMBEDDING_MODEL_NAME | 模型选择 | 否 |

前端读取：`FLOWER_API_BASE_URL`（后端地址）、`FLOWER_API_TOKEN`（= API_TOKEN）。
Docker 里 docker-compose 已映射，本地开发 frontend/config.py 自动读根目录 .env。

## 关键约定

- **错误风格**：业务失败 → HTTP 200 + `{"success": false, "error": ...}`；协议/参数错误 → 4xx/5xx。前端 `api.py` 统一收敛成 success:false。
- **鉴权**：`API_TOKEN` 配置后所有 /api/* 要求 `Authorization: Bearer <token>`；/health 与 /docs 不鉴权（探活/文档用）。
- **图片链路**：前端压缩 900px 缩略图（展示+上传）→ 后端魔数校验 + 压缩 1568px → OSS → 视觉模型。消息历史只存缩略图 data URL。
- **会话历史**：文字聊天经 Agent 落盘 SQLite；图片识别回合由前端调 `POST /api/chat/messages` 批量落盘（含 image_url）。前端本地 `_sessions` 是缓存，后端是权威。
- **性能**：图片识别结果按内容缓存（`st.cache_data` ttl=1h max_entries=20）；知识库检索热点 LRU（agent 内 50 条）；多图识别并行（4 并发封顶）；同会话请求持 asyncio.Lock 串行化。
- **测试**：`python -m pytest tests/ -v` 全离线可跑。聊天走 FakeAgent 替身，知识库走 FakeEmbeddings + 临时目录，不碰 data/。

## 常用命令

```bash
python -m pytest tests/ -v            # 全量测试（离线）
python run_backend.py                 # 启动后端
python run_frontend.py                # 启动前端
python diagnose_kb.py                 # 知识库诊断
```
