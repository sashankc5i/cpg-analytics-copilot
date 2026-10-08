import json
import logging

from groq import Groq

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    TOOL_DEFINITIONS,
    execute_tool_as_json,
)
from app.config import get_settings


settings = get_settings()

MAX_TOOL_ITERATIONS = settings.max_tool_iterations

logger = logging.getLogger(__name__)


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

        The agent treats the LLM as an external dependency.
        Provider failures and malformed responses are converted
        into controlled RuntimeError exceptions so callers do
        not have to understand provider-specific exceptions.
        """

        logger.info(
            "agent_llm_call_started | model=%s",
            self.model,
        )

        try:
            response = (
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=0,
                )
            )

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