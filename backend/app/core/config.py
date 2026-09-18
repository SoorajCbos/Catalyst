"""Central configuration for the Catalyst backend.

Every environment-specific value — URLs, secrets, resource ids — is read
here and nowhere else. Locally the values come from backend/.env; on
Catalyst they come from the environment variables set per environment
(Development for UAT, Production for prod) in the console.
"""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# app/core/config.py -> parents[2] is the backend/ directory
BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Local development only. On AppSail there is no .env file and the real
# environment variables are already present, so this is a harmless no-op.
# override=False means a real environment variable always wins, so a .env
# that reaches the server by accident can never shadow console settings.
load_dotenv(BACKEND_ROOT / ".env", override=False)


class ConfigError(RuntimeError):
    """Raised when the environment is missing something the app needs."""


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _csv(name: str, default: str = "") -> list[str]:
    return [part.strip() for part in _get(name, default).split(",") if part.strip()]


def _int(name: str, default: int) -> int:
    raw = _get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _bool(name: str, default: bool = False) -> bool:
    raw = _get(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


class Settings:
    """Resolved configuration for this process."""

    # ---- Environment ----------------------------------------------------
    # local | uat | production
    APP_ENV: str = _get("APP_ENV", "local").lower()

    # AppSail assigns the port and it cannot be overridden. Locally this
    # falls back to 8000, matching the uvicorn command used in development.
    PORT: int = _int("X_ZOHO_CATALYST_LISTEN_PORT", 8000)

    # ---- URLs -----------------------------------------------------------
    # Origins permitted to call this API. In UAT and production this is the
    # Slate deployment URL for the matching environment.
    ALLOWED_ORIGINS: list[str] = _csv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )

    # This service's own public base URL, for building absolute links.
    API_BASE_URL: str = _get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    # The frontend's base URL. Used in outbound mail — organisation admin
    # onboarding, one-time password handover, password reset — so a wrong
    # value here sends UAT testers into production.
    FRONTEND_BASE_URL: str = _get(
        "FRONTEND_BASE_URL", "http://localhost:3000"
    ).rstrip("/")

    API_V1_PREFIX: str = "/api/v1"

    # ---- Secrets --------------------------------------------------------
    # Never carries a committed default. Set per environment in the console.
    SESSION_SECRET: str = _get("SESSION_SECRET")

    # ---- Catalyst resources ---------------------------------------------
    ORGANIZATION_GUIDE_FOLDER_ID: str = _get("ORGANIZATION_GUIDE_FOLDER_ID")

    # ---- Paths ----------------------------------------------------------
    # Read-only reference data that ships with the app.
    DATA_DIR: Path = BACKEND_ROOT / "data"

    # Anything written at runtime. Catalyst restricts writes to the app
    # directory, so on the server this must be the OS temp directory.
    WRITABLE_DIR: Path = Path(_get("WRITABLE_DIR") or (BACKEND_ROOT / "data"))

    # ---- Behaviour flags ------------------------------------------------
    DEBUG: bool = _bool("DEBUG", False)

    # ---- Derived --------------------------------------------------------
    @property
    def is_local(self) -> bool:
        return self.APP_ENV == "local"

    @property
    def is_uat(self) -> bool:
        return self.APP_ENV == "uat"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_deployed(self) -> bool:
        return not self.is_local

    def validate(self) -> None:
        """Fail fast and loudly rather than halfway through a request."""
        if self.APP_ENV not in {"local", "uat", "production"}:
            raise ConfigError(
                f"APP_ENV must be local, uat or production; got {self.APP_ENV!r}"
            )

        if not self.SESSION_SECRET:
            if self.is_deployed:
                raise ConfigError(
                    "SESSION_SECRET is not set. Set it in the Catalyst console "
                    "for this environment — never in app-config.json."
                )
            # Local convenience: a throwaway secret so the app starts.
            # Sessions do not survive a restart, which is fine in development.
            self.SESSION_SECRET = secrets.token_urlsafe(32)
            print("[config] SESSION_SECRET not set — using an ephemeral local value.")

        if self.is_deployed:
            if not self.ALLOWED_ORIGINS:
                raise ConfigError("ALLOWED_ORIGINS must be set when deployed.")
            for origin in self.ALLOWED_ORIGINS:
                if origin == "*":
                    raise ConfigError(
                        "ALLOWED_ORIGINS cannot be '*' with credentialed requests."
                    )
                if not origin.startswith("https://"):
                    raise ConfigError(
                        f"Deployed origins must use https; got {origin!r}"
                    )
            if not self.FRONTEND_BASE_URL.startswith("https://"):
                raise ConfigError(
                    "FRONTEND_BASE_URL must use https when deployed; "
                    "outbound links depend on it."
                )

    def summary(self) -> dict:
        """Safe to expose on a diagnostic endpoint. Contains no secrets."""
        return {
            "env": self.APP_ENV,
            "port": self.PORT,
            "allowed_origins": self.ALLOWED_ORIGINS,
            "api_base_url": self.API_BASE_URL,
            "frontend_base_url": self.FRONTEND_BASE_URL,
            "session_secret_set": bool(self.SESSION_SECRET),
        }


settings = Settings()
settings.validate()