# SignaLens

**投研信息分流浏览器插件**：把一段文字或一份文档交给 SignaLens，它结合你的研究方向，返回 `RESEARCH`、`KEEP` 或 `SKIP`。旧方案中的名称 ResearchGate 已统一为 **SignaLens**。

> 当前版本是需要在本机启动 API 的开源 MVP，已在 Chrome 本地开发模式验证。它尚未上架浏览器商店，也没有面向所有人可直接使用的托管服务。

## 它做什么

| 结果 | 含义 |
| --- | --- |
| `RESEARCH` | 现在值得投入额外时间核查或继续研究。 |
| `KEEP` | 有相关性或潜在价值，先保留，暂时不用深入。 |
| `SKIP` | 对当前研究范围的边际价值较低。 |

- **输入**：粘贴文本，或上传单个 `.txt`、`.md`、`.pdf`、`.docx`、`.doc` 文件，文件上限 20 MB。默认评估整份文档中可提取的文字。扫描 PDF 可以通过 Tesseract OCR 提取文字；图表和图片的含义不在当前判断范围内。
- **Research Context**：填写 Research Areas（研究领域）或 Watchlist（关注公司/代码），并选择 Investment Horizon（投资期限）。这些信息是判断相关性的上下文，不是自动关注、联网跟踪或投资组合功能。
- **输出**：固定三档、Jev 模型把握度和一条简短说明。把握度表示模型输出分布的倾向，**不是校准后的判对概率**。
- **超长内容**：估算超过约 12,000 token 时拒绝给出决定；PDF 可选页码，DOCX 可选章节。不会静默截断或自动总结后再判断。
- **错误处理**：空输入、无效文件、OCR 失败、服务或模型错误会显示错误，不会伪造 `SKIP`。

侧边栏是唯一的用户界面。当前版本不会自动抓网页、做深度研究、生成研报、给出买卖建议或交易。

## 本地运行（已验证环境：macOS + Chrome）

需要 Python 3.11+、[uv](https://docs.astral.sh/uv/)、Chrome，以及你自己的 **TypeSafe Jev API key**。Jev 是外部服务；本仓库开源的是插件、提取与分流调用代码，**不包含 Jev 模型或免费 API 额度**。

```bash
git clone https://github.com/loranisme/SignaLens.git
cd SignaLens
uv sync
bash scripts/setup_ocr_macos.sh  # 需要扫描 PDF 的 OCR 时运行
bash scripts/run_local.sh
```

`run_local.sh` 会在终端隐藏输入 API key。不要把 key 粘贴到插件、Issue 或提交中。服务重启后需要重新输入。API 只监听 `127.0.0.1:8765`，终端要保持运行；`http://127.0.0.1:8765/api/health` 可检查服务状态。

随后打开 Chrome 的 `chrome://extensions`，开启**开发者模式**，点击**加载已解压的扩展程序**，选择仓库内的 `extension/` 文件夹。点击工具栏中的 SignaLens 图标打开侧边栏，设置 Research Context 后提交文字或文件。Edge 的实际安装与交互尚未验收。

普通文本 PDF 和 DOCX 使用项目依赖提取文字；旧版 `.doc` 在 macOS 上依赖系统 `textutil`。`setup_ocr_macos.sh` 使用 Homebrew 安装 Tesseract，并校验中文简体 OCR 数据的 SHA-256。当前仅对少量合成 `.doc` 和扫描 PDF 做过功能检查，复杂文件的保真度仍需验证。

## 目前效果（2026-09-20）

以下数字来自**实施者自拟、自己标注的合成材料**。测试集刻意平衡三档，并不能代表真实信息流中的正确率；尤其不能据此宣称产品已达到真实场景 **90% 准确率**。

| 测试 | 首轮与预设标签一致 | 覆盖与说明 |
| --- | ---: | --- |
| v1 新文本诊断 | 42/48（87.5%） | 中文、英文、西班牙文、日文；4 组 Research Context。6 条 `KEEP` 判为 `RESEARCH`。 |
| v2 新文本封存集 | 48/48（100%） | 四种语言、4 组新 Context；修改文本规则前冻结，标签仍由同一人编写。 |
| v2 PDF/Word 交叉回归 | 14/16（87.5%） | 文件文字 16/16 完整提取；内容复用了 v2 文本，不能加到 48 条独立样本里。 |
| v3 新 PDF/Word 封存集 | 22/24（91.7%） | 四种语言、2 组新 Context、三档、PDF 与 Word；文字 24/24 完整提取，24/24 返回三档。两条保险 Context 下的西语/日语 `SKIP` 误判。 |

v3 文件集在本机脚本到本地 API 的请求耗时为 **P50 348 ms、P95 892 ms**，包含文件提取与 Jev 调用；这不是插件用户操作的端到端时间，也不是高并发或长期稳定性证明。成本尚未测量。Chrome 侧边栏的文字、DOCX、扫描 PDF 和 Context 保存做过手工检查；Edge 尚未检查。

完整口径、逐条记录、冻结哈希及失败分析见[多语言评测报告](docs/multilingual-evaluation-2026-09-20.md)、[机器可读结果](eval/synthetic_2026-09-20/summary.json)与[合成测试数据](eval/synthetic_2026-09-20/README.md)。正式的 90% 验收仍需自然来源信息、独立研究员标签和按语言、文件格式、Context 分组的封存测试集。

## 架构与隐私

```text
Chrome 侧边栏 → 本机 API（文字提取） → TypeSafe Jev → RESEARCH / KEEP / SKIP
```

扩展权限仅包括 `sidePanel`、`storage` 和本机 `http://127.0.0.1:8765/*` 的主机访问。它不读取当前网页、不注入内容脚本、不访问浏览历史。Research Context 保存在浏览器本地存储中；API key 在本机服务进程的环境变量中，脚本不会写入文件。提交的原文会发送给 **TypeSafe Jev** 判断，请只提交你有权交由该服务处理的材料。

本机 API 的来源限制与速率限制面向单人本地使用；它不是可直接部署给公众的多用户服务。公开分发仍需完成托管、身份验证、密钥与费用管理、权限审查和真实用户验收。

## 开发与复现

```bash
uv run pytest -q
uv run python eval/score.py --gold /path/to/gold.jsonl --predictions /path/to/predictions.jsonl --output /path/to/report.json
```

当前 20 项自动化测试通过，主要覆盖三档响应校验、文件提取、错误状态和 API 来源检查。自动化测试使用模拟模型响应，不能证明真实研究价值。评测输入格式与正式验收建议见 [eval/README.md](eval/README.md)。

## 许可

本仓库代码和自拟合成测试材料按 [MIT License](LICENSE) 开源。TypeSafe Jev、Tesseract 及其他依赖各自遵循其服务条款或许可证。
