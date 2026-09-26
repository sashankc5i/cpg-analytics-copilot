import json
from typing import Any, TypedDict

from groq import Groq
from langgraph.graph import END, START, StateGraph

from app.agent.investigation import (
    INVESTIGATION_CATALOG,
    INVESTIGATION_TO_TOOL,
)
from app.agent.investigation_session import (
    investigation_session_manager,
)
from app.agent.tools import execute_tool
from app.config import get_settings


settings = get_settings()


MAX_CLAIMS = 5


VALID_CLAIM_TYPES = {
    "descriptive",
    "comparative",
    "causal",
}


VALID_CLAIM_STATUSES = {
    "unchallenged",
    "supported",
    "partially_supported",
    "contradicted",
    "insufficient_evidence",
}


class ChallengeState(TypedDict):
    question: str
    original_answer: str
    hypotheses: list[dict[str, Any]]
    evidence: dict[str, Any]
    claims: list[dict[str, Any]]
    challenge_plan: list[str]
    challenge_evidence: dict[str, Any]
    challenge_answer: str


client = Groq(
    api_key=settings.groq_api_key
)


# ---------------------------------------------------------------------------
# Claim extraction
# ---------------------------------------------------------------------------

def get_claim_extraction_prompt(
    question: str,
    original_answer: str,
) -> str:
    catalog = ", ".join(INVESTIGATION_CATALOG)

    return f"""
You are the claim extraction component of an enterprise
CPG analytics investigation system.

The system produced an investigation answer for this question:

QUESTION:
{question}

ORIGINAL ANSWER:
{original_answer}

Your job is to identify the important factual or analytical
claims made by the answer that should be challenged.

Extract between 1 and {MAX_CLAIMS} claims.

Each claim must:

1. Be directly based on the original answer.
2. Represent a meaningful business assertion.
3. Avoid inventing facts.
4. Avoid adding numbers that were not present.
5. Identify whether the claim is:
   - descriptive
   - comparative
   - causal

For each claim, identify which approved investigations
could provide evidence relevant to challenging it.

APPROVED INVESTIGATIONS:
{catalog}

Return ONLY valid JSON.

Expected structure:

{{
    "claims": [
        {{
            "id": "C1",
            "claim": "Regional performance contributed to the decline.",
            "type": "causal",
            "investigations": [
                "regional_performance",
                "revenue_trend"
            ]
        }}
    ]
}}
"""


def validate_claims(
    claims: Any,
) -> list[dict[str, Any]]:
    if not isinstance(claims, list):
        return []

    validated = []

    for index, claim in enumerate(
        claims[:MAX_CLAIMS]
    ):
        if not isinstance(claim, dict):
            continue

        text = claim.get("claim")

        if not isinstance(
            text,
            str,
        ) or not text.strip():
            continue

        claim_type = claim.get("type")

        if claim_type not in VALID_CLAIM_TYPES:
            continue

        investigations = claim.get(
            "investigations",
            [],
        )

        if not isinstance(
            investigations,
            list,
        ):
            investigations = []

        valid_investigations = [
            investigation
            for investigation in investigations
            if investigation in INVESTIGATION_CATALOG
        ]

        if not valid_investigations:
            continue

        validated.append(
            {
                "id": claim.get(
                    "id",
                    f"C{index + 1}",
                ),
                "claim": text.strip(),
                "type": claim_type,
                "investigations": (
                    valid_investigations
                ),
                "status": "unchallenged",
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "missing_evidence": [],
            }
        )

    return validated


def extract_claims(
    state: ChallengeState,
) -> dict[str, Any]:

    prompt = get_claim_extraction_prompt(
        question=state["question"],
        original_answer=state["original_answer"],
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured business claims. "
                    "Return JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        response_format={
            "type": "json_object",
        },
    )

    content = (
        response.choices[0].message.content
        or "{}"
    )

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {
            "claims": []
        }

    claims = []

    if isinstance(parsed, dict):
        claims = parsed.get(
            "claims",
            [],
        )

    return {
        "claims": validate_claims(claims)
    }


# ---------------------------------------------------------------------------
# Challenge planning
# ---------------------------------------------------------------------------

def build_challenge_plan(
    claims: list[dict[str, Any]],
) -> list[str]:

    investigations = []

    for claim in claims:
        for investigation in claim[
            "investigations"
        ]:
            if investigation not in investigations:
                investigations.append(
                    investigation
                )

    return investigations


def get_challenge_planner_prompt(
    question: str,
    original_answer: str,
    claims: list[dict[str, Any]],
) -> str:

    return f"""
You are the challenge planning component of an
enterprise CPG analytics system.

Your job is to determine which approved analytical
investigations should be used to challenge the claims
made in an existing analytics conclusion.

CURRENT QUESTION:

{question}

ORIGINAL ANSWER:

{original_answer}

CLAIMS:

{json.dumps(claims, indent=2)}

APPROVED INVESTIGATIONS:

{json.dumps(INVESTIGATION_CATALOG, indent=2)}

Your objective is NOT to confirm the original conclusion.

Instead, identify investigations that could:

1. Support the claim.
2. Contradict the claim.
3. Reveal missing evidence.
4. Expose an alternative explanation.

Rules:

1. Use ONLY investigations from the approved catalog.
2. Do not invent investigation names.
3. Do not assume a claim is true.
4. Do not assume a claim is false.
5. Prefer the minimum set of investigations required
   to meaningfully challenge the claims.
6. A causal claim should generally require more scrutiny
   than a descriptive claim.
7. Return JSON only.

Return exactly:

{{
    "investigations": [
        "investigation_name"
    ]
}}
"""


def challenge_planner(
    state: ChallengeState,
):
    """
    Build a deterministic challenge investigation plan
    from the extracted claims.

    The planner deliberately does not call the LLM.

    Claim extraction is an LLM task because natural-language
    conclusions need to be converted into structured claims.

    Once claims are structured, selecting the appropriate
    approved investigations is deterministic business logic.
    """

    claims = state.get("claims", [])

    challenge_plan = []

    for claim in claims:
        claim_type = claim.get("type")

        # The claim extractor produces an `investigations`
        # field. These are the approved investigations that
        # are relevant to challenging this claim.
        required_investigations = claim.get(
            "investigations",
            [],
        )

        if not isinstance(
            required_investigations,
            list,
        ):
            required_investigations = []

        for investigation in required_investigations:
            if investigation not in challenge_plan:
                challenge_plan.append(
                    investigation
                )

        # Causal claims require stronger evidence.
        #
        # If the claim extractor did not provide explicit
        # investigations, use the broader approved catalog
        # needed to challenge causal reasoning.
        if (
            claim_type == "causal"
            and not required_investigations
        ):
            for investigation in [
                "revenue_trend",
                "regional_performance",
                "product_performance",
                "category_performance",
                "customer_segments",
                "promotion_impact",
                "inventory_stockouts",
            ]:
                if investigation not in challenge_plan:
                    challenge_plan.append(
                        investigation
                    )

    # Safety boundary:
    # only allow investigations that the application
    # explicitly knows how to execute.
    allowed_investigations = {
        "revenue_trend",
        "regional_performance",
        "product_performance",
        "category_performance",
        "customer_segments",
        "promotion_impact",
        "inventory_stockouts",
    }

    challenge_plan = [
        investigation
        for investigation in challenge_plan
        if investigation in allowed_investigations
    ]

    # Deterministic fallback.
    #
    # If claim extraction produced claims but no explicit
    # investigation mapping, use revenue trend as the
    # minimum evidence required to challenge the conclusion.
    if claims and not challenge_plan:
        challenge_plan = [
            "revenue_trend"
        ]

    print(
        "[Challenge Planner] Deterministic plan:",
        challenge_plan,
    )

    return {
        "challenge_plan": challenge_plan,
    }
# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------

def challenge_evidence_collector(
    state: ChallengeState,
) -> dict[str, Any]:

    evidence = {}

    for investigation in state[
        "challenge_plan"
    ]:

        tool_name = INVESTIGATION_TO_TOOL.get(
            investigation
        )

        if not tool_name:
            continue

        try:
            result = execute_tool(
                tool_name,
                {},
            )

            evidence[investigation] = {
                "tool": tool_name,
                "result": result,
            }

        except Exception as error:
            evidence[investigation] = {
                "tool": tool_name,
                "result": {
                    "error": str(error)
                },
            }

    return {
        "challenge_evidence": evidence
    }


# ---------------------------------------------------------------------------
# Claim evaluation
# ---------------------------------------------------------------------------

def get_claim_evaluation_prompt(
    question: str,
    original_answer: str,
    claims: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> str:

    return f"""
You are evaluating whether an analytics conclusion survives
an adversarial evidence review.

QUESTION:
{question}

ORIGINAL ANSWER:
{original_answer}

CLAIMS:
{json.dumps(claims, indent=2)}

CHALLENGE EVIDENCE:
{json.dumps(evidence, indent=2, default=str)}

For every claim:

1. Identify evidence supporting the claim.
2. Identify evidence contradicting the claim.
3. Identify evidence that is missing.
4. Assign exactly one status:
   - supported
   - partially_supported
   - contradicted
   - insufficient_evidence

Important rules:

- Use only the supplied evidence.
- Never invent metrics.
- Never invent business facts.
- Do not treat correlation as causation.
- A causal claim requires stronger evidence than a
  descriptive claim.
- If the available evidence cannot establish causality,
  explicitly say so.
- Do not assume currency.
- Do not claim that one factor is the primary cause unless
  the evidence actually establishes that.
- Distinguish observed facts from possible explanations.

Return ONLY valid JSON.

Expected structure:

{{
    "claims": [
        {{
            "id": "C1",
            "status": "partially_supported",
            "supporting_evidence": [
                "..."
            ],
            "contradicting_evidence": [
                "..."
            ],
            "missing_evidence": [
                "..."
            ]
        }}
    ]
}}
"""


def evaluate_claims(
    state: ChallengeState,
) -> dict[str, Any]:

    prompt = get_claim_evaluation_prompt(
        question=state["question"],
        original_answer=state["original_answer"],
        claims=state["claims"],
        evidence=state["challenge_evidence"],
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an evidence evaluator. "
                    "Return JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        response_format={
            "type": "json_object",
        },
    )

    content = (
        response.choices[0].message.content
        or "{}"
    )

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {
            "claims": state["claims"]
        }

    evaluated_claims = parsed.get(
        "claims",
        [],
    )

    if not isinstance(
        evaluated_claims,
        list,
    ):
        return {
            "claims": state["claims"]
        }

    evaluation_by_id = {
        claim.get("id"): claim
        for claim in evaluated_claims
        if isinstance(
            claim,
            dict,
        )
    }

    updated_claims = []

    for claim in state["claims"]:

        evaluation = evaluation_by_id.get(
            claim["id"],
            {},
        )

        status = evaluation.get(
            "status",
            "insufficient_evidence",
        )

        if status not in VALID_CLAIM_STATUSES:
            status = "insufficient_evidence"

        supporting = evaluation.get(
            "supporting_evidence",
            [],
        )

        contradicting = evaluation.get(
            "contradicting_evidence",
            [],
        )

        missing = evaluation.get(
            "missing_evidence",
            [],
        )

        if not isinstance(
            supporting,
            list,
        ):
            supporting = []

        if not isinstance(
            contradicting,
            list,
        ):
            contradicting = []

        if not isinstance(
            missing,
            list,
        ):
            missing = []

        updated_claims.append(
            {
                **claim,
                "status": status,
                "supporting_evidence": supporting,
                "contradicting_evidence": (
                    contradicting
                ),
                "missing_evidence": missing,
            }
        )

    return {
        "claims": updated_claims
    }


# ---------------------------------------------------------------------------
# Challenge synthesis
# ---------------------------------------------------------------------------

def get_challenge_synthesis_prompt(
    question: str,
    original_answer: str,
    claims: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> str:

    return f"""
You are the final synthesis component of an enterprise
CPG analytics copilot.

The user asked:

{question}

The original investigation concluded:

{original_answer}

The conclusion has now been challenged.

Evaluated claims:

{json.dumps(claims, indent=2)}

Challenge evidence:

{json.dumps(evidence, indent=2, default=str)}

Produce a concise evidence-based challenge report.

Use this structure:

### Challenge

Give a one-paragraph overall assessment of how well
the original conclusion survives the challenge.

### Supporting evidence

Explain evidence that supports the conclusion.

### Contradicting evidence

Explain evidence that weakens or conflicts with the
conclusion.

### Missing evidence

Explain what evidence would be required to make the
conclusion stronger.

### Alternative explanations

Identify plausible alternative explanations only when
supported by the available evidence.

### Bottom line

State whether the conclusion is:
- supported
- partially supported
- contradicted
- insufficiently supported

Do not invent metrics.

Do not assume currency.

Do not claim causality unless the evidence establishes it.

Do not turn a possible explanation into a confirmed cause.

Keep descriptive observations separate from interpretation.
"""


def challenge_synthesizer(
    state: ChallengeState,
) -> dict[str, Any]:

    prompt = get_challenge_synthesis_prompt(
        question=state["question"],
        original_answer=state["original_answer"],
        claims=state["claims"],
        evidence=state["challenge_evidence"],
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an enterprise analytics "
                    "challenge reviewer."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
    )

    answer = (
        response.choices[0].message.content
        or "Unable to generate challenge assessment."
    )

    return {
        "challenge_answer": answer
    }


def stream_challenge_synthesis(
    question: str,
    original_answer: str,
    claims: list[dict[str, Any]],
    evidence: dict[str, Any],
):

    prompt = get_challenge_synthesis_prompt(
        question=question,
        original_answer=original_answer,
        claims=claims,
        evidence=evidence,
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an enterprise analytics "
                    "challenge reviewer."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        stream=True,
    )

    for chunk in response:

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        if delta.content:
            yield delta.content


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_challenge_graph():

    graph = StateGraph(
        ChallengeState
    )

    graph.add_node(
        "claim_extractor",
        extract_claims,
    )

    graph.add_node(
        "challenge_planner",
        challenge_planner,
    )

    graph.add_node(
        "challenge_evidence_collector",
        challenge_evidence_collector,
    )

    graph.add_node(
        "claim_evaluator",
        evaluate_claims,
    )

    graph.add_node(
        "challenge_synthesizer",
        challenge_synthesizer,
    )

    graph.add_edge(
        START,
        "claim_extractor",
    )

    graph.add_edge(
        "claim_extractor",
        "challenge_planner",
    )

    graph.add_edge(
        "challenge_planner",
        "challenge_evidence_collector",
    )

    graph.add_edge(
        "challenge_evidence_collector",
        "claim_evaluator",
    )

    graph.add_edge(
        "claim_evaluator",
        "challenge_synthesizer",
    )

    graph.add_edge(
        "challenge_synthesizer",
        END,
    )

    return graph.compile()


challenge_graph = (
    build_challenge_graph()
)


# ---------------------------------------------------------------------------
# Challenge preparation
# ---------------------------------------------------------------------------

def prepare_challenge(
    investigation_id: str,
):
    session = (
        investigation_session_manager.get_session(
            investigation_id
        )
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

    result = challenge_graph.invoke(
        {
            "question": question,
            "original_answer": original_answer,
            "hypotheses": [],
            "evidence": session.get(
                "latest_evidence",
                {},
            ),
            "claims": [],
            "challenge_plan": [],
            "challenge_evidence": {},
            "challenge_answer": "",
        }
    )

    return {
        "question": question,
        "original_answer": original_answer,
        "claims": result["claims"],
        "challenge_plan": result[
            "challenge_plan"
        ],
        "challenge_evidence": result[
            "challenge_evidence"
        ],
        "challenge_answer": result[
            "challenge_answer"
        ],
    }