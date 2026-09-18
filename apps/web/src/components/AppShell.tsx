"use client";

import Link from "next/link";
import { BookOpen, Database, FileText, Home, Network } from "lucide-react";
import { useEffect, useState } from "react";
import { getHealth } from "@/lib/api";

type AppShellProps = {
  children: React.ReactNode;
  active?: "library" | "reader";
};

export function AppShell({ children, active = "library" }: AppShellProps) {
  const [online, setOnline] = useState(false);

  useEffect(() => {
    getHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/">
          <span className="brand-mark" aria-hidden="true">
            <BookOpen size={22} />
          </span>
          <span>
            <p className="brand-title">PaperMind</p>
            <p className="brand-subtitle">AI 文档阅读</p>
          </span>
        </Link>

        <nav className="nav-list" aria-label="主导航">
          <Link className={`nav-item ${active === "library" ? "is-active" : ""}`} href="/">
            <Home size={17} />
            文档库
          </Link>
          <span className={`nav-item ${active === "reader" ? "is-active" : ""}`}>
            <FileText size={17} />
            阅读器
          </span>
          <span className="nav-item">
            <Network size={17} />
            工作流
          </span>
          <span className="nav-item">
            <Database size={17} />
            调用日志
          </span>
        </nav>

        <div className="sidebar-footer">
          <div className="status-line">
            <span>AI Service</span>
            <span
              className={`status-dot ${online ? "is-online" : ""}`}
              title={online ? "online" : "offline"}
            />
          </div>
          <div className="status-line">
            <span>Storage</span>
            <span>Local JSON</span>
          </div>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
