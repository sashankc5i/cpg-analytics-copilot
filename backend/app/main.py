import json
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from app.agent.session import conversation_manager
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
from app.agent.session import (
    ConversationNotFoundError,
    conversation_manager,
)
from app.agent.session import conversation_manager
from app.analytics.visualization import build_visualization
from app.config import get_settings
from app.logging_config import (
    configure_logging,
    get_logger,
    get_request_id,
)
from app.middleware import request_logging_middleware
from app.models.chat import ChatResponse


# ---------------------------------------------------------------------------
# Application Setup
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


def _strip_and_validate_text(
    value: str,
    field_name: str,
) -> str:
    """
    Normalize a request string and reject blank values.

    Pydantic performs type and length validation through
    the Field definition. This helper handles the
    semantic distinction between an empty string and a
    whitespace-only string.
    """

    value = value.strip()

    if not value:
        raise ValueError(
            f"{field_name} must not be blank."
        )

    return value


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

    @field_validator("message")
    @classmethod
    def validate_message(
        cls,
        value: str,
    ) -> str:
        return _strip_and_validate_text(
            value,
            "message",
        )

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(
        cls,
        value: str,
    ) -> str:
        return _strip_and_validate_text(
            value,
            "conversation_id",
        )


class ConversationCreateRequest(BaseModel):
    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    title: str = Field(
        default="New Chat",
        min_length=1,
        max_length=200,
    )

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return _strip_and_validate_text(
            value,
            "conversation_id",
        )

    @field_validator("title")
    @classmethod
    def validate_title(
        cls,
        value: str,
    ) -> str:
        return _strip_and_validate_text(
            value,
            "title",
        )


class ConversationRenameRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )

    @field_validator("title")
    @classmethod
    def validate_title(
        cls,
        value: str,
    ) -> str:
        return _strip_and_validate_text(
            value,
            "title",
        )


# ---------------------------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/readiness")
def readiness_check(http_request: Request):
    request_id = get_request_id(
    http_request,
)

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
        logger.exception(
            "readiness_check_failed | "
            "request_id=%s",
            request_id,
        )

        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "message": "Service dependencies are not ready.",
                "request_id": request_id,
            },
        )


# ---------------------------------------------------------------------------
# Conversation Management
# ---------------------------------------------------------------------------


@app.post("/api/conversations")
def create_conversation(
    request: ConversationCreateRequest,
):
    """
    Create a new conversation session.

    The caller may provide a conversation ID.
    If no ID is provided, the backend generates one.
    """

    conversation_id = (
        request.conversation_id
        or str(uuid4())
    )

    session = conversation_manager.create(
        conversation_id=conversation_id,
        title=request.title,
    )

    logger.info(
        "conversation_created | conversation_id=%s",
        conversation_id,
    )

    return conversation_manager.get_conversation(
        conversation_id
    )


@app.get("/api/conversations")
def list_conversations(
    include_archived: bool = False,
):
    """
    List conversation sessions.

    Archived conversations are excluded by default.
    """

    return conversation_manager.list_sessions(
        include_archived=include_archived,
    )

@app.get("/api/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
):
    """
    Return a complete existing conversation including history.

    A missing conversation is treated as a missing API
    resource rather than being implicitly created.
    """

    conversation = conversation_manager.get_existing(
        conversation_id
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return conversation
@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: str,
    request: ConversationRenameRequest,
):
    """
    Rename an existing conversation.
    """

    try:
        session = conversation_manager.rename(
            conversation_id,
            request.title,
        )

        return {
            "conversation_id": session["conversation_id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "archived": session["archived"],
        }

    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: str,
    request: ConversationRenameRequest,
):
    """
    Rename an existing conversation.
    """

    try:
        session = conversation_manager.rename(
            conversation_id,
            request.title,
        )

        return {
            "conversation_id": session["conversation_id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "archived": session["archived"],
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.post(
    "/api/conversations/{conversation_id}/archive"
)
def archive_conversation(
    conversation_id: str,
):
    """
    Archive an existing conversation.
    """

    try:
        session = conversation_manager.archive(
            conversation_id
        )

        return {
            "conversation_id": session["conversation_id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "archived": session["archived"],
        }

    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )
@app.post(
    "/api/conversations/{conversation_id}/unarchive"
)
def unarchive_conversation(
    conversation_id: str,
):
    """
    Restore an existing archived conversation.
    """

    try:
        session = conversation_manager.unarchive(
            conversation_id
        )

        return {
            "conversation_id": session["conversation_id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "archived": session["archived"],
        }

    except ConversationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
):
    """
    Permanently delete a conversation session and any
    investigation state associated with the same ID.
    """

    deleted = conversation_manager.delete(
        conversation_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    investigation_deleted = (
        investigation_session_manager.delete(
            conversation_id
        )
    )

    logger.info(
        "conversation_deleted | "
        "conversation_id=%s | "
        "investigation_state_deleted=%s",
        conversation_id,
        investigation_deleted,
    )

    return {
        "conversation_id": conversation_id,
        "deleted": True,
    }


# ---------------------------------------------------------------------------
# Standard Copilot Chat
# ---------------------------------------------------------------------------


@app.post(
    "/api/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    http_request: Request,
):
    """
    Execute a standard Copilot conversation.

    The conversation ID determines which conversational
    history is supplied to the agent.
    """

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
            detail={
                "message": (
                    "The analytics service could not process "
                    "the request."
                ),
                "request_id": request_id,
            },
        )

    except Exception:
        logger.exception(
            "chat_unexpected_error | "
            "request_id=%s",
            request_id,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred.",
                "request_id": request_id,
            },
        )


# ---------------------------------------------------------------------------
# Investigation Mode
# ---------------------------------------------------------------------------


@app.post("/api/investigate/stream")
def investigate_stream(
    request: ChatRequest,
    http_request: Request,
):
    """
    Run Investigation Mode and stream the final
    synthesis to the client.

    Investigation uses the same conversation ID
    as the standard Copilot session, while maintaining
    its own analytical investigation memory.
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
        claims = investigation.get("claims", [])

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
                            "type": "evidence",
                            "data": evidence,
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
                    claims,
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
                    claims=claims,
                    answer=answer,
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
                        "content": answer,
                        "claims": claims,
                        "investigationEvidence": evidence,
                    },
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
                    "hypotheses=%s | "
                    "claims=%s",
                    request_id,
                    request.conversation_id,
                    plan,
                    len(hypotheses),
                    len(claims),
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
                            "data": {
                                "message": (
                                    "The investigation could not be completed."
                                ),
                                "request_id": request_id,
                            },
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
            detail={
                "message": "Unable to start investigation.",
                "request_id": request_id,
            },
        )


# ---------------------------------------------------------------------------
# Challenge My Conclusion
# ---------------------------------------------------------------------------


@app.post("/api/investigate/challenge/stream")
def challenge_stream(
    request: ChatRequest,
    http_request: Request,
):
    """
    Challenge the latest completed investigation
    associated with the supplied conversation ID.

    The original conclusion and evidence are retrieved
    from InvestigationSessionManager rather than being
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
                            "data": {
                                "message": (
                                    "The challenge could not be completed."
                                ),
                                "request_id": request_id,
                            },
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