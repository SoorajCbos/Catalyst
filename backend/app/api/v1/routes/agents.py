"""Agent-chat endpoint with context loading and audit logging."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.access import require_user
from app.core.catalyst_app import get_catalyst_app
from app.services.agent_call_store import (
    complete_agent_call,
    start_agent_call,
)
from app.services.agent_context import build_agent_context

router = APIRouter()


class AgentChatRequest(BaseModel):
    """Message submitted through the agent-chat interface."""

    message: str = Field(min_length=1, max_length=4_000)


class AgentChatResponse(BaseModel):
    """Temporary response used before GenAI is connected."""

    reply: str
    agentName: str
    contextLoaded: bool


@router.post("/chat", response_model=AgentChatResponse)
def chat(
    payload: AgentChatRequest,
    current_user: dict[str, Any] = Depends(require_user),
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> AgentChatResponse:
    """
    Test the complete context and logging pipeline.

    A real GenAI response will replace the temporary reply later.
    """

    agent_name = "permission-assistant"

    call_id = start_agent_call(
        user_id=current_user["recordId"],
        organization_id=current_user["organizationId"],
        agent_name=agent_name,
        prompt=payload.message,
        catalyst_app=catalyst_app,
    )

    try:
        context = build_agent_context(
            organization_id=current_user["organizationId"],
            profile=current_user["profile"],
            catalyst_app=catalyst_app,
        )

        reply = (
            "Agent context loaded successfully."
            if context
            else "No applicable organization guide was found."
        )

        complete_agent_call(
            record_id=call_id,
            status="completed",
            tokens_used=0,
            catalyst_app=catalyst_app,
        )

        return AgentChatResponse(
            reply=reply,
            agentName=agent_name,
            contextLoaded=bool(context),
        )

    except Exception as error:
        complete_agent_call(
            record_id=call_id,
            status="failed",
            error_message=str(error)[:1_000],
            catalyst_app=catalyst_app,
        )
        raise