"use client";

import { RefreshCw, ServerCog } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { listLlmLogs } from "@/lib/api";
import type { LlmCallLog } from "@/types";

const statusLabels: Record<LlmCallLog["status"], string> = {
  success: "成功",
  skipped: "跳过",
  failed: "失败"
};

const modeLabels: Record<LlmCallLog["mode"], string> = {
  model: "模型",
  extractive: "兜底"
};

export function LlmLogsPanel() {
  const [logs, setLogs] = useState<LlmCallLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setLogs(await listLlmLogs());
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载调用日志");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">最近调用</h2>
        </div>
        <button className="icon-action" title="刷新" type="button" onClick={() => void refresh()}>
          <RefreshCw size={17} />
        </button>
      </div>
      <div className="panel-body">
        {error ? <p className="alert">{error}</p> : null}

        {isLoading ? (
          <div className="log-list">
            <div className="skeleton" />
            <div className="skeleton" />
            <div className="skeleton" />
          </div>
        ) : null}

        {!isLoading && logs.length === 0 ? (
          <div className="empty-state">
            <ServerCog size={34} />
            <strong>暂无调用日志</strong>
          </div>
        ) : null}

        {!isLoading && logs.length > 0 ? (
          <div className="log-list">
            {logs.map((log) => (
              <article className="log-row" key={log.id}>
                <div className="log-row-main">
                  <div className="log-title-line">
                    <span className={`log-status ${log.status}`}>
                      {statusLabels[log.status]}
                    </span>
                    <strong>{log.question_preview}</strong>
                  </div>
                  <div className="log-meta">
                    <span>{formatDate(log.created_at)}</span>
                    <span>{modeLabels[log.mode]}</span>
                    <span>{log.provider}</span>
                    <span>{log.latency_ms} ms</span>
                    <span>{log.total_tokens} tokens</span>
                    <span>{formatCost(log.estimated_cost_usd)}</span>
                    {log.cache_hit ? <span>缓存命中</span> : null}
                    <span>{log.citation_count} 引用</span>
                  </div>
                  {log.error ? <p className="log-error">{log.error}</p> : null}
                </div>
                <div className="log-model">{log.model}</div>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function formatCost(value: number) {
  if (value <= 0) return "$0";
  return `$${value.toFixed(6)}`;
}
