"""Score frozen human labels against one model's predictions without raw content."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

LABELS = ("RESEARCH", "KEEP", "SKIP")


def read_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: invalid JSON") from exc
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path}:{number}: case_id is required")
        if case_id in rows:
            raise ValueError(f"{path}:{number}: duplicate case_id {case_id}")
        rows[case_id] = row
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    index = math.ceil(fraction * len(sorted_values)) - 1
    return round(sorted_values[max(0, index)], 3)


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def summarize(rows: list[tuple[dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    confusion = {gold: {pred: 0 for pred in LABELS} for gold in LABELS}
    times: list[float] = []
    costs: list[float] = []
    for gold, prediction in rows:
        confusion[gold["gold"]][prediction["decision"]] += 1
        if "latency_ms" in prediction:
            times.append(float(prediction["latency_ms"]))
        if "cost_usd" in prediction:
            costs.append(float(prediction["cost_usd"]))
    tp = confusion["RESEARCH"]["RESEARCH"]
    predicted_research = sum(confusion[label]["RESEARCH"] for label in LABELS)
    actual_research = sum(confusion["RESEARCH"].values())
    predicted_skip = sum(confusion[label]["SKIP"] for label in LABELS)
    false_skip = confusion["RESEARCH"]["SKIP"]
    return {
        "count": len(rows),
        "gold_counts": {label: sum(confusion[label].values()) for label in LABELS},
        "predicted_counts": {label: sum(confusion[gold][label] for gold in LABELS) for label in LABELS},
        "confusion": confusion,
        "precision_research": ratio(tp, predicted_research),
        "recall_research": ratio(tp, actual_research),
        "false_skip_miss_rate": ratio(false_skip, predicted_skip),
        "research_missed_as_skip": ratio(false_skip, actual_research),
        "latency_p50_ms": percentile(times, 0.5),
        "latency_p95_ms": percentile(times, 0.95),
        "latency_coverage": len(times),
        "cost_per_1000_usd": round(sum(costs) / len(costs) * 1000, 6) if costs else None,
        "cost_coverage": len(costs),
    }


def score(gold_path: Path, prediction_path: Path) -> dict[str, Any]:
    gold = read_jsonl(gold_path)
    predicted = read_jsonl(prediction_path)
    if set(gold) != set(predicted):
        missing = sorted(set(gold) - set(predicted))
        extra = sorted(set(predicted) - set(gold))
        raise ValueError(f"prediction IDs differ: missing={missing[:5]}, extra={extra[:5]}")
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for case_id in sorted(gold):
        row, prediction = gold[case_id], predicted[case_id]
        if row.get("gold") not in LABELS or prediction.get("decision") not in LABELS:
            raise ValueError(f"invalid label on case {case_id}")
        for name in ("latency_ms", "cost_usd"):
            if name in prediction:
                value = prediction[name]
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError(f"invalid {name} on case {case_id}")
        pairs.append((row, prediction))
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for row, prediction in pairs:
        for field in ("language", "input_format"):
            grouped[f"{field}:{row.get(field, 'unknown')}"].append((row, prediction))
    return {
        "overall": summarize(pairs),
        "groups": {name: summarize(group) for name, group in sorted(grouped.items())},
        "note": "Human intake labels are a proxy for usefulness; this report does not measure live investment outcomes.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = score(args.gold, args.predictions)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
