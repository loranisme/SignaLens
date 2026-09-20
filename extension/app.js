"use strict";

const API_BASE = "http://127.0.0.1:8765";
const $ = (id) => document.getElementById(id);
let inputMode = "text";
let currentContext = null;

function parseItems(value) {
  return [...new Set(value.split(/[\n,，;；]+/).map((item) => item.trim()).filter(Boolean))];
}

function readContext() {
  const researchAreas = parseItems($("research-areas").value);
  const watchlist = parseItems($("watchlist").value);
  if (researchAreas.length + watchlist.length === 0) {
    throw new Error("请先填写 Research Areas 或 Watchlist。");
  }
  if (researchAreas.length > 10 || watchlist.length > 30) {
    throw new Error("Research Areas 最多 10 项，Watchlist 最多 30 项。");
  }
  return {
    research_areas: researchAreas,
    watchlist,
    investment_horizon: $("investment-horizon").value,
  };
}

function setStatus(message, error = false) {
  $("status").textContent = message;
  $("status").classList.toggle("error", error);
}

function switchMode(mode) {
  inputMode = mode;
  const text = mode === "text";
  $("text-panel").hidden = !text;
  $("file-panel").hidden = text;
  $("mode-text").classList.toggle("active", text);
  $("mode-file").classList.toggle("active", !text);
  $("mode-text").setAttribute("aria-pressed", String(text));
  $("mode-file").setAttribute("aria-pressed", String(!text));
  $("result").hidden = true;
  setStatus("");
}

async function saveContext(event) {
  event?.preventDefault();
  try {
    currentContext = readContext();
    await chrome.storage.local.set({ research_context: currentContext });
    $("context-status").textContent = "已保存在本机";
    setTimeout(() => { $("context-status").textContent = ""; }, 2500);
  } catch (error) {
    $("settings").open = true;
    setStatus(error.message, true);
  }
}

async function loadContext() {
  const saved = await chrome.storage.local.get("research_context");
  currentContext = saved.research_context || null;
  if (!currentContext) {
    $("settings").open = true;
    return;
  }
  $("research-areas").value = (currentContext.research_areas || []).join("\n");
  $("watchlist").value = (currentContext.watchlist || []).join("\n");
  $("investment-horizon").value = currentContext.investment_horizon || "6_24m";
}

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/api/health`, { cache: "no-store", signal: AbortSignal.timeout(4000) });
    const data = await response.json();
    if (response.ok && data.status === "ready") {
      $("connection").textContent = "服务已连接";
      $("connection").className = "connection ready";
    } else {
      $("connection").textContent = "需要 Jev key";
      $("connection").className = "connection error";
    }
  } catch {
    $("connection").textContent = "启动本地服务";
    $("connection").className = "connection error";
  }
}

function showResult(data) {
  if (!["RESEARCH", "KEEP", "SKIP"].includes(data.decision) || !Number.isFinite(data.confidence_score)) {
    throw new Error("服务返回了无效的三档结果。");
  }
  const card = $("result-card");
  card.className = `result-card ${data.decision.toLowerCase()}`;
  $("decision-label").textContent = data.decision;
  $("confidence").textContent = `模型把握度 ${Math.round(data.confidence_score * 100)}%`;
  $("confidence").title = "表示三档区分的明确程度，不是判断正确率。";
  $("result-message").textContent = data.message || "";
  if (data.evaluated_scope === "selected_pages") {
    $("scope").textContent = `评估范围：所选 PDF 页 ${data.pages_evaluated?.join(", ") || ""}`;
  } else if (data.evaluated_scope === "selected_section") {
    $("scope").textContent = `评估范围：所选 Word 章节 ${data.section_title || ""}`;
  } else if (data.evaluated_scope === "whole_document_text") {
    $("scope").textContent = "评估范围：整份文档的可提取文字";
  } else {
    $("scope").textContent = "评估范围：本次粘贴的文字";
  }
  const warnings = Array.isArray(data.warnings) ? data.warnings.join(" ") : "";
  $("warning").textContent = warnings;
  $("warning").hidden = !warnings;
  $("result").hidden = false;
}

function showSelectionOptions(data) {
  if (data.available_page_range) {
    $("page-choice").hidden = false;
    $("page-range").placeholder = `例如 1-3,5；可用 ${data.available_page_range}`;
  }
  if (Array.isArray(data.sections) && data.sections.length > 1) {
    const select = $("section-index");
    select.replaceChildren();
    for (const [index, title] of data.sections.entries()) {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = title;
      select.append(option);
    }
    $("section-choice").hidden = false;
  }
}

async function evaluate() {
  const button = $("evaluate");
  $("result").hidden = true;
  let context;
  try {
    context = readContext();
    currentContext = context;
    await chrome.storage.local.set({ research_context: context });
  } catch (error) {
    $("settings").open = true;
    setStatus(error.message, true);
    return;
  }
  let body;
  let headers;
  if (inputMode === "file") {
    const file = $("information-file").files[0];
    if (!file) { setStatus("请先选择一个文件。", true); return; }
    if (file.size > 20 * 1024 * 1024) { setStatus("文件超过 20 MB 上限。", true); return; }
    body = new FormData();
    body.append("file", file, file.name);
    body.append("research_context", JSON.stringify(context));
    if (!$("page-choice").hidden && $("page-range").value.trim()) {
      body.append("page_range", $("page-range").value.trim());
    }
    if (!$("section-choice").hidden) {
      body.append("section_index", $("section-index").value);
    }
  } else {
    const text = $("information-text").value.trim();
    if (!text) { setStatus("请先粘贴需要评估的文字。", true); return; }
    body = JSON.stringify({ information_text: text, research_context: context });
    headers = { "Content-Type": "application/json" };
  }
  button.disabled = true;
  button.textContent = "正在评估…";
  setStatus("正在处理输入并生成三档判断。扫描文件可能需要更久。");
  try {
    const response = await fetch(`${API_BASE}/api/evaluate`, {
      method: "POST",
      body,
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(inputMode === "file" ? 120000 : 16000),
    });
    const data = await response.json();
    if (!response.ok) {
      if (data.error_code === "CONTENT_TOO_LONG") showSelectionOptions(data);
      throw new Error(data.message || "本次无法评估，请稍后重试。");
    }
    showResult(data);
    setStatus("判断完成。此结果不是事实核验或投资建议。");
  } catch (error) {
    setStatus(error.name === "TimeoutError" ? "处理超时；本次没有生成决策。" : error.message, true);
  } finally {
    button.disabled = false;
    button.replaceChildren("Evaluate ");
    const arrow = document.createElement("span");
    arrow.textContent = "↗";
    arrow.setAttribute("aria-hidden", "true");
    button.append(arrow);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  $("mode-text").addEventListener("click", () => switchMode("text"));
  $("mode-file").addEventListener("click", () => switchMode("file"));
  $("context-form").addEventListener("submit", saveContext);
  $("evaluate").addEventListener("click", evaluate);
  $("information-file").addEventListener("change", () => {
    const file = $("information-file").files[0];
    $("selected-file").textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB` : "";
    $("page-choice").hidden = true;
    $("section-choice").hidden = true;
    $("result").hidden = true;
  });
  $("copy-result").addEventListener("click", async () => {
    const copy = `${$("decision-label").textContent}\n${$("confidence").textContent}\n${$("result-message").textContent}`;
    await navigator.clipboard.writeText(copy);
    $("copy-result").textContent = "已复制";
    setTimeout(() => { $("copy-result").textContent = "复制"; }, 1600);
  });
  await loadContext();
  await checkHealth();
});
