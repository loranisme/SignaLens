# SignaLens 多语言测试数据

所有文字、公司代号与数值均由实施者编写，`source_type=self_authored_synthetic`。这些是产品诊断题，不是真实公告、研报或独立研究员标签；不得将一致率称为真实投研正确率。

## 版本与用途

| 文件 | 用途 |
| --- | --- |
| `multilingual_gold.jsonl`、`multilingual_predictions_first_pass.jsonl` | 48 条中英西日语、四种 Context 的 v1 开发诊断；原始标签与首轮预测 |
| `holdout_v2_gold.jsonl`、`holdout_v2_predictions_first_pass.jsonl` | 修改文本口径前冻结的 48 条新题；v2 首轮预测 |
| `file_probe_crossed_manifest.json`、`file_probe_crossed_predictions.jsonl`、`file_probes_crossed/` | 重复 v2 文本，交叉四种语言、两个 Context、PDF/Word 的 16 份文件回归；不可与 48 条相加 |
| `file_holdout_v3_gold.jsonl`、`file_holdout_v3_manifest.json`、`file_holdout_v3/`、`file_holdout_v3_predictions_first_pass.jsonl` | 修改文件口径前冻结的 24 份新 PDF/Word 与 v3 首轮预测 |
| `v3_known_file_failure_regression.jsonl`、`v3_file_error_paired_text.jsonl` | 事后诊断：两条 v2 文件错误的回归，以及 v3 两条新文件错误的同文字粘贴配对；均不算独立样本 |
| `v3_long_one_lead.docx`、`v3_long_one_lead_result.json` | 旧合成材料的全文聚合事后回归；不能加入封存集分母 |
| `v2_known_failure_regression.jsonl` | v1 已知六条错误的事后回归，不是独立测试 |
| `predictions_transport_regression.jsonl` | 旧 36 条样本的连接回归，不能作为新质量验证 |
| `scripts/` | 生成、哈希验证、首轮运行和指标脚本的副本；运行需本地项目依赖和已启动 API |

`.sha256` 文件存储冻结文本集哈希；每份 PDF/Word 的 SHA-256 见对应 manifest。预测记录只含 case ID、三档结果、把握度、版本和耗时，不含 API key。文件测试保留每条服务失败及错误码，不用重试覆盖首轮结果。

按 [评测报告](../../docs/multilingual-evaluation-2026-09-20.md) 阅读数字和限制。
