import json
from typing import Any, TypedDict

from groq import Groq

from app.agent.investigation_session import (
    investigation_session_manager,
)
from app.config import get_settings


settings = get_settings()

MAX_CHALLENGE_SYNTHESIS_TOKENS = 900
MAX_EVIDENCE_ROWS_PER_INVESTIGATION = 8
MAX_EVIDENCE_DIGEST_CHARS = 7000


class ChallengeState(TypedDict):
    """
    Context for a direct adversarial review of an existing
    investigation conclusion.

    There is deliberately no claim-extraction or planning state.
    The investigation already produced the analytical evidence.
    """

    question: str
    original_answer: str
    evidence: dict[str, Any]
    challenge_plan: list[str]
    challenge_evidence: dict[str, Any]
    challenge_answer: str


client = Groq(
    api_key=settings.groq_api_key,
    max_retries=0,
)


# ---------------------------------------------------------------------------
# Compact evidence digest
# ---------------------------------------------------------------------------


def _compact_value(value: Any) -> Any:
    """
    Keep evidence values JSON-friendly while removing unnecessary
    transport/detail noise from the LLM context.
    """
    if isinstance(value, dict):
        return {
            str(key): _compact_value(item)
            for key, item in value.items()
            if item is not None
        }

    if isinstance(value, list):
        return [_compact_value(item) for item in value]

    return value


def build_challenge_evidence_digest(
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a deterministic, bounded evidence digest for Challenge Mode.

    The investigation evidence remains the source of truth. This function
    only creates a smaller representation for the LLM review context.

    For tabular/list results, only the first bounded number of rows are
    included and the total row count is retained. This prevents large
    investigation outputs from consuming the Challenge TPM budget.
    """
    digest: dict[str, Any] = {}

    for investigation, payload in evidence.items():
        if not isinstance(payload, dict):
            digest[investigation] = _compact_value(payload)
            continue

        result = payload.get(
            "result",
            payload,
        )

        if isinstance(result, list):
            rows = [
                _compact_value(row)
                for row in result[
                    :MAX_EVIDENCE_ROWS_PER_INVESTIGATION
                ]
            ]

            item: dict[str, Any] = {
                "row_count": len(result),
                "rows": rows,
            }

            if len(result) > MAX_EVIDENCE_ROWS_PER_INVESTIGATION:
                item["rows_omitted"] = (
                    len(result)
                    - MAX_EVIDENCE_ROWS_PER_INVESTIGATION
                )

            digest[investigation] = item
        else:
            digest[investigation] = _compact_value(result)

    return digest


def _serialize_digest(
    evidence: dict[str, Any],
) -> str:
    """
    Serialize and hard-bound the evidence context.

    The normal digest should already be small. The final character bound
    is a defensive safeguard against unexpectedly large analytics output.
    """
    serialized = json.dumps(
        evidence,
        separators=(",", ":"),
        default=str,
    )

    if len(serialized) <= MAX_EVIDENCE_DIGEST_CHARS:
        return serialized

    return (
        serialized[:MAX_EVIDENCE_DIGEST_CHARS]
        + "...[evidence digest truncated]"
    )


def get_challenge_prompt(
    question: str,
    original_answer: str,
    evidence: dict[str, Any],
) -> str:
    evidence_digest = build_challenge_evidence_digest(
        evidence
    )

    return f"""
You are the adversarial review component of an enterprise CPG
analytics copilot.

The user asked:
{question}

The original investigation concluded:
{original_answer}

Your job is NOT to produce a new investigation and NOT to agree
with the conclusion automatically.

Challenge the conclusion using ONLY the supplied evidence.

Review the conclusion for:

1. What the evidence directly supports.
2. What the evidence contradicts or weakens.
3. What is not established by the evidence.
4. Whether the conclusion confuses correlation with causation.
5. Whether an observed pattern is being presented as an explanation.
6. Plausible alternative explanations supported by the evidence.
7. What additional evidence would be required to make the conclusion
   stronger.

Important rules:

- The evidence is the source of truth.
- Never invent metrics, facts, dates, or currency.
- Do not claim causality unless the evidence establishes it.
- Do not treat correlation as causation.
- If the evidence is insufficient, say so explicitly.
- Preserve useful observations even when the stronger conclusion
  is unsupported.
- Distinguish facts from interpretations.
- Do not manufacture contradictory evidence merely to be adversarial.
- Some evidence rows may be omitted from this review context to keep
  the prompt bounded. Do not infer facts from omitted rows.

Return a concise business-facing report using exactly these sections:

### Challenge
Assess how well the original conclusion survives review.

### Supporting evidence
State the evidence that supports the conclusion.

### Contradicting or limiting evidence
State evidence that weakens the conclusion or limits what can
reasonably be inferred.

### Missing evidence
State what would be needed to establish the stronger conclusion.

### Alternative explanations
Include only alternatives supported by the supplied evidence.

### Bottom line
Classify the conclusion as one of:
- supported
- partially supported
- contradicted
- insufficiently supported

SUPPLIED EVIDENCE DIGEST:
{_serialize_digest(evidence_digest)}
"""


# ---------------------------------------------------------------------------
# Challenge preparation
# ---------------------------------------------------------------------------


def prepare_challenge(
    investigation_id: str,
) -> dict[str, Any]:
    """
    Prepare a direct review from the completed investigation session.

    No LLM is called here.

    The investigation's existing evidence snapshot is reused instead of
    running a second analytical investigation.
    """
    session = investigation_session_manager.get_session(
        investigation_id
    )

    original_answer = session.get(
        "latest_answer",
        "",
    )

    if not original_answer:
        raise ValueError(
            "No completed investigation exists "
            "for this conversation."
        )

    history = session.get(
        "history",
        [],
    )

    question = ""

    for message in reversed(history):
        if message.get("role") == "user":
            question = message.get(
                "content",
                "",
            )
            break

    if not question:
        raise ValueError(
            "No investigation question exists "
            "for this conversation."
        )

    evidence = session.get(
        "latest_evidence",
        {},
    )

    plan = session.get(
        "latest_plan",
        [],
    )

    return {
        "question": question,
        "original_answer": original_answer,
        "claims": [],
        "challenge_plan": plan,
        "challenge_evidence": evidence,
        "challenge_answer": "",
    }


# ---------------------------------------------------------------------------
# Direct challenge synthesis
# ---------------------------------------------------------------------------


def challenge_synthesizer(
    state: ChallengeState,
) -> dict[str, Any]:
    """
    Perform one bounded LLM review of the existing conclusion.

    This is intentionally plain-text output. There is no structured
    extraction step because the Challenge feature is a review task,
    not a data-generation task.
    """
    prompt = get_challenge_prompt(
        question=state["question"],
        original_answer=state["original_answer"],
        evidence=state["challenge_evidence"],
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an adversarial enterprise "
                    "analytics reviewer. "
                    "Return a concise plain-text report."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        max_completion_tokens=MAX_CHALLENGE_SYNTHESIS_TOKENS,
        include_reasoning=False,
    )

    answer = (
        response.choices[0].message.content
        or "Unable to generate challenge assessment."
    )

    return {
        "challenge_answer": answer,
    }


def stream_challenge_synthesis(
    question: str,
    original_answer: str,
    claims: list[dict[str, Any]],
    evidence: dict[str, Any],
):
    """
    Stream the single direct adversarial review.

    `claims` remains in the function signature for API compatibility
    with the existing endpoint. The new implementation deliberately
    does not depend on extracted claims.
    """
    del claims

    prompt = get_challenge_prompt(
        question=question,
        original_answer=original_answer,
        evidence=evidence,
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an adversarial enterprise "
                    "analytics reviewer. "
                    "Return a concise plain-text report."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        max_completion_tokens=MAX_CHALLENGE_SYNTHESIS_TOKENS,
        include_reasoning=False,
        stream=True,
    )

    for chunk in response:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        if delta.content:
            yield delta.content
