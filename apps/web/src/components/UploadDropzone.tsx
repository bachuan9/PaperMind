"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { uploadDocument } from "@/lib/api";
import type { DocumentSummary } from "@/types";

type UploadDropzoneProps = {
  onUploaded: (document: DocumentSummary) => void;
};

export function UploadDropzone({ onUploaded }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitFile(file?: File) {
    if (!file) return;
    setError(null);
    setIsUploading(true);

    try {
      const document = await uploadDocument(file);
      onUploaded(document);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setIsUploading(false);
    }
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    void submitFile(event.target.files?.[0]);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    void submitFile(event.dataTransfer.files?.[0]);
  }

  return (
    <div>
      <div
        className={`upload-zone ${isDragging ? "is-dragging" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
      >
        <span className="upload-icon" aria-hidden="true">
          <UploadCloud size={26} />
        </span>
        <div>
          <p className="upload-title">{isUploading ? "正在解析文档" : "上传文档"}</p>
          <p className="upload-meta">PDF, Markdown, TXT</p>
        </div>
        <input
          ref={inputRef}
          className="file-input"
          id="document-upload"
          type="file"
          accept=".pdf,.md,.markdown,.txt,text/plain,text/markdown,application/pdf"
          onChange={onFileChange}
        />
        <button
          className="primary-action"
          type="button"
          disabled={isUploading}
          onClick={() => inputRef.current?.click()}
        >
          <UploadCloud size={17} />
          选择文件
        </button>
      </div>
      {error ? <p className="alert">{error}</p> : null}
    </div>
  );
}
