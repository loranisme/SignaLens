"""Create crossed language/context/format file fixtures from frozen holdout text."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pymupdf
from docx import Document

from signalens.extract import extract_file

ROOT = Path(__file__).resolve().parent
DEST = ROOT / "file_probes_crossed"
DEST.mkdir(exist_ok=True)
rows = [json.loads(line) for line in (ROOT / "holdout_v2_gold.jsonl").read_text(encoding="utf-8").splitlines()]
by_key = {(row["language"], row["context_id"], row["gold"]): row for row in rows}
selections = {
    "zh": ("solar", "bank"),
    "en": ("bank", "shipping"),
    "es": ("shipping", "devices"),
    "ja": ("devices", "solar"),
}


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


manifest = []
for language, context_names in selections.items():
    for index, context_id in enumerate(context_names):
        for gold in ("RESEARCH", "KEEP"):
            row = by_key[(language, context_id, gold)]
            # Each language has both labels in both formats, in two contexts.
            is_pdf = (gold == "RESEARCH") == (index == 0)
            suffix = ".pdf" if is_pdf else ".docx"
            path = DEST / (row["case_id"] + suffix)
            assert not path.exists(), "Refuse to overwrite a fixture"
            if is_pdf:
                doc = pymupdf.open()
                page = doc.new_page()
                font = {"zh": "china-s", "ja": "japan"}.get(language, "helv")
                fit = page.insert_textbox(pymupdf.Rect(55, 80, 550, 600), row["information_text"], fontname=font, fontsize=12, lineheight=1.6)
                assert fit >= 0
                doc.save(path)
                doc.close()
            else:
                doc = Document()
                doc.add_paragraph(row["information_text"])
                doc.save(path)
            data = path.read_bytes()
            extracted = extract_file(path.name, data)
            exact = compact(row["information_text"]) in compact(extracted.text)
            manifest.append({
                "case_id": row["case_id"],
                "language": language,
                "context_id": context_id,
                "gold": gold,
                "format": suffix[1:],
                "filename": path.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "extraction_contains_original_without_whitespace": exact,
                "extracted_scope": extracted.evaluated_scope,
            })
            print(row["case_id"], language, context_id, gold, suffix, "exact" if exact else "DIFF")

assert len(manifest) == 16
assert all(item["extraction_contains_original_without_whitespace"] for item in manifest)
(ROOT / "file_probe_crossed_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
