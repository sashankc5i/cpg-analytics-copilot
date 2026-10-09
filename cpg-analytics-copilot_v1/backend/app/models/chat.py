
from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class Visualization(BaseModel):
    type: str
    title: str | None = None
    x: list[Any] = Field(default_factory=list)
    y: list[Any] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    tools_used: list[str] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    visualization: Visualization | dict[str, Any] | None = None


class ConversationCreateRequest(BaseModel):
    conversation_id: str | None = None
    title: str = Field(
        default="New Chat",
        min_length=1,
        max_length=200,
    )


class ConversationRenameRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    created_at: str
    updated_at: str
    archived: bool


class ConversationDetail(ConversationSummary):
    history: list[ChatMessage] = Field(default_factory=list)
