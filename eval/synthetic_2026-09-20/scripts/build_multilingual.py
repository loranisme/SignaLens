"""Freeze an independently worded, multilingual synthetic diagnostic set.

All labels and rationales are authored before provider calls. This is a
synthetic agreement test, not a human-labelled field accuracy estimate.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "multilingual_gold.jsonl"
assert not OUT.exists(), "Refuse to overwrite frozen cases"

contexts = {
    "chips": {"research_areas": ["Semiconductor Equipment", "AI Compute"], "watchlist": ["CHIP-X"], "investment_horizon": "6_24m"},
    "bio": {"research_areas": ["Biotechnology", "Clinical Trials"], "watchlist": ["BIO-X"], "investment_horizon": "gt_24m"},
    "retail": {"research_areas": ["Consumer Retail"], "watchlist": ["SHOP-X"], "investment_horizon": "lt_6m"},
    "grid": {"research_areas": ["Electric Grid", "Power Equipment"], "watchlist": ["GRID-X"], "investment_horizon": "6_24m"},
}

# Each language has one RESEARCH, KEEP and SKIP case in each context.
# For SKIP, some texts contain potentially material facts in another field:
# relevance must be judged against the supplied context.
items = {
    "zh": {
        "chips": {
            "RESEARCH": "CHIP-X 的封装设备试产验收率据称从 92% 降到 61%，两家客户暂停了新增订单；需核对验收口径和订单状态。",
            "KEEP": "CHIP-X 公布下月技术交流会的日期，议程包含先进封装；没有公布新设备参数、客户或订单。",
            "SKIP": "一家连锁咖啡店调整三家门店的背景音乐，未涉及电子设备或半导体采购。",
        },
        "bio": {
            "RESEARCH": "BIO-X 的关键三期试验据称因独立监测委员会发现疗效差距而提前停止，正式披露尚未发布；需核查停试原因。",
            "KEEP": "BIO-X 提醒投资者，已知的三期试验将在下月更新读出时间表；本次通知没有患者数据或方案变化。",
            "SKIP": "一家包装设备公司称半导体产线良率下降三成；文本没有生物医药应用或 BIO-X 关联。",
        },
        "retail": {
            "RESEARCH": "SHOP-X 本月同店销售初步同比下滑 11%，此前季度指引为增长 3%；应核查门店覆盖范围和退货口径。",
            "KEEP": "SHOP-X 将在两个月后介绍新的会员活动，今天没有披露销售、客单价或利润目标。",
            "SKIP": "一家地方天文馆周末延长开放一小时，并新增儿童讲解场次。",
        },
        "grid": {
            "RESEARCH": "GRID-X 的大型变压器交付期据称由 14 个月延长至 26 个月，三个数据中心项目已重新排期；应核查产能瓶颈。",
            "KEEP": "GRID-X 宣布下一季度举行产能说明会，暂未发布扩产金额、投产日期或新增合同。",
            "SKIP": "某药企披露一项肿瘤试验的入组速度加快；文中没有电网负荷或电力设备联系。",
        },
    },
    "en": {
        "chips": {
            "RESEARCH": "A customer says CHIP-X's new lithography module missed acceptance on four of six pilot lines, potentially delaying next quarter's orders; the failure cause is unconfirmed.",
            "KEEP": "CHIP-X scheduled a packaging technology day for next month. The announcement includes no specifications, customer commitments or shipment targets.",
            "SKIP": "The city museum replaced the signs outside its sculpture garden and changed weekend tour times.",
        },
        "bio": {
            "RESEARCH": "An interim monitor reportedly found the primary endpoint in BIO-X's pivotal trial was unlikely to be met; the company has not released the analysis.",
            "KEEP": "BIO-X confirmed the date of an already announced trial update. No efficacy, safety or enrollment figures were provided today.",
            "SKIP": "A chipmaker reported a 30% fall in its advanced packaging yield; the note identifies no healthcare application or link to BIO-X.",
        },
        "retail": {
            "RESEARCH": "SHOP-X's preliminary weekly transactions fell 17% across most regions while management had guided to mid-single-digit growth; coverage and calendar effects need checking.",
            "KEEP": "SHOP-X will hold a loyalty-program briefing in six weeks. The notice contains no new traffic, basket-size or margin data.",
            "SKIP": "A local rowing club moved its annual picnic to a different park and updated the event logo.",
        },
        "grid": {
            "RESEARCH": "GRID-X reportedly lost its only qualified supplier for a critical transformer core, putting delivery dates for two contracted substations at risk; alternatives are unknown.",
            "KEEP": "GRID-X published the agenda for next month's factory tour. No capacity, backlog or delivery figures were released.",
            "SKIP": "A biotech company changed its clinical trial recruitment target; the text contains no power infrastructure link.",
        },
    },
    "es": {
        "chips": {
            "RESEARCH": "Un cliente afirma que el rendimiento de un equipo de CHIP-X bajó del 88 % al 54 % en la línea piloto y que dos pedidos quedaron en revisión; falta confirmar la causa.",
            "KEEP": "CHIP-X anunció una presentación técnica para el próximo mes, sin nuevos datos de rendimiento, clientes ni entregas.",
            "SKIP": "La biblioteca municipal cambió el horario de sus talleres de lectura infantil durante los sábados.",
        },
        "bio": {
            "RESEARCH": "Según una nota preliminar, el ensayo decisivo de BIO-X podría no alcanzar su objetivo principal; todavía no hay resultados oficiales y conviene verificarlo.",
            "KEEP": "BIO-X comunicó la fecha de publicación de unos resultados ya previstos; hoy no aportó datos de eficacia ni seguridad.",
            "SKIP": "Un fabricante de semiconductores informó de retrasos en equipos de grabado, sin relación indicada con ensayos clínicos ni BIO-X.",
        },
        "retail": {
            "RESEARCH": "Las ventas comparables preliminares de SHOP-X cayeron un 12 % este mes frente a una previsión de crecimiento del 4 %; es necesario comprobar la base de tiendas.",
            "KEEP": "SHOP-X anunció una reunión sobre su programa de fidelización para el trimestre próximo, sin objetivos nuevos de ventas o margen.",
            "SKIP": "Un centro cultural renovó los carteles de su exposición de cerámica y cambió la hora de apertura del domingo.",
        },
        "grid": {
            "RESEARCH": "Los plazos de entrega de transformadores de GRID-X habrían aumentado de 12 a 22 meses y dos proyectos firmados podrían retrasarse; falta verificar el atasco.",
            "KEEP": "GRID-X fijó la fecha de una visita a fábrica para analistas, pero no publicó cifras de capacidad, cartera de pedidos ni entregas.",
            "SKIP": "Una empresa farmacéutica revisó el calendario de un estudio oncológico, sin vínculo indicado con la red eléctrica.",
        },
    },
    "ja": {
        "chips": {
            "RESEARCH": "CHIP-Xの新型製造装置について、試験ラインの合格率が90％から58％に低下し、顧客２社が発注を保留したとの情報がある。原因と受注への影響は未確認。",
            "KEEP": "CHIP-Xは来月の技術説明会の日程を発表したが、新しい性能値、顧客名、出荷計画は示していない。",
            "SKIP": "市立図書館は週末の読み聞かせ会を一時間早め、会場の案内板を交換した。",
        },
        "bio": {
            "RESEARCH": "BIO-Xの主要な第３相試験で主要評価項目を達成できない可能性があるとする暫定情報が出た。正式発表はなく、根拠の確認が必要だ。",
            "KEEP": "BIO-Xは既知の臨床試験結果の発表日を確認した。今回、効果、安全性、患者数に関する新データはない。",
            "SKIP": "半導体メーカーが製造装置の納期遅延を報告したが、医薬品開発やBIO-Xとの関連は示されていない。",
        },
        "retail": {
            "RESEARCH": "SHOP-Xの今月の既存店売上高は速報値で前年同月比13％減となり、会社の増収見通しから大きく外れた。対象店舗と返品の扱いを確認したい。",
            "KEEP": "SHOP-Xは来四半期に会員制度の説明会を開くと発表したが、客数や利益率の新しい数値はない。",
            "SKIP": "地元の美術館は陶芸展のポスターを更新し、日曜日の開館時間を変更した。",
        },
        "grid": {
            "RESEARCH": "GRID-Xの大型変圧器の納期が従来の15か月から27か月へ延び、契約済みの変電所２件の稼働時期に影響する可能性がある。",
            "KEEP": "GRID-Xは来月の工場見学会の予定を公表した。生産能力や受注残、納期の新しい数字はない。",
            "SKIP": "製薬会社はがん治験の登録期間を変更したが、電力設備や送電網との関係は示されていない。",
        },
    },
}

rows = []
for lang, by_context in items.items():
    for context_name, by_label in by_context.items():
        for gold, information_text in by_label.items():
            rows.append({
                "case_id": f"multi-{len(rows)+1:02d}",
                "source_type": "self_authored_synthetic",
                "language": lang,
                "context_id": context_name,
                "input_format": "pasted_text",
                "gold": gold,
                "research_context": contexts[context_name],
                "information_text": information_text,
                "rationale": {
                    "RESEARCH": "A specific potentially material claim has a concrete verification question in this context.",
                    "KEEP": "Relevant schedule or preview without new operating evidence to investigate now.",
                    "SKIP": "No meaningful connection to the supplied research context or incremental research value.",
                }[gold],
            })

assert len(rows) == 48
assert all(sum(row["gold"] == label for row in rows if row["language"] == lang) == 4 for lang in items for label in ("RESEARCH", "KEEP", "SKIP"))
OUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
(ROOT / "multilingual_gold.sha256").write_text(digest + "  multilingual_gold.jsonl\n", encoding="utf-8")
print(f"Frozen {len(rows)} cases, SHA256 {digest}")
