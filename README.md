# PaperMind

PaperMind 是一个面向简历项目和作品集展示的 AI 论文/文档阅读助手。它的目标不是只做一个“套壳聊天框”，而是完整覆盖文档上传、文本解析、片段检索、基于引用的问答和摘要展示这条 AI 应用落地链路。

## 当前已实现

- 上传 Markdown、TXT、PDF 文档
- 解析文档正文并切分为可检索片段
- 展示文档元数据、摘要和原文片段
- 针对单篇文档进行问答
- 返回带引用片段的回答
- 未配置模型 API Key 时，自动使用基于原文片段的抽取式回答兜底
- 预留 OpenAI-compatible 模型接口，方便后续接入真实大模型

## 技术栈

- 前端：Next.js、React、TypeScript
- 后端：FastAPI、Python
- 存储：本地 JSON 文件，适合第一版 MVP 演示
- 文档解析：pypdf、文本解析器
- AI 接入：OpenAI-compatible Chat Completions API

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

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

如果暂时没有模型 Key，可以保持 `OPENAI_API_KEY` 为空。系统会自动使用抽取式回答兜底，仍然可以演示上传、解析、检索和引用展示。

## 接入大模型

如果要接入真实模型，在 `.env` 中填写：

```bash
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

只要服务兼容 OpenAI `/chat/completions` 接口，也可以把 `OPENAI_BASE_URL` 改成其他供应商地址。

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

## 示例文档

可以用下面这个示例文件测试上传和问答：

```text
samples/rag-notes.md
```

示例问题：

```text
为什么需要引用溯源？
```

## 简历写法参考

```text
独立开发 PaperMind AI 文档阅读平台，基于 Next.js、TypeScript、FastAPI 和 Python 实现文档上传、文本解析、分块检索、基于引用的问答和摘要展示。封装 OpenAI-compatible 模型调用层，并在未配置模型时提供基于原文片段的兜底回答，提升系统可演示性和稳定性。
```

后续可以继续扩展为：

- SQLite/PostgreSQL 持久化存储
- 向量数据库和语义检索
- 流式回答
- 摘要、提纲、关键词生成
- 笔记导出
- 文档处理异步队列
- 模型调用日志和成本统计
