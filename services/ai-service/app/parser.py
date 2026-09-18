import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


@dataclass(frozen=True)
class ParsedPage:
    page_number: int | None
    text: str


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"仅支持 {supported} 文件")
    return extension


def parse_document(path: Path) -> list[ParsedPage]:
    extension = path.suffix.lower()
    if extension == ".pdf":
        return parse_pdf(path)
    return parse_text(path)


def parse_pdf(path: Path) -> list[ParsedPage]:
    reader = PdfReader(str(path))
    pages: list[ParsedPage] = []
    for index, page in enumerate(reader.pages):
        text = normalize_text(page.extract_text() or "")
        if text:
            pages.append(ParsedPage(page_number=index + 1, text=text))
    return pages


def parse_text(path: Path) -> list[ParsedPage]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    text = normalize_text(raw)
    return [ParsedPage(page_number=None, text=text)] if text else []


def chunk_pages(
    pages: list[ParsedPage],
    *,
    chunk_size: int = 1100,
    overlap: int = 140,
) -> list[tuple[int | None, str]]:
    chunks: list[tuple[int | None, str]] = []
    for page in pages:
        text = page.text
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            candidate = text[start:end].strip()
            if candidate:
                chunks.append((page.page_number, candidate))
            if end == len(text):
                break
            start = max(0, end - overlap)
    return chunks


def build_summary(pages: list[ParsedPage], limit: int = 280) -> str:
    text = " ".join(page.text for page in pages)
    if not text:
        return ""
    sentences = re.split(r"(?<=[。！？.!?])\s+", text)
    summary = ""
    for sentence in sentences:
        if len(summary) + len(sentence) > limit:
            break
        summary += sentence + " "
    summary = summary.strip()
    if not summary:
        summary = text[:limit]
    return summary[:limit].strip()


def normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()
