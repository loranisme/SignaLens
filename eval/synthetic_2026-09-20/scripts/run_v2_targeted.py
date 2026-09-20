"""Post-hoc regression on six known v1 KEEP failures; not independent accuracy."""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
IDS = {"multi-05", "multi-08", "multi-11", "multi-29", "multi-35", "multi-44"}
cases = [json.loads(line) for line in (ROOT / "multilingual_gold.jsonl").read_text(encoding="utf-8").splitlines()]
assert {row["case_id"] for row in cases if row["case_id"] in IDS} == IDS
OUT = ROOT / "v2_known_failure_regression.jsonl"
assert not OUT.exists()
with httpx.Client(timeout=20.0) as client, OUT.open("w", encoding="utf-8") as output:
    for row in cases:
        if row["case_id"] not in IDS:
            continue
        started = time.perf_counter()
        result = {"case_id": row["case_id"]}
        try:
            response = client.post("http://127.0.0.1:8765/api/evaluate", json={
                "information_text": row["information_text"],
                "research_context": row["research_context"],
            })
            body = response.json()
            result["http_status"] = response.status_code
            if response.status_code == 200:
                result.update({key: body[key] for key in ("decision", "confidence_score", "model_version", "rubric_version")})
            else:
                result["error_code"] = body.get("error_code", "UNKNOWN_ERROR")
        except Exception as error:
            result.update({"error_code": type(error).__name__, "http_status": None})
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        output.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        output.flush()
        print(row["case_id"], row["gold"], result.get("decision", result.get("error_code")), result["latency_ms"], flush=True)
        time.sleep(max(0, 2.2 - result["latency_ms"] / 1000))
