# 🌸 花卉识别 AI Agent - 部署指南

> 👨‍💻 作者：何胤霖 (Yinlin He)

## 目录

1. [环境要求](#环境要求)
2. [本地开发部署](#本地开发部署)
3. [Docker 部署](#docker-部署)
4. [云服务器部署](#云服务器部署)
5. [阿里云函数计算部署](#阿里云函数计算部署)
6. [常见问题](#常见问题)

---

## 环境要求

### Python 环境
- Python 3.11+
- pip 22.0+

### 系统要求
- 操作系统：Windows 10+, macOS 10.15+, Ubuntu 20.04+
- 内存：建议 4GB+
- 磁盘空间：建议 2GB+

### 云服务
- 阿里云百炼大模型平台账号
- 阿里云 OSS 服务
- 阿里云 DashScope API Key

---

## 本地开发部署

### 1. 克隆项目

```bash
cd flower-ai-agent
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
DASHSCOPE_API_KEY=your_api_key
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_BUCKET_NAME=your_bucket_name
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

### 5. 启动后端

```bash
python run_backend.py
```

### 6. 启动前端

```bash
python run_frontend.py
```

### 7. 访问应用

- 前端界面：http://localhost:8501
- API 文档：http://localhost:8000/docs

---

## Docker 部署

### 1. 创建 Dockerfile

在项目根目录创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000 8501

# 启动脚本
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
```

### 2. 创建 docker-entrypoint.sh

```bash
#!/bin/bash

# 启动后端
python run_backend.py &

# 启动前端
python run_frontend.py &

# 等待所有后台进程
wait
```

### 3. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  flower-ai-agent:
    build: .
    ports:
      - "8000:8000"
      - "8501:8501"
    env_file:
      - .env
    volumes:
      - ./knowledge:/app/knowledge
      - ./data:/app/data
    restart: unless-stopped
```

### 4. 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 云服务器部署

### 1. 服务器准备

推荐配置：
- CPU: 2核+
- 内存: 4GB+
- 系统: Ubuntu 22.04 LTS

### 2. 安装依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python
sudo apt install python3.11 python3.11-venv python3-pip -y

# 安装 Nginx
sudo apt install nginx -y
```

### 3. 部署项目

```bash
# 克隆项目
cd /opt
git clone <repository_url> flower-ai-agent
cd flower-ai-agent

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置
```

### 4. 配置 Systemd 服务

创建 `/etc/systemd/system/flower-backend.service`：

```ini
[Unit]
Description=Flower AI Agent Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/flower-ai-agent
Environment="PATH=/opt/flower-ai-agent/venv/bin"
ExecStart=/opt/flower-ai-agent/venv/bin/python run_backend.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

创建 `/etc/systemd/system/flower-frontend.service`：

```ini
[Unit]
Description=Flower AI Agent Frontend
After=network.target flower-backend.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/flower-ai-agent
Environment="PATH=/opt/flower-ai-agent/venv/bin"
ExecStart=/opt/flower-ai-agent/venv/bin/python run_frontend.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 5. 启动服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start flower-backend
sudo systemctl start flower-frontend

# 设置开机自启
sudo systemctl enable flower-backend
sudo systemctl enable flower-frontend

# 查看状态
sudo systemctl status flower-backend
sudo systemctl status flower-frontend
```

### 6. 配置 Nginx

创建 `/etc/nginx/sites-available/flower-ai-agent`：

```nginx
server {
    listen 80;
    server_name your_domain.com;

    # 前端
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/flower-ai-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 阿里云函数计算部署

### 1. 安装 Serverless Devs

```bash
npm install -g @serverless-devs/s
```

### 2. 创建 s.yaml

```yaml
edition: 3.0.0
name: flower-ai-agent
access: "default"

vars:
  region: "cn-hangzhou"

resources:
  backend:
    component: fc3
    props:
      region: ${vars.region}
      functionName: "flower-backend"
      runtime: "python3.11"
      handler: "backend.main.handler"
      timeout: 60
      memorySize: 1024
      code: "./"
      environmentVariables:
        DASHSCOPE_API_KEY: "{{DASHSCOPE_API_KEY}}"
```

### 3. 部署

```bash
s deploy
```

---

## 常见问题

### Q: 端口被占用怎么办？

A: 修改 `.env` 文件中的端口配置：

```env
APP_PORT=8001
```

或者杀掉占用端口的进程：

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8000
kill -9 <PID>
```

### Q: 依赖安装失败？

A: 尝试以下方法：

```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 单独安装问题依赖
pip install faiss-cpu --no-cache-dir
```

### Q: ChromaDB 初始化失败？

A: 检查目录权限：

```bash
mkdir -p data/chroma_db
chmod 755 data/chroma_db
```

### Q: OSS 上传失败？

A: 检查以下配置：
1. OSS Bucket 是否存在
2. AccessKey 是否正确
3. Bucket 权限是否设置为公共读

### Q: 模型调用超时？

A: 检查网络连接和 API Key 是否有效。可以增加超时时间：

```python
# 在 config.py 中添加
API_TIMEOUT = 60
```

---

## 性能优化

### 1. 启用缓存

在 `.env` 中启用 Redis 缓存：

```env
REDIS_URL=redis://localhost:6379/0
```

### 2. 使用 Gunicorn

安装 Gunicorn：

```bash
pip install gunicorn
```

修改启动命令：

```bash
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 3. 配置 CDN

将静态资源和图片通过阿里云 CDN 加速。

---

## 监控和日志

### 查看日志

```bash
# 后端日志
tail -f logs/backend.log

# 前端日志
tail -f logs/frontend.log

# Systemd 日志
journalctl -u flower-backend -f
```

### 配置日志轮转

创建 `/etc/logrotate.d/flower-ai-agent`：

```
/opt/flower-ai-agent/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

---

## 备份和恢复

### 备份数据

```bash
# 备份知识库
tar -czf knowledge_backup.tar.gz knowledge/

# 备份向量数据库
tar -czf chroma_backup.tar.gz data/chroma_db/

# 备份配置
cp .env .env.backup
```

### 恢复数据

```bash
# 恢复知识库
tar -xzf knowledge_backup.tar.gz

# 恢复向量数据库
tar -xzf chroma_backup.tar.gz

# 恢复配置
cp .env.backup .env
```
