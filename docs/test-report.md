# PaperMind 测试报告

报告日期：2026-09-19

## 测试范围

当前测试覆盖四类能力：

- 后端单元和接口测试：文档上传、解析、RAG 检索、模型调用、工程化能力、Agent 工具。
- 后端静态检查：ruff 代码风格和基础质量检查。
- 前端生产构建：Next.js 类型检查、构建和页面生成。
- 端到端测试：真实浏览器中上传文档、进入阅读页、执行 Agent 工具、基于文档问答和异常上传提示。

## 测试命令和结果

| 命令 | 结果 | 说明 |
| --- | --- | --- |
| `npm run test:api` | 43 passed | 后端 pytest 全部通过 |
| `npm run lint:api` | passed | ruff 检查通过 |
| `npm run build:web` | passed | Next.js 构建通过 |
| `npm run test:e2e` | 2 passed | Playwright E2E 全部通过 |
| `git diff --check` | passed | 无空白错误，仅 Windows 换行提示 |
| 密钥扫描 | passed | 未发现提交中的 `sk-...` 密钥 |

## 后端测试矩阵

| 测试文件 | 覆盖内容 |
| --- | --- |
| `test_agent_tools.py` | 工具注册表、Agent 工具接口、Markdown 工具输出、未处理文档拒绝执行 |
| `test_analyzer.py` | 本地摘要、关键词、提纲和建议追问 |
| `test_conversations.py` | 问答会话、重复上传、大文件、模型超时、缓存边界、多轮历史、笔记 |
| `test_embeddings.py` | 本地向量生成和相似度 |
| `test_engineering.py` | 统一错误返回、请求 ID、限流 |
| `test_llm.py` | Prompt 结构、Token 估算、长历史压缩、结构化洞察解析 |
| `test_processing.py` | 文档处理任务 |
| `test_queue.py` | Redis 队列封装 |
| `test_retrieval.py` | 混合检索、引用片段、无依据回答 |
| `test_runtime.py` | 模型状态、存储持久化、删除级联 |
| `test_streaming.py` | 流式问答、流式兜底 |

## E2E 场景

### 场景 1：上传文档、执行 Agent 工具、文档问答

流程：

1. 打开首页。
2. 上传 Markdown 文档。
3. 进入阅读页。
4. 校验原文片段可见。
5. 执行 Agent 工具“复习题”。
6. 校验工具输出包含文档内容。
7. 输入问题并提交。
8. 校验回答和引用片段可见。

覆盖能力：

- 前端上传组件
- 后端解析和切分
- 阅读页渲染
- Agent 工具接口和面板
- 流式问答
- 引用展示

### 场景 2：异常上传提示

流程：

1. 上传不支持的 `.exe` 文件。
2. 校验页面出现错误提示。

覆盖能力：

- 文件扩展名校验
- 统一错误返回
- 前端错误提示

## 阶段六边界测试覆盖

已补齐的边界场景：

- 文件过大：超过 `AI_MAX_UPLOAD_MB` 返回 413。
- 模型超时：自动降级为本地抽取式回答，并写入失败日志。
- 连续快速提问：同一会话保留完整 user/assistant 消息序列。
- 多轮上下文过长：调用模型前压缩较早历史。
- 缓存边界：已有会话内相同问题不会误用独立问题缓存。
- 文件格式错误：E2E 验证前端错误提示。

## 已知说明

- `npm run lint:web` 当前会触发 Next.js 的交互式 ESLint 配置提示，不适合非交互式 CI。当前前端质量以 `npm run build:web` 的类型检查和构建结果作为主要验证。后续可迁移到 ESLint CLI。
- Playwright 输出中可能出现 Next.js dev server 的跨源资源提示，这是本地 E2E 端口配置导致的开发环境提示，不影响测试结果。

## 后续测试建议

- 增加 Docker Compose 模式下的 API + worker 集成测试。
- 增加真实 PDF 样例解析测试。
- 增加 Agent 工具 Markdown 下载的浏览器断言。
- 增加模型接口 429/500 重试路径测试。
- 增加删除文档后前端列表刷新和详情页 404 的 E2E。
