# 🌸 花卉识别 AI Agent + RAG 智能聊天系统

基于 Python、LangChain、RAG 和 Agent 技术的花卉识别智能聊天系统。

> 👨‍💻 **作者：何胤霖** · 个人项目展示 · [功能一览](#-功能特点) | [快速开始](#-快速开始) | [API 接口](#-api-接口)

## ✨ 功能特点

- 🔍 **智能花卉识别**: 上传花卉图片 / 图片链接，AI 自动识别花卉种类（结果按图缓存，同一张图 1 小时内不重复调用模型）
- 💬 **图片附带问题**: 视觉模型只做结构化识别，附带的问题（如"怎么养护"）识别完成后交给文字 LLM 流式回答，多图并行识别
- 🖼️ **图片压缩**: 上传图片统一压缩为 JPEG 缩略图（省内存 / 带宽 / 存储），失败自动回退原图
- 📚 **RAG 知识库**: 基于向量检索的花卉知识问答，支持搜索去重与相关度评分
- 🤖 **Agent 智能体**: 自动选择工具处理用户请求（图片识别 + 知识库搜索）
- 💬 **自然语言对话**: 支持多轮对话、SSE 流式输出、停止生成
- 🎤 **语音输入**: 按住录音提问，后端 DashScope Paraformer 自动转文字（API 化，不阻塞前端）
- 💾 **会话持久化**: 会话与消息（含图片）SQLite 落盘，刷新页面 / 重启后端历史不丢
- 🔒 **API Token 鉴权**: 配置 `API_TOKEN` 后所有 `/api/*` 请求必须携带 Bearer Token，防止公网裸奔被刷额度 / 删数据
- 📖 **知识管理**: 添加花卉数据、JSON 批量导入、知识库概览与删除
- 📱 **友好界面**: Streamlit 构建的美观聊天界面（暖色花卉主题）

## 🏗️ 系统架构

```
用户
  │
  ├── 聊天界面 (Streamlit)
  │
  ├── FastAPI 接口（Bearer Token 鉴权）
  │     ├── 聊天 / SSE 流式 / 会话历史 (Agent)
  │     ├── 语音识别 (DashScope Paraformer)
  │     └── 图片识别 / 知识库管理 / 消息持久化
  │
  ├── LangChain Agent
  │     ├── 图片识别工具 (通义千问 VL)
  │     └── 知识库搜索工具 (ChromaDB/FAISS)
  │
  └── 阿里云 OSS（识别图片存储，未配置则 base64 模式）
```

## 🛠️ 技术栈

### 后端
- **Python 3.11+**
- **FastAPI** - Web 框架（含 Bearer Token 鉴权）
- **LangChain** - LLM 应用框架
- **LangGraph** - Agent 编排
- **Pydantic** - 数据验证

### 大模型
- **通义千问 qwen-plus** - 文本对话
- **通义千问 qwen-vl-max** - 图片识别
- **DashScope Paraformer** - 语音识别
- **DashScope Embedding** - 文本向量化

### 存储
- **ChromaDB / FAISS** - 向量数据库
- **SQLite** - 会话与消息持久化
- **阿里云 OSS** - 文件存储

### 前端
- **Streamlit** - Web 界面

### 测试
- **pytest + httpx ASGI** - 进程内 API 集成测试（全离线：stub Agent + 假 Embedding，无需 API Key）

### 依赖管理
- **requirements.txt 版本锁定**（`==` 精确到本地 venv 实测版本），本地 / Docker / CI 行为一致

## 📁 项目结构

```
flower-ai-agent/
├── backend/                    # 后端代码
│   ├── __init__.py
│   ├── main.py                # FastAPI 主程序（Token 鉴权中间件）
│   ├── config.py              # 配置管理（含 API_TOKEN 鉴权开关）
│   ├── agent/                 # Agent 模块
│   │   ├── __init__.py
│   │   ├── flower_agent.py   # 花卉 Agent（文字直连 LLM 快速路径 + 图片 Agent 路径）
│   │   └── session_store.py  # 会话 SQLite 持久化
│   ├── rag/                   # RAG 模块
│   │   ├── __init__.py
│   │   ├── knowledge_base.py # 知识库管理
│   │   ├── document_loader.py # 文档加载器
│   │   ├── dashscope_embeddings.py # DashScope Embedding 封装
│   │   └── vector_store.py   # 向量存储
│   ├── tools/                 # 工具模块
│   │   ├── __init__.py
│   │   ├── flower_recognition.py  # 花卉识别工具（支持附带问题）
│   │   └── knowledge_search.py    # 知识库搜索工具
│   ├── oss/                   # OSS 模块
│   │   ├── __init__.py
│   │   └── oss_manager.py    # OSS 管理器（未配置则 base64 模式）
│   ├── image_utils.py        # 图片压缩（上传前归一化 JPEG 缩略图）
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   ├── flower.py         # 花卉模型
│   │   ├── chat.py           # 聊天模型
│   │   └── knowledge.py      # 知识库模型
│   └── api/                   # API 路由
│       ├── __init__.py
│       ├── chat_router.py    # 聊天 / 流式 / 语音识别 / 消息持久化接口
│       └── flower_router.py  # 花卉识别 / 知识库接口
├── frontend/                  # 前端代码
│   ├── config.py             # 前端公共配置（API 地址 / Token）
│   ├── api.py                # 统一 HTTP 封装（错误结构 + Bearer Token）
│   ├── app.py                # Streamlit 主应用
│   ├── assets/               # 会话侧边栏 CCv2 组件
│   └── app_pages/            # 页面：聊天 / 知识搜索 / 知识管理 / 关于
├── tests/                     # pytest 集成测试（全离线：stub Agent + 假 Embedding）
│   ├── conftest.py           # ASGI 测试客户端 + 离线环境
│   ├── fakes.py              # 测试替身
│   └── test_api.py           # 15 个 API 测试用例
├── knowledge/                 # 知识库
│   ├── raw/                  # 原始文档
│   └── processed/            # 处理后的文档
│       └── flowers_database.json
├── docs/                      # 文档
│   ├── API.md                # API 详细说明
│   └── DEPLOYMENT.md         # 部署指南
├── .github/workflows/         # GitHub Actions
│   ├── ci.yml                # PR 自动测试（全离线，无密钥）
│   └── deploy.yml            # push 到 main 自动构建镜像并部署
├── AGENTS.md                  # 给 AI 编码助手的项目说明
├── .env.example              # 环境变量示例
├── requirements.txt          # Python 依赖（版本锁定）
├── run_backend.py            # 后端启动脚本
├── run_frontend.py           # 前端启动脚本
└── README.md                 # 项目说明
```

## 🚀 快速开始

### 1. 环境准备

确保已安装 Python 3.11+：

```bash
python --version
```

### 2. 克隆项目

```bash
git clone https://github.com/Heyinlin495/flower-ai-agent.git
cd flower-ai-agent
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入您的配置（完整字段见 `.env.example`）：

```env
# 阿里云百炼大模型平台 API Key（文本 / 视觉 / 语音 / Embedding 共用）
DASHSCOPE_API_KEY=your_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/apps/anthropic

# API 访问令牌（生产必填！为空时后端 /api/* 无鉴权，公网会被任意调用）
API_TOKEN=

# 阿里云 OSS 配置（可选，不配置则识别图片走 base64 模式）
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=your_bucket_name
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

### 5. 启动后端服务

```bash
python run_backend.py
```

后端服务将在 http://localhost:8000 启动

API 文档：http://localhost:8000/docs

### 6. 启动前端应用

在新的终端窗口：

```bash
python run_frontend.py
```

前端应用将在 http://localhost:8501 启动

## 📖 使用说明

应用包含 4 个页面（侧边栏导航）：**智能聊天 / 知识搜索 / 知识管理 / 关于**

### 花卉识别

1. 进入"智能聊天"页面，直接在欢迎卡片上传图片（支持多张，并行识别），或使用输入框 📎 上传
2. 也可点击"识别图片链接"粘贴图片 URL 识别
3. AI 将自动识别花卉并以卡片形式展示花名、科属、花期、花语等
4. 同一张图 1 小时内重复识别直接返回缓存结果，不重复调用模型
5. 上传图片时附带的问题（如"玫瑰怎么养护？"）会在识别完成后由文字 LLM 流式回答

### 语音提问

1. 点击聊天输入框的 🎤 按钮录音
2. 松开后音频上传到后端识别，成功后自动发送（符合主流 App"松手即发"体验）

### 知识问答

在聊天输入框中输入问题，例如：
- "玫瑰怎么养护？"
- "菊花的花语是什么？"
- "兰花需要什么样的光照？"

生成中可点击"停止"终止回复。

### 知识搜索

在"知识搜索"页面直接检索知识库，支持按花卉名过滤、调整返回条数，结果附带相关度评分；同名重复结果自动折叠。

### 知识管理

在"知识管理"页面添加花卉数据、JSON 批量导入，底部"知识库概览"可查看已有花卉并删除。

### 会话持久化

会话与消息（含图片消息）自动保存到 `data/sessions.db`，刷新页面或重启后端后，侧边栏历史会话与聊天记录（含图片）完整保留。

## 🔧 API 接口

> 🔒 配置了 `API_TOKEN` 后，所有 `/api/*` 请求必须携带请求头 `Authorization: Bearer <token>`（前端自动附带，本地开发未配置时跳过校验）。

### 聊天接口

**POST** `/api/chat/send` — 发送聊天消息（普通响应）

**POST** `/api/chat/stream` — 发送聊天消息（SSE 流式，逐 token 输出）

```json
{
  "message": "这是什么花？",
  "session_id": "session_123",
  "image_url": "https://example.com/flower.jpg"
}
```

**GET** `/api/chat/sessions` — 列出所有会话（标题 / 消息数 / 更新时间）

**GET** `/api/chat/history/{session_id}` — 获取会话历史

**DELETE** `/api/chat/history/{session_id}` — 清除会话历史

**POST** `/api/chat/transcribe` — 语音转文字（DashScope Paraformer，base64 音频）

**POST** `/api/chat/messages` — 批量持久化会话消息（前端图片识别回合专用，刷新后历史不丢）

### 花卉识别接口

**POST** `/api/flower/recognize` — 上传图片识别（图片先压缩为 JPEG 缩略图）

**POST** `/api/flower/recognize-url` — 通过图片 URL 识别（`form: image_url`）

```bash
curl -X POST "http://localhost:8000/api/flower/recognize" \
  -F "image=@flower.jpg"
```

### 知识库接口

**GET** `/api/flower/knowledge/search` — 搜索花卉知识（`query`、`flower_name`、`top_k`）

**GET** `/api/flower/knowledge/list` — 列出知识库花卉名称（去重）

**POST** `/api/flower/knowledge/add` — 添加花卉知识（JSON body）

**DELETE** `/api/flower/knowledge/delete/{flower_name}` — 删除指定花卉

```bash
curl "http://localhost:8000/api/flower/knowledge/search?query=玫瑰养护"
```

更多细节见 [docs/API.md](docs/API.md)。

## 🧪 运行测试

pytest 使用进程内 ASGI 客户端（stub Agent + 假 Embedding），**全离线运行，无需 API Key**：

```bash
pytest tests/ -v
```

覆盖健康检查、Token 鉴权、知识库增删查、聊天发送/流式、语音识别、图片识别参数校验、会话历史往返（含图片）等 15 个用例。

## 🐳 Docker 部署

多阶段构建（小镜像 · 快构建 · 非 root 安全运行），本地开发用 compose：

```bash
# 构建并启动前后端（自动加载 .env 注入 API Key 与 API_TOKEN）
docker compose up --build

# 前端 http://localhost:8501 · 后端 http://localhost:8000
# 改代码即时生效（代码目录已挂载进容器）
```

```bash
# 生产环境：单独构建镜像，仅跑后端
docker build -t flower-ai-agent .
docker run -d --env-file .env -p 8000:8000 -v flower-data:/app/data flower-ai-agent
```

- `.env`（真实 API Key / API_TOKEN）通过 `env_file` / `--env-file` 注入，**不烧入镜像**
- compose 已自动把 `.env` 的 `API_TOKEN` 映射为前端的 `FLOWER_API_TOKEN`，前后端鉴权开闭一致
- 容器以非 root 用户运行，数据写入挂载卷（`data/`、`uploads/`、`logs/`）
- 前端默认通过 `FLOWER_API_BASE_URL=http://backend:8000` 访问 compose 内的后端

## 🤖 GitHub Actions 自动化

| Workflow | 触发 | 行为 |
|---|---|---|
| `ci.yml` | 任意 PR（含 draft） | 语法检查 + pytest（进程内 ASGI，**全离线无需任何密钥**） |
| `deploy.yml` | push 到 `main`（代码/配置变更） | 构建镜像 → 推 GHCR → SSH 部署到服务器 |

**服务器部署流程**：登录 GHCR → 拉取 `ghcr.io/<你的账号>/flower-ai-agent:latest` → 写入 compose 配置 → `docker compose up -d` 重启 → 健康检查。

### 需要配置的 GitHub Secrets

在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret | 用途 | 必填 |
|---|---|---|
| `DEPLOY_HOST` | 服务器 IP/域名 | ✅（部署用） |
| `DEPLOY_USER` | SSH 用户名（如 `ubuntu`） | ✅ |
| `DEPLOY_SSH_KEY` | SSH 私钥（`-----BEGIN OPENSSH PRIVATE KEY-----` 全文） | ✅ |
| `DEPLOY_PORT` | SSH 端口（默认 22） | ✅ |

> `GITHUB_TOKEN` 无需配置，Actions 自动提供（用于登录 GHCR）。
>
> ⚠️ 模型 / OSS 的 API Key（`DASHSCOPE_*`、`OSS_*`）**不需要、也不应**配置为 GitHub Secrets——CI 测试全离线，部署时密钥只存在于服务器上的 `.env`（由 `env_file` 注入容器），避免密钥进入第三方平台。

## 🔑 获取 API Key

### 阿里云百炼大模型平台

1. 访问 https://dashscope.console.aliyun.com/
2. 注册/登录阿里云账号
3. 开通百炼大模型服务
4. 创建 API Key

### 阿里云 OSS

1. 访问 https://oss.console.aliyun.com/
2. 创建 Bucket
3. 获取 AccessKey

## 📝 知识库扩展

在 `knowledge/processed/` 目录下添加 JSON 文件：

```json
{
  "flowers": [
    {
      "name": "花卉名称",
      "family": "科",
      "genus": "属",
      "description": "描述",
      "care_tips": "养护建议"
    }
  ]
}
```

启动后端时会自动加载新添加的知识库文件。

## 🐛 常见问题

### Q: 启动时报错 "ModuleNotFoundError"

A: 确保已安装所有依赖：
```bash
pip install -r requirements.txt
```

### Q: 接口返回 401 / 前端提示鉴权失败

A: `.env` 中配置了 `API_TOKEN` 后，所有 `/api/*` 请求必须携带 `Authorization: Bearer <token>`。前端会自动附带；curl 测试需手动加请求头：
```bash
curl -H "Authorization: Bearer your_token" "http://localhost:8000/api/flower/knowledge/list"
```

### Q: 无法连接到后端服务

A: 确保后端服务已启动，默认地址为 http://localhost:8000

### Q: 图片识别失败

A: 检查 DASHSCOPE_API_KEY 是否正确配置

### Q: 语音识别失败

A: 按部署环境排查：

1. **本地能用、部署到服务器后用不了（最常见）**：浏览器录音（`getUserMedia`）只在**安全上下文**可用，即 `https://` 或 `http://localhost`。直接访问 `http://服务器IP:8501` 时麦克风权限不可用，录音按钮点了没反应。**必须给站点配 HTTPS**（Caddy / Nginx + certbot / Cloudflare 均可），反代时记得保留 WebSocket 升级头（Streamlit SSE 依赖）。
2. **换浏览器 / 手机后失败**：浏览器录音格式因浏览器而异（Chrome/Firefox/Edge=webm/opus，Safari=mp4/aac），前端会把真实格式上报后端，后端用 ffmpeg 统一转 16k 单声道 wav 再识别。**服务器 Docker 镜像需安装 ffmpeg**（见 Dockerfile），否则退回按原格式直送（Paraformer 也支持部分压缩格式）。
3. 检查 DASHSCOPE_API_KEY 是否正确配置（与图片识别共用同一 Key）。

### Q: OSS 上传失败

A: 检查 OSS 配置是否正确，确保 Bucket 权限已设置；未配置 OSS 时系统自动使用 base64 模式，不影响使用

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 👨‍💻 作者

**何胤霖 (Yinlin He)**

- 本项目为个人独立开发项目，从需求分析、后端架构（FastAPI + LangChain + RAG + Agent）到前端 UI（Streamlit）全栈实现
- 项目亮点：多模态输入（图片识别 / 语音 / 文字）、SSE 流式对话、SQLite 会话持久化（含图片）、向量知识库管理、API Token 鉴权、GitHub Actions 自动部署、pytest 全离线自动化测试

如有问题或合作意向，欢迎通过 Issue 联系。
