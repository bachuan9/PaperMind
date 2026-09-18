export type DocumentStatus = "ready" | "failed" | "processing";

export type DocumentSummary = {
  id: string;
  title: string;
  filename: string;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  size_bytes: number;
  page_count: number;
  chunk_count: number;
  summary: string;
  error?: string | null;
};

export type DocumentChunk = {
  id: string;
  document_id: string;
  index: number;
  text: string;
  page_number?: number | null;
};

export type DocumentDetail = DocumentSummary & {
  chunks: DocumentChunk[];
};

export type Citation = {
  chunk_id: string;
  page_number?: number | null;
  text: string;
  score: number;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
  conversation_id: string;
  mode: "model" | "extractive";
  provider: string;
  model?: string | null;
  fallback_reason?: string | null;
};

export type ConversationSummary = {
  id: string;
  document_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type ConversationMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  citations: Citation[];
  mode?: "model" | "extractive" | null;
  provider?: string | null;
  model?: string | null;
};

export type InsightSection = {
  title: string;
  summary: string;
};

export type DocumentInsightResponse = {
  summary: string;
  keywords: string[];
  sections: InsightSection[];
  suggested_questions: string[];
  mode: "model" | "extractive";
};

export type ModelStatusResponse = {
  provider: string;
  model: string;
  base_url: string;
  configured: boolean;
};

export type LlmCallLog = {
  id: string;
  created_at: string;
  document_id: string;
  question_preview: string;
  provider: string;
  model: string;
  mode: "model" | "extractive";
  status: "success" | "skipped" | "failed";
  latency_ms: number;
  citation_count: number;
  error?: string | null;
};

export type AskStreamEvent =
  | {
      type: "meta";
      conversation_id: string;
      mode: "model" | "extractive";
      provider: string;
      model?: string | null;
      fallback_reason?: string | null;
      citations: Citation[];
    }
  | {
      type: "token";
      token: string;
    }
  | {
      type: "done";
      answer: string;
    };
