"""Create eight multilingual DOCX/PDF fixtures and check extracted key text."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pymupdf
from docx import Document

from signalens.extract import extract_file

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "holdout_v2_gold.jsonl"
DEST = ROOT / "file_probes"
DEST.mkdir(exist_ok=True)
rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()]
selected = [row for row in rows if row["context_id"] == "solar" and row["gold"] in {"RESEARCH", "KEEP"}]
assert len(selected) == 8


def normalized(value: str) -> str:
    return re.sub(r"\s+", "", value)


manifest = []
for row in selected:
    is_pdf = row["gold"] == "KEEP"
    suffix = ".pdf" if is_pdf else ".docx"
    path = DEST / (row["case_id"] + suffix)
    assert not path.exists(), "Refuse to overwrite a fixture"
    if is_pdf:
        doc = pymupdf.open()
        page = doc.new_page()
        font = {"zh": "china-s", "ja": "japan"}.get(row["language"], "helv")
        result = page.insert_textbox(
            pymupdf.Rect(55, 80, 550, 600),
            row["information_text"],
            fontname=font,
            fontsize=12,
            lineheight=1.6,
        )
        assert result >= 0, f"PDF text did not fit: {row['case_id']}"
        doc.save(path)
        doc.close()
    else:
        doc = Document()
        doc.add_paragraph(row["information_text"])
        doc.save(path)
    data = path.read_bytes()
    extracted = extract_file(path.name, data)
    expected = normalized(row["information_text"])
    actual = normalized(extracted.text)
    exact = expected in actual
    manifest.append({
        "case_id": row["case_id"],
        "language": row["language"],
        "context_id": row["context_id"],
        "gold": row["gold"],
        "format": suffix[1:],
        "filename": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "extraction_contains_original_without_whitespace": exact,
        "extracted_scope": extracted.evaluated_scope,
        "extracted_character_count": len(extracted.text),
    })
    print(row["case_id"], suffix, row["language"], "exact" if exact else "DIFF")

(ROOT / "file_probe_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert all(row["extraction_contains_original_without_whitespace"] for row in manifest)
