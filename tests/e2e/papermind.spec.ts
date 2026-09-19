import { expect, test } from "@playwright/test";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const apiBaseUrl = "http://127.0.0.1:8010";
const rootDir = path.resolve(__dirname, "../..");

let apiProcess: ChildProcessWithoutNullStreams | null = null;
let dataDir = "";

test.describe.configure({ mode: "serial" });

test.beforeAll(async () => {
  dataDir = mkdtempSync(path.join(tmpdir(), "papermind-e2e-"));
  const pythonPath =
    process.platform === "win32"
      ? path.join(rootDir, ".venv", "Scripts", "python.exe")
      : path.join(rootDir, ".venv", "bin", "python");

  apiProcess = spawn(
    pythonPath,
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8010",
      "--app-dir",
      "services/ai-service"
    ],
    {
      cwd: rootDir,
      env: {
        ...process.env,
        AI_DATA_DIR: dataDir,
        AI_QUEUE_BACKEND: "inline",
        DEEPSEEK_API_KEY: "",
        AI_ALLOWED_ORIGINS: "http://127.0.0.1:3100,http://localhost:3100"
      },
      windowsHide: true
    }
  );

  await waitForApi();
});

test.afterAll(() => {
  apiProcess?.kill();
  if (dataDir) {
    rmSync(dataDir, { recursive: true, force: true });
  }
});

test("uploads a markdown document and asks a grounded question", async ({ page }) => {
  await page.goto("/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "e2e-rag-notes.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(
      [
        "# E2E RAG Notes",
        "",
        "Grounded answers require source citations and original text.",
        "PaperMind retrieves document chunks before answering questions."
      ].join("\n"),
      "utf-8"
    )
  });

  await expect(page.getByText("e2e-rag-notes")).toBeVisible();
  await page.getByText("e2e-rag-notes").click();

  await expect(page.getByText("Grounded answers require source citations")).toBeVisible();

  await page.locator(".question-input").fill("What requires source citations?");
  await page.locator(".question-form button[type='submit']").click();

  await expect(page.locator(".answer-body")).toContainText("source citations");
  await expect(page.locator(".citation")).toContainText("Grounded answers");
});

async function waitForApi() {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${apiBaseUrl}/health`);
      if (response.ok) return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
  }
  throw new Error("Timed out waiting for PaperMind API");
}
