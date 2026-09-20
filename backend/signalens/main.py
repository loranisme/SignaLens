"""API-only backend for the SignaLens extension."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from .config import MAX_FILE_BYTES, MAX_REQUESTS_PER_MINUTE, allowed_extension_origin, api_key
from .extract import ExtractionError, ExtractedText, extract_file, extract_pasted_text
from .triage import TriageError, close_jev_client, evaluate_with_jev, public_result

log = logging.getLogger("signalens")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_jev_client()


app = FastAPI(title="SignaLens API", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_attempts: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = asyncio.Lock()
_extension_re = re.compile(r"^chrome-extension://[a-p]{32}$")
_horizons = {
    "lt_6m": "Less than 6 months",
    "6_24m": "6 to 24 months, inclusive",
    "gt_24m": "More than 24 months",
}


def _error(code: str, message: str, status: int, request_id: str, details: dict[str, Any] | None = None) -> JSONResponse:
    response = JSONResponse(
        status_code=status,
        content={"error_code": code, "message": message, "request_id": request_id, **(details or {})},
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def _origin_ok(request: Request) -> bool:
    origin = request.headers.get("origin")
    expected = allowed_extension_origin()
    if origin:
        return origin == expected if expected else bool(_extension_re.fullmatch(origin))
    # CLI/test calls on loopback are useful for smoke tests. Browsers always send
    # an Origin for cross-origin extension requests.
    return (request.client is not None and request.client.host in {"127.0.0.1", "::1", "testclient"})


async def _rate_allowed(request: Request) -> bool:
    origin = request.headers.get("origin") or (request.client.host if request.client else "unknown")
    now = time.monotonic()
    async with _rate_lock:
        queue = _attempts[origin]
        while queue and queue[0] < now - 60:
            queue.popleft()
        if len(queue) >= MAX_REQUESTS_PER_MINUTE:
            return False
        queue.append(now)
    return True


def _clean_items(value: Any, limit: int, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) > limit:
        raise ExtractionError("INPUT_INVALID", f"{field} 须为不超过 {limit} 项的列表。")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > 100:
            raise ExtractionError("INPUT_INVALID", f"{field} 含无效项目。")
        cleaned = item.strip()
        if cleaned not in output:
            output.append(cleaned)
    return output


def _context(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExtractionError("INPUT_INVALID", "请先设置 Research Context。")
    areas = _clean_items(value.get("research_areas", []), 10, "Research Areas")
    watchlist = _clean_items(value.get("watchlist", []), 30, "Watchlist")
    if not areas and not watchlist:
        raise ExtractionError("INPUT_INVALID", "Research Areas 和 Watchlist 至少填写一项。")
    horizon = value.get("investment_horizon")
    if horizon not in _horizons:
        raise ExtractionError("INPUT_INVALID", "请选择 Investment Horizon。")
    return {"research_areas": areas, "watchlist": watchlist, "investment_horizon": _horizons[horizon]}


async def _extract_request(request: Request) -> tuple[ExtractedText, dict[str, Any]]:
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ExtractionError("INPUT_INVALID", "请求 JSON 无效。") from exc
        if not isinstance(payload, dict):
            raise ExtractionError("INPUT_INVALID", "请求内容无效。")
        context = _context(payload.get("research_context"))
        extracted = extract_pasted_text(payload.get("information_text"))
        return extracted, context
    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise ExtractionError("INPUT_INVALID", "请选择一个文件。")
        raw_context = form.get("research_context")
        try:
            context = _context(json.loads(raw_context) if isinstance(raw_context, str) else None)
        except json.JSONDecodeError as exc:
            raise ExtractionError("INPUT_INVALID", "Research Context 无效。") from exc
        data = await upload.read(MAX_FILE_BYTES + 1)
        filename = upload.filename or ""
        await upload.close()
        if len(data) > MAX_FILE_BYTES:
            raise ExtractionError("INPUT_INVALID", "文件超过 20 MB 上限。")
        page_range = form.get("page_range")
        section_value = form.get("section_index")
        try:
            section_index = int(section_value) if section_value not in (None, "") else None
        except ValueError as exc:
            raise ExtractionError("INPUT_INVALID", "章节编号无效。") from exc
        if page_range is not None and not isinstance(page_range, str):
            raise ExtractionError("INPUT_INVALID", "页码范围无效。")
        extracted = await asyncio.to_thread(extract_file, filename, data, page_range, section_index)
        return extracted, context
    raise ExtractionError("INPUT_INVALID", "请提交文字或一个文件。")


@app.get("/api/health")
async def health(request: Request):
    request_id = uuid.uuid4().hex
    if not _origin_ok(request):
        return _error("FORBIDDEN_ORIGIN", "请求来源不允许。", 403, request_id)
    response = JSONResponse({"status": "ready" if api_key() else "needs_api_key", "api_only": True})
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/evaluate")
async def evaluate(request: Request):
    request_id = uuid.uuid4().hex
    started = time.perf_counter()
    if not _origin_ok(request):
        return _error("FORBIDDEN_ORIGIN", "请求来源不允许。", 403, request_id)
    if not await _rate_allowed(request):
        return _error("RATE_LIMITED", "请求过于频繁，请稍后再试。", 429, request_id)
    key = api_key()
    if not key:
        return _error("EVALUATION_UNAVAILABLE", "本地服务尚未配置 Jev API key。", 503, request_id)
    try:
        extracted, context = await _extract_request(request)
        extraction_ms = round((time.perf_counter() - started) * 1000)
        decision = await evaluate_with_jev(extracted.text, context, extracted.evaluated_scope, key)
    except ExtractionError as exc:
        statuses = {"INPUT_INVALID": 400, "UNSUPPORTED_FILE": 415, "CONTENT_TOO_LONG": 413, "OCR_UNAVAILABLE": 422}
        return _error(exc.code, exc.message, statuses.get(exc.code, 422), request_id, exc.details)
    except TriageError as exc:
        log.warning("evaluation_failed request_id=%s code=%s", request_id, exc.code)
        return _error(exc.code, exc.message, 503 if exc.code in {"EVALUATION_UNAVAILABLE", "PROVIDER_AUTH"} else 502, request_id)
    except Exception:
        # Tracebacks can contain parser input or provider response bodies.
        log.error("internal_error request_id=%s", request_id)
        return _error("INTERNAL_ERROR", "内部处理失败；本次没有生成决策。", 500, request_id)
    total_ms = round((time.perf_counter() - started) * 1000)
    log.info(
        "evaluation_ok request_id=%s format=%s scope=%s extraction_ms=%d total_ms=%d input_tokens=%s",
        request_id, extracted.input_format, extracted.evaluated_scope, extraction_ms, total_ms, decision.input_tokens,
    )
    response = JSONResponse({
        **public_result(decision),
        **extracted.public_metadata(),
        "request_id": request_id,
    })
    response.headers["Cache-Control"] = "no-store"
    return response
