"""Invoke Catalyst QuickML endpoints through a managed Connection."""

import os
from typing import Any

import requests


CONNECTION_LINK_NAME = os.environ.get(
    "QUICKML_CONNECTION_LINK_NAME",
    "quickml_connection",
)

# Names must not start with CATALYST_ because Catalyst reserves them.
CATALYST_ORG_ID = os.environ.get(
    "QUICKML_ORG_ID",
    "932258476",
)

PROJECT_ID = os.environ.get(
    "QUICKML_PROJECT_ID",
    "100295000000014025",
)

CATALYST_ENVIRONMENT = os.environ.get(
    "QUICKML_ENVIRONMENT",
    "Development",
)

GLM_URL = (
    "https://console.catalyst.zoho.com/quickml/v1/project/"
    f"{PROJECT_ID}/genai/endpoints/glm-flash-47/generate"
)

QWEN_URL = (
    "https://console.catalyst.zoho.com/quickml/v1/project/"
    f"{PROJECT_ID}/genai/endpoints/vlm/generate"
)


def _find_value(
    value: Any,
    accepted_keys: set[str],
) -> str:
    """Find a string value recursively without logging credentials."""

    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = (
                str(key)
                .replace("_", "")
                .replace("-", "")
                .lower()
            )

            if (
                normalized_key in accepted_keys
                and isinstance(item, str)
                and item.strip()
            ):
                return item.strip()

        for item in value.values():
            result = _find_value(item, accepted_keys)

            if result:
                return result

    elif isinstance(value, list):
        for item in value:
            result = _find_value(item, accepted_keys)

            if result:
                return result

    return ""


def _safe_structure(value: Any) -> Any:
    """Return only the shape of a response, never secret values."""

    if isinstance(value, dict):
        return {
            str(key): _safe_structure(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_safe_structure(item) for item in value[:3]]

    if value is None:
        return None

    return f"<{type(value).__name__}>"


def _authorization_header(catalyst_app: Any) -> str:
    """Get a usable QuickML Authorization header from Catalyst Connections."""

    credentials = (
        catalyst_app.connections()
        .get_connection_credentials(CONNECTION_LINK_NAME)
    )

    if not isinstance(credentials, (dict, list)):
        raise RuntimeError(
            "QuickML Connection returned an unexpected response type: "
            f"{type(credentials).__name__}."
        )

    # Some SDK versions return the full Authorization header.
    authorization = _find_value(
        credentials,
        {
            "authorization",
            "authorizationheader",
            "authheader",
        },
    )

    if authorization:
        if authorization.lower().startswith("zoho-oauthtoken "):
            return authorization

        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            return f"Zoho-oauthtoken {token}"

        return f"Zoho-oauthtoken {authorization}"

    # Other SDK versions return only the access token.
    access_token = _find_value(
        credentials,
        {
            "accesstoken",
            "oauthaccesstoken",
            "token",
        },
    )

    if access_token:
        if access_token.lower().startswith("zoho-oauthtoken "):
            return access_token

        return f"Zoho-oauthtoken {access_token}"

    structure = _safe_structure(credentials)

    raise RuntimeError(
        "QuickML Connection contains no usable Authorization header "
        f"or access token. Response structure: {structure}"
    )


def _endpoint_key(variable_name: str) -> str:
    """Read and validate a QuickML endpoint key."""

    endpoint_key = os.environ.get(variable_name, "").strip()

    if not endpoint_key or endpoint_key == "PRIVATE_VALUE":
        raise RuntimeError(
            f"{variable_name} is not configured with a real endpoint key."
        )

    return endpoint_key


def _headers(
    catalyst_app: Any,
    endpoint_key: str,
) -> dict[str, str]:
    """Build authenticated QuickML request headers."""

    return {
        "Authorization": _authorization_header(catalyst_app),
        "Environment": CATALYST_ENVIRONMENT,
        "x-quickml-endpoint-key": endpoint_key,
        "CATALYST-ORG": CATALYST_ORG_ID,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _post(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    """Call QuickML and return a clear, safe error if it fails."""

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.Timeout as error:
        raise RuntimeError("QuickML request timed out.") from error
    except requests.RequestException as error:
        raise RuntimeError(
            f"QuickML network request failed: {error}"
        ) from error

    if not response.ok:
        raise RuntimeError(
            "QuickML returned "
            f"HTTP {response.status_code}: {response.text[:1000]}"
        )

    try:
        data = response.json()
    except ValueError as error:
        raise RuntimeError(
            "QuickML returned a non-JSON response: "
            f"{response.text[:500]}"
        ) from error

    if not isinstance(data, dict):
        raise RuntimeError(
            "QuickML returned an unexpected response format."
        )

    return data


def ask_glm(
    catalyst_app: Any,
    prompt: str,
) -> tuple[str, int]:
    """Call the GLM text endpoint."""

    endpoint_key = _endpoint_key("GLM_AGENT_ENDPOINT_KEY")

    payload = _post(
        url=GLM_URL,
        headers=_headers(catalyst_app, endpoint_key),
        payload={"prompt": prompt},
        timeout_seconds=60,
    )

    data = payload.get("data", [])

    if not isinstance(data, list) or not data:
        raise RuntimeError("GLM response does not contain a data item.")

    first_item = data[0]

    if not isinstance(first_item, dict):
        raise RuntimeError("GLM returned an unexpected data item.")

    reply = str(first_item.get("data", "")).strip()

    if not reply:
        raise RuntimeError("GLM returned an empty response.")

    usage = payload.get("usage", {})

    tokens_used = (
        int(usage.get("total_tokens", 0))
        if isinstance(usage, dict)
        else 0
    )

    return reply, tokens_used


def ask_qwen(
    catalyst_app: Any,
    prompt: str,
    images: list[str],
) -> tuple[str, int]:
    """Call Qwen using up to three Base64-encoded images."""

    endpoint_key = _endpoint_key("QWEN_AGENT_ENDPOINT_KEY")

    if not images:
        raise ValueError("Qwen requires at least one image.")

    payload = _post(
        url=QWEN_URL,
        headers=_headers(catalyst_app, endpoint_key),
        payload={
            "images": images[:3],
            "prompt": prompt,
        },
        timeout_seconds=90,
    )

    reply = str(payload.get("response", "")).strip()

    if not reply:
        raise RuntimeError("Qwen returned an empty response.")

    metrics = payload.get("metrics", {})

    if not isinstance(metrics, dict):
        metrics = {}

    tokens_used = (
        int(metrics.get("input_text_token_length", 0))
        + int(metrics.get("input_image_token_length", 0))
        + int(metrics.get("input_guided_prompt_length", 0))
        + int(metrics.get("output_text_token_length", 0))
    )

    return reply, tokens_used