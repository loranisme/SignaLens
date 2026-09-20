"""Read only extraction of user-supplied text files. Never silently truncate."""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf
from docx import Document

from .config import MAX_ESTIMATED_INPUT_TOKENS, MAX_FILE_BYTES, MAX_PDF_PAGES

ALLOWED_SUFFIXES = {".txt", ".md", ".pdf", ".docx", ".doc"}


class ExtractionError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass
class ExtractedText:
    text: str
    input_format: str
    evaluated_scope: str
    extraction_status: str = "complete_text"
    estimated_tokens: int = 0
    total_pages: int | None = None
    pages_evaluated: list[int] | None = None
    section_title: str | None = None
    ocr_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def public_metadata(self) -> dict[str, Any]:
        return {
            "input_format": self.input_format,
            "evaluated_scope": self.evaluated_scope,
            "extraction_status": self.extraction_status,
            "estimated_tokens": self.estimated_tokens,
            "total_pages": self.total_pages,
            "pages_evaluated": self.pages_evaluated,
            "section_title": self.section_title,
            "ocr_pages": self.ocr_pages,
            "warnings": self.warnings,
        }


def estimated_tokens(text: str) -> int:
    # TypeSafe does not publish Jev's tokenizer. Avoid a runtime tokenizer
    # download; enforce a conservative, deterministic local estimate instead.
    ascii_count = sum(ord(char) < 128 for char in text)
    non_ascii_count = len(text) - ascii_count
    byte_count = len(text.encode("utf-8"))
    return max((byte_count + 1) // 2, (ascii_count + 2) // 3 + 2 * non_ascii_count)


def _clean(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{4,}", "\n\n\n", text).strip()


def _enforce_budget(result: ExtractedText, details: dict[str, Any] | None = None) -> ExtractedText:
    result.text = _clean(result.text)
    if not result.text:
        raise ExtractionError("EXTRACTION_INCOMPLETE", "未取得可评估的文字。")
    result.estimated_tokens = estimated_tokens(result.text)
    if result.estimated_tokens > MAX_ESTIMATED_INPUT_TOKENS:
        raise ExtractionError(
            "CONTENT_TOO_LONG",
            "内容超过单次完整评估预算；请选定页码或章节后重试。",
            {"estimated_tokens": result.estimated_tokens, "limit": MAX_ESTIMATED_INPUT_TOKENS, **(details or {})},
        )
    return result


def extract_pasted_text(text: str) -> ExtractedText:
    if not isinstance(text, str) or not text.strip():
        raise ExtractionError("INPUT_INVALID", "请粘贴需要评估的文字。")
    cleaned = _clean(text)
    if re.fullmatch(r"https?://\S+", cleaned, flags=re.IGNORECASE):
        raise ExtractionError("INPUT_INVALID", "请粘贴网页正文；MVP 不抓取网址。")
    return _enforce_budget(ExtractedText(cleaned, "pasted_text", "pasted_text"))


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "gb18030"):
        try:
            text = data.decode(encoding)
            if text.count("\ufffd") == 0:
                return text
        except UnicodeDecodeError:
            continue
    raise ExtractionError("EXTRACTION_INCOMPLETE", "文本编码无法读取；请改用 UTF-8。")


def _check_type(suffix: str, data: bytes) -> None:
    if suffix not in ALLOWED_SUFFIXES:
        raise ExtractionError("UNSUPPORTED_FILE", "当前仅支持 TXT、MD、PDF、DOCX、DOC。")
    if suffix == ".pdf" and not data.lstrip().startswith(b"%PDF-"):
        raise ExtractionError("UNSUPPORTED_FILE", "文件内容不是有效 PDF。")
    if suffix == ".docx":
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise ExtractionError("UNSUPPORTED_FILE", "文件内容不是有效 DOCX。")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.infolist()
            if len(info) > 2000 or sum(item.file_size for item in info) > 80 * 1024 * 1024:
                raise ExtractionError("UNSUPPORTED_FILE", "DOCX 解压后超出安全限制。")
            if "word/document.xml" not in archive.namelist():
                raise ExtractionError("UNSUPPORTED_FILE", "DOCX 缺少正文。")
    if suffix == ".doc" and not data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        raise ExtractionError("UNSUPPORTED_FILE", "文件内容不是有效旧版 DOC。")


def _parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec:
        return list(range(1, total + 1))
    numbers: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not re.fullmatch(r"\d+(?:-\d+)?", part):
            raise ExtractionError("INPUT_INVALID", "页码格式应为 1-3,5。")
        if "-" in part:
            start, end = (int(piece) for piece in part.split("-"))
        else:
            start = end = int(part)
        if start < 1 or end < start or end > total:
            raise ExtractionError("INPUT_INVALID", "所选页码超出文档范围。")
        numbers.update(range(start, end + 1))
    return sorted(numbers)


def _ocr_image(png: bytes) -> str:
    executable = shutil.which("tesseract")
    if not executable:
        raise ExtractionError("OCR_UNAVAILABLE", "扫描件需要 OCR；本机尚未安装 Tesseract。")
    langs = subprocess.run([executable, "--list-langs"], capture_output=True, text=True, timeout=5)
    available = set(langs.stdout.splitlines()) | set(langs.stderr.splitlines())
    if not {"eng", "chi_sim"}.issubset(available):
        raise ExtractionError("OCR_UNAVAILABLE", "扫描件需要英文及简体中文 OCR 语言数据。")
    try:
        process = subprocess.run(
            [executable, "stdin", "stdout", "-l", "eng+chi_sim", "--psm", "3"],
            input=png,
            capture_output=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExtractionError("EXTRACTION_INCOMPLETE", "扫描页 OCR 超时。") from exc
    if process.returncode != 0:
        raise ExtractionError("EXTRACTION_INCOMPLETE", "扫描页 OCR 失败。")
    return process.stdout.decode("utf-8", errors="replace")


def _page_has_marks(page: pymupdf.Page) -> bool:
    preview = page.get_pixmap(matrix=pymupdf.Matrix(1, 1), colorspace=pymupdf.csGRAY)
    dark = sum(pixel < 220 for pixel in preview.samples)
    return dark > len(preview.samples) * 0.002


def _pdf_text(data: bytes, page_range: str | None) -> ExtractedText:
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ExtractionError("EXTRACTION_INCOMPLETE", "PDF 无法打开。") from exc
    try:
        if pdf.is_encrypted:
            raise ExtractionError("EXTRACTION_INCOMPLETE", "加密 PDF 无法评估。")
        total = len(pdf)
        if total < 1:
            raise ExtractionError("EXTRACTION_INCOMPLETE", "PDF 没有可评估的页面。")
        if total > MAX_PDF_PAGES and not page_range:
            raise ExtractionError(
                "CONTENT_TOO_LONG", "PDF 页数超出首版整份处理上限；请选定页码。",
                {"total_pages": total, "limit_pages": MAX_PDF_PAGES, "available_page_range": f"1-{total}"},
            )
        pages = _parse_pages(page_range, total)
        if len(pages) > MAX_PDF_PAGES:
            raise ExtractionError(
                "CONTENT_TOO_LONG", "所选 PDF 页数超过单次处理上限。",
                {"total_pages": total, "limit_pages": MAX_PDF_PAGES, "available_page_range": f"1-{total}"},
            )
        if len(pages) > 10 and any(
            not pdf[number - 1].get_text().strip() and _page_has_marks(pdf[number - 1])
            for number in pages
        ):
            raise ExtractionError(
                "CONTENT_TOO_LONG", "含扫描页的文档超过 10 页；请选定最多 10 页。",
                {"total_pages": total, "available_page_range": f"1-{total}"},
            )
        chunks: list[str] = []
        ocr_pages: list[int] = []
        visual_pages: list[int] = []
        for number in pages:
            page = pdf[number - 1]
            page_text = _clean(page.get_text("text", sort=True))
            images = page.get_images(full=True)
            if images:
                visual_pages.append(number)
            if len(page_text) < 30:
                # Blank pages carry no decision content; nonblank pages need OCR.
                if _page_has_marks(page):
                    rendered = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), colorspace=pymupdf.csRGB)
                    page_text = _clean(_ocr_image(rendered.tobytes("png")))
                    ocr_pages.append(number)
                    if len(page_text) < 12:
                        raise ExtractionError(
                            "EXTRACTION_INCOMPLETE",
                            f"第 {number} 页文字无法可靠提取。",
                            {"total_pages": total, "unreadable_page": number},
                        )
            if page_text:
                chunks.append(f"[Page {number}]\n{page_text}")
        result = ExtractedText(
            text="\n\n".join(chunks),
            input_format="pdf",
            evaluated_scope="selected_pages" if page_range else "whole_document_text",
            total_pages=total,
            pages_evaluated=pages,
            ocr_pages=ocr_pages,
        )
        if visual_pages:
            result.warnings.append("文档含图片或图表；系统只评估可提取及 OCR 识别的文字。")
        return _enforce_budget(result, {"total_pages": total, "available_page_range": f"1-{total}"})
    finally:
        pdf.close()


def _docx_text(data: bytes, section_index: int | None) -> ExtractedText:
    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError("EXTRACTION_INCOMPLETE", "DOCX 无法读取。") from exc
    sections: list[tuple[str, list[str]]] = []
    current_title = "文档开头"
    current_blocks: list[str] = []
    for block in document.iter_inner_content():
        if hasattr(block, "rows"):
            for row in block.rows:
                row_text = " | ".join(_clean(cell.text) for cell in row.cells)
                if row_text.strip(" |"):
                    current_blocks.append(row_text)
            continue
        value = _clean(block.text)
        if not value:
            continue
        style_name = (block.style.name or "").lower() if block.style else ""
        if style_name.startswith("heading") or style_name.startswith("标题"):
            if current_blocks:
                sections.append((current_title, current_blocks))
            current_title = value[:100]
            current_blocks = [value]
        else:
            current_blocks.append(value)
    if current_blocks:
        sections.append((current_title, current_blocks))
    titles = [title for title, _ in sections]
    if section_index is not None:
        if section_index < 0 or section_index >= len(sections):
            raise ExtractionError("INPUT_INVALID", "章节编号超出范围。", {"sections": titles})
        title, blocks = sections[section_index]
        scope = "selected_section"
    else:
        title = None
        blocks = [item for _, block_list in sections for item in block_list]
        scope = "whole_document_text"
    result = ExtractedText("\n".join(blocks), "docx", scope, section_title=title)
    if document.inline_shapes:
        result.warnings.append("Word 文档含图片；系统只评估可提取的文字。")
    return _enforce_budget(result, {"sections": titles})


def _doc_text(data: bytes) -> ExtractedText:
    converter = shutil.which("textutil")
    if not converter:
        raise ExtractionError("UNSUPPORTED_FILE", "本机没有旧版 DOC 转换工具；请改用 DOCX。")
    with tempfile.TemporaryDirectory(prefix="signalens-doc-") as temp_dir:
        input_path = Path(temp_dir) / "input.doc"
        input_path.write_bytes(data)
        try:
            process = subprocess.run(
                [converter, "-convert", "txt", "-stdout", str(input_path)],
                capture_output=True,
                timeout=20,
                cwd=temp_dir,
            )
        except subprocess.TimeoutExpired as exc:
            raise ExtractionError("EXTRACTION_INCOMPLETE", "旧版 DOC 转换超时。") from exc
        if process.returncode != 0:
            raise ExtractionError("EXTRACTION_INCOMPLETE", "旧版 DOC 无法转换为文字。")
        result = ExtractedText(_decode_text(process.stdout), "doc", "whole_document_text")
        result.warnings.append("旧版 DOC 只评估转换后的文字；请核对表格和图片覆盖。")
        return _enforce_budget(result)


def extract_file(filename: str, data: bytes, page_range: str | None = None, section_index: int | None = None) -> ExtractedText:
    suffix = Path(filename).suffix.lower()
    if not data:
        raise ExtractionError("INPUT_INVALID", "文件为空。")
    if len(data) > MAX_FILE_BYTES:
        raise ExtractionError("INPUT_INVALID", "文件超过 20 MB 上限。")
    _check_type(suffix, data)
    if suffix != ".pdf" and page_range:
        raise ExtractionError("INPUT_INVALID", "页码选择仅适用于 PDF。")
    if suffix != ".docx" and section_index is not None:
        raise ExtractionError("INPUT_INVALID", "章节选择仅适用于 DOCX。")
    if suffix == ".pdf":
        return _pdf_text(data, page_range)
    if suffix == ".docx":
        return _docx_text(data, section_index)
    if suffix == ".doc":
        return _doc_text(data)
    return _enforce_budget(ExtractedText(_decode_text(data), suffix.lstrip("."), "whole_document_text"))
