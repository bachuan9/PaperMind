"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Download, FileText } from "lucide-react";
import { AskPanel } from "./AskPanel";
import { InsightPanel } from "./InsightPanel";
import { StatusPill } from "./StatusPill";
import { getDocumentInsights } from "@/lib/api";
import type { DocumentDetail, DocumentInsightResponse } from "@/types";

type DocumentWorkspaceProps = {
  document: DocumentDetail;
};

export function DocumentWorkspace({ document }: DocumentWorkspaceProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setExportError(null);
    try {
      const insights = await getDocumentInsights(document.id);
      const markdown = buildNotesMarkdown(document, insights);
      downloadMarkdown(markdown, `${sanitizeFileName(document.title)}-PaperMind笔记.md`);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "笔记导出失败");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <>
      <div className="topbar">
        <div>
          <p className="page-kicker">阅读器</p>
          <h1 className="page-title">{document.title}</h1>
          <p className="page-subtitle">{document.summary || document.filename}</p>
        </div>
        <div className="topbar-actions">
          <button
            className="secondary-action"
            disabled={isExporting}
            type="button"
            onClick={() => void handleExport()}
          >
            <Download size={17} />
            {isExporting ? "生成中" : "导出笔记"}
          </button>
          <Link className="secondary-action" href="/">
            <ArrowLeft size={17} />
            返回
          </Link>
        </div>
      </div>

      {exportError ? <p className="alert page-alert">{exportError}</p> : null}

      <div className="document-layout">
        <div className="reader">
          <InsightPanel documentId={document.id} />

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
        </div>

        <AskPanel documentId={document.id} />
      </div>
    </>
  );
}

function buildNotesMarkdown(
  document: DocumentDetail,
  insights: DocumentInsightResponse
) {
  const createdAt = new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date());
  const pageCount = document.page_count || 1;
  const keywords = insights.keywords.length
    ? insights.keywords.map((keyword) => `- ${keyword}`)
    : ["- 暂无关键词"];
  const sections = insights.sections.length
    ? insights.sections.flatMap((section, index) => [
        `${index + 1}. ${section.title}`,
        `   ${section.summary || "暂无摘要"}`
      ])
    : ["暂无提纲。"];
  const questions = insights.suggested_questions.length
    ? insights.suggested_questions.map((question) => `- ${question}`)
    : ["- 暂无建议追问"];
  const chunks = document.chunks.slice(0, 6).flatMap((chunk) => [
    `### 片段 ${chunk.index + 1}${chunk.page_number ? `（第 ${chunk.page_number} 页）` : ""}`,
    "",
    quoteBlock(trimForMarkdown(chunk.text, 650)),
    ""
  ]);

  return [
    `# ${document.title}`,
    "",
    `> 由 PaperMind 生成于 ${createdAt}`,
    "",
    "## 文档信息",
    `- 文件名：${document.filename}`,
    `- 页数：${pageCount}`,
    `- 片段数：${document.chunk_count}`,
    `- 阅读状态：${document.status}`,
    "",
    "## 摘要",
    insights.summary || document.summary || "暂无摘要。",
    "",
    "## 关键词",
    ...keywords,
    "",
    "## 提纲",
    ...sections,
    "",
    "## 建议追问",
    ...questions,
    "",
    "## 关键摘录",
    ...(chunks.length ? chunks : ["暂无摘录。"]),
    ""
  ].join("\n");
}

function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = filename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function sanitizeFileName(value: string) {
  const sanitized = value.replace(/[\\/:*?"<>|]/g, "-").trim();
  return sanitized.slice(0, 80) || "papermind-notes";
}

function trimForMarkdown(value: string, limit: number) {
  const text = value.replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, limit).trim()}...`;
}

function quoteBlock(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => `> ${line || " "}`)
    .join("\n");
}
