"""Freeze a new multilingual/context holdout before testing rubric v2."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "holdout_v2_gold.jsonl"
assert not OUT.exists(), "Refuse to overwrite frozen holdout"

contexts = {
    "solar": {"research_areas": ["Solar Manufacturing", "Energy Storage"], "watchlist": ["SOL-X"], "investment_horizon": "6_24m"},
    "bank": {"research_areas": ["Regional Banks", "Credit Quality"], "watchlist": ["BANK-X"], "investment_horizon": "lt_6m"},
    "shipping": {"research_areas": ["Container Shipping", "Freight Rates"], "watchlist": ["SHIP-X"], "investment_horizon": "6_24m"},
    "devices": {"research_areas": ["Medical Devices", "Regulatory Approval"], "watchlist": ["MED-X"], "investment_horizon": "gt_24m"},
}

# One of each label per context and language. This is independent of the
# diagnostic set; the author still supplies the labels, so no field-accuracy
# claim is permitted.
items = {
    "zh": {
        "solar": {
            "RESEARCH": "SOL-X 的新电池产线连续三批量产良率低于 60%，此前管理层预计本季度达到 85%；需要核查缺陷与出货影响。",
            "KEEP": "SOL-X 宣布三个月后举办新品交流会，今天仅公布会场和议程，没有效率、成本或量产数据。",
            "SKIP": "集装箱航运协会公布了港口收费变更，材料没有太阳能或储能供应链联系。",
        },
        "bank": {
            "RESEARCH": "BANK-X 内部月报显示商业地产贷款逾期率由 2.1% 升至 5.4%，同时拨备覆盖率下降；统计范围尚待核实。",
            "KEEP": "BANK-X 将在下周已预告的投资者活动中讨论信贷质量，本次只确认参会时间，没有新风险数据。",
            "SKIP": "某博物馆新开了一家纪念品店，并调整了周末导览路线。",
        },
        "shipping": {
            "RESEARCH": "SHIP-X 最大航线的有效运价据称较上月下降 28%，三家客户正重新谈判年度合同；需要核对合同覆盖面。",
            "KEEP": "SHIP-X 在行业会议预告中列出一场运价展望讨论，但尚未提供运量、合同价格或舱位变化。",
            "SKIP": "一家医疗器械公司收到新的试验反馈，但材料未显示与航运需求或运价有关。",
        },
        "devices": {
            "RESEARCH": "MED-X 的核心植入器械据称在监管审查中被要求补做关键耐久性试验，上市时间可能推迟一年；官方文件待核查。",
            "KEEP": "MED-X 完成了非核心配件的小范围内部演示，尚无性能指标、监管路径或商业化时间。",
            "SKIP": "银行业协会发布地区贷款利率统计，文中没有医疗器械采购或 MED-X 关联。",
        },
    },
    "en": {
        "solar": {
            "RESEARCH": "SOL-X reportedly paused a battery line after a defect affected 38% of pilot cells; two customers have deferred qualification pending a root-cause review.",
            "KEEP": "SOL-X announced the date of a product showcase. It released no efficiency, cost, yield or customer information today.",
            "SKIP": "A regional bank changed its branch opening hours; the note identifies no solar or storage connection.",
        },
        "bank": {
            "RESEARCH": "BANK-X's preliminary nonperforming commercial loans rose from 3% to 7% of that book in one quarter, according to an unverified internal summary.",
            "KEEP": "BANK-X scheduled a previously announced credit update for next month. The notice gives no new delinquencies, reserves or exposures.",
            "SKIP": "The local aquarium moved its evening tour from Thursday to Friday and changed the ticket artwork.",
        },
        "shipping": {
            "RESEARCH": "A major SHIP-X customer reportedly shifted 22% of its contracted cargo to a rival after repeated delays; the contract and volume impact need checking.",
            "KEEP": "SHIP-X confirmed its attendance at a maritime conference but released no fresh freight, volume, utilization or contract figures.",
            "SKIP": "A medical device maker published a regulatory timetable with no stated relation to cargo volumes or shipping rates.",
        },
        "devices": {
            "RESEARCH": "A regulator reportedly requested a new pivotal safety study for MED-X's main implant, which could delay approval by more than a year; the request is unconfirmed.",
            "KEEP": "MED-X described an early concept demonstration for an accessory, without performance results, funding, regulatory pathway or launch timing.",
            "SKIP": "A freight operator cut container rates on an ocean route; no link to device procurement or MED-X is given.",
        },
    },
    "es": {
        "solar": {
            "RESEARCH": "Tres lotes de la nueva línea de SOL-X habrían tenido un rendimiento inferior al 62 %, frente al objetivo del 86 % para este trimestre; faltan detalles del defecto.",
            "KEEP": "SOL-X confirmó una presentación de producto para dentro de dos meses, pero hoy no dio cifras de eficiencia, costes, producción ni clientes.",
            "SKIP": "Una naviera anunció un cambio de horario en su ruta atlántica, sin relación indicada con la fabricación solar o el almacenamiento.",
        },
        "bank": {
            "RESEARCH": "La morosidad preliminar de los préstamos inmobiliarios de BANK-X habría pasado del 2 % al 6 % en un trimestre; es necesario confirmar la muestra.",
            "KEEP": "BANK-X publicará el mes próximo una actualización crediticia ya prevista; el aviso de hoy no incluye morosidad, provisiones ni exposición nueva.",
            "SKIP": "Un museo municipal reorganizó las salas de su exposición y cambió el horario de las visitas guiadas.",
        },
        "shipping": {
            "RESEARCH": "Un cliente importante de SHIP-X habría trasladado una cuarta parte de su carga contratada a otra naviera tras varios retrasos; falta verificar el contrato.",
            "KEEP": "SHIP-X figura en el programa de un congreso marítimo, sin publicar nuevos datos de tarifas, volumen, ocupación o contratos.",
            "SKIP": "Una empresa de dispositivos médicos revisó su calendario regulatorio, sin vínculo indicado con transporte de contenedores.",
        },
        "devices": {
            "RESEARCH": "El regulador habría exigido a MED-X un nuevo ensayo de seguridad para su implante principal, lo que podría retrasar su aprobación más de un año.",
            "KEEP": "MED-X mostró un prototipo de accesorio en una demostración interna; no hay resultados de rendimiento, financiación ni plan regulatorio.",
            "SKIP": "Un banco regional informó de cambios en su cartera de crédito, sin relación indicada con compras de equipos médicos.",
        },
    },
    "ja": {
        "solar": {
            "RESEARCH": "SOL-Xの新しい電池ラインで３回連続の生産歩留まりが60％を下回り、四半期目標の85％から大きく離れたとの情報がある。原因は未確認。",
            "KEEP": "SOL-Xは２か月後の新製品説明会の日程を発表したが、効率、原価、量産、顧客の新しい数値はない。",
            "SKIP": "海運会社は地方港の寄港時刻を変更したが、太陽電池や蓄電池との関係は示されていない。",
        },
        "bank": {
            "RESEARCH": "BANK-Xの商業不動産融資の延滞率が四半期で2％から6％に上がったとの暫定資料がある。対象債権と引当金への影響を確認する必要がある。",
            "KEEP": "BANK-Xは予定済みの信用状況説明会の日程を確認した。今回、延滞率、引当金、融資残高の新しい数値はない。",
            "SKIP": "市の水族館は週末の見学ルートを変更し、入場券のデザインを更新した。",
        },
        "shipping": {
            "RESEARCH": "SHIP-Xの主要顧客が遅延を理由に契約貨物の約25％を競合へ移したとの情報がある。契約条件と運賃への影響は未確認。",
            "KEEP": "SHIP-Xは来月の海運会議への参加を公表したが、運賃、輸送量、稼働率、契約の新情報はない。",
            "SKIP": "医療機器メーカーが承認申請の予定を更新したが、コンテナ輸送との関係は示されていない。",
        },
        "devices": {
            "RESEARCH": "MED-Xの主力インプラントについて、規制当局が追加の安全性試験を求め、承認が１年以上遅れる可能性があるとの未確認情報が出た。",
            "KEEP": "MED-Xは周辺機器の社内向け試作品を公開したが、性能試験、規制計画、発売時期は示していない。",
            "SKIP": "地方銀行の貸出金利に関する資料で、医療機器の調達やMED-Xとの関連は示されていない。",
        },
    },
}

rows = []
for language, by_context in items.items():
    for context_id, by_label in by_context.items():
        for label, text in by_label.items():
            rows.append({
                "case_id": f"hold-{len(rows)+1:02d}",
                "source_type": "self_authored_synthetic",
                "language": language,
                "context_id": context_id,
                "input_format": "pasted_text",
                "gold": label,
                "research_context": contexts[context_id],
                "information_text": text,
                "rationale": {
                    "RESEARCH": "A specific potentially material change has a concrete question to check now.",
                    "KEEP": "Related future event or preliminary low-information item, with no new material facts to check now.",
                    "SKIP": "Clearly outside this context with no indicated indirect link.",
                }[label],
            })

assert len(rows) == 48
assert all(sum(row["gold"] == label for row in rows if row["language"] == language) == 4 for language in items for label in ("RESEARCH", "KEEP", "SKIP"))
OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
(ROOT / "holdout_v2_gold.sha256").write_text(digest + "  holdout_v2_gold.jsonl\n", encoding="utf-8")
print(f"Frozen {len(rows)} holdout cases, SHA256 {digest}")
