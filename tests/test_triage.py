import pytest
import httpx

from signalens import triage
from signalens.triage import (
    DOCUMENT_INSTRUCTIONS,
    TriageError,
    make_jev_request,
    validate_jev_response,
)


def test_document_question_protects_a_single_important_lead():
    request = make_jev_request(
        "Most sections are background. One section changes the thesis.",
        {"research_areas": ["Semiconductor"], "watchlist": [], "investment_horizon": "6 to 24 months"},
        "whole_document_text",
    )
    question = request["questions"]["triage"]
    assert question["instructions"] == DOCUMENT_INSTRUCTIONS
    assert "ANY" in question["instructions"]
    assert set(question["criteria"]) == {"RESEARCH", "KEEP", "SKIP"}
    assert request["model"] == "jev-1.13.0"


def test_jev_confidence_is_not_the_selected_probability():
    answer = validate_jev_response({
        "model": "jev-1.13.0",
        "answers": {"triage": {
            "type": "choice",
            "choice": "RESEARCH",
            "confidence": 0.81,
            "probabilities": {"RESEARCH": 0.88, "KEEP": 0.12, "SKIP": 0.0},
        }},
        "usage": {"input_tokens": 347},
    })
    assert answer.confidence == 0.81
    assert answer.probabilities["RESEARCH"] == 0.88
    assert answer.input_tokens == 347


@pytest.mark.parametrize("bad", [
    {"RESEARCH": 0.4, "KEEP": 0.4, "SKIP": 0.4},
    {"RESEARCH": 0.0, "KEEP": 0.9, "SKIP": 0.1},
    {"RESEARCH": 0.8, "KEEP": 0.2},
])
def test_invalid_provider_result_never_becomes_business_decision(bad):
    with pytest.raises(TriageError) as exc:
        validate_jev_response({
            "model": "jev-1.13.0",
            "answers": {"triage": {"type": "choice", "choice": "RESEARCH", "confidence": 0.7, "probabilities": bad}},
        })
    assert exc.value.code == "PROVIDER_RESPONSE_INVALID"


def test_model_version_is_pinned():
    with pytest.raises(TriageError):
        validate_jev_response({
            "model": "jev-1.14.0",
            "answers": {"triage": {"type": "choice", "choice": "SKIP", "confidence": 0.9,
                                   "probabilities": {"RESEARCH": 0.0, "KEEP": 0.1, "SKIP": 0.9}}},
        })


@pytest.mark.asyncio
async def test_one_connect_failure_retries_without_changing_business_label(monkeypatch):
    class FakeClient:
        calls = 0

        async def post(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise httpx.ConnectTimeout("synthetic connection timeout")
            return httpx.Response(200, json={
                "model": "jev-1.13.0",
                "answers": {"triage": {"type": "choice", "choice": "KEEP", "confidence": 0.7,
                                       "probabilities": {"RESEARCH": 0.1, "KEEP": 0.8, "SKIP": 0.1}}},
                "usage": {"input_tokens": 250},
            })

    fake = FakeClient()

    async def get_fake():
        return fake

    monkeypatch.setattr(triage, "_get_client", get_fake)
    result = await triage.evaluate_with_jev("text", {"research_areas": ["Semiconductor"]}, "pasted_text", "test-only")
    assert fake.calls == 2
    assert result.label == "KEEP"
