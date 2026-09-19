# PaperMind

PaperMind 是一个面向简历项目和作品集展示的 AI 论文/文档阅读助手。它的目标不是只做一个“套壳聊天框”，而是完整覆盖文档上传、文本解析、片段检索、基于引用的问答和摘要展示这条 AI 应用落地链路。

## 当前已实现

- 上传 Markdown、TXT、PDF 文档
- 解析文档正文并切分为可检索片段
- 为文档片段生成本地向量索引，问答检索结合关键词和向量相似度
- 展示文档元数据、摘要和原文片段
- 针对单篇文档进行问答
- 支持单篇文档的多轮对话历史，历史消息会作为模型上下文传入
- 对话历史过长时会自动裁剪最近消息，并压缩较早历史为摘要
- 返回带引用片段的回答
- 问答输出固定为“直接回答 / 文档依据 / 边界和不确定性”结构
- 生成文档洞察，包括短摘要、详细摘要、关键词、提纲和建议追问
- 配置模型后，文档洞察会优先使用 DeepSeek 结构化 JSON 输出，并通过 Schema 校验
- 支持保存用户自己的阅读笔记
- 未配置模型 API Key 时，自动使用基于原文片段的抽取式回答兜底
- 模型洞察输出异常或校验失败时，会自动回退到本地启发式分析
- 预留 SiliconFlow DeepSeek 模型接口，方便后续接入真实大模型
- 展示 DeepSeek 配置状态、回答模式和模型调用失败原因
- 记录最近的模型调用日志，便于排查模型回退原因
- 提供调用日志页面，可查看最近调用状态、耗时、模型和错误信息
- 后端提供统一错误返回、请求 ID、请求日志和基础限流
- 模型请求支持超时配置和失败重试
- 上传文件大小限制支持环境变量配置
- 支持流式问答输出，DeepSeek 生成过程会实时显示在页面中
- 支持一键导出 Markdown 阅读笔记，包含摘要、关键词、提纲、建议追问和关键摘录
- 提供 Agent 工具面板，可对当前文档执行摘要、关键词、复习题、Markdown 笔记和汇报大纲生成
- 后端封装工具注册表和统一工具执行接口，工具结果同时返回 Markdown 内容和结构化 JSON 数据

## 技术栈

- 前端：Next.js、React、TypeScript
- 后端：FastAPI、Python
- 存储：本地 JSON 文件，适合第一版 MVP 演示
- 文档解析：pypdf、文本解析器
- 检索：本地哈希向量索引、关键词匹配和余弦相似度
- AI 接入：SiliconFlow DeepSeek Chat Completions API
- 文档洞察：DeepSeek 结构化输出 + Pydantic Schema 校验，本地启发式分析兜底
- Agent 工具：FastAPI 工具注册表、结构化工具结果、前端工具调用面板

## 项目结构

```text
papermind/
|-- apps/
|   `-- web/                  # Next.js 前端
|-- services/
|   `-- ai-service/           # FastAPI AI 服务
|-- samples/                  # 示例文档
|-- docker-compose.yml
|-- pytest.ini
|-- .env.example              # 环境变量模板，可以提交
|-- .env                      # 本地环境变量，不提交
`-- README.md
```

## 项目文档

- [系统架构](docs/architecture.md)
- [数据结构设计](docs/database-design.md)
- [API 文档](docs/api-reference.md)
- [测试报告](docs/test-report.md)
- [简历项目描述](docs/resume-project-description.md)
- [启动和关闭命令](docs/frontend-terminal-commands.md)
- [七阶段开发计划](docs/development-plan.md)

## 本地启动

安装前端依赖：

```bash
npm install
```

创建并激活 Python 虚拟环境：

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r services/ai-service/requirements.txt
```

启动 AI 服务：

```bash
npm run dev:api
```

再打开另一个终端启动前端：

```bash
npm run dev:web
```

访问前端：

```text
http://localhost:3000
```

API 服务地址：

```text
http://127.0.0.1:8000
```

## 环境变量

项目根目录下提供两个环境变量文件：

- `.env.example`：模板文件，可以提交到 Git。
- `.env`：本地开发配置，已经被 `.gitignore` 忽略，不建议提交。

默认配置如下：

```bash
NEXT_PUBLIC_AI_SERVICE_URL=http://localhost:8000

AI_SERVICE_HOST=0.0.0.0
AI_SERVICE_PORT=8000
AI_DATA_DIR=./data
AI_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
AI_MAX_UPLOAD_MB=25
AI_PARSE_MAX_ATTEMPTS=2
AI_QUEUE_BACKEND=inline
AI_REDIS_URL=redis://localhost:6379/0
AI_REDIS_QUEUE_NAME=papermind:document-processing
AI_QUEUE_POLL_TIMEOUT_SECONDS=5
AI_RATE_LIMIT_PER_MINUTE=120
AI_REQUEST_LOG_ENABLED=true

DEEPSEEK_BASE_URL=https://api.siliconflow.cn/v1
DEEPSEEK_API_KEY=
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
LLM_INPUT_PRICE_PER_1M_TOKENS=0
LLM_OUTPUT_PRICE_PER_1M_TOKENS=0
```

如果暂时没有模型 Key，可以保持 `DEEPSEEK_API_KEY` 为空。系统会自动使用抽取式回答兜底，仍然可以演示上传、解析、检索和引用展示。

## 接入大模型

如果要接入真实模型，在 `.env` 中填写：

```bash
DEEPSEEK_BASE_URL=https://api.siliconflow.cn/v1
DEEPSEEK_API_KEY=your_key
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
```

当前项目默认使用 SiliconFlow 的 `/chat/completions` 接口和 DeepSeek 模型。

修改 `.env` 后，需要重启 AI 服务。

## 验证命令

运行后端单测：

```bash
npm run test:api
```

检查后端代码风格：

```bash
npm run lint:api
```

构建前端：

```bash
npm run build:web
```

运行端到端测试：
```bash
npm run test:e2e
```

## 示例文档

可以用下面这个示例文件测试上传和问答：

```text
samples/rag-notes.md
```

示例问题：

```text
为什么需要引用溯源？
```

阅读页会自动生成文档洞察，包括摘要、关键词、提纲和建议追问。短问题如“什么意思”会自动回退到当前文档上下文，不会因为没有关键词重合就直接返回空结果。

## 简历写法参考

```text
独立开发 PaperMind AI 文档阅读平台，基于 Next.js、TypeScript、FastAPI 和 Python 实现文档上传、文本解析、本地向量索引、混合检索、基于引用的多轮问答、文档洞察、流式回答、Markdown 笔记导出和 Agent 工具调用。封装 SiliconFlow DeepSeek 模型调用层，并在未配置模型时提供基于原文片段的兜底回答；后端提供工具注册表和统一执行接口，支持摘要、关键词、复习题、学习卡片和汇报大纲等作品集能力。
```

后续可以继续扩展为：

- SQLite/PostgreSQL 持久化存储
- 外部向量数据库和可替换 Embedding 模型
- 文档处理异步队列
- 模型调用成本统计
## 阶段六工程化进展

- 文档上传增加内容哈希校验，重复上传同一文件时直接返回已有文档，避免重复解析和向量化。
- 问答增加结果缓存，相同文档下的独立相同问题会命中缓存，并继续写入当前对话历史。
- 模型调用日志增加 Token 用量、估算费用和缓存命中标记，便于排查调用成本。
- 费用估算由 `LLM_INPUT_PRICE_PER_1M_TOKENS` 和 `LLM_OUTPUT_PRICE_PER_1M_TOKENS` 控制，默认值为 0。
- 文档解析会写入 `processing_jobs` 任务记录，并按 `AI_PARSE_MAX_ATTEMPTS` 自动重试。
- Docker Compose 模式支持 Redis 异步任务队列，`ai-worker` 会消费文档处理任务。
阶段六补充：已增加 Playwright 端到端测试，覆盖上传文档、进入阅读页和基于文档提问。
