"use client";

import Link from "next/link";
import { ArrowLeft, FileText } from "lucide-react";
import { AskPanel } from "./AskPanel";
import { StatusPill } from "./StatusPill";
import type { DocumentDetail } from "@/types";

type DocumentWorkspaceProps = {
  document: DocumentDetail;
};

export function DocumentWorkspace({ document }: DocumentWorkspaceProps) {
  return (
    <>
      <div className="topbar">
        <div>
          <p className="page-kicker">阅读器</p>
          <h1 className="page-title">{document.title}</h1>
          <p className="page-subtitle">{document.summary || document.filename}</p>
        </div>
        <Link className="secondary-action" href="/">
          <ArrowLeft size={17} />
          返回
        </Link>
      </div>

      <div className="document-layout">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">原文片段</h2>
            </div>
            <StatusPill status={document.status} />
          </div>
          <div className="panel-body">
            <div className="reader">
              {document.chunks.map((chunk) => (
                <article className="chunk" key={chunk.id}>
                  <div className="chunk-header">
                    <span>片段 {chunk.index + 1}</span>
                    <span>{chunk.page_number ? `第 ${chunk.page_number} 页` : "正文"}</span>
                  </div>
                  <p className="chunk-text">{chunk.text}</p>
                </article>
              ))}
              {document.chunks.length === 0 ? (
                <div className="empty-state">
                  <FileText size={34} />
                  <strong>暂无可读片段</strong>
                </div>
              ) : null}
            </div>
          </div>
        </section>

        <AskPanel documentId={document.id} />
      </div>
    </>
  );
}
