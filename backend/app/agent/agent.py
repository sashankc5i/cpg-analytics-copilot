import json
import logging
from pyexpat.errors import messages
import re
import time
from copy import deepcopy

from groq import Groq
from groq import RateLimitError

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    TOOL_DEFINITIONS,
    execute_tool_as_json,
)
from app.agent.clarification import (
    build_clarification_response,
)
from app.config import get_settings
from app.agent.session import conversation_manager
from app.analytics.metrics import (
    resolve_metric_from_text,
)
settings = get_settings()

MAX_TOOL_ITERATIONS = settings.max_tool_iterations

# Keep the generated response bounded so a single request does not consume
# most of the organization's TPM window.
MAX_COMPLETION_TOKENS = 1200

# A 429 can be temporary. Retry a small, bounded number of times instead of
# immediately converting the provider response into a 500.
MAX_RATE_LIMIT_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 5.0
MAX_RETRY_DELAY_SECONDS = 30.0

logger = logging.getLogger(__name__)


def _is_daily_token_limit(
    error: RateLimitError,
) -> bool:
    """
    Detect provider errors caused by a daily token limit.

    Daily token exhaustion must fail fast because retrying within the
    same request will not meaningfully change the available quota.
    """

    message = str(error).lower()

    daily_limit_markers = (
        "tpd",
        "tokens per day",
        "daily token",
        "daily limit",
        "per day",
    )

    return any(
        marker in message
        for marker in daily_limit_markers
    )


def _retry_delay_from_error(
    error: RateLimitError,
    attempt: int = 0,
) -> float:
    """
    Extract Groq's suggested retry delay when it is present.

    Groq commonly includes a message such as:
    "Please try again in 17.67s."

    If the provider does not provide a retry delay, use bounded
    exponential backoff.
    """

    message = str(error)

    match = re.search(
        r"try again in\s+([0-9]+(?:\.[0-9]+)?)s",
        message,
        flags=re.IGNORECASE,
    )

    if match:
        try:
            return min(
                float(match.group(1)),
                MAX_RETRY_DELAY_SECONDS,
            )
        except ValueError:
            pass

    # Some provider responses expose Retry-After as a header.
    response = getattr(
        error,
        "response",
        None,
    )

    headers = getattr(
        response,
        "headers",
        None,
    )

    if headers:
        retry_after = headers.get(
            "retry-after"
        )

        if retry_after:
            try:
                return min(
                    float(retry_after),
                    MAX_RETRY_DELAY_SECONDS,
                )
            except (TypeError, ValueError):
                pass

    # Bounded exponential backoff:
    #
    # attempt 0 -> 5s
    # attempt 1 -> 10s
    # attempt 2 -> 20s
    #
    # Never exceed MAX_RETRY_DELAY_SECONDS.
    return min(
        DEFAULT_RETRY_DELAY_SECONDS * (2 ** attempt),
        MAX_RETRY_DELAY_SECONDS,
    )


def _build_analytical_context_message(
    analytical_context: dict | None,
) -> dict | None:
    """
    Build a compact system message containing the current analytical context.

    The context is intentionally small and structured so that follow-up
    questions can reuse successful filters without replaying large amounts
    of conversational history.
    """

    if not analytical_context:
        return None

    context = {
        "metric": analytical_context.get("metric"),
        "filters": analytical_context.get("filters", {}),
        "date_range": analytical_context.get(
            "date_range",
            {
                "start_date": None,
                "end_date": None,
            },
        ),
        "comparison_period": analytical_context.get(
            "comparison_period"
        ),
        "selected_entity": analytical_context.get(
            "selected_entity"
        ),
        "active_investigation": analytical_context.get(
            "active_investigation"
        ),
        "last_tool": analytical_context.get("last_tool"),
    }

    return {
        "role": "system",
        "content": (
            "CURRENT ANALYTICAL CONTEXT:\n"
            f"{json.dumps(context, separators=(',', ':'))}\n\n"
            "Use this context to resolve follow-up analytical questions. "
            "Preserve existing filters when the user does not explicitly "
            "change them. If the user explicitly changes a filter, use the "
            "new value instead. Do not invent values that are not present "
            "in the context."
        ),
    }

def _update_metric_context_from_message(
    context: dict,
    user_message: str,
) -> dict:
    """
    Resolve an explicitly identifiable governed metric from the
    current user message.

    The resolver is deterministic and conservative. If the
    current message does not identify exactly one governed metric,
    the existing metric context is preserved.
    """

    updated_context = deepcopy(
        context
    )

    metric = resolve_metric_from_text(
        user_message
    )

    if metric is None:
        return updated_context

    updated_context["metric"] = {
        "id": metric["metric_id"],
        "display_name": metric["display_name"],
    }

    return updated_context
def _update_analytical_context_from_tool(
    context: dict,
    tool_name: str,
    arguments: dict,
) -> dict:
    """
    Update analytical context only from a successfully executed tool call.

    The LLM does not directly control this state. Context is derived from
    validated tool arguments instead.
    """

    updated_context = deepcopy(context)

    filters = arguments.get("filters") or {}

    if filters:
        existing_filters = updated_context.setdefault(
            "filters",
            {},
        )

        for key, value in filters.items():
            existing_filters[key] = value

        date_range = updated_context.setdefault(
            "date_range",
            {
                "start_date": None,
                "end_date": None,
            },
        )

        if "start_date" in filters:
            date_range["start_date"] = filters["start_date"]

        if "end_date" in filters:
            date_range["end_date"] = filters["end_date"]

    updated_context["last_tool"] = tool_name

    return updated_context


class AnalyticsAgent:

    def __init__(self):
        if not settings.groq_api_key.get_secret_value():
            raise ValueError(
                "GROQ_API_KEY is not configured."
            )

        self.client = Groq(
            api_key=settings.groq_api_key.get_secret_value(),
            max_retries=0,
        )

        self.model = settings.groq_model

    def _call_llm(
    self,
    messages: list,
    ):
        """
        Call the LLM and validate the provider response.

        Rate limits are classified before retrying:

        - Daily token exhaustion (TPD) fails immediately.
        - Temporary rate limits use bounded retry with backoff.
        - Other provider failures are converted into controlled
          RuntimeError exceptions.

        The completion token limit is intentionally bounded to reduce
        unnecessary TPM consumption.
        """

        logger.info(
            "agent_llm_call_started | model=%s | messages=%s",
            self.model,
            len(messages),
        )

        

        response = None

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    max_tokens=MAX_COMPLETION_TOKENS,
                    temperature=0,
                )
                break

            except RateLimitError as error:

                # ---------------------------------------------------------
                # Daily token exhaustion
                # ---------------------------------------------------------
                #
                # A TPD limit cannot be solved by retrying the same request
                # a few seconds later. Retrying here only wastes time and
                # causes the request to hang unnecessarily.
                #
                if _is_daily_token_limit(error):
                    logger.error(
                        "agent_llm_daily_token_limit | "
                        "model=%s | "
                        "attempt=%s",
                        self.model,
                        attempt + 1,
                    )

                    raise RuntimeError(
                        "The analytics model has reached its daily "
                        "token limit. Please try again later."
                    ) from error

                # ---------------------------------------------------------
                # Temporary rate limit
                # ---------------------------------------------------------
                if attempt >= MAX_RATE_LIMIT_RETRIES:
                    logger.error(
                        "agent_llm_rate_limit_exhausted | "
                        "model=%s | attempts=%s",
                        self.model,
                        attempt + 1,
                    )

                    raise RuntimeError(
                        "The analytics model is temporarily "
                        "rate-limited. Please try again shortly."
                    ) from error

                delay = _retry_delay_from_error(
                    error,
                    attempt=attempt,
                )

                logger.warning(
                    "agent_llm_rate_limited | "
                    "model=%s | "
                    "attempt=%s/%s | "
                    "retry_in=%.2fs",
                    self.model,
                    attempt + 1,
                    MAX_RATE_LIMIT_RETRIES + 1,
                    delay,
                )

                time.sleep(delay)

            except Exception as error:
                logger.exception(
                    "agent_llm_call_failed | model=%s",
                    self.model,
                )

                raise RuntimeError(
                    "The analytics model could not be reached."
                ) from error

        if not response:
            logger.error(
                "agent_llm_empty_response | model=%s",
                self.model,
            )

            raise RuntimeError(
                "The analytics model returned an empty response."
            )

        choices = getattr(
            response,
            "choices",
            None,
        )

        if not choices:
            logger.error(
                "agent_llm_response_missing_choices | model=%s",
                self.model,
            )

            raise RuntimeError(
                "The analytics model returned an invalid response."
            )

        assistant_message = getattr(
            choices[0],
            "message",
            None,
        )

        if assistant_message is None:
            logger.error(
                "agent_llm_response_missing_message | model=%s",
                self.model,
            )

            raise RuntimeError(
                "The analytics model returned an invalid message."
            )

        return assistant_message

    def _validate_final_answer(
        self,
        assistant_message,
    ) -> str:
        """
        Validate the final assistant response.

        A final response must contain non-empty text.
        """

        content = getattr(
            assistant_message,
            "content",
            None,
        )

        if not isinstance(content, str):
            logger.error(
                "agent_llm_final_answer_invalid_type"
            )

            raise RuntimeError(
                "The analytics model returned an invalid answer."
            )

        answer = content.strip()

        if not answer:
            logger.error(
                "agent_llm_final_answer_empty"
            )

            raise RuntimeError(
                "The analytics model returned an empty answer."
            )

        return answer

    def run(
        self,
        user_message: str,
        history: list | None = None,
        analytical_context: dict | None = None,
    ):
        """
        Run the analytics agent.

        analytical_context contains structured state from previously
        successful analytical tool executions. It is used to resolve
        follow-up questions without relying entirely on raw conversation
        history.

        Context is maintained locally during the request and returned to
        the caller. The caller is responsible for persisting it.
        """

        logger.info(
            "agent_started | model=%s",
            self.model,
        )

        # ---------------------------------------------------------
        # 1. Clarification gate
        # ---------------------------------------------------------
        #
        # This is intentionally before the normal LLM/tool flow.
        # If the request is genuinely ambiguous, return the
        # clarification question immediately.
        #
        clarification = build_clarification_response(
            user_message
        )

        if clarification:
            logger.info(
                "agent_clarification_requested | "
                "reason=missing_comparison"
            )

            default_context = {
                "metric": None,
                "filters": {},
                "date_range": {
                    "start_date": None,
                    "end_date": None,
                },
                "comparison_period": None,
                "selected_entity": None,
                "active_investigation": None,
                "last_tool": None,
            }

            return {
                "answer": clarification,
                "tools_used": [],
                "tool_results": [],
                "messages": [
                    {
                        "role": "user",
                        "content": user_message,
                    },
                    {
                        "role": "assistant",
                        "content": clarification,
                    },
                ],
                "analytical_context": deepcopy(
                    analytical_context
                    or default_context
                ),
            }

        # ---------------------------------------------------------
        # 2. Normal analytical execution
        # ---------------------------------------------------------
        #
        # IMPORTANT:
        # This block must NOT be inside `if clarification:`.
        #

        working_context = deepcopy(
            analytical_context
            or {
                "metric": None,
                "filters": {},
                "date_range": {
                    "start_date": None,
                    "end_date": None,
                },
                "comparison_period": None,
                "selected_entity": None,
                "active_investigation": None,
                "last_tool": None,
            }
        )

        working_context = _update_metric_context_from_message(
            context=working_context,
            user_message=user_message,
        )

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

        context_message = _build_analytical_context_message(
            working_context
        )

        if context_message:
            messages.append(
                context_message
            )

        if history:
            messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        tools_used = []
        tool_results = []

        # ---------------------------------------------------------
        # 3. LLM / tool-calling loop
        # ---------------------------------------------------------

        for iteration in range(
            MAX_TOOL_ITERATIONS
        ):
            assistant_message = self._call_llm(
                messages
            )

            messages.append(
                assistant_message
            )

            # -----------------------------------------------------
            # Final answer
            # -----------------------------------------------------

            if not assistant_message.tool_calls:
                answer = self._validate_final_answer(
                    assistant_message
                )

                logger.info(
                    "agent_completed | "
                    "model=%s | "
                    "iterations=%s | "
                    "tools_used=%s",
                    self.model,
                    iteration + 1,
                    len(tools_used),
                )

                return {
                    "answer": answer,
                    "tools_used": tools_used,
                    "tool_results": tool_results,
                    "messages": messages,
                    "analytical_context": working_context,
                }

            # -----------------------------------------------------
            # Tool execution
            # -----------------------------------------------------

            for tool_call in (
                assistant_message.tool_calls
            ):
                tool_name = (
                    tool_call.function.name
                )

                logger.info(
                    "agent_tool_execution_started | "
                    "tool=%s | "
                    "iteration=%s",
                    tool_name,
                    iteration + 1,
                )

                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                        or "{}"
                    )

                    result = execute_tool_as_json(
                        tool_name,
                        arguments,
                    )

                    # Update analytical context only after
                    # successful tool execution.
                    working_context = (
                        _update_analytical_context_from_tool(
                            context=working_context,
                            tool_name=tool_name,
                            arguments=arguments,
                        )
                    )

                    tools_used.append(
                        tool_name
                    )

                    try:
                        parsed_result = json.loads(
                            result
                        )
                    except json.JSONDecodeError:
                        parsed_result = result

                    tool_results.append(
                        {
                            "tool": tool_name,
                            "result": parsed_result,
                        }
                    )

                    logger.info(
                        "agent_tool_execution_completed | "
                        "tool=%s | "
                        "iteration=%s",
                        tool_name,
                        iteration + 1,
                    )

                except Exception as error:
                    logger.exception(
                        "agent_tool_execution_failed | "
                        "tool=%s | "
                        "iteration=%s",
                        tool_name,
                        iteration + 1,
                    )

                    result = json.dumps(
                        {
                            "error": str(error)
                        }
                    )

                    tool_results.append(
                        {
                            "tool": tool_name,
                            "result": {
                                "error": str(error)
                            },
                        }
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": (
                            tool_call.id
                        ),
                        "name": tool_name,
                        "content": result,
                    }
                )

        # ---------------------------------------------------------
        # 4. Maximum tool iterations exceeded
        # ---------------------------------------------------------

        logger.error(
            "agent_max_tool_iterations_exceeded | "
            "model=%s | "
            "max_iterations=%s",
            self.model,
            MAX_TOOL_ITERATIONS,
        )

        raise RuntimeError(
            "Agent exceeded maximum "
            "tool-calling iterations."
        )

agent = AnalyticsAgent()