# Evaluation protocol

No real research labels are included. The repository contains self-authored synthetic examples and live provider predictions under [`synthetic_2026-09-20/`](synthetic_2026-09-20/README.md). Their agreement is diagnostic, not real-world accuracy or independently labeled precision and recall. Real-use cost has not been measured.

1. Start with roughly 60 boundary cases to settle the `RESEARCH / KEEP / SKIP` rubric, including a long document with one material lead. At least 20% of later cases receive two independent labels with recorded adjudication.
2. Collect naturally occurring text/PDF/Word items with the analyst's Research Context. Keep items from the same original document or event in one split. Assign development, calibration, and final holdout before model tuning. Use development for rubric/prompt changes, calibration for thresholds, and the final holdout once for acceptance.
3. A final holdout of at least 200 cases with at least 50 human `RESEARCH` cases is a **suggested minimum**, not a guarantee of narrow uncertainty. Report counts and intervals; do not claim Chinese or a file format is verified when its subgroup is small.
4. Feed every baseline the **same extracted text, scope and Context**. Run keyword rules, embedding similarity, a traditional classifier, small LLM, general LLM, and Jev. Mark a baseline `NOT_READY` if there is too little training data or no authorized model access. Do not use Jev predictions as human ground truth.
5. Report the full three-class confusion matrix, Research precision/recall, both false-SKIP denominators, end-to-end latency and unit cost. Separate pasted text, text PDF, scanned PDF, Word, Chinese and English. File extraction errors count against the end-to-end product, even if the model would have performed well on clean text.

`score.py` requires one gold JSONL and one prediction JSONL with **exactly matching case IDs**. It rejects missing/duplicate cases and invalid labels rather than silently dropping them.

Gold row example:

```json
{"case_id":"case-001","gold":"RESEARCH","language":"zh","input_format":"pdf","event_group":"event-17"}
```

Prediction row example:

```json
{"case_id":"case-001","decision":"KEEP","latency_ms":2230,"cost_usd":0.00015,"model_version":"jev-1.13.0"}
```

Run:

```bash
uv run python eval/score.py --gold /path/to/frozen_gold.jsonl --predictions /path/to/one_model_predictions.jsonl --output /path/to/report.json
```

The scorer uses only labels and metadata. Raw research content belongs in separately authorized, access-controlled storage, never in the packaged extension or public reports.
