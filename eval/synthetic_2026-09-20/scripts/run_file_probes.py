"""End-to-end upload probes; repeated holdout content, not independent accuracy."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "file_probe_manifest.json").read_text(encoding="utf-8"))
GOLD = {row["case_id"]: row for row in map(json.loads, (ROOT / "holdout_v2_gold.jsonl").read_text(encoding="utf-8").splitlines())}
OUT = ROOT / "file_probe_predictions.jsonl"
assert not OUT.exists(), "Refuse to overwrite first-pass file probes"
started_at = datetime.now(timezone.utc).isoformat()

with httpx.Client(timeout=40.0) as client, OUT.open("w", encoding="utf-8") as output:
    for item in MANIFEST:
        row = GOLD[item["case_id"]]
        path = ROOT / "file_probes" / item["filename"]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
        started = time.perf_counter()
        result = {"case_id": row["case_id"], "input_format": item["format"]}
        try:
            response = client.post(
                "http://127.0.0.1:8765/api/evaluate",
                data={"research_context": json.dumps(row["research_context"], ensure_ascii=False)},
                files={"file": (path.name, data)},
            )
            body = response.json()
            result["http_status"] = response.status_code
            if response.status_code == 200:
                result.update({key: body.get(key) for key in ("decision", "confidence_score", "model_version", "rubric_version", "input_format", "evaluated_scope", "extraction_ms")})
            else:
                result["error_code"] = body.get("error_code", "UNKNOWN_ERROR")
        except Exception as error:
            result.update({"error_code": type(error).__name__, "http_status": None})
        result["latency_ms"] = round((time.perf_counter() - started) * 1000)
        output.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        output.flush()
        print(row["case_id"], item["language"], item["format"], row["gold"], result.get("decision", result.get("error_code")), result["latency_ms"], flush=True)
        time.sleep(max(0, 2.2 - result["latency_ms"] / 1000))

(ROOT / "file_probe_run_manifest.json").write_text(json.dumps({
    "started_at_utc": started_at,
    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    "n_probes": len(MANIFEST),
    "purpose": "file_extraction_and_transport_regression_not_independent_quality_validation",
}, indent=2) + "\n", encoding="utf-8")
