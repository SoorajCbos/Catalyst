"""Agent endpoints with context loading and audit logging."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.access import require_user
from app.core.catalyst_app import get_catalyst_app
from app.services.agent_call_store import (
    complete_agent_call,
    start_agent_call,
)
from app.services.agent_context import build_agent_context
from app.services.agent_registry import get_agent, list_agents

router = APIRouter()


class AgentResponse(BaseModel):
    """Agent available to the current application."""

    key: str
    name: str
    description: str
    agentId: str
    available: bool


class AgentChatRequest(BaseModel):
    """Message and selected agent from the workspace."""

    message: str = Field(min_length=1, max_length=4_000)
    agentKey: str = Field(min_length=1, max_length=100)


class AgentChatResponse(BaseModel):
    """Response returned to the agent workspace."""

    reply: str
    agentName: str
    contextLoaded: bool
    callId: str


@router.get("", response_model=list[AgentResponse])
def get_agents(
    _: dict[str, Any] = Depends(require_user),
) -> list[AgentResponse]:
    """List configured agents for the right-side panel."""

    return [
        AgentResponse(**agent)
        for agent in list_agents()
    ]


@router.post("/chat", response_model=AgentChatResponse)
def chat(
    payload: AgentChatRequest,
    current_user: dict[str, Any] = Depends(require_user),
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> AgentChatResponse:
    """
    Run the selected agent pipeline.

    Real model execution will replace the temporary reply after the
    Catalyst agent IDs and API method are confirmed.
    """

    agent = get_agent(payload.agentKey)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found.",
        )

    if not agent["available"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{agent['name']} is not configured.",
        )

    call_id = start_agent_call(
        user_id=current_user["recordId"],
        organization_id=current_user["organizationId"],
        agent_name=agent["name"],
        prompt=payload.message,
        catalyst_app=catalyst_app,
    )

    try:
        context = build_agent_context(
            organization_id=current_user["organizationId"],
            profile=current_user["profile"],
            catalyst_app=catalyst_app,
        )

        # Temporary response until the Catalyst agent API is connected.
        reply = (
            f"{agent['name']} is selected. "
            f"Organization context loaded: {bool(context)}."
        )

        complete_agent_call(
            record_id=call_id,
            status="completed",
            tokens_used=0,
            catalyst_app=catalyst_app,
        )

        return AgentChatResponse(
            reply=reply,
            agentName=agent["name"],
            contextLoaded=bool(context),
            callId=call_id,
        )

    except Exception as error:
        complete_agent_call(
            record_id=call_id,
            status="failed",
            error_message=str(error)[:1_000],
            catalyst_app=catalyst_app,
        )
        raise