"""Compute immutable first-pass synthetic evaluation summaries."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEST = ROOT.parents[1] / "outputs" / "SignaLens_多语言评测结果.json"
LABELS = ("RESEARCH", "KEEP", "SKIP")


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def percentile(values: list[int], portion: float) -> int | None:
    if not values:
        return None
    values = sorted(values)
    return values[max(0, math.ceil(portion * len(values)) - 1)]


def wilson_95(successes: int, count: int) -> list[float] | None:
    if count == 0:
        return None
    z = 1.959963984540054
    p = successes / count
    denominator = 1 + z * z / count
    center = (p + z * z / (2 * count)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * count)) / count) / denominator
    return [round(center - spread, 4), round(center + spread, 4)]


def summarize(pairs: list[tuple[dict, dict]]) -> dict:
    count = len(pairs)
    correct = sum(g["gold"] == p.get("decision") for g, p in pairs)
    success = sum(p.get("decision") in LABELS for _, p in pairs)
    matrix = {gold: {prediction: 0 for prediction in (*LABELS, "ERROR")} for gold in LABELS}
    for gold, prediction in pairs:
        matrix[gold["gold"]][prediction.get("decision") if prediction.get("decision") in LABELS else "ERROR"] += 1
    r_pred = sum(matrix[gold]["RESEARCH"] for gold in LABELS)
    r_true = sum(matrix["RESEARCH"].values())
    times = [p["latency_ms"] for _, p in pairs if isinstance(p.get("latency_ms"), int)]
    return {
        "n": count,
        "correct": correct,
        "accuracy_end_to_end": round(correct / count, 4) if count else None,
        "accuracy_wilson_95": wilson_95(correct, count),
        "business_label_success": success,
        "business_label_availability": round(success / count, 4) if count else None,
        "precision_research": round(matrix["RESEARCH"]["RESEARCH"] / r_pred, 4) if r_pred else None,
        "recall_research": round(matrix["RESEARCH"]["RESEARCH"] / r_true, 4) if r_true else None,
        "research_missed_as_skip": matrix["RESEARCH"]["SKIP"],
        "confusion": matrix,
        "latency_p50_ms": percentile(times, 0.5),
        "latency_p95_ms": percentile(times, 0.95),
    }


def evaluation(name: str, gold_file: str, prediction_file: str, *, subset: bool = False) -> dict:
    gold = read(ROOT / gold_file)
    predictions = read(ROOT / prediction_file)
    ids = {row["case_id"] for row in gold}
    assert len(ids) == len(gold)
    pmap = {row["case_id"]: row for row in predictions}
    assert len(pmap) == len(predictions)
    assert set(pmap) <= ids if subset else set(pmap) == ids
    pairs = [(row, pmap[row["case_id"]]) for row in gold if row["case_id"] in pmap]
    result = {"name": name, "overall": summarize(pairs), "by_language": {}, "by_context": {}, "by_gold": {}, "by_format": {}}
    for field, output in (("language", "by_language"), ("context_id", "by_context"), ("gold", "by_gold"), ("input_format", "by_format")):
        def group_value(g: dict, p: dict) -> str:
            return p.get("input_format", g.get("input_format", "unknown")) if field == "input_format" else g.get(field, "unknown")

        groups = sorted({group_value(g, p) for g, p in pairs})
        result[output] = {value: summarize([(g, p) for g, p in pairs if group_value(g, p) == value]) for value in groups}
    result["error_cases"] = [
        {"case_id": g["case_id"], "language": g.get("language"), "context_id": g.get("context_id"), "gold": g["gold"], "decision": p.get("decision"), "error_code": p.get("error_code"), "confidence_score": p.get("confidence_score")}
        for g, p in pairs if g["gold"] != p.get("decision")
    ]
    result["rubric_versions"] = dict(Counter(p.get("rubric_version", "missing") for _, p in pairs))
    return result


def main() -> None:
    output = {
        "interpretation": "Self-authored synthetic label agreement; not real-world investment research accuracy or independent analyst ground truth.",
        "v1_multilingual_diagnostic": evaluation("v1 multilingual diagnostic", "multilingual_gold.jsonl", "multilingual_predictions_first_pass.jsonl"),
        "v2_independent_synthetic_holdout": evaluation("v2 frozen synthetic holdout", "holdout_v2_gold.jsonl", "holdout_v2_predictions_first_pass.jsonl"),
        "v1_transport_regression": evaluation("v1 old-set transport regression", "gold.jsonl", "predictions_transport_regression.jsonl"),
        "v2_crossed_file_regression": evaluation("v2 repeated-text crossed file regression", "holdout_v2_gold.jsonl", "file_probe_crossed_predictions.jsonl", subset=True),
    }
    if (ROOT / "file_holdout_v3_predictions_first_pass.jsonl").exists():
        output["v3_new_file_holdout"] = evaluation("v3 frozen synthetic file holdout", "file_holdout_v3_gold.jsonl", "file_holdout_v3_predictions_first_pass.jsonl")
    DEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(DEST)
    for key in ("v1_multilingual_diagnostic", "v2_independent_synthetic_holdout", "v1_transport_regression", "v2_crossed_file_regression", "v3_new_file_holdout"):
        if key not in output:
            continue
        block = output[key]
        print(key, block["overall"]["correct"], "/", block["overall"]["n"], block["overall"]["accuracy_end_to_end"], block["rubric_versions"])


if __name__ == "__main__":
    main()
