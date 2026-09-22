"""QuickML agent endpoints with context and audit logging."""

import logging
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field

from app.core.access import require_user
from app.core.catalyst_app import get_catalyst_app
from app.services.agent_call_store import (
    complete_agent_call,
    start_agent_call,
)
from app.services.agent_context import build_agent_context
from app.services.agent_registry import get_agent, list_agents
from app.services.quickml_agent import ask_glm, ask_qwen

router = APIRouter()
logger = logging.getLogger(__name__)


class AgentResponse(BaseModel):
    """Agent shown in the workspace."""

    key: str
    name: str
    description: str
    agentId: str
    available: bool
    acceptsImages: bool


class AgentChatRequest(BaseModel):
    """Agent request from the workspace."""

    message: str = Field(min_length=1, max_length=500)
    agentKey: str = Field(min_length=1, max_length=100)
    images: list[str] = Field(default_factory=list, max_length=3)


class AgentChatResponse(BaseModel):
    """QuickML response returned to the workspace."""

    reply: str
    agentName: str
    contextLoaded: bool
    callId: str
    tokensUsed: int


@router.get("", response_model=list[AgentResponse])
def get_agents(
    _: dict[str, Any] = Depends(require_user),
) -> list[AgentResponse]:
    """List configured QuickML agents."""

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
    """Load user context and invoke the selected QuickML agent."""

    if catalyst_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QuickML agents are available only in Catalyst.",
        )

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

        model_prompt = (
            "Organization permission context:\n"
            f"{context or 'No organization guide is available.'}\n\n"
            "User request:\n"
            f"{payload.message}"
        )

        if payload.agentKey == "glm":
            reply, tokens_used = ask_glm(
                catalyst_app,
                model_prompt,
            )
        elif payload.agentKey == "qwen":
            reply, tokens_used = ask_qwen(
                catalyst_app,
                model_prompt,
                payload.images,
            )
        else:
            raise ValueError("Unsupported agent.")

        complete_agent_call(
            record_id=call_id,
            status="completed",
            tokens_used=tokens_used,
            catalyst_app=catalyst_app,
        )

        return AgentChatResponse(
            reply=reply,
            agentName=agent["name"],
            contextLoaded=bool(context),
            callId=call_id,
            tokensUsed=tokens_used,
        )

    except Exception as error:
        logger.exception(
            "QuickML request failed for agent %s (call_id=%s)",
            agent["name"],
            call_id,
        )
        complete_agent_call(
            record_id=call_id,
            status="failed",
            error_message=str(error)[:1_000],
            catalyst_app=catalyst_app,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{agent['name']} request failed: {error}",
        ) from error