"""FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
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
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get(f"{settings.API_V1_PREFIX}/_meta")
def meta():
    return settings.summary()


if __name__ == "__main__":
    # AppSail supplies the port via X_ZOHO_CATALYST_LISTEN_PORT;
    # settings.PORT falls back to 8000 locally.
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)