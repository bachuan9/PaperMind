# 前后端终端命令

本文档记录 PaperMind 前端和后端的启动、关闭和排查命令，适用于 Windows PowerShell。

## 进入项目目录

```powershell
cd D:\PaperMind\papermind
```

## 推荐启动方式

本地开发需要同时启动后端和前端，建议开两个 PowerShell 终端。

终端 1 启动后端：

```powershell
cd D:\PaperMind\papermind
npm run dev:api
```

终端 2 启动前端：

```powershell
cd D:\PaperMind\papermind
npm run dev:web
```

浏览器访问：

```text
http://localhost:3000
```

## 启动前端

```powershell
npm run dev:web
```

启动成功后，终端会看到类似输出：

```text
Local: http://localhost:3000
Ready
```

浏览器访问：

```text
http://localhost:3000
```

## 启动后端

```powershell
npm run dev:api
```

启动成功后，终端会看到类似输出：

```text
Uvicorn running on http://0.0.0.0:8000
Application startup complete.
```

后端健康检查地址：

```text
http://127.0.0.1:8000/health
```

## 正常关闭前端

在运行前端的终端窗口里按：

```text
Ctrl + C
```

如果终端询问是否终止批处理任务，输入：

```text
Y
```

然后按回车。

## 正常关闭后端

在运行后端的终端窗口里按：

```text
Ctrl + C
```

如果终端询问是否终止批处理任务，输入：

```text
Y
```

然后按回车。

## 检查前端是否正在运行

```powershell
Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing
```

如果返回 `StatusCode: 200`，说明前端正在运行。

也可以检查 3000 端口：

```powershell
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue
```

## 检查后端是否正在运行

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
```

如果返回 `StatusCode: 200`，并且内容包含：

```json
{"status":"ok"}
```

说明后端正在运行。

也可以检查 8000 端口：

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

## 强制关闭占用 3000 端口的前端进程

如果忘记在哪个终端启动了前端，或者 3000 端口被旧进程占用，可以执行：

```powershell
Get-NetTCPConnection -LocalPort 3000 -State Listen |
  Select-Object -ExpandProperty OwningProcess |
  ForEach-Object { Stop-Process -Id $_ -Force }
```

执行后重新启动：

```powershell
npm run dev:web
```

## 强制关闭占用 8000 端口的后端进程

如果 8000 端口被旧的后端进程占用，可以执行：

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  Select-Object -ExpandProperty OwningProcess |
  ForEach-Object { Stop-Process -Id $_ -Force }
```

执行后重新启动：

```powershell
npm run dev:api
```

## 常见情况

如果网页打不开，优先确认前端是否启动：

```powershell
Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing
```

如果上传文档失败，通常不是前端问题，还需要确认后端是否启动：

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing
```

如果修改了 `.env`，需要重启后端才会生效：

```powershell
Ctrl + C
npm run dev:api
```
## Docker Compose 启动完整队列版

这个方式会同时启动前端、后端、Redis 和文档处理 worker：

```powershell
docker compose up --build
```

关闭：

```powershell
docker compose down
```

查看 worker 日志：

```powershell
docker compose logs -f ai-worker
```
