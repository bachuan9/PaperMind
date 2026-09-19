# PaperMind API 文档

默认 API 地址：

```text
http://127.0.0.1:8000
```

前端通过环境变量 `NEXT_PUBLIC_AI_SERVICE_URL` 指向该服务。

## 通用错误格式

所有 HTTP 异常会统一返回：

```json
{
  "detail": "错误说明",
  "error": {
    "code": "bad_request",
    "message": "错误说明",
    "request_id": "请求 ID"
  }
}
```

常见错误码：

| HTTP | error.code | 场景 |
| --- | --- | --- |
| 400 | `bad_request` | 文件类型错误、非法会话 |
| 404 | `not_found` | 文档或会话不存在 |
| 409 | `conflict` | 文档尚未解析完成 |
| 413 | `payload_too_large` | 上传文件超过大小限制 |
| 422 | `validation_error` | 请求体格式错误 |
| 429 | `rate_limited` | 请求过于频繁 |
| 500 | `internal_error` | 未捕获服务异常 |

## 健康检查

### `GET /health`

返回服务是否可用。

响应：

```json
{
  "status": "ok"
}
```

## 模型状态和日志

### `GET /model/status`

返回模型配置状态。

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `provider` | string | 模型服务商 |
| `model` | string | 模型名称 |
| `base_url` | string | API Base URL |
| `configured` | boolean | 是否配置 API Key |

### `GET /llm/logs`

返回最近的模型调用日志。

主要字段：

- `status`：`success`、`skipped`、`failed`
- `mode`：`model` 或 `extractive`
- `latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `estimated_cost_usd`
- `cache_hit`

## 文档

### `GET /documents`

返回文档列表。

### `POST /documents`

上传 PDF、Markdown 或 TXT 文档。

请求类型：`multipart/form-data`

字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `file` | file | 上传文件，支持 `.pdf`、`.md`、`.markdown`、`.txt` |

响应：`DocumentSummary`

处理逻辑：

1. 校验扩展名。
2. 校验空文件和大小限制。
3. 计算 SHA-256，重复上传时直接返回已有文档。
4. inline 模式下同步解析；Redis 模式下入队异步处理。

### `GET /documents/{document_id}`

返回文档详情，包括 chunks。

### `DELETE /documents/{document_id}`

删除文档以及相关向量、任务、会话、消息、笔记和缓存。

响应：

```json
{
  "ok": true
}
```

### `GET /documents/{document_id}/processing-jobs`

返回文档处理任务记录。

## 文档洞察

### `GET /documents/{document_id}/insights`

返回文档摘要、关键词、章节提纲和建议追问。

响应字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `summary` | string | 兼容字段，等同短摘要 |
| `short_summary` | string | 短摘要 |
| `detailed_summary` | string | 详细摘要 |
| `keywords` | string[] | 关键词 |
| `sections` | object[] | 章节标题和总结 |
| `suggested_questions` | string[] | 建议追问 |
| `mode` | string | `model` 或 `extractive` |

## Agent 工具

### `GET /agent-tools`

返回可用工具列表。

当前工具：

- `summarize_document`
- `extract_keywords`
- `generate_questions`
- `create_markdown_note`
- `export_outline`

### `POST /documents/{document_id}/agent-tools/run`

对指定文档执行工具。

请求：

```json
{
  "tool_name": "generate_questions"
}
```

响应：`AgentToolResult`

```json
{
  "tool_name": "generate_questions",
  "title": "复习题",
  "output_format": "markdown",
  "content": "# 文档标题 复习题\n...",
  "data": {
    "questions": ["问题 1"]
  },
  "citations": [
    {
      "chunk_id": "chunk id",
      "page_number": 1,
      "text": "引用片段",
      "score": 1
    }
  ],
  "created_at": "2026-09-19T00:00:00Z"
}
```

## 笔记

### `GET /documents/{document_id}/notes`

返回用户手写笔记。

### `POST /documents/{document_id}/notes`

创建阅读笔记。

请求：

```json
{
  "content": "需要重点复习引用溯源"
}
```

## 会话和问答

### `GET /documents/{document_id}/conversations`

返回文档下的对话列表。

### `GET /conversations/{conversation_id}/messages`

返回会话消息。

### `POST /documents/{document_id}/ask`

非流式文档问答。

请求：

```json
{
  "question": "为什么需要引用溯源？",
  "conversation_id": null
}
```

响应：`AskResponse`

关键字段：

- `answer`
- `citations`
- `conversation_id`
- `mode`
- `provider`
- `model`
- `fallback_reason`
- `cache_hit`

### `POST /documents/{document_id}/ask/stream`

流式文档问答。

响应类型：`application/x-ndjson`

事件格式：

```json
{"type":"meta","conversation_id":"...","mode":"model","citations":[]}
{"type":"token","token":"片段"}
{"type":"done","answer":"完整答案"}
```

## 本地调试示例

上传文档：

```bash
curl -F "file=@samples/rag-notes.md" http://127.0.0.1:8000/documents
```

运行 Agent 工具：

```bash
curl -X POST http://127.0.0.1:8000/documents/{document_id}/agent-tools/run ^
  -H "Content-Type: application/json" ^
  -d "{\"tool_name\":\"create_markdown_note\"}"
```

文档问答：

```bash
curl -X POST http://127.0.0.1:8000/documents/{document_id}/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"为什么需要引用溯源？\"}"
```
