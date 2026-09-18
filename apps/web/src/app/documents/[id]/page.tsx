import { notFound } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { DocumentWorkspace } from "@/components/DocumentWorkspace";
import { getDocument } from "@/lib/api";

export default async function DocumentPage({
  params
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  try {
    const document = await getDocument(id);
    return (
      <AppShell active="reader">
        <DocumentWorkspace document={document} />
      </AppShell>
    );
  } catch {
    notFound();
  }
}
