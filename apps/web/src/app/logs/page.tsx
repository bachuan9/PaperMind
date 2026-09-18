import { AppShell } from "@/components/AppShell";
import { LlmLogsPanel } from "@/components/LlmLogsPanel";

export default function LogsPage() {
  return (
    <AppShell active="logs">
      <div className="topbar">
        <div>
          <p className="page-kicker">Observability</p>
          <h1 className="page-title">调用日志</h1>
          <p className="page-subtitle">
            查看最近的 DeepSeek 调用、兜底回答和失败原因，快速判断问答链路是否正常。
          </p>
        </div>
      </div>
      <LlmLogsPanel />
    </AppShell>
  );
}
