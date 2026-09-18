import type { DocumentStatus } from "@/types";

const labels: Record<DocumentStatus, string> = {
  ready: "已就绪",
  failed: "失败",
  processing: "处理中"
};

export function StatusPill({ status }: { status: DocumentStatus }) {
  return <span className={`status-pill ${status}`}>{labels[status]}</span>;
}
