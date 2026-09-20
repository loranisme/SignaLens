# SignaLens

**一个面向投研场景的快速信息分流浏览器插件。**
![Uploading image.png…]()

SignaLens 的目标非常简单：

> **帮助研究人员快速判断一段信息是否值得继续投入研究时间。**

用户可以提交一段文字，或者上传一份文档。SignaLens 会结合用户设置的研究方向、关注公司和投资期限，快速返回以下三个结果之一：

* `RESEARCH`
* `KEEP`
* `SKIP`

SignaLens 不是 Deep Research Agent。

它不会自动搜索资料，不会生成完整研报，不会构建投资观点，也不会给出买卖建议。

它只负责一件事：

> **在你真正开始深入研究之前，先判断这条信息值不值得继续看。**

---

## 为什么做 SignaLens

投研工作中真正稀缺的往往不是信息，而是注意力。

研究人员每天可能需要处理大量内容，例如：

* 券商研报
* 行业新闻
* 公司公告
* 财报与电话会纪要
* 专家访谈
* 产业链信息
* 投资观点
* 技术文章
* 各类 PDF 或 Word 研究材料

问题在于：

> 并不是所有信息都值得继续花 20 分钟、30 分钟甚至几个小时深入研究。

传统流程通常是：

```text
大量信息
  ↓
人工逐条阅读
  ↓
判断是否值得继续研究
```

SignaLens 希望在中间加入一个非常轻量的决策层：

```text
投研信息
  ↓
SignaLens
  ↓
RESEARCH / KEEP / SKIP
```

它的核心设计原则是：

> **先判断什么值得研究，再花时间研究。**

---

## 三种结果

### RESEARCH

表示：

> 当前值得继续投入时间核查、阅读或研究。

常见情况包括：

* 可能影响当前行业判断
* 可能影响关注公司的核心逻辑
* 出现新的产业链变化
* 存在值得验证的重要不确定性
* 信息中包含明确的增量线索

`RESEARCH` 不代表这条信息已经被验证为真实。

对于未经证实、但如果成立会产生较大影响的信息，SignaLens 仍可能返回 `RESEARCH`。

这里的含义只是：

> **值得进一步核查。**

---

### KEEP

表示：

> 信息与当前研究有关，也可能具有价值，但现在暂时没有必要继续投入更多研究时间。

常见情况包括：

* 信息与研究方向相关
* 当前影响尚不明确
* 时点还比较早
* 缺少进一步研究所需的细节
* 暂时没有明确的下一步研究问题

这类信息可以先保留，之后根据新信息重新判断。

---

### SKIP

表示：

> 当前继续投入研究时间的边际价值较低。

常见情况包括：

* 与当前研究方向关系较弱
* 信息过于泛化
* 没有明确增量
* 只是重复已有观点
* 对当前研究期限没有明显价值

---

## Research Context

SignaLens 并不是单纯判断：

> “这是不是一条重要新闻？”

它判断的是：

> **“对于当前这个研究者而言，这条信息值不值得继续研究？”**

因此用户需要设置一个非常简单的 Research Context。

目前包括：

* Research Areas：研究领域
* Watchlist：关注公司或股票代码
* Investment Horizon：研究时间范围

例如：

```text
Research Areas
- Semiconductors
- AI Infrastructure
- Optical Networking

Watchlist
- NVDA
- AVGO
- LITE

Investment Horizon
- 6–24 months
```

同一条信息，在不同 Research Context 下可能得到不同判断。

例如，一条关于 AI 光通信产业链的消息：

* 对半导体研究员可能是 `RESEARCH`
* 对医疗行业研究员可能是 `SKIP`

因此 SignaLens 的核心判断可以理解为：

```text
信息
+
用户研究背景
=
当前是否值得继续研究
```

---

## 当前支持的输入

SignaLens 当前支持：

* 直接粘贴文本
* `.txt`
* `.md`
* `.pdf`
* `.docx`
* `.doc`

单个文件最大支持 20 MB。

对于普通 PDF 和 Word 文件，系统会直接提取其中的文字。

对于扫描版 PDF，可以通过 Tesseract OCR 提取文字。

当前版本只基于可提取的文本内容进行判断。

暂时不会理解：

* 图表
* 图片
* 流程图
* 财务模型截图
* 其他视觉信息

如果输入内容估算超过约 12,000 tokens，系统会要求用户缩小评估范围。

SignaLens 不会：

* 静默截断长文档
* 自动总结后再判断
* 自动忽略部分内容

对于 PDF 可以选择页码范围。

对于 DOCX 可以选择特定章节。

---

## 浏览器插件

SignaLens 当前采用 Chrome Side Panel 作为主要用户界面。

基本使用流程：

```text
粘贴文字或上传文档
        ↓
     Evaluate
        ↓
RESEARCH / KEEP / SKIP
```

结果界面保持极简，例如：

```text
RESEARCH

模型把握度：84%

这条线索可能影响当前研究判断，
值得进一步核查。
```

或者：

```text
KEEP

模型把握度：72%

与当前研究相关，
但暂时无需投入更多时间。
```

或者：

```text
SKIP

模型把握度：91%

基于当前研究范围，
继续阅读的边际价值较低。
```

当前版本不会提供：

* 聊天界面
* 自动 Deep Research
* 自动搜索
* 多 Agent 工作流
* 长篇分析报告

---

## 工作原理

整体架构非常简单：

```text
Chrome Side Panel
        ↓
本地 API
        ↓
文本提取
        ↓
Research Context
        ↓
TypeSafe Jev
        ↓
RESEARCH / KEEP / SKIP
```

Jev 在 SignaLens 中承担的是：

> **Decision Engine**

而不是 Research Agent。

它的任务不是生成复杂研究报告，而是在一个非常有限的 Action Space 中快速完成分流判断。

---

## 模型把握度

SignaLens 会显示 Jev 返回的模型把握度。

需要注意：

> **模型把握度不是“判断正确的概率”。**

例如：

```text
模型把握度：84%
```

并不代表：

> 这次判断有 84% 的概率是正确的。

它表示的是模型在 `RESEARCH / KEEP / SKIP` 三个选项之间，本次输出分布的明确程度。

在没有经过独立真实数据校准之前，SignaLens 不会把这个数字解释成真实准确率。

---

## 本地运行

当前版本是一个需要本机运行 API 的开源 MVP。

已验证环境：

* macOS
* Chrome
* Python 3.11+
* uv
* TypeSafe Jev API Key

首先克隆仓库：

```bash
git clone https://github.com/loranisme/SignaLens.git
cd SignaLens
```

安装依赖：

```bash
uv sync
```

如果需要支持扫描 PDF OCR：

```bash
bash scripts/setup_ocr_macos.sh
```

启动本地服务：

```bash
bash scripts/run_local.sh
```

启动时需要输入自己的 TypeSafe Jev API Key。

API Key：

* 不应该写进插件代码
* 不应该提交到 GitHub
* 不应该发到 Issue
* 不会由启动脚本保存到文件

本地 API 默认运行在：

```text
http://127.0.0.1:8765
```

可以通过：

```text
http://127.0.0.1:8765/api/health
```

检查服务状态。

---

## 安装 Chrome 插件

打开：

```text
chrome://extensions
```

然后：

1. 开启 Developer Mode
2. 点击 Load unpacked
3. 选择仓库中的 `extension/` 文件夹
4. 点击浏览器工具栏中的 SignaLens 图标
5. 打开 Side Panel
6. 设置 Research Context
7. 粘贴文字或上传文件
8. 点击 Evaluate

当前版本已经在 Chrome 本地开发模式中验证。

Edge 尚未完成正式验收。

---

## 当前状态

SignaLens 目前仍然是一个实验性质的开源 MVP。

截至 2026-09-20，目前已经完成：

* Chrome Side Panel
* 文本输入
* PDF 输入
* Word 输入
* OCR 支持
* Research Context
* Jev 三分类决策
* 输入校验
* 响应校验
* 错误处理
* 本地 API
* 自动化测试
* 多语言合成数据评测

---

## 当前测试结果

目前的测试主要基于实施者自行构造并标注的合成样本。

| 测试                | 与预设标签一致 |
| ----------------- | ------: |
| v1 新文本测试          | 42 / 48 |
| v2 新文本封存集         | 48 / 48 |
| v2 PDF / Word 回归  | 14 / 16 |
| v3 PDF / Word 封存集 | 22 / 24 |

v3 文件测试中，本地脚本到本地 API 的请求耗时为：

```text
P50：348 ms
P95：892 ms
```

该时间包含：

* 文件文字提取
* Jev 调用

但不代表：

* 浏览器用户完整操作耗时
* 高并发性能
* 长期稳定性

---

## 关于当前测试结果

上述测试数据全部来自：

> **实施者自行设计并自行标注的合成材料。**

因此这些结果只能说明：

> 当前实现已经能够按照预期流程完成基本的三档判断。

不能据此声称：

> SignaLens 在真实投研环境中已经达到 90% 或更高准确率。

正式验证仍然需要：

* 真实来源的投研材料
* 独立研究人员标注
* 自然类别比例
* 不同 Research Context
* 中文和英文分别测试
* 不同文件格式分别测试
* 独立封存测试集

详细评测材料可以查看：

```text
docs/multilingual-evaluation-2026-09-20.md
```

以及：

```text
eval/synthetic_2026-09-20/
```

和：

```text
eval/README.md
```

---

## 隐私

Research Context 保存在浏览器本地。

Jev API Key 只保存在本机 API 服务进程中。

插件当前不会：

* 自动读取浏览历史
* 自动读取当前网页
* 注入网页内容
* 自动跟踪 Watchlist
* 自动上传本地其他文件

但是：

> 用户主动提交给 SignaLens 的文字内容会发送给 TypeSafe Jev 进行判断。

因此请只提交你有权交由该服务处理的内容。

---

## SignaLens 不做什么

SignaLens 当前明确不做：

* Deep Research Agent
* 自动联网搜索
* 自动扩展研究资料
* 自动生成完整研报
* 自动构建 Investment Thesis
* 股票买卖建议
* Portfolio Management
* Trading
* Multi-Agent Workflow
* 自动 Financial Modeling

这些并不是“未来一定要补上的缺失功能”。

其中很多是 SignaLens 当前产品设计中刻意排除的范围。

SignaLens 希望保持一个非常明确的 Single-Purpose：

```text
Information
    ↓
SignaLens
    ↓
RESEARCH / KEEP / SKIP
```

---

## 开发与测试

运行自动化测试：

```bash
uv run pytest -q
```

运行评测：

```bash
uv run python eval/score.py \
  --gold /path/to/gold.jsonl \
  --predictions /path/to/predictions.jsonl \
  --output /path/to/report.json
```

当前自动化测试主要覆盖：

* 三档响应校验
* 文件提取
* 错误状态
* API 来源检查

自动化测试使用模拟模型响应。

因此：

> 自动化测试通过不能证明 SignaLens 的真实 Research Value。

---

## 核心设计理念

SignaLens 不希望成为另一个 AI Analyst。

它更接近一个：

> **Research Attention Filter**

它想解决的问题不是：

> “AI 能不能替我把这篇研报研究完？”

而是：

> **“在我花时间研究之前，这个东西到底值不值得继续看？”**

因此 SignaLens 想优化的是：

```text
Information Overload
        ↓
Research Triage
        ↓
Better Attention Allocation
```

## License

本项目采用 MIT License。

TypeSafe Jev、Tesseract 以及其他第三方依赖分别遵循其各自的服务条款或许可证。
