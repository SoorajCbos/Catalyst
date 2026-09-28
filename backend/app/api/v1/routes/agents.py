"""QuickML agent endpoints with sessions, context and audit logging."""

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
from app.services.chat_session_store import (
    add_message,
    create_session,
    get_session,
    list_messages,
    list_sessions,
    make_title,
)
from app.services.quickml_agent import ask_glm, ask_qwen

router = APIRouter()

# Keep prompts small to control QuickML token usage.
HISTORY_MESSAGES = 6
HISTORY_MESSAGE_CHARACTERS = 500


class AgentResponse(BaseModel):
    """Safe agent metadata. Endpoint keys are never returned."""

    key: str
    name: str
    description: str
    available: bool
    acceptsImages: bool


class AgentChatRequest(BaseModel):
    """Message from the workspace."""

    message: str = Field(min_length=1, max_length=500)
    agentKey: str = Field(min_length=1, max_length=100)
    images: list[str] = Field(default_factory=list, max_length=3)
    sessionId: str | None = Field(default=None, max_length=100)


class AgentChatResponse(BaseModel):
    """Agent reply returned to the workspace."""

    reply: str
    agentName: str
    contextLoaded: bool
    callId: str
    tokensUsed: int
    sessionId: str


class ChatSessionResponse(BaseModel):
    """Session shown in the left panel."""

    sessionId: str
    agentKey: str
    title: str
    lastMessageAt: str


class ChatMessageResponse(BaseModel):
    """Message shown when a session is reopened."""

    messageId: str
    sender: str
    content: str
    tokensUsed: int
    createdAt: str


@router.get("", response_model=list[AgentResponse])
def get_agents(
    _: dict[str, Any] = Depends(require_user),
):
    """List configured QuickML agents."""

    return [AgentResponse(**agent) for agent in list_agents()]


@router.get("/sessions", response_model=list[ChatSessionResponse])
def get_sessions(
    current_user: dict[str, Any] = Depends(require_user),
    catalyst_app: Any | None = Depends(get_catalyst_app),
):
    """List the current user's chat sessions."""

    sessions = list_sessions(current_user["recordId"], catalyst_app)

    return [ChatSessionResponse(**session) for session in sessions]


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageResponse],
)
def get_session_messages(
    session_id: str,
    current_user: dict[str, Any] = Depends(require_user),
    catalyst_app: Any | None = Depends(get_catalyst_app),
):
    """Return messages of one session owned by the current user."""

    session = get_session(session_id, current_user["recordId"], catalyst_app)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found.",
        )

    messages = list_messages(session["sessionId"], catalyst_app)

    return [ChatMessageResponse(**item) for item in messages]


def _history_text(messages: list) -> str:
    """Format only the most recent messages for the model."""

    recent = messages[-HISTORY_MESSAGES:]
    lines = []

    for item in recent:
        speaker = "User" if item["sender"] == "user" else "Assistant"
        content = item["content"][:HISTORY_MESSAGE_CHARACTERS]
        lines.append(f"{speaker}: {content}")

    return "\n".join(lines)


@router.post("/chat", response_model=AgentChatResponse)
def chat(
    payload: AgentChatRequest,
    current_user: dict[str, Any] = Depends(require_user),
    catalyst_app: Any | None = Depends(get_catalyst_app),
):
    """Continue or start a session and invoke the selected agent."""

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

    user_id = current_user["recordId"]

    if payload.sessionId:
        session = get_session(payload.sessionId, user_id, catalyst_app)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found.",
            )

        history = list_messages(session["sessionId"], catalyst_app)
    else:
        session = create_session(
            user_id=user_id,
            organization_id=current_user["organizationId"],
            agent_key=payload.agentKey,
            title=make_title(payload.message),
            catalyst_app=catalyst_app,
        )
        history = []

    session_id = session["sessionId"]

    add_message(
        session_id,
        "user",
        payload.message,
        catalyst_app=catalyst_app,
    )

    call_id = start_agent_call(
        user_id=user_id,
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

        guide_text = context or "No organization guide is available."
        prompt_parts = [f"Organization permission context:\n{guide_text}"]

        if history:
            prompt_parts.append(
                f"Conversation so far:\n{_history_text(history)}"
            )

        prompt_parts.append(f"User request:\n{payload.message}")
        model_prompt = "\n\n".join(prompt_parts)

        if payload.agentKey == "glm":
            reply, tokens_used = ask_glm(catalyst_app, model_prompt)
        elif payload.agentKey == "qwen":
            reply, tokens_used = ask_qwen(
                catalyst_app,
                model_prompt,
                payload.images,
            )
        else:
            raise ValueError("Unsupported agent.")

        add_message(
            session_id,
            "agent",
            reply,
            tokens_used=tokens_used,
            catalyst_app=catalyst_app,
        )

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
            sessionId=session_id,
        )

    except Exception as error:
        complete_agent_call(
            record_id=call_id,
            status="failed",
            error_message=str(error)[:1000],
            catalyst_app=catalyst_app,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{agent['name']} request failed: {str(error)[:500]}",
        ) from error