"""Build safe AI context from organization permission guides."""

from typing import Any

from app.services.organization_guide_store import (
    list_organization_guides,
)

MAX_CONTEXT_CHARACTERS = 20_000


def build_agent_context(
    organization_id: str,
    profile: str,
    role: str = "",
    catalyst_app: Any | None = None,
) -> str:
    """
    Load only guides applicable to the current user.

    Main guides apply to everyone. Profile and role guides apply only when
    their audience matches the authenticated user's profile or role.
    """

    guides = list_organization_guides(
        organization_id=organization_id,
        catalyst_app=catalyst_app,
    )

    selected: list[dict[str, Any]] = []

    for guide in guides:
        if not guide.get("active", True):
            continue

        guide_type = guide["guideType"]
        audience = guide["audience"].strip().casefold()

        if guide_type == "main":
            selected.append(guide)
        elif guide_type == "profile" and audience == profile.casefold():
            selected.append(guide)
        elif guide_type == "role" and role and audience == role.casefold():
            selected.append(guide)

    sections = [
        (
            f"## {guide['title']}\n"
            f"Type: {guide['guideType']}\n"
            f"Audience: {guide['audience']}\n\n"
            f"{guide['content']}"
        )
        for guide in selected
    ]

    context = "\n\n---\n\n".join(sections)

    # Limit context size to control model-token usage.
    return context[:MAX_CONTEXT_CHARACTERS]