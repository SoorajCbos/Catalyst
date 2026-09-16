"""FastAPI application entry point."""

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.services.organization_guide_store import (
    initialize_organization_guide_store,
)
from app.services.organization_store import initialize_organization_store
from app.services.template_store import initialize_template_store
from app.services.user_store import initialize_user_store

# Create local testing tables when the backend starts.
initialize_user_store()
initialize_organization_store()
initialize_template_store()
initialize_organization_guide_store()

app = FastAPI(title="Catalyst Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    # AppSail provides this port. Local development falls back to 8000.
    port = int(
        os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT", "8000")
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
    )