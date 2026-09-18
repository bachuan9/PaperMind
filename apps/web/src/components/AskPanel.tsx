"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { History, MessageSquareText, Plus, Send } from "lucide-react";
import {
  listConversationMessages,
  listConversations,
  streamAskDocument
} from "@/lib/api";
import type {
  AskResponse,
  ConversationMessage,
  ConversationSummary
} from "@/types";

export function AskPanel({ documentId }: { documentId: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [isAsking, setIsAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshConversations = useCallback(async () => {
    const nextConversations = await listConversations(documentId);
    setConversations(nextConversations);
    return nextConversations;
  }, [documentId]);

  const loadMessages = useCallback(async (nextConversationId: string) => {
    const nextMessages = await listConversationMessages(nextConversationId);
    setConversationId(nextConversationId);
    setMessages(nextMessages);
    setAnswer(null);
  }, []);

  useEffect(() => {
    let isMounted = true;

    refreshConversations()
      .then(async (nextConversations) => {
        if (!isMounted || !nextConversations[0]) return;
        const nextMessages = await listConversationMessages(nextConversations[0].id);
        if (!isMounted) return;
        setConversationId(nextConversations[0].id);
        setMessages(nextMessages);
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "对话历史加载失败");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [refreshConversations]);

  function startNewConversation() {
    setConversationId(null);
    setMessages([]);
    setAnswer(null);
    setError(null);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submittedQuestion = question.trim();
    if (!submittedQuestion) return;

    setIsAsking(true);
    setError(null);
    setAnswer(null);
    let streamedConversationId = conversationId;

    try {
      await streamAskDocument(
        documentId,
        submittedQuestion,
        conversationId,
        (event) => {
          if (event.type === "meta") {
            streamedConversationId = event.conversation_id;
            setConversationId(event.conversation_id);
            setAnswer({
              answer: "",
              citations: event.citations,
              conversation_id: event.conversation_id,
              mode: event.mode,
              provider: event.provider,
              model: event.model,
              fallback_reason: event.fallback_reason
            });
            return;
          }
          if (event.type === "token") {
            setAnswer((current) =>
              current ? { ...current, answer: current.answer + event.token } : current
            );
          }
        }
      );
      setQuestion("");
      if (streamedConversationId) {
        await loadMessages(streamedConversationId);
        await refreshConversations();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "问答失败");
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <aside className="panel ask-panel">
      <div className="panel-header">
        <div className="ask-panel-title">
          <h2 className="panel-title">文档问答</h2>
          <MessageSquareText size={18} color="var(--accent)" />
        </div>
        <div className="conversation-actions">
          <History size={16} color="var(--muted)" />
          <select
            aria-label="选择对话"
            className="conversation-select"
            value={conversationId ?? ""}
            onChange={(event) => {
              if (!event.target.value) {
                startNewConversation();
                return;
              }
              void loadMessages(event.target.value);
            }}
          >
            <option value="">新建对话</option>
            {conversations.map((conversation) => (
              <option key={conversation.id} value={conversation.id}>
                {conversation.title} ({Math.floor(conversation.message_count / 2)} 轮)
              </option>
            ))}
          </select>
          <button
            aria-label="新建对话"
            className="icon-action"
            title="新建对话"
            type="button"
            onClick={startNewConversation}
          >
            <Plus size={16} />
          </button>
        </div>
      </div>
      <div className="panel-body">
        {messages.length > 0 ? (
          <div className="conversation-history">
            {messages.map((message) => (
              <article className={`message-bubble ${message.role}`} key={message.id}>
                <div className="message-meta">
                  {message.role === "user" ? "你" : "PaperMind"}
                </div>
                <p>{message.content}</p>
                {message.role === "assistant" && message.citations.length > 0 ? (
                  <span className="message-citation-count">
                    {message.citations.length} 条引用
                  </span>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}

        <form className="question-form" onSubmit={onSubmit}>
          <textarea
            className="question-input"
            value={question}
            placeholder="输入问题"
            onChange={(event) => setQuestion(event.target.value)}
          />
          <button className="primary-action" type="submit" disabled={isAsking}>
            <Send size={17} />
            {isAsking ? "生成中" : "提问"}
          </button>
        </form>

        {error ? <p className="alert">{error}</p> : null}

        {answer ? (
          <div className="answer">
            <div className="answer-meta">
              <span className={`mode-chip ${answer.mode}`}>
                {answer.mode === "model" ? "DeepSeek 模型" : "本地兜底"}
              </span>
              <span>{answer.model ?? answer.provider}</span>
            </div>
            {answer.fallback_reason ? (
              <div className="fallback-note">{answer.fallback_reason}</div>
            ) : null}
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
