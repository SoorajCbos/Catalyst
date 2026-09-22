import os
from typing import Any

TEXT_KEYS = (
    "reply",
    "response",
    "output",
    "prediction",
    "text",
    "content",
    "generated_text",
    "answer",
)


def _find_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in TEXT_KEYS:
            text = _find_text(value.get(key))
            if text:
                return text

        for item in value.values():
            text = _find_text(item)
            if text:
                return text

    if isinstance(value, list):
        for item in value:
            text = _find_text(item)
            if text:
                return text

    return ""


def _find_tokens(value: Any) -> int:
    if isinstance(value, dict):
        for key in ("tokensUsed", "tokens_used", "total_tokens"):
            tokens = value.get(key)
            if isinstance(tokens, int):
                return tokens

        for item in value.values():
            tokens = _find_tokens(item)
            if tokens:
                return tokens

    if isinstance(value, list):
        for item in value:
            tokens = _find_tokens(item)
            if tokens:
                return tokens

    return 0


def _predict(
    catalyst_app: Any,
    endpoint_key_name: str,
    input_data: dict[str, Any],
) -> tuple[str, int]:
    endpoint_key = os.environ.get(endpoint_key_name, "").strip()

    if not endpoint_key:
        raise RuntimeError(f"{endpoint_key_name} is not configured.")

    response = catalyst_app.quick_ml().predict(endpoint_key, input_data)

    reply = _find_text(response)
    tokens_used = _find_tokens(response)

    if not isinstance(reply, str) or not reply:
        raise RuntimeError(
            "QuickML endpoint returned no text response. "
            f"Response type: {type(response).__name__}."
        )

    return reply, tokens_used


def ask_glm(catalyst_app: Any, prompt: str) -> tuple[str, int]:
    """Ask the configured GLM QuickML endpoint."""

    return _predict(
        catalyst_app,
        "GLM_AGENT_ENDPOINT_KEY",
        {"prompt": prompt},
    )


def ask_qwen(
    catalyst_app: Any,
    prompt: str,
    images: list[str],
) -> tuple[str, int]:
    """Ask the configured Qwen QuickML endpoint."""

    return _predict(
        catalyst_app,
        "QWEN_AGENT_ENDPOINT_KEY",
        {"prompt": prompt, "images": images},
    )