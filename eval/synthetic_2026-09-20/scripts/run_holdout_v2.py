"""One pass over the frozen v2 holdout; never replace first-pass results."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
GOLD = ROOT / "holdout_v2_gold.jsonl"
EXPECTED = (ROOT / "holdout_v2_gold.sha256").read_text(encoding="utf-8").split()[0]
assert hashlib.sha256(GOLD.read_bytes()).hexdigest() == EXPECTED
OUT = ROOT / "holdout_v2_predictions_first_pass.jsonl"
assert not OUT.exists(), "Refuse to overwrite holdout predictions"

cases = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines()]
started_at = datetime.now(timezone.utc).isoformat()
with httpx.Client(timeout=20.0) as client, OUT.open("w", encoding="utf-8") as output:
    for row in cases:
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
        print(row["case_id"], row["language"], row["context_id"], row["gold"], result.get("decision", result.get("error_code")), result["latency_ms"], flush=True)
        time.sleep(max(0, 2.2 - result["latency_ms"] / 1000))

(ROOT / "holdout_v2_run_manifest.json").write_text(json.dumps({
    "gold_sha256": EXPECTED,
    "started_at_utc": started_at,
    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    "n_cases": len(cases),
    "source_type": "self_authored_synthetic",
    "purpose": "first_pass_multilingual_v2_holdout",
    "labels_frozen_before_rubric_edit": True,
}, indent=2) + "\n", encoding="utf-8")
