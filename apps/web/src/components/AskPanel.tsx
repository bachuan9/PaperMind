"use client";

import { FormEvent, useState } from "react";
import { MessageSquareText, Send } from "lucide-react";
import { askDocument } from "@/lib/api";
import type { AskResponse } from "@/types";

export function AskPanel({ documentId }: { documentId: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) return;

    setIsAsking(true);
    setError(null);
    try {
      setAnswer(await askDocument(documentId, question.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "问答失败");
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <aside className="panel ask-panel">
      <div className="panel-header">
        <h2 className="panel-title">文档问答</h2>
        <MessageSquareText size={18} color="var(--accent)" />
      </div>
      <div className="panel-body">
        <form className="question-form" onSubmit={onSubmit}>
          <textarea
            className="question-input"
            value={question}
            placeholder="输入问题"
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button className="primary-action" type="submit" disabled={isAsking}>
            <Send size={17} />
            {isAsking ? "检索中" : "提问"}
          </button>
        </form>

        {error ? <p className="alert">{error}</p> : null}

        {answer ? (
          <div className="answer">
            <div className="answer-body">{answer.answer}</div>
            <div className="citation-list">
              {answer.citations.map((citation, index) => (
                <article className="citation" key={`${citation.chunk_id}-${index}`}>
                  <div className="citation-meta">
                    <span>引用 {index + 1}</span>
                    <span>
                      {citation.page_number ? `第 ${citation.page_number} 页` : "正文"} ·{" "}
                      {citation.score.toFixed(2)}
                    </span>
                  </div>
                  <p className="citation-text">{citation.text}</p>
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
