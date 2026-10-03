import json
import logging
import re
import time
from copy import deepcopy

from groq import Groq
from groq import RateLimitError

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.clarification import build_clarification_response
from app.analytics.metrics import resolve_metric_from_text
from app.agent.tools import (
    TOOL_DEFINITIONS,
    execute_tool_as_json,
)

from app.config import get_settings
from app.logging_config import get_logger, log_event
from app.observability.telemetry import (
    record_llm_call,
    record_tool_execution,
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

logger = get_logger(__name__)


def _retry_delay_from_error(error: RateLimitError) -> float:
    """
    Extract Groq's suggested retry delay when it is present.

    Groq commonly includes a message such as:
    "Please try again in 17.67s."
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
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)

    if headers:
        retry_after = headers.get("retry-after")

        if retry_after:
            try:
                return min(
                    float(retry_after),
                    MAX_RETRY_DELAY_SECONDS,
                )
            except (TypeError, ValueError):
                pass

    return DEFAULT_RETRY_DELAY_SECONDS
def _is_daily_token_limit_error(error: RateLimitError) -> bool:
    """
    Detect provider responses indicating that the daily token
    allowance has been exhausted.

    Groq may describe this as TPD (tokens per day) or explicitly
    mention a daily token limit.
    """
    message = str(error).lower()

    return (
        "tpd limit" in message
        or "tokens per day" in message
        or "daily token limit" in message
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
    updated_context = deepcopy(context)

    metric = resolve_metric_from_text(user_message)

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
        tools_enabled: bool = True,
    ):
        """
        Call the LLM and validate the provider response.
        """

        logger.info(
            "agent_llm_call_started | model=%s | messages=%s",
            self.model,
            len(messages),
        )

        call_start = time.perf_counter()
        retry_count = 0
        response = None

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                request_kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0,
                    "max_completion_tokens": MAX_COMPLETION_TOKENS,
                }

                if tools_enabled:
                    request_kwargs["tools"] = TOOL_DEFINITIONS
                    request_kwargs["tool_choice"] = "auto"

                response = self.client.chat.completions.create(
                    **request_kwargs
                )

                usage = getattr(response, "usage", None)

                prompt_tokens = getattr(usage, "prompt_tokens", None)
                completion_tokens = getattr(usage, "completion_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)

                duration_ms = round(
                    (time.perf_counter() - call_start) * 1000,
                    2,
                )

                record_llm_call(
                    model=self.model,
                    duration_ms=duration_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    success=True,
                    retry_count=retry_count,
                )

                log_event(
                    logger,
                    "llm_call_completed",
                    model=self.model,
                    duration_ms=duration_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    retry_count=retry_count,
                )

                break

            except RateLimitError as error:
                if _is_daily_token_limit_error(error):
                    duration_ms = round(
                        (time.perf_counter() - call_start) * 1000,
                        2,
                    )

                    record_llm_call(
                        model=self.model,
                        duration_ms=duration_ms,
                        prompt_tokens=None,
                        completion_tokens=None,
                        total_tokens=None,
                        success=False,
                        retry_count=retry_count,
                        error_type=type(error).__name__,
                    )

                    log_event(
                        logger,
                        "llm_call_failed",
                        model=self.model,
                        duration_ms=duration_ms,
                        retry_count=retry_count,
                        error_type=type(error).__name__,
                        reason="daily_token_limit",
                    )

                    logger.warning(
                        "agent_llm_daily_token_limit | model=%s",
                        self.model,
                    )

                    raise RuntimeError(
                        "The analytics model has reached its daily token "
                        "limit. Please try again later."
                    ) from error

                if attempt >= MAX_RATE_LIMIT_RETRIES:
                    duration_ms = round(
                        (time.perf_counter() - call_start) * 1000,
                        2,
                    )

                    record_llm_call(
                        model=self.model,
                        duration_ms=duration_ms,
                        prompt_tokens=None,
                        completion_tokens=None,
                        total_tokens=None,
                        success=False,
                        retry_count=retry_count,
                        error_type=type(error).__name__,
                    )

                    log_event(
                        logger,
                        "llm_call_failed",
                        model=self.model,
                        duration_ms=duration_ms,
                        retry_count=retry_count,
                        error_type=type(error).__name__,
                    )

                    logger.exception(
                        "agent_llm_rate_limit_exhausted | model=%s | attempts=%s",
                        self.model,
                        attempt + 1,
                    )

                    raise RuntimeError(
                        "The analytics model is temporarily rate-limited. "
                        "Please try again shortly."
                    ) from error

                retry_count += 1
                delay = _retry_delay_from_error(error)

                logger.warning(
                    "agent_llm_rate_limited | model=%s | attempt=%s/%s | retry_in=%.2fs",
                    self.model,
                    attempt + 1,
                    MAX_RATE_LIMIT_RETRIES + 1,
                    delay,
                )

                time.sleep(delay)

            except Exception as error:
                duration_ms = round(
                    (time.perf_counter() - call_start) * 1000,
                    2,
                )

                record_llm_call(
                    model=self.model,
                    duration_ms=duration_ms,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    success=False,
                    retry_count=retry_count,
                    error_type=type(error).__name__,
                )

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

        choices = getattr(response, "choices", None)

        if not choices:
            logger.error(
                "agent_llm_response_missing_choices | model=%s",
                self.model,
            )

            raise RuntimeError(
                "The analytics model returned an invalid response."
            )

        assistant_message = getattr(choices[0], "message", None)

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

        # Work on a request-local copy so a failed tool execution cannot
        # accidentally mutate the persisted conversation context.
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

        clarification = build_clarification_response(user_message)

        if clarification:
            logger.info(
                "agent_clarification_required | model=%s",
                self.model,
            )

            return {
                "answer": clarification,
                "tools_used": [],
                "tool_results": [],
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                "analytical_context": working_context,
            }

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
            messages.append(context_message)

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
        executed_tool_results = {}

        # Stop evidence collection when the model repeats an identical
        # analytical tool request instead of spending another LLM call
        # deciding what to do next.
        duplicate_tool_detected = False

        for iteration in range(
            MAX_TOOL_ITERATIONS
        ):
            assistant_message = self._call_llm(
                messages
            )

            messages.append(
                assistant_message
            )

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

                tool_start = time.perf_counter()
                execution_key = None
                tool_was_executed = False

                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                        or "{}"
                    )

                    execution_key = (
                        tool_name,
                        json.dumps(
                            arguments,
                            sort_keys=True,
                            separators=(",", ":"),
                            default=str,
                        ),
                    )

                    if execution_key in executed_tool_results:
                        result = executed_tool_results[execution_key]
                        duplicate_tool_detected = True

                        logger.warning(
                            "agent_duplicate_tool_request_detected | "
                            "tool=%s | "
                            "iteration=%s",
                            tool_name,
                            iteration + 1,
                        )

                        log_event(
                            logger,
                            "tool_execution_reused",
                            tool=tool_name,
                            success=True,
                        )
                    else:
                        result = execute_tool_as_json(
                            tool_name,
                            arguments,
                        )

                        executed_tool_results[execution_key] = result
                        tool_was_executed = True

                        tool_duration_ms = round(
                            (time.perf_counter() - tool_start) * 1000,
                            2,
                        )

                        record_tool_execution(
                            tool=tool_name,
                            duration_ms=tool_duration_ms,
                            success=True,
                        )

                        # OBS-005:
                        # Emit a structured operational event separately from
                        # the request-level telemetry record.
                        #
                        # Do not log tool arguments or tool results here.
                        log_event(
                            logger,
                            "tool_execution_completed",
                            tool=tool_name,
                            duration_ms=tool_duration_ms,
                            success=True,
                        )

                    # Update context only after the tool has successfully
                    # executed. This prevents failed tool calls from
                    # polluting the analytical state.
                    working_context = (
                        _update_analytical_context_from_tool(
                            context=working_context,
                            tool_name=tool_name,
                            arguments=arguments,
                        )
                    )

                    if tool_was_executed:
                        tools_used.append(
                            tool_name
                        )

                    try:
                        parsed_result = (
                            json.loads(result)
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
                    tool_duration_ms = round(
                        (time.perf_counter() - tool_start) * 1000,
                        2,
                    )

                    record_tool_execution(
                        tool=tool_name,
                        duration_ms=tool_duration_ms,
                        success=False,
                        error_type=type(error).__name__,
                    )

                    # OBS-005:
                    # Emit a structured failure event without exposing
                    # tool arguments or result payloads.
                    log_event(
                        logger,
                        "tool_execution_failed",
                        tool=tool_name,
                        duration_ms=tool_duration_ms,
                        success=False,
                        error_type=type(error).__name__,
                    )

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
                    if execution_key is not None:
                        executed_tool_results[execution_key] = result

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

            if duplicate_tool_detected:
                logger.warning(
                    "agent_stopping_after_duplicate_tool_request | "
                    "model=%s | "
                    "iteration=%s | "
                    "tools_used=%s",
                    self.model,
                    iteration + 1,
                    len(tools_used),
                )
                break

        logger.warning(
            "agent_tool_collection_stopped | "
            "model=%s | "
            "max_iterations=%s | "
            "duplicate_tool_detected=%s | "
            "tools_used=%s",
            self.model,
            MAX_TOOL_ITERATIONS,
            duplicate_tool_detected,
            len(tools_used),
        )

        # Do not turn a controlled investigation boundary into an HTTP 500.
        # Ask the model for one final synthesis with tool calling disabled so
        # it must work from the evidence already collected.
        messages.append(
            {
                "role": "system",
                "content": (
                    "The investigation evidence-collection limit has been "
                    "reached. Do not call any more tools. Synthesize the "
                    "best possible answer using only the evidence already "
                    "returned in this conversation. Clearly state any "
                    "limitations or evidence gaps. Do not invent facts."
                ),
            }
        )

        try:
            final_message = self._call_llm(
                messages,
                tools_enabled=False,
            )

            if getattr(final_message, "tool_calls", None):
                logger.error(
                    "agent_final_synthesis_requested_tools | model=%s",
                    self.model,
                )
                raise RuntimeError(
                    "The analytics model could not complete the investigation "
                    "within the allowed evidence limit."
                )

            answer = self._validate_final_answer(final_message)
            messages.append(final_message)
        except Exception as error:
            # The evidence collected so far is still valid even if the
            # provider cannot perform the final synthesis call.
            #
            # Do not convert a controlled tool-iteration boundary or a
            # transient provider failure into an HTTP 500.
            logger.warning(
                "agent_final_synthesis_failed | "
                "model=%s | error_type=%s | reason=%s",
                self.model,
                type(error).__name__,
                str(error),
            )

            answer = (
                "I collected the available analytical evidence, but I "
                "could not complete the final narrative synthesis right now. "
                "The available evidence can still be reviewed from the "
                "successful tool results."
            )

        logger.info(
            "agent_completed_with_evidence_limit | "
            "model=%s | tools_used=%s | synthesis_fallback=%s",
            self.model,
            len(tools_used),
            not bool(
                messages
                and messages[-1] is not None
                and getattr(messages[-1], "role", None) == "assistant"
            ),
        )

        return {
            "answer": answer,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "messages": messages,
            "analytical_context": working_context,
        }


agent = AnalyticsAgent()
