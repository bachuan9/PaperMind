"use client";

import Link from "next/link";
import { FileSearch, FileText, Trash2 } from "lucide-react";
import { deleteDocument } from "@/lib/api";
import type { DocumentSummary } from "@/types";
import { StatusPill } from "./StatusPill";

type DocumentListProps = {
  documents: DocumentSummary[];
  onDeleted: (id: string) => void;
};

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export function DocumentList({ documents, onDeleted }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <div className="empty-state">
        <FileSearch size={34} />
        <strong>暂无文档</strong>
      </div>
    );
  }

  return (
    <div className="doc-list">
      {documents.map((document) => (
        <article className="doc-row" key={document.id}>
          <Link className="doc-main" href={`/documents/${document.id}`}>
            <div className="doc-title-line">
              <FileText size={17} color="var(--accent)" />
              <h3 className="doc-title">{document.title}</h3>
            </div>
            <div className="doc-meta">
              <StatusPill status={document.status} />
              <span>{formatBytes(document.size_bytes)}</span>
              <span>{document.page_count || 1} 页</span>
              <span>{document.chunk_count} 段</span>
            </div>
            {document.summary ? (
              <p className="doc-summary">{document.summary}</p>
            ) : null}
          </Link>
          <button
            className="icon-action"
            type="button"
            title="删除文档"
            onClick={async () => {
              await deleteDocument(document.id);
              onDeleted(document.id);
            }}
          >
            <Trash2 size={17} />
          </button>
        </article>
      ))}
    </div>
  );
}
