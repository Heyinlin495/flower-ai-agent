# syntax=docker/dockerfile:1
# =============================================================================
# 花卉识别 AI Agent — 多阶段构建 Dockerfile
#   目标：镜像尽量小 · 构建尽量快 · 安全性好
#   - Python 3.12-slim 基础（比全量镜像小约 1GB）
#   - 依赖安装层缓存（requirements.txt 不变则不重装）
#   - 非 root 运行 + 只读根文件系统 + 不缓存 .pyc
# =============================================================================

# ── 阶段 1：依赖安装 ────────────────────────────────────────────────────────
# 独立阶段只为利用 Docker layer cache：requirements.txt 不变就不重装依赖
FROM python:3.12-slim AS deps

# 禁用 pip 缓存（小）· 固定编译路径（构建可复现）
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 只拷贝依赖清单 → 利用层缓存
COPY requirements.txt ./
# 分离编译与运行依赖：chromadb 等含原生扩展的包需要编译工具链，
# 安装完成后立即清除，避免留在最终镜像
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential gcc g++ \
    && pip install -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential gcc g++ \
    && rm -rf /var/lib/apt/lists/*


# ── 阶段 2：运行时 ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# 环境：UTF-8（中文正常显示）· 无 .pyc · 缓冲输出（日志实时）
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# 从依赖阶段复制已安装的 site-packages
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# 拷贝项目代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY knowledge/ ./knowledge/
COPY run_backend.py run_frontend.py ./

# ── 非 root 运行（安全）─────────────────────────────────────────────────────
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data /app/uploads /app/logs \
    && chown -R appuser:appuser /app
USER appuser

# 只读根文件系统（安全）：数据目录单独挂载可写卷
VOLUME ["/app/data", "/app/uploads", "/app/logs"]

EXPOSE 8000 8501

# 默认启动后端
CMD ["python", "run_backend.py"]
