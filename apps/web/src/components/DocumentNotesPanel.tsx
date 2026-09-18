"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { NotebookPen, Save } from "lucide-react";
import { createDocumentNote, listDocumentNotes } from "@/lib/api";
import type { DocumentNote } from "@/types";

type DocumentNotesPanelProps = {
  documentId: string;
};

export function DocumentNotesPanel({ documentId }: DocumentNotesPanelProps) {
  const [notes, setNotes] = useState<DocumentNote[]>([]);
  const [content, setContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshNotes = useCallback(async () => {
    setNotes(await listDocumentNotes(documentId));
  }, [documentId]);

  useEffect(() => {
    let isMounted = true;

    listDocumentNotes(documentId)
      .then((nextNotes) => {
        if (isMounted) {
          setNotes(nextNotes);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "笔记加载失败");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [documentId]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextContent = content.trim();
    if (!nextContent) return;

    setIsSaving(true);
    setError(null);
    try {
      await createDocumentNote(documentId, nextContent);
      setContent("");
      await refreshNotes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "笔记保存失败");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="panel notes-panel">
      <div className="panel-header">
        <h2 className="panel-title">我的笔记</h2>
        <NotebookPen size={18} color="var(--accent)" />
      </div>
      <div className="panel-body">
        <form className="note-form" onSubmit={onSubmit}>
          <textarea
            className="note-input"
            value={content}
            placeholder="写下你的阅读笔记"
            onChange={(event) => setContent(event.target.value)}
          />
          <button className="secondary-action" type="submit" disabled={isSaving}>
            <Save size={17} />
            {isSaving ? "保存中" : "保存笔记"}
          </button>
        </form>

        {error ? <p className="alert">{error}</p> : null}

        {notes.length > 0 ? (
          <div className="note-list">
            {notes.map((note) => (
              <article className="note-item" key={note.id}>
                <p>{note.content}</p>
                <span>{formatDate(note.created_at)}</span>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
