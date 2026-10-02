import json
import logging
import re
import time

from groq import Groq
from groq import RateLimitError

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    TOOL_DEFINITIONS,
    execute_tool_as_json,
)
from app.config import get_settings


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

        Provider rate limits are handled separately from other provider
        failures. A bounded retry is used for HTTP 429 responses, while
        other failures are converted into controlled RuntimeError
        exceptions.

        The completion token limit is intentionally bounded to reduce
        unnecessary TPM consumption.
        """

        logger.info(
            "agent_llm_call_started | model=%s | messages=%s",
            self.model,
            len(messages),
        )

        for attempt in range(
            MAX_RATE_LIMIT_RETRIES + 1
        ):
            try:
                response = (
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=TOOL_DEFINITIONS,
                        tool_choice="auto",
                        temperature=0,
                        max_completion_tokens=MAX_COMPLETION_TOKENS,
                    )
                )

                break

            except RateLimitError as error:
                if attempt >= MAX_RATE_LIMIT_RETRIES:
                    logger.exception(
                        "agent_llm_rate_limit_exhausted | "
                        "model=%s | attempts=%s",
                        self.model,
                        attempt + 1,
                    )

                    raise RuntimeError(
                        "The analytics model is temporarily rate-limited. "
                        "Please try again shortly."
                    ) from error

                delay = _retry_delay_from_error(error)

                logger.warning(
                    "agent_llm_rate_limited | "
                    "model=%s | attempt=%s/%s | "
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
    ):
        logger.info(
            "agent_started | model=%s",
            self.model,
        )

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

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

                try:
                    arguments = json.loads(
                        tool_call.function.arguments
                        or "{}"
                    )

                    result = execute_tool_as_json(
                        tool_name,
                        arguments,
                    )

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
