# 🌸 花卉识别 AI Agent - API 接口文档

> 👨‍💻 作者：何胤霖 (Yinlin He)

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API 文档**: `http://localhost:8000/docs` (Swagger UI)
- **数据格式**: JSON

## 接口列表

### 1. 聊天接口

#### 1.1 发送消息

**POST** `/api/chat/send`

发送聊天消息给 AI 助手。

**请求参数：**

```json
{
  "message": "这是什么花？",
  "session_id": "session_123",
  "image_url": "https://example.com/flower.jpg"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户消息 |
| session_id | string | 否 | 会话ID，不传则自动生成 |
| image_url | string | 否 | 图片URL |

**响应示例：**

```json
{
  "success": true,
  "message": "这是一朵玫瑰花...",
  "session_id": "session_123",
  "image_url": "https://example.com/flower.jpg",
  "timestamp": "2024-01-01T12:00:00"
}
```

#### 1.2 获取聊天历史

**GET** `/api/chat/history/{session_id}`

获取指定会话的聊天历史。

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话ID |

**响应示例：**

```json
{
  "success": true,
  "session_id": "session_123",
  "messages": [
    {
      "role": "user",
      "content": "这是什么花？"
    },
    {
      "role": "assistant",
      "content": "这是一朵玫瑰花..."
    }
  ],
  "total": 2
}
```

#### 1.3 清除聊天历史

**DELETE** `/api/chat/history/{session_id}`

清除指定会话的聊天历史。

**响应示例：**

```json
{
  "success": true,
  "message": "聊天历史已清除"
}
```

#### 1.4 测试 Agent

**POST** `/api/chat/test`

测试 Agent 是否正常工作。

**响应示例：**

```json
{
  "success": true,
  "message": "Agent 测试成功",
  "response": {
    "success": true,
    "message": "你好！我是花卉识别 AI 助手...",
    "session_id": "test_session"
  }
}
```

---

### 2. 花卉识别接口

#### 2.1 上传图片识别

**POST** `/api/flower/recognize`

上传花卉图片进行识别。

**请求参数：**

使用 `multipart/form-data` 格式：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| image | file | 是 | 图片文件 |
| session_id | string | 否 | 会话ID |

**请求示例：**

```bash
curl -X POST "http://localhost:8000/api/flower/recognize" \
  -F "image=@flower.jpg" \
  -F "session_id=session_123"
```

**响应示例：**

```json
{
  "success": true,
  "image_url": "https://oss.xxx.com/flower-images/2024/01/01/xxx.jpg",
  "flowers": [
    {
      "name": "玫瑰",
      "probability": 0.95,
      "family": "蔷薇科",
      "genus": "蔷薇属",
      "characteristics": "落叶灌木，茎密生锐刺",
      "habitat": "温带地区",
      "flowering_period": "5-6月",
      "language": "爱情、美丽",
      "origin": "中国"
    }
  ],
  "message": "识别成功",
  "raw_response": "..."
}
```

#### 2.2 通过 URL 识别

**POST** `/api/flower/recognize-url`

通过图片 URL 进行识别。

**请求参数：**

```json
{
  "image_url": "https://example.com/flower.jpg"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| image_url | string | 是 | 图片URL |

**响应示例：**

同 2.1 响应格式。

---

### 3. 知识库接口

#### 3.1 搜索花卉知识

**GET** `/api/flower/knowledge/search`

搜索花卉知识库。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | 是 | 搜索查询 |
| flower_name | string | 否 | 花卉名称（精确查询） |
| top_k | int | 否 | 返回数量，默认3 |

**请求示例：**

```bash
curl "http://localhost:8000/api/flower/knowledge/search?query=玫瑰养护&top_k=5"
```

**响应示例：**

```json
{
  "success": true,
  "query": "玫瑰养护",
  "results": [
    {
      "content": "花卉名称：玫瑰\n科：蔷薇科\n养护建议：...",
      "metadata": {
        "flower_name": "玫瑰",
        "source": "flowers_database.json"
      },
      "score": 0.85
    }
  ],
  "total": 1
}
```

#### 3.2 添加花卉知识

**POST** `/api/flower/knowledge/add`

添加新的花卉知识到知识库。

**请求参数：**

```json
{
  "name": "新花卉名称",
  "family": "科",
  "genus": "属",
  "description": "描述",
  "care_tips": "养护建议"
}
```

**响应示例：**

```json
{
  "success": true,
  "message": "花卉知识添加成功"
}
```

---

### 4. 系统接口

#### 4.1 根路径

**GET** `/`

返回欢迎信息。

**响应示例：**

```json
{
  "message": "欢迎使用花卉识别 AI Agent",
  "version": "1.0.0",
  "docs": "/docs",
  "endpoints": {
    "chat": "/api/chat/send",
    "recognize": "/api/flower/recognize",
    "knowledge_search": "/api/flower/knowledge/search"
  }
}
```

#### 4.2 健康检查

**GET** `/health`

检查服务健康状态。

**响应示例：**

```json
{
  "status": "healthy",
  "service": "flower-ai-agent"
}
```

---

## 错误处理

所有接口在出错时返回以下格式：

```json
{
  "success": false,
  "error": "错误信息",
  "detail": "详细错误描述"
}
```

### 常见错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 使用示例

### Python 示例

```python
import requests

# 发送聊天消息
response = requests.post(
    "http://localhost:8000/api/chat/send",
    json={
        "message": "玫瑰怎么养护？",
        "session_id": "my_session"
    }
)
print(response.json())

# 上传图片识别
with open("flower.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/flower/recognize",
        files={"image": f}
    )
print(response.json())

# 搜索知识库
response = requests.get(
    "http://localhost:8000/api/flower/knowledge/search",
    params={"query": "兰花养护", "top_k": 5}
)
print(response.json())
```

### cURL 示例

```bash
# 发送聊天消息
curl -X POST "http://localhost:8000/api/chat/send" \
  -H "Content-Type: application/json" \
  -d '{"message": "这是什么花？", "session_id": "test"}'

# 上传图片识别
curl -X POST "http://localhost:8000/api/flower/recognize" \
  -F "image=@flower.jpg"

# 搜索知识库
curl "http://localhost:8000/api/flower/knowledge/search?query=菊花花语"
```

---

## 注意事项

1. **图片大小限制**: 建议图片大小不超过 10MB
2. **支持的图片格式**: JPG, PNG, WebP, GIF
3. **会话管理**: 会话ID用于维护对话上下文，不传则自动生成
4. **并发限制**: 无特殊限制，但建议控制并发量以保证服务质量
