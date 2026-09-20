import json

import pytest

from eval.score import score


def _write(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_false_skip_uses_both_denominators(tmp_path):
    gold = tmp_path / "gold.jsonl"
    predictions = tmp_path / "pred.jsonl"
    _write(gold, [
        {"case_id": "a", "gold": "RESEARCH", "language": "zh", "input_format": "pdf"},
        {"case_id": "b", "gold": "RESEARCH", "language": "zh", "input_format": "pdf"},
        {"case_id": "c", "gold": "KEEP", "language": "en", "input_format": "text"},
        {"case_id": "d", "gold": "SKIP", "language": "en", "input_format": "text"},
    ])
    _write(predictions, [
        {"case_id": "a", "decision": "RESEARCH", "latency_ms": 1000},
        {"case_id": "b", "decision": "SKIP", "latency_ms": 1200},
        {"case_id": "c", "decision": "KEEP", "latency_ms": 1400},
        {"case_id": "d", "decision": "SKIP", "latency_ms": 1600},
    ])
    report = score(gold, predictions)
    assert report["overall"]["recall_research"] == 0.5
    assert report["overall"]["false_skip_miss_rate"] == 0.5
    assert report["overall"]["research_missed_as_skip"] == 0.5
    assert report["overall"]["latency_p95_ms"] == 1600
    assert report["groups"]["input_format:pdf"]["count"] == 2


def test_missing_prediction_is_an_error(tmp_path):
    gold = tmp_path / "gold.jsonl"
    predictions = tmp_path / "pred.jsonl"
    _write(gold, [{"case_id": "a", "gold": "RESEARCH"}, {"case_id": "b", "gold": "KEEP"}])
    _write(predictions, [{"case_id": "a", "decision": "RESEARCH"}])
    with pytest.raises(ValueError, match="prediction IDs differ"):
        score(gold, predictions)
