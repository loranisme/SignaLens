"""Freeze new multilingual PDF/Word cases before revising document rubric."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pymupdf
from docx import Document

from signalens.extract import extract_file

ROOT = Path(__file__).resolve().parent
GOLD = ROOT / "file_holdout_v3_gold.jsonl"
FIXTURES = ROOT / "file_holdout_v3"
MANIFEST = ROOT / "file_holdout_v3_manifest.json"
assert not GOLD.exists() and not MANIFEST.exists()
FIXTURES.mkdir(exist_ok=True)

contexts = {
    "mining": {"research_areas": ["Critical Minerals", "Rare Earth Mining"], "watchlist": ["MINE-X"], "investment_horizon": "6_24m"},
    "insurance": {"research_areas": ["Property Insurance", "Reinsurance"], "watchlist": ["INS-X"], "investment_horizon": "lt_6m"},
}

texts = {
    "zh": {
        "mining": {
            "RESEARCH": "MINE-X 核心矿区的试采回收率据称从 79% 降到 48%，若持续会影响明年的产量目标；应核对矿石批次和测量方法。",
            "KEEP": "MINE-X 展示了一个稀土分离工艺的实验室概念样品，没有回收率、扩产预算、客户或投产计划。",
            "SKIP": "一家保险公司调整了家庭财产险宣传册封面，材料没有矿业或稀土采购联系。",
        },
        "insurance": {
            "RESEARCH": "INS-X 一季度巨灾赔付内部初值比已设准备金高出 35%，再保险分摊金额尚未核对。",
            "KEEP": "INS-X 确认下月按既定安排召开业绩会，今天没有披露新的赔付、准备金或再保险数据。",
            "SKIP": "某矿山的地质队更新了野外测绘路线，文本没有保险风险敞口或承保关系。",
        },
    },
    "en": {
        "mining": {
            "RESEARCH": "MINE-X reportedly lost access to a key processing permit, potentially delaying half of next year's rare-earth output; the regulator's notice needs checking.",
            "KEEP": "MINE-X showed a laboratory separation concept with no measured recovery, scale-up budget, buyer commitment or production schedule.",
            "SKIP": "A clinic moved its weekly nutrition class to another room, with no stated connection to mineral supply.",
        },
        "insurance": {
            "RESEARCH": "A major reinsurer reportedly declined to renew 30% of INS-X's catastrophe cover, exposing the insurer to larger retained losses next season.",
            "KEEP": "INS-X posted the date of a previously planned earnings call. It supplied no new claims, reserve or reinsurance figures.",
            "SKIP": "A semiconductor firm altered a chip packaging test procedure; no insurance contract or loss exposure is described.",
        },
    },
    "es": {
        "mining": {
            "RESEARCH": "La recuperación de la planta piloto de MINE-X habría bajado del 80 % al 50 %, lo que podría reducir la producción del próximo año; falta confirmar las muestras.",
            "KEEP": "MINE-X presentó un concepto de separación en laboratorio sin datos de recuperación, presupuesto de escala, clientes ni fecha de producción.",
            "SKIP": "Una aseguradora actualizó el diseño de su folleto comercial, sin relación indicada con minerales críticos.",
        },
        "insurance": {
            "RESEARCH": "Un reasegurador importante habría retirado una parte sustancial de la cobertura de catástrofes de INS-X; falta verificar los términos del contrato.",
            "KEEP": "INS-X confirmó la fecha prevista de su próxima llamada de resultados, sin nuevas cifras de siniestros, reservas o reaseguro.",
            "SKIP": "Una mina cambió el recorrido de su equipo geológico, sin exposición aseguradora identificada para INS-X.",
        },
    },
    "ja": {
        "mining": {
            "RESEARCH": "MINE-Xの主要鉱区で試験採掘の回収率が78％から49％に下がったとの情報がある。来年の生産目標への影響を確認する必要がある。",
            "KEEP": "MINE-Xは希土類分離の研究室向け試作品を公開したが、回収率、設備投資、顧客、量産時期は示していない。",
            "SKIP": "保険会社は家庭向け商品の広告デザインを更新したが、重要鉱物との関連は示されていない。",
        },
        "insurance": {
            "RESEARCH": "INS-Xの災害保険金の暫定額が積み立て済みの準備金を約35％上回るとの情報がある。再保険による補填額は未確認だ。",
            "KEEP": "INS-Xは予定済みの決算説明会の日程を確認した。今回、保険金請求、準備金、再保険に関する新しい数値はない。",
            "SKIP": "鉱山会社が地質調査の現地ルートを変更したが、INS-Xの保険契約との関係は示されていない。",
        },
    },
}


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


rows = []
manifest = []
for language, by_context in texts.items():
    for context_index, (context_id, by_gold) in enumerate(by_context.items()):
        for gold, information_text in by_gold.items():
            case_id = f"filehold-{len(rows)+1:02d}"
            # Across the two contexts each language has each label in both
            # DOCX and PDF, giving six files per language.
            pdf = (gold in {"RESEARCH", "SKIP"}) if context_index == 0 else (gold == "KEEP")
            suffix = ".pdf" if pdf else ".docx"
            path = FIXTURES / (case_id + suffix)
            assert not path.exists()
            if pdf:
                doc = pymupdf.open()
                page = doc.new_page()
                font = {"zh": "china-s", "ja": "japan"}.get(language, "helv")
                fit = page.insert_textbox(pymupdf.Rect(55, 80, 550, 600), information_text, fontname=font, fontsize=12, lineheight=1.6)
                assert fit >= 0
                doc.save(path)
                doc.close()
            else:
                doc = Document()
                doc.add_paragraph(information_text)
                doc.save(path)
            data = path.read_bytes()
            extracted = extract_file(path.name, data)
            exact = compact(information_text) in compact(extracted.text)
            assert exact, f"Extraction mismatch: {case_id}"
            rows.append({
                "case_id": case_id,
                "source_type": "self_authored_synthetic",
                "language": language,
                "context_id": context_id,
                "input_format": suffix[1:],
                "gold": gold,
                "information_text": information_text,
                "research_context": contexts[context_id],
                "rationale": {
                    "RESEARCH": "Potentially material new claim with a fact to verify now.",
                    "KEEP": "Relevant preliminary concept or routine date without material new facts.",
                    "SKIP": "Clearly outside this research context.",
                }[gold],
            })
            manifest.append({
                "case_id": case_id,
                "filename": path.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "language": language,
                "context_id": context_id,
                "format": suffix[1:],
                "gold": gold,
                "extraction_contains_original_without_whitespace": exact,
                "evaluated_scope": extracted.evaluated_scope,
            })
            print(case_id, language, context_id, gold, suffix, "exact")

assert len(rows) == 24
GOLD.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
digest = hashlib.sha256(GOLD.read_bytes()).hexdigest()
(ROOT / "file_holdout_v3_gold.sha256").write_text(digest + "  file_holdout_v3_gold.jsonl\n", encoding="utf-8")
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Frozen", len(rows), "files", digest)
