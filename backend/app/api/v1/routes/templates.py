"""Template management routes."""

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.catalyst_app import get_catalyst_app
from app.services.template_store import (
    create_template,
    get_template,
    list_templates,
    set_template_active,
    template_name_exists,
    update_template,
)

router = APIRouter()

ALLOWED_MERGE_FIELDS = {
    "{{username}}",
    "{{email}}",
    "{{organization_name}}",
    "{{default_password}}",
}

MERGE_FIELD_PATTERN = re.compile(
    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
)


class TemplateResponse(BaseModel):
    recordId: str
    name: str
    subject: str
    body: str
    allowedMergeFields: list[str]
    active: bool


class SaveTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10_000)


class TemplateStatusRequest(BaseModel):
    active: bool


def validate_merge_fields(subject: str, body: str) -> list[str]:
    """Return supported merge fields and reject unknown fields."""

    names = MERGE_FIELD_PATTERN.findall(f"{subject}\n{body}")
    fields = sorted({f"{{{{{name}}}}}" for name in names})
    invalid = [field for field in fields if field not in ALLOWED_MERGE_FIELDS]

    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported merge fields: " + ", ".join(invalid),
        )

    return fields


@router.get("", response_model=list[TemplateResponse])
def get_templates(
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> list[TemplateResponse]:
    return [
        TemplateResponse(**template)
        for template in list_templates(catalyst_app)
    ]


@router.get("/{record_id}", response_model=TemplateResponse)
def get_template_by_id(
    record_id: str,
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> TemplateResponse:
    template = get_template(record_id, catalyst_app)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    return TemplateResponse(**template)


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_template(
    payload: SaveTemplateRequest,
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> TemplateResponse:
    name = payload.name.strip()
    subject = payload.subject.strip()
    body = payload.body.strip()

    if template_name_exists(
        name,
        catalyst_app=catalyst_app,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A template with that name already exists.",
        )

    template = create_template(
        name=name,
        subject=subject,
        body=body,
        merge_fields=validate_merge_fields(subject, body),
        catalyst_app=catalyst_app,
    )

    return TemplateResponse(**template)


@router.put("/{record_id}", response_model=TemplateResponse)
def put_template(
    record_id: str,
    payload: SaveTemplateRequest,
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> TemplateResponse:
    if get_template(record_id, catalyst_app) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    name = payload.name.strip()
    subject = payload.subject.strip()
    body = payload.body.strip()

    if template_name_exists(
        name,
        excluded_record_id=record_id,
        catalyst_app=catalyst_app,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A template with that name already exists.",
        )

    template = update_template(
        record_id=record_id,
        name=name,
        subject=subject,
        body=body,
        merge_fields=validate_merge_fields(subject, body),
        catalyst_app=catalyst_app,
    )

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    return TemplateResponse(**template)


@router.patch(
    "/{record_id}/status",
    response_model=TemplateResponse,
)
def patch_template_status(
    record_id: str,
    payload: TemplateStatusRequest,
    catalyst_app: Any | None = Depends(get_catalyst_app),
) -> TemplateResponse:
    template = set_template_active(
        record_id,
        payload.active,
        catalyst_app,
    )

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    return TemplateResponse(**template)