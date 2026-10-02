import json
from typing import Any, TypedDict

from groq import Groq
from langgraph.graph import END, START, StateGraph

from app.agent.claims import validate_claims
from app.agent.confidence import calculate_confidence
from app.agent.evidence_graph import build_evidence_graph
from app.agent.investigation_session import (
    investigation_session_manager,
)
from app.agent.retry import execute_with_retry
from app.agent.tools import execute_tool
from app.config import get_settings


settings = get_settings()


# ============================================================
# Investigation configuration
# ============================================================

INVESTIGATION_CATALOG = [
    "revenue_trend",
    "regional_performance",
    "product_performance",
    "category_performance",
    "customer_segments",
    "promotion_impact",
    "inventory_stockouts",
]

INVESTIGATION_TO_TOOL = {
    "revenue_trend": "get_monthly_sales_trend",
    "regional_performance": "get_sales_by_region",
    "product_performance": "get_top_products",
    "category_performance": "get_sales_by_category",
    "customer_segments": "get_customer_segment_performance",
    "promotion_impact": "get_promotion_impact",
    "inventory_stockouts": "get_stockout_rate",
}

VALID_HYPOTHESIS_STATUSES = {
    "unverified",
    "supported",
    "partially_supported",
    "not_supported",
}

MAX_HYPOTHESES = 5
MAX_CLAIMS = 10

# Keep structured claim generation bounded.
CLAIM_MAX_TOKENS = 4096


# ============================================================
# LangGraph state
# ============================================================

class InvestigationState(TypedDict):
    question: str
    history: list[dict[str, str]]
    hypotheses: list[dict[str, Any]]
    plan: list[str]
    evidence: dict[str, Any]
    claims: list[dict[str, Any]]
    confidence: dict[str, Any]
    evidence_graph: dict[str, Any]
    answer: str


# ============================================================
# Groq client
# ============================================================

client = Groq(
    api_key=settings.groq_api_key.get_secret_value(),
    max_retries=0,
)


# ============================================================
# Planner
# ============================================================

def get_planner_prompt(
    question: str,
    history: list[dict[str, str]],
) -> str:

    history_text = ""

    if history:
        history_text = "\n".join(
            f"{message['role'].upper()}: "
            f"{message['content']}"
            for message in history
        )

    return f"""
You are the investigation planner for an enterprise
CPG analytics system.

Your job is to determine which analytical investigations
are relevant to the user's CURRENT question.

The available investigations are:

{json.dumps(INVESTIGATION_CATALOG, indent=2)}

Previous investigation conversation:

{history_text or "No previous investigation conversation."}

Current question:

{question}

Rules:

1. The current question has priority over previous messages.
2. Previous messages provide context only.
3. Select only investigations from the approved catalog.
4. Do not invent investigation names.
5. Select only investigations that are relevant.
6. A diagnostic question may require multiple investigations.
7. Return JSON only.

Return exactly this JSON object.
Generate only the claims needed to represent the strongest
observable findings; do not enumerate every data point.


{{
    "investigations": [
        "investigation_name"
    ]
}}
"""


def validate_plan(
    plan: list[str],
) -> list[str]:

    validated = []

    if not isinstance(plan, list):
        return validated

    for item in plan:
        if item in INVESTIGATION_CATALOG:
            if item not in validated:
                validated.append(item)

    return validated


def planner(
    state: InvestigationState,
) -> dict:

    question = state["question"]
    history = state["history"]

    print(
        "[Investigation Planner] "
        f"Planning investigation for: {question}"
    )

    if history:
        print(
            "[Investigation Planner] "
            f"Using {len(history)} previous messages"
        )

    response = execute_with_retry(
        lambda: client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": get_planner_prompt(
                        question,
                        history,
                    ),
                }
            ],
            temperature=0,
            response_format={
                "type": "json_object"
            },
        ),
        operation_name="investigation_planner",
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "Investigation planner returned an empty response."
        )

    parsed = json.loads(content)

    plan = validate_plan(
        parsed.get("investigations", [])
    )

    print(
        "[Investigation Planner] "
        f"Selected: {plan}"
    )

    return {
        "plan": plan,
    }


# ============================================================
# Hypothesis Generator
# ============================================================

def get_hypothesis_prompt(
    question: str,
    history: list[dict[str, str]],
) -> str:

    history_text = ""

    if history:
        history_text = "\n".join(
            f"{message['role'].upper()}: "
            f"{message['content']}"
            for message in history
        )

    return f"""
You are the hypothesis generation layer of an
enterprise CPG analytics investigation system.

Your task is to generate plausible BUSINESS HYPOTHESES
that could explain the user's current question.

You are NOT determining the answer.

You are proposing explanations that must later be
tested against deterministic analytical evidence.

CURRENT QUESTION:

{question}

PREVIOUS INVESTIGATION CONVERSATION:

{history_text or "No previous investigation conversation."}

APPROVED INVESTIGATIONS:

{json.dumps(INVESTIGATION_CATALOG, indent=2)}

Each hypothesis MUST specify which approved investigations
are required to test it.

Rules:

1. Generate hypotheses specifically relevant to the
   current question.
2. Do not blindly generate generic hypotheses.
3. Generate between 2 and {MAX_HYPOTHESES} hypotheses.
4. Each hypothesis must be testable using the approved
   investigation catalog.
5. Use only investigation names from the approved catalog.
6. Never claim that a hypothesis is true.
7. Every hypothesis must start with status "unverified".
8. Do not include numerical claims.
9. Do not invent business facts.
10. Previous conversation is context, not evidence.
11. The current question has priority.
12. Return JSON only.

Return exactly this structure:

{{
    "hypotheses": [
        {{
            "id": "H1",
            "statement": "A plausible explanation",
            "required_investigations": [
                "approved_investigation"
            ],
            "status": "unverified"
        }}
    ]
}}
"""


def generate_hypotheses(
    state: InvestigationState,
) -> dict:

    question = state["question"]
    history = state["history"]

    print(
        "[Hypothesis Generator] "
        f"Generating hypotheses for: {question}"
    )

    response = execute_with_retry(
        lambda: client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": get_hypothesis_prompt(
                        question,
                        history,
                    ),
                }
            ],
            temperature=0,
            response_format={
                "type": "json_object"
            },
        ),
        operation_name="investigation_hypothesis_generation",
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "Hypothesis generator returned an empty response."
        )

    parsed = json.loads(content)

    hypotheses = validate_hypotheses(
        parsed.get("hypotheses", [])
    )

    print(
        "[Hypothesis Generator] "
        f"Generated {len(hypotheses)} valid hypotheses"
    )

    for hypothesis in hypotheses:
        print(
            "[Hypothesis Generator] "
            f"{hypothesis['id']} | "
            f"{hypothesis['statement']} | "
            f"{hypothesis['required_investigations']}"
        )

    return {
        "hypotheses": hypotheses,
    }


# ============================================================
# Hypothesis validation
# ============================================================

def validate_hypotheses(
    hypotheses: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    validated = []

    if not isinstance(hypotheses, list):
        return validated

    for hypothesis in hypotheses:

        if not isinstance(hypothesis, dict):
            continue

        hypothesis_id = hypothesis.get("id")
        statement = hypothesis.get("statement")
        investigations = hypothesis.get(
            "required_investigations",
            [],
        )

        if not hypothesis_id:
            continue

        if not statement:
            continue

        if not isinstance(
            investigations,
            list,
        ):
            continue

        valid_investigations = []

        for investigation in investigations:

            if investigation in INVESTIGATION_CATALOG:
                if investigation not in valid_investigations:
                    valid_investigations.append(
                        investigation
                    )

        # A hypothesis that cannot be tested by our
        # approved analytics layer is not useful.
        if not valid_investigations:
            continue

        validated.append(
            {
                "id": hypothesis_id,
                "statement": statement,
                "required_investigations": (
                    valid_investigations
                ),
                "status": "unverified",
                "evidence": {},
            }
        )

        if len(validated) >= MAX_HYPOTHESES:
            break

    return validated


# ============================================================
# Evidence Collector
# ============================================================

def evidence_collector(
    state: InvestigationState,
) -> dict:

    plan = state["plan"]
    hypotheses = state["hypotheses"]

    print(
        "[Evidence Collector] "
        f"Collecting evidence for: {plan}"
    )

    evidence = {}

    # --------------------------------------------------------
    # Collect evidence from planner-selected investigations.
    # --------------------------------------------------------

    for investigation in plan:

        tool_name = INVESTIGATION_TO_TOOL.get(
            investigation
        )

        if not tool_name:
            continue

        print(
            "[Evidence Collector] "
            f"Running {tool_name}"
        )

        result = execute_tool(
            tool_name,
            {},
        )

        evidence[investigation] = result

    # --------------------------------------------------------
    # Make sure hypothesis-required investigations are also
    # collected.
    #
    # This is important because the hypothesis generator is
    # independent from the planner.
    # --------------------------------------------------------

    for hypothesis in hypotheses:

        for investigation in hypothesis.get(
            "required_investigations",
            [],
        ):

            if investigation in evidence:
                continue

            tool_name = INVESTIGATION_TO_TOOL.get(
                investigation
            )

            if not tool_name:
                continue

            print(
                "[Evidence Collector] "
                f"Running hypothesis-required "
                f"{tool_name}"
            )

            result = execute_tool(
                tool_name,
                {},
            )

            evidence[investigation] = result

    # --------------------------------------------------------
    # Attach relevant evidence to hypotheses.
    # --------------------------------------------------------

    validated_hypotheses = []

    for hypothesis in hypotheses:

        hypothesis_copy = dict(hypothesis)

        hypothesis_evidence = {}

        for investigation in hypothesis.get(
            "required_investigations",
            [],
        ):

            if investigation in evidence:
                hypothesis_evidence[
                    investigation
                ] = evidence[investigation]

        hypothesis_copy["evidence"] = (
            hypothesis_evidence
        )

        validated_hypotheses.append(
            hypothesis_copy
        )

    print(
        "[Evidence Collector] "
        f"Collected evidence for: "
        f"{list(evidence.keys())}"
    )

    return {
        "evidence": evidence,
        "hypotheses": validated_hypotheses,
    }


# ============================================================
# Claim Generator
# ============================================================

def build_claim_hypothesis_context(
    hypotheses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build a compact representation of hypotheses for claim
    generation.

    Hypotheses contain attached evidence after the evidence
    collector runs. Sending that evidence again to the claim
    generator duplicates a potentially large amount of data.

    The claim generator already receives the complete
    deterministic evidence separately, so only the hypothesis
    metadata is required here.
    """

    compact_hypotheses = []

    for hypothesis in hypotheses:

        compact_hypotheses.append(
            {
                "id": hypothesis.get("id"),
                "statement": hypothesis.get("statement"),
                "required_investigations": hypothesis.get(
                    "required_investigations",
                    [],
                ),
                "status": hypothesis.get(
                    "status",
                    "unverified",
                ),
            }
        )

    return compact_hypotheses


def get_claim_prompt(
    question: str,
    evidence: dict[str, Any],
    hypotheses: list[dict[str, Any]],
) -> str:

    compact_hypotheses = build_claim_hypothesis_context(
        hypotheses
    )

    return f"""
You are the claim generation layer of an enterprise
CPG analytics investigation system.

Your job is to identify concise, evidence-backed BUSINESS
OBSERVATIONS from deterministic analytical evidence.

You are NOT writing the final answer.

CURRENT QUESTION:

{question}

HYPOTHESIS CONTEXT:

{json.dumps(compact_hypotheses, indent=2, default=str)}

DETERMINISTIC ANALYTICAL EVIDENCE:

{json.dumps(evidence, indent=2, default=str)}

Generate concise candidate claims that can be directly traced
to the supplied deterministic evidence.

Rules:

1. Use ONLY the supplied deterministic evidence.
2. Never invent metrics, values, entities, periods, or facts.
3. Do not infer causality.
4. Do not turn a hypothesis into a fact.
5. Claims must describe observable analytical findings.
6. Prefer the most decision-relevant observations instead of
   exhaustively listing every increase or decrease.
7. Generate only the minimum number of useful claims needed to
   represent the strongest observed findings.
8. Every claim MUST contain at least one evidence reference.
9. Every evidence reference MUST use an investigation name
   that exists in the supplied evidence.
10. The "field" must be an actual field present in the
    referenced evidence.
11. If referencing a specific entity, use the exact value
    appearing in the evidence.
12. If no specific entity is applicable, use null.
13. Do not include a status field.
14. Do not claim that an observation is causally responsible
    for another observation.
15. Generate at most {MAX_CLAIMS} claims.
16. Keep each claim statement concise.
17. Return JSON only.
18. Do not return markdown.
19. Do not return explanatory text outside the JSON object.

Return exactly:

{{
    "claims": [
        {{
            "id": "C1",
            "statement": "An observable evidence-backed finding.",
            "evidence_refs": [
                {{
                    "investigation": "regional_performance",
                    "field": "revenue",
                    "entity": "South"
                }}
            ]
        }}
    ]
}}
"""


def generate_claims(
    state: InvestigationState,
) -> dict:

    question = state["question"]
    evidence = state["evidence"]
    hypotheses = state["hypotheses"]

    print(
        "[Claim Generator] "
        f"Generating claims from "
        f"{len(evidence)} evidence sources"
    )

    if not evidence:
        print(
            "[Claim Generator] "
            "No deterministic evidence available"
        )

        return {
            "claims": []
        }

    response = execute_with_retry(
        lambda: client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": get_claim_prompt(
                        question,
                        evidence,
                        hypotheses,
                    ),
                }
            ],
            temperature=0,
            max_tokens=CLAIM_MAX_TOKENS,
            response_format={
                "type": "json_object"
            },
        ),
        operation_name="investigation_claim_generation",
    )

    content = response.choices[0].message.content

    if not content:
        print(
            "[Claim Generator] "
            "LLM returned an empty response"
        )

        return {
            "claims": []
        }

    parsed = json.loads(content)

    candidate_claims = parsed.get(
        "claims",
        [],
    )

    claims = validate_claims(
        candidate_claims,
        evidence,
    )

    if len(claims) > MAX_CLAIMS:
        claims = claims[:MAX_CLAIMS]

    print(
        "[Claim Generator] "
        f"Validated {len(claims)} "
        "traceable claims"
    )

    for claim in claims:
        print(
            "[Claim Generator] "
            f"{claim['id']} | "
            f"{claim['traceability_status']} | "
            f"{claim['statement']}"
        )

    return {
        "claims": claims,
    }


def assess_confidence(
    state: InvestigationState,
) -> dict[str, Any]:
    confidence = calculate_confidence(
        plan=state["plan"],
        evidence=state["evidence"],
        hypotheses=state["hypotheses"],
        claims=state["claims"],
    )

    print(
        "[Confidence Assessor] "
        f"score={confidence['score']} | "
        f"level={confidence['level']}"
    )

    return {
        "confidence": confidence,
    }


def build_graph(
    state: InvestigationState,
) -> dict[str, Any]:
    graph = build_evidence_graph(
        claims=state["claims"],
        evidence=state["evidence"],
    )

    print(
        "[Evidence Graph] "
        f"nodes={len(graph['nodes'])} | "
        f"edges={len(graph['edges'])}"
    )

    return {
        "evidence_graph": graph,
    }


# ============================================================
# Synthesis
# ============================================================

def build_synthesis_context(
    question: str,
    evidence: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    history: list[dict[str, str]],
    claims: list[dict[str, Any]] | None = None,
    confidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a purpose-specific context for the synthesis LLM.

    Hypotheses may contain evidence attached by the evidence collector.
    The complete deterministic evidence is already supplied separately,
    so that attached evidence is intentionally removed here to avoid
    duplicating the same data in the synthesis prompt.

    The synthesizer receives:
    - the current question
    - compact hypothesis metadata
    - complete deterministic evidence
    - validated traceable claims
    - prior investigation conversation
    """

    return {
        "question": question,
        "history": history,
        "hypotheses": build_claim_hypothesis_context(hypotheses),
        "evidence": evidence,
        "claims": claims or [],
        "confidence": confidence or {},
    }


def get_synthesis_prompt(
    question: str,
    evidence: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    history: list[dict[str, str]],
    claims: list[dict[str, Any]] | None = None,
    confidence: dict[str, Any] | None = None,
) -> str:

    context = build_synthesis_context(
        question=question,
        evidence=evidence,
        hypotheses=hypotheses,
        history=history,
        claims=claims,
        confidence=confidence,
    )

    history_text = ""

    if context["history"]:
        history_text = "\n".join(
            f"{message['role'].upper()}: "
            f"{message['content']}"
            for message in context["history"]
        )

    return f"""
You are the synthesis layer of an enterprise
CPG analytics investigation system.

USER QUESTION:

{context["question"]}

PREVIOUS INVESTIGATION CONVERSATION:

{history_text or "No previous conversation."}

HYPOTHESIS TREE:

{json.dumps(context["hypotheses"], indent=2, default=str)}

DETERMINISTIC ANALYTICAL EVIDENCE:

{json.dumps(context["evidence"], indent=2, default=str)}

TRACEABLE CANDIDATE CLAIMS:

{json.dumps(context["claims"], indent=2, default=str)}

EVIDENCE-BASED CONFIDENCE:

{json.dumps(context["confidence"], indent=2, default=str)}

Rules:

1. SQLite analytics are the source of truth.
2. Never invent metrics.
3. Never fabricate numbers.
4. Do not assume currency unless explicitly provided.
5. Do not treat a hypothesis as proven merely because it
   was generated.
6. Distinguish observed facts from possible explanations.
7. Do not claim causality unless the evidence supports it.
8. Evaluate hypotheses using the evidence attached to them.
9. Use traceable candidate claims as evidence-backed
   observations, but do not treat their traceability alone
   as proof of causality.
10. Previous answers are context, not factual evidence.
11. The current question has priority.
12. If evidence is insufficient, explicitly say so.
13. Do not force a conclusion.
14. Treat the confidence assessment as evidence coverage, not a probability of truth.
15. Explain important confidence limitations when they materially affect the conclusion.

Structure the answer as:

### Finding

Give the main evidence-backed finding.

### Evidence

Explain the most relevant observed metrics.

### Hypothesis assessment

Discuss which hypotheses are supported by the available
evidence and which remain unverified.

### Possible explanations

Clearly label explanations that are not proven.

### Caveat

Mention important limitations or missing evidence.

Keep the answer concise but useful for a business user.
"""


def synthesizer(
    state: InvestigationState,
) -> dict:

    question = state["question"]
    evidence = state["evidence"]
    hypotheses = state["hypotheses"]
    history = state["history"]
    claims = state["claims"]
    confidence = state["confidence"]

    print(
        "[Investigation Synthesizer] "
        "Generating final answer"
    )

    response = execute_with_retry(
        lambda: client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": get_synthesis_prompt(
                        question,
                        evidence,
                        hypotheses,
                        history,
                        claims,
                        confidence,
                    ),
                }
            ],
            temperature=0,
        ),
        operation_name="investigation_synthesis",
    )

    answer = response.choices[0].message.content

    if not answer:
        raise ValueError(
            "Investigation synthesizer returned an empty response."
        )

    return {
        "answer": answer,
    }


# ============================================================
# Streaming synthesis
# ============================================================

def stream_synthesis(
    question: str,
    evidence: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    history: list[dict[str, str]],
    claims: list[dict[str, Any]] | None = None,
    confidence: dict[str, Any] | None = None,
):
    """
    Stream the final investigation synthesis.

    The retry wrapper protects the initial provider request.
    Once the stream has started, already-emitted tokens are not
    replayed because replaying them could duplicate output.
    """

    response = execute_with_retry(
        lambda: client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": get_synthesis_prompt(
                        question,
                        evidence,
                        hypotheses,
                        history,
                        claims,
                        confidence,
                    ),
                }
            ],
            temperature=0,
            stream=True,
        ),
        operation_name="investigation_stream_synthesis",
    )

    for chunk in response:

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        if delta.content:
            yield delta.content


# ============================================================
# Full Investigation Graph
# ============================================================

def build_investigation_graph():

    graph = StateGraph(
        InvestigationState
    )

    graph.add_node(
        "planner",
        planner,
    )

    graph.add_node(
        "hypothesis_generator",
        generate_hypotheses,
    )

    graph.add_node(
        "evidence_collector",
        evidence_collector,
    )

    graph.add_node(
        "claim_generator",
        generate_claims,
    )

    graph.add_node(
        "confidence_assessor",
        assess_confidence,
    )

    graph.add_node(
        "evidence_graph",
        build_graph,
    )

    graph.add_node(
        "synthesizer",
        synthesizer,
    )

    graph.add_edge(
        START,
        "planner",
    )

    graph.add_edge(
        "planner",
        "hypothesis_generator",
    )

    graph.add_edge(
        "hypothesis_generator",
        "evidence_collector",
    )

    graph.add_edge(
        "evidence_collector",
        "claim_generator",
    )

    graph.add_edge(
        "claim_generator",
        "confidence_assessor",
    )

    graph.add_edge(
        "confidence_assessor",
        "evidence_graph",
    )

    graph.add_edge(
        "evidence_graph",
        "synthesizer",
    )

    graph.add_edge(
        "synthesizer",
        END,
    )

    return graph.compile()


investigation_graph = (
    build_investigation_graph()
)


# ============================================================
# Preparation Graph
# ============================================================

def build_investigation_preparation_graph():

    graph = StateGraph(
        InvestigationState
    )

    graph.add_node(
        "planner",
        planner,
    )

    graph.add_node(
        "hypothesis_generator",
        generate_hypotheses,
    )

    graph.add_node(
        "evidence_collector",
        evidence_collector,
    )

    graph.add_node(
        "claim_generator",
        generate_claims,
    )

    graph.add_node(
        "confidence_assessor",
        assess_confidence,
    )

    graph.add_node(
        "evidence_graph",
        build_graph,
    )

    graph.add_edge(
        START,
        "planner",
    )

    graph.add_edge(
        "planner",
        "hypothesis_generator",
    )

    graph.add_edge(
        "hypothesis_generator",
        "evidence_collector",
    )

    graph.add_edge(
        "evidence_collector",
        "claim_generator",
    )

    graph.add_edge(
        "claim_generator",
        "confidence_assessor",
    )

    graph.add_edge(
        "confidence_assessor",
        "evidence_graph",
    )

    graph.add_edge(
        "evidence_graph",
        END,
    )

    return graph.compile()


investigation_preparation_graph = (
    build_investigation_preparation_graph()
)


# ============================================================
# Prepare Investigation
# ============================================================

def prepare_investigation(
    question: str,
    investigation_id: str,
):

    history = (
        investigation_session_manager
        .get_history(investigation_id)
    )

    result = (
        investigation_preparation_graph.invoke(
            {
                "question": question,
                "history": history,
                "hypotheses": [],
                "plan": [],
                "evidence": {},
                "claims": [],
                "confidence": {},
                "evidence_graph": {},
                "answer": "",
            }
        )
    )

    return {
        "question": question,
        "history": history,
        "hypotheses": result["hypotheses"],
        "plan": result["plan"],
        "evidence": result["evidence"],
        "claims": result["claims"],
        "confidence": result["confidence"],
        "evidence_graph": result["evidence_graph"],
    }