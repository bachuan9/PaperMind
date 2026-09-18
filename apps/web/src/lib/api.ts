import type {
  AskResponse,
  AskStreamEvent,
  ConversationMessage,
  ConversationSummary,
  DocumentDetail,
  DocumentInsightResponse,
  DocumentSummary,
  LlmCallLog,
  ModelStatusResponse
} from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_AI_SERVICE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<{ status: string }> {
  return parseResponse(await fetch(`${API_BASE}/health`, { cache: "no-store" }));
}

export async function getModelStatus(): Promise<ModelStatusResponse> {
  return parseResponse(await fetch(`${API_BASE}/model/status`, { cache: "no-store" }));
}

export async function listLlmLogs(): Promise<LlmCallLog[]> {
  return parseResponse(await fetch(`${API_BASE}/llm/logs`, { cache: "no-store" }));
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  return parseResponse(await fetch(`${API_BASE}/documents`, { cache: "no-store" }));
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  return parseResponse(await fetch(`${API_BASE}/documents/${id}`, { cache: "no-store" }));
}

export async function getDocumentInsights(id: string): Promise<DocumentInsightResponse> {
  return parseResponse(
    await fetch(`${API_BASE}/documents/${id}/insights`, { cache: "no-store" })
  );
}

export async function listConversations(id: string): Promise<ConversationSummary[]> {
  return parseResponse(
    await fetch(`${API_BASE}/documents/${encodeURIComponent(id)}/conversations`, {
      cache: "no-store"
    })
  );
}

export async function listConversationMessages(
  id: string
): Promise<ConversationMessage[]> {
  return parseResponse(
    await fetch(`${API_BASE}/conversations/${encodeURIComponent(id)}/messages`, {
      cache: "no-store"
    })
  );
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const formData = new FormData();
  formData.append("file", file);

  return parseResponse(
    await fetch(`${API_BASE}/documents`, {
      method: "POST",
      body: formData
    })
  );
}

export async function deleteDocument(id: string): Promise<{ ok: boolean }> {
  return parseResponse(
    await fetch(`${API_BASE}/documents/${id}`, {
      method: "DELETE"
    })
  );
}

export async function askDocument(
  id: string,
  question: string,
  conversationId: string | null = null
): Promise<AskResponse> {
  return parseResponse(
    await fetch(`${API_BASE}/documents/${id}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        question,
        conversation_id: conversationId
      })
    })
  );
}

export async function streamAskDocument(
  id: string,
  question: string,
  conversationId: string | null,
  onEvent: (event: AskStreamEvent) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/documents/${id}/ask/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      question,
      conversation_id: conversationId
    })
  });

  if (!response.ok) {
    await parseResponse(response);
    return;
  }
  if (!response.body) {
    throw new Error("当前浏览器不支持流式读取");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      onEvent(JSON.parse(trimmed) as AskStreamEvent);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    onEvent(JSON.parse(buffer.trim()) as AskStreamEvent);
  }
}
