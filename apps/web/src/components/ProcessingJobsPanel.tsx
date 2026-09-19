"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { listProcessingJobs } from "@/lib/api";
import type { ProcessingJob } from "@/types";

type ProcessingJobsPanelProps = {
  documentId: string;
  active: boolean;
};

const statusLabels: Record<ProcessingJob["status"], string> = {
  queued: "等待中",
  processing: "处理中",
  succeeded: "已完成",
  failed: "失败"
};

export function ProcessingJobsPanel({
  documentId,
  active
}: ProcessingJobsPanelProps) {
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setJobs(await listProcessingJobs(documentId));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "处理任务加载失败");
    }
  }, [documentId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => {
      void refresh();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [active, refresh]);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2 className="panel-title">处理任务</h2>
        <button
          className="icon-action"
          title="刷新"
          type="button"
          onClick={() => void refresh()}
        >
          <RefreshCw size={17} />
        </button>
      </div>
      <div className="panel-body">
        {error ? <p className="alert">{error}</p> : null}
        <div className="job-list">
          {jobs.map((job) => (
            <article className="job-row" key={job.id}>
              <div>
                <strong>{statusLabels[job.status]}</strong>
                <p>
                  尝试 {job.attempts}/{job.max_attempts}
                </p>
              </div>
              {job.error ? <span>{job.error}</span> : null}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
