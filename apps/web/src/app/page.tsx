import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/components/Dashboard";

export default function Home() {
  return (
    <AppShell active="library">
      <div className="topbar">
        <div>
          <p className="page-kicker">Workspace</p>
          <h1 className="page-title">文档库</h1>
          <p className="page-subtitle">
            上传论文、产品文档或运营资料，围绕原文片段检索、阅读和提问。
          </p>
        </div>
      </div>
      <Dashboard />
    </AppShell>
  );
}
