"use client";

import { Lightbulb, ListChecks, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { getDocumentInsights } from "@/lib/api";
import type { DocumentInsightResponse } from "@/types";

type InsightPanelProps = {
  documentId: string;
};

export function InsightPanel({ documentId }: InsightPanelProps) {
  const [insights, setInsights] = useState<DocumentInsightResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    getDocumentInsights(documentId)
      .then((data) => {
        if (isMounted) {
          setInsights(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "洞察生成失败");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [documentId]);

  return (
    <section className="panel insight-panel">
      <div className="panel-header">
        <h2 className="panel-title">文档洞察</h2>
        <Sparkles size={18} color="var(--accent)" />
      </div>
      <div className="panel-body">
        {isLoading ? (
          <div className="insight-grid">
            <div className="skeleton" />
            <div className="skeleton" />
          </div>
        ) : null}

        {error ? <p className="alert">{error}</p> : null}

        {insights ? (
          <div className="insight-stack">
            <div className="insight-summary">
              <div className="insight-heading">
                <Lightbulb size={17} />
                <span>摘要</span>
              </div>
              <p>{insights.summary || "暂无摘要"}</p>
            </div>

            <div className="keyword-row">
              {insights.keywords.map((keyword) => (
                <span className="keyword-chip" key={keyword}>
                  {keyword}
                </span>
              ))}
            </div>

            <div className="insight-grid">
              <div>
                <div className="insight-heading">
                  <ListChecks size={17} />
                  <span>提纲</span>
                </div>
                <div className="section-list">
                  {insights.sections.map((section) => (
                    <article className="section-item" key={section.title}>
                      <strong>{section.title}</strong>
                      <p>{section.summary}</p>
                    </article>
                  ))}
                </div>
              </div>

              <div>
                <div className="insight-heading">
                  <Sparkles size={17} />
                  <span>可追问</span>
                </div>
                <div className="question-list">
                  {insights.suggested_questions.map((question) => (
                    <span className="question-chip" key={question}>
                      {question}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
