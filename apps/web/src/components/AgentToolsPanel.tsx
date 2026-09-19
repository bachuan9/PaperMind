"use client";

import { Clipboard, Download, FileText, KeyRound, ListChecks, Loader2, Presentation, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { listAgentTools, runDocumentAgentTool } from "@/lib/api";
import type { AgentToolDefinition, AgentToolName, AgentToolResult } from "@/types";

type AgentToolsPanelProps = {
  documentId: string;
  documentTitle: string;
};

export function AgentToolsPanel({ documentId, documentTitle }: AgentToolsPanelProps) {
  const [tools, setTools] = useState<AgentToolDefinition[]>([]);
  const [result, setResult] = useState<AgentToolResult | null>(null);
  const [runningTool, setRunningTool] = useState<AgentToolName | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied">("idle");

  useEffect(() => {
    let isMounted = true;

    listAgentTools()
      .then((nextTools) => {
        if (isMounted) {
          setTools(nextTools);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Agent 工具加载失败");
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  async function runTool(toolName: AgentToolName) {
    setRunningTool(toolName);
    setError(null);
    setCopyState("idle");
    try {
      setResult(await runDocumentAgentTool(documentId, toolName));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Agent 工具执行失败");
    } finally {
      setRunningTool(null);
    }
  }

  async function copyResult() {
    if (!result) return;
    await navigator.clipboard.writeText(result.content);
    setCopyState("copied");
    window.setTimeout(() => setCopyState("idle"), 1400);
  }

  function downloadResult() {
    if (!result) return;
    const filename = `${sanitizeFileName(documentTitle)}-${result.tool_name}.md`;
    const blob = new Blob([result.content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement("a");
    link.href = url;
    link.download = filename;
    window.document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="panel agent-tools-panel">
      <div className="panel-header">
        <h2 className="panel-title">Agent 工具</h2>
        <Sparkles size={18} color="var(--accent)" />
      </div>
      <div className="panel-body">
        {error ? <p className="alert">{error}</p> : null}

        <div className="agent-tool-grid">
          {tools.length === 0 && !error ? (
            <>
              <div className="skeleton" />
              <div className="skeleton" />
            </>
          ) : null}
          {tools.map((tool) => (
            <button
              className={`tool-button ${result?.tool_name === tool.name ? "is-active" : ""}`}
              disabled={runningTool !== null}
              key={tool.name}
              title={tool.description}
              type="button"
              onClick={() => void runTool(tool.name)}
            >
              {runningTool === tool.name ? <Loader2 size={17} /> : toolIcon(tool.name)}
              {tool.title}
            </button>
          ))}
        </div>

        {result ? (
          <div className="agent-result">
            <div className="agent-result-header">
              <div>
                <span className="result-label">{result.title}</span>
                <span className="result-meta">{formatDate(result.created_at)}</span>
              </div>
              <div className="agent-result-actions">
                <button className="icon-action" title="复制" type="button" onClick={() => void copyResult()}>
                  <Clipboard size={16} />
                </button>
                <button className="icon-action" title="下载 Markdown" type="button" onClick={downloadResult}>
                  <Download size={16} />
                </button>
              </div>
            </div>
            {copyState === "copied" ? <span className="copy-hint">已复制</span> : null}
            <pre className="agent-output">{result.content}</pre>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function toolIcon(name: AgentToolName) {
  switch (name) {
    case "extract_keywords":
      return <KeyRound size={17} />;
    case "generate_questions":
      return <ListChecks size={17} />;
    case "create_markdown_note":
      return <FileText size={17} />;
    case "export_outline":
      return <Presentation size={17} />;
    case "summarize_document":
    default:
      return <Sparkles size={17} />;
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function sanitizeFileName(value: string) {
  const sanitized = value.replace(/[\\/:*?"<>|]/g, "-").trim();
  return sanitized.slice(0, 80) || "papermind-agent";
}
