"""Agents available to the application."""

import os
from typing import Any


def list_agents() -> list[dict[str, Any]]:
    """
    Return configured agents.

    Agent IDs come from environment variables so Development and
    Production can use different Catalyst agents without code changes.
    """

    agents = [
        {
            "key": "qwen",
            "name": "Qwen",
            "description": "General reasoning and assistance.",
            "agentId": os.environ.get("QWEN_AGENT_ID", ""),
        },
        {
            "key": "secondary",
            "name": os.environ.get(
                "SECONDARY_AGENT_NAME",
                "Secondary Agent",
            ),
            "description": "Specialized organization agent.",
            "agentId": os.environ.get("SECONDARY_AGENT_ID", ""),
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