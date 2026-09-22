"""Agents available to the application."""

import os
from typing import Any


def list_agents() -> list[dict[str, Any]]:
    """Return configured QuickML agents."""

    agents = [
        {
            "key": "glm",
            "name": "GLM-4.7-Flash",
            "description": "Text chat, reasoning and agent workflows.",
            "agentId": os.environ.get(
                "GLM_AGENT_ENDPOINT_KEY",
                "",
            ),
            "acceptsImages": False,
        },
        {
            "key": "qwen",
            "name": "Qwen 3.6 Vision",
            "description": "Image, document and chart analysis.",
            "agentId": os.environ.get(
                "QWEN_AGENT_ENDPOINT_KEY",
                "",
            ),
            "acceptsImages": True,
        },
    ]

    return [
        {
            **agent,
            "available": bool(agent["agentId"]),
        }
        for agent in agents
    ]


def get_agent(agent_key: str) -> dict[str, Any] | None:
    """Return one configured agent."""

    return next(
        (
            agent
            for agent in list_agents()
            if agent["key"] == agent_key
        ),
        None,
    )