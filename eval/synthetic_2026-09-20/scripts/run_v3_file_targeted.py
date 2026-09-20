"""Post-hoc file regression for the two known v2 KEEP failures."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
MANIFEST = [x for x in json.loads((ROOT / "file_probe_crossed_manifest.json").read_text(encoding="utf-8")) if x["case_id"] in {"hold-35", "hold-47"}]
assert {x["case_id"] for x in MANIFEST} == {"hold-35", "hold-47"}
GOLD = {row["case_id"]: row for row in map(json.loads, (ROOT / "holdout_v2_gold.jsonl").read_text(encoding="utf-8").splitlines())}
OUT = ROOT / "v3_known_file_failure_regression.jsonl"
assert not OUT.exists()
with httpx.Client(timeout=40.0) as client, OUT.open("w", encoding="utf-8") as output:
    for item in MANIFEST:
        row = GOLD[item["case_id"]]
        path = ROOT / "file_probes_crossed" / item["filename"]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
        started = time.perf_counter()
        result = {"case_id": item["case_id"]}
        try:
            response = client.post(
                "http://127.0.0.1:8765/api/evaluate",
                data={"research_context": json.dumps(row["research_context"], ensure_ascii=False)},
                files={"file": (path.name, data)},
            )
            body = response.json()
            result["http_status"] = response.status_code
            if response.status_code == 200:
                result.update({key: body.get(key) for key in ("decision", "confidence_score", "model_version", "rubric_version", "input_format", "evaluated_scope")})
            else:
                result["error_code"] = body.get("error_code", "UNKNOWN_ERROR")
        except Exception as error:
            result.update({"error_code": type(error).__name__, "http_status": None})
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        output.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        output.flush()
        print(item["case_id"], row["gold"], result.get("decision", result.get("error_code")), result["latency_ms"], flush=True)
        time.sleep(max(0, 2.2 - result["latency_ms"] / 1000))
