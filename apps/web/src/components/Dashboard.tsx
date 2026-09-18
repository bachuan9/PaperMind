"use client";

import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { listDocuments } from "@/lib/api";
import type { DocumentSummary } from "@/types";
import { DocumentList } from "./DocumentList";
import { UploadDropzone } from "./UploadDropzone";

export function Dashboard() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      setDocuments(await listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法加载文档");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="grid-dashboard">
      <section className="panel">
        <div className="panel-header">
          <div>
            <h2 className="panel-title">文档库</h2>
          </div>
          <button className="icon-action" title="刷新" type="button" onClick={() => void refresh()}>
            <RefreshCw size={17} />
          </button>
        </div>
        <div className="panel-body">
          {error ? <p className="alert">{error}</p> : null}
          {isLoading ? (
            <div className="doc-list">
              <div className="skeleton" />
              <div className="skeleton" />
            </div>
          ) : (
            <DocumentList
              documents={documents}
              onDeleted={(id) =>
                setDocuments((current) => current.filter((item) => item.id !== id))
              }
            />
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2 className="panel-title">导入</h2>
        </div>
        <div className="panel-body">
          <UploadDropzone
            onUploaded={(document) =>
              setDocuments((current) => [document, ...current.filter((item) => item.id !== document.id)])
            }
          />
        </div>
      </section>
    </div>
  );
}
