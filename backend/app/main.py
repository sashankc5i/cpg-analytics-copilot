from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agent.agent import agent
from app.agent.session import conversation_manager
from app.analytics.visualization import (
    build_visualization,
)
from app.config import get_settings
from app.logging_config import (
    configure_logging,
    get_logger,
)
from app.middleware import (
    request_logging_middleware,
)
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
        "chat_request | request_id=%s | conversation_id=%s",
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
            status_code=500,
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

@app.get("/readiness")
def readiness_check():
    try:
        settings = get_settings()

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