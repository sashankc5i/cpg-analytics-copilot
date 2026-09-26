import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.agent import agent
from app.agent.challenge import (
    prepare_challenge,
    stream_challenge_synthesis,
)
from app.agent.investigation import (
    prepare_investigation,
    stream_synthesis,
)
from app.agent.investigation_session import (
    investigation_session_manager,
)
from app.agent.session import conversation_manager
from app.analytics.visualization import build_visualization
from app.config import get_settings
from app.logging_config import (
    configure_logging,
    get_logger,
)
from app.middleware import request_logging_middleware
from app.models.chat import ChatResponse


configure_logging()

logger = get_logger(__name__)
settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    description="Enterprise Data Analytics Copilot for CPG",
    version=settings.app_version,
)


app.middleware("http")(
    request_logging_middleware
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
    )

    conversation_id: str = Field(
        default="default",
        min_length=1,
        max_length=100,
    )


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/readiness")
def readiness_check():
    try:
        if not settings.groq_api_key:
            raise RuntimeError(
                "Groq API key is not configured."
            )

        return {
            "status": "ready",
            "service": settings.app_name,
            "version": settings.app_version,
        }

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "reason": str(error),
            },
        )


@app.post(
    "/api/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    http_request: Request,
):
    request_id = getattr(
        http_request.state,
        "request_id",
        "unknown",
    )

    logger.info(
        "chat_request | "
        "request_id=%s | conversation_id=%s",
        request_id,
        request.conversation_id,
    )

    history = conversation_manager.get_history(
        request.conversation_id
    )

    try:
        result = agent.run(
            user_message=request.message,
            history=history,
        )

        visualization = build_visualization(
            tools_used=result["tools_used"],
            tool_results=result["tool_results"],
        )

        conversation_manager.add_message(
            request.conversation_id,
            {
                "role": "user",
                "content": request.message,
            },
        )

        conversation_manager.add_message(
            request.conversation_id,
            {
                "role": "assistant",
                "content": result["answer"],
            },
        )

        logger.info(
            "chat_completed | "
            "request_id=%s | tools=%s",
            request_id,
            result["tools_used"],
        )

        return {
            "answer": result["answer"],
            "tools_used": result["tools_used"],
            "tool_results": result["tool_results"],
            "visualization": visualization,
            "conversation_id": request.conversation_id,
        }

    except ValueError as error:
        logger.warning(
            "chat_validation_error | "
            "request_id=%s | error=%s",
            request_id,
            error,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except RuntimeError as error:
        logger.error(
            "chat_runtime_error | "
            "request_id=%s | error=%s",
            request_id,
            error,
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    except Exception:
        logger.exception(
            "chat_unexpected_error | "
            "request_id=%s",
            request_id,
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        )


@app.post("/api/investigate/stream")
def investigate_stream(
    request: ChatRequest,
    http_request: Request,
):
    """
    Run Investigation Mode and stream the final
    synthesis to the client.

    Investigation uses its own independent session
    and hypothesis context.
    """

    request_id = getattr(
        http_request.state,
        "request_id",
        "unknown",
    )

    logger.info(
        "investigation_request | "
        "request_id=%s | conversation_id=%s",
        request_id,
        request.conversation_id,
    )

    try:
        investigation = prepare_investigation(
            question=request.message,
            investigation_id=request.conversation_id,
        )

        question = investigation["question"]
        history = investigation["history"]
        plan = investigation["plan"]
        hypotheses = investigation["hypotheses"]
        evidence = investigation["evidence"]

        def generate():
            answer_parts = []

            try:
                yield (
                    json.dumps(
                        {
                            "type": "investigation_started"
                        }
                    )
                    + "\n"
                )

                yield (
                    json.dumps(
                        {
                            "type": "plan",
                            "data": plan,
                        }
                    )
                    + "\n"
                )

                yield (
                    json.dumps(
                        {
                            "type": "hypotheses",
                            "data": hypotheses,
                        },
                        default=str,
                    )
                    + "\n"
                )

                yield (
                    json.dumps(
                        {
                            "type": "answer_start"
                        }
                    )
                    + "\n"
                )

                for chunk in stream_synthesis(
                    question,
                    evidence,
                    hypotheses,
                    history,
                ):
                    answer_parts.append(chunk)

                    yield (
                        json.dumps(
                            {
                                "type": "token",
                                "data": chunk,
                            }
                        )
                        + "\n"
                    )

                answer = "".join(answer_parts)

                investigation_session_manager.add_message(
                    request.conversation_id,
                    {
                        "role": "user",
                        "content": request.message,
                    },
                )

                investigation_session_manager.add_message(
                    request.conversation_id,
                    {
                        "role": "assistant",
                        "content": answer,
                    },
                )

                investigation_session_manager.update_investigation(
                    request.conversation_id,
                    plan=plan,
                    evidence=evidence,
                    answer=answer,
                )

                yield (
                    json.dumps(
                        {
                            "type": "answer_end"
                        }
                    )
                    + "\n"
                )

                logger.info(
                    "investigation_stream_completed | "
                    "request_id=%s | "
                    "conversation_id=%s | "
                    "plan=%s | "
                    "hypotheses=%s",
                    request_id,
                    request.conversation_id,
                    plan,
                    len(hypotheses),
                )

            except Exception as error:
                logger.exception(
                    "investigation_stream_failed | "
                    "request_id=%s | "
                    "conversation_id=%s",
                    request_id,
                    request.conversation_id,
                )

                yield (
                    json.dumps(
                        {
                            "type": "error",
                            "data": str(error),
                        }
                    )
                    + "\n"
                )

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Request-ID": request_id,
            },
        )

    except Exception as error:
        logger.exception(
            "investigation_request_failed | "
            "request_id=%s | "
            "conversation_id=%s",
            request_id,
            request.conversation_id,
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


@app.post("/api/investigate/challenge/stream")
def challenge_stream(
    request: ChatRequest,
    http_request: Request,
):
    """
    Challenge the latest completed investigation
    associated with the supplied conversation ID.

    The original conclusion is retrieved from the
    InvestigationSessionManager rather than being
    supplied by the frontend.
    """

    request_id = getattr(
        http_request.state,
        "request_id",
        "unknown",
    )

    logger.info(
        "challenge_request | "
        "request_id=%s | conversation_id=%s",
        request_id,
        request.conversation_id,
    )

    try:
        challenge = prepare_challenge(
            investigation_id=request.conversation_id,
        )

        question = challenge["question"]
        original_answer = challenge["original_answer"]
        claims = challenge["claims"]
        challenge_plan = challenge["challenge_plan"]
        challenge_evidence = challenge["challenge_evidence"]

        def generate():
            answer_parts = []

            try:
                yield (
                    json.dumps(
                        {
                            "type": "challenge_started"
                        }
                    )
                    + "\n"
                )

                yield (
                    json.dumps(
                        {
                            "type": "claims",
                            "data": claims,
                        },
                        default=str,
                    )
                    + "\n"
                )

                yield (
                    json.dumps(
                        {
                            "type": "challenge_plan",
                            "data": challenge_plan,
                        },
                        default=str,
                    )
                    + "\n"
                )

                yield (
                    json.dumps(
                        {
                            "type": "challenge_evidence",
                            "data": challenge_evidence,
                        },
                        default=str,
                    )
                    + "\n"
                )

                yield (
                    json.dumps(
                        {
                            "type": "answer_start"
                        }
                    )
                    + "\n"
                )

                for chunk in stream_challenge_synthesis(
                    question=question,
                    original_answer=original_answer,
                    claims=claims,
                    evidence=challenge_evidence,
                ):
                    answer_parts.append(chunk)

                    yield (
                        json.dumps(
                            {
                                "type": "token",
                                "data": chunk,
                            }
                        )
                        + "\n"
                    )

                answer = "".join(answer_parts)

                yield (
                    json.dumps(
                        {
                            "type": "answer_end",
                            "data": {
                                "answer": answer,
                            },
                        }
                    )
                    + "\n"
                )

                logger.info(
                    "challenge_stream_completed | "
                    "request_id=%s | "
                    "conversation_id=%s | "
                    "claims=%s | "
                    "plan=%s",
                    request_id,
                    request.conversation_id,
                    len(claims),
                    challenge_plan,
                )

            except Exception as error:
                logger.exception(
                    "challenge_stream_failed | "
                    "request_id=%s | "
                    "conversation_id=%s",
                    request_id,
                    request.conversation_id,
                )

                yield (
                    json.dumps(
                        {
                            "type": "error",
                            "data": str(error),
                        }
                    )
                    + "\n"
                )

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Request-ID": request_id,
            },
        )

    except ValueError as error:
        logger.warning(
            "challenge_validation_error | "
            "request_id=%s | error=%s",
            request_id,
            error,
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        logger.exception(
            "challenge_request_failed | "
            "request_id=%s | "
            "conversation_id=%s",
            request_id,
            request.conversation_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to start challenge.",
        )