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
  mode: "model" | "extractive";
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
