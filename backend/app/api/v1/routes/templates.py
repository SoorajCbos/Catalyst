"""API routes for creating, listing, editing and enabling templates."""

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.template_store import (
    create_template,
    get_template,
    list_templates,
    set_template_active,
    template_name_exists,
    update_template,
)

router = APIRouter()

# These are the only merge fields currently supported by the application.
ALLOWED_MERGE_FIELDS = {
    "{{username}}",
    "{{email}}",
    "{{organization_name}}",
    "{{default_password}}",
}

# Find values written in the {{field_name}} format.
MERGE_FIELD_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class TemplateResponse(BaseModel):
    """Template information returned to the frontend."""

    recordId: str
    name: str
    subject: str
    body: str
    allowedMergeFields: list[str]
    active: bool


class SaveTemplateRequest(BaseModel):
    """Template information accepted while creating or editing."""

    name: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10_000)


class TemplateStatusRequest(BaseModel):
    """Active status accepted by the enable/disable endpoint."""

    active: bool


def find_merge_fields(subject: str, body: str) -> list[str]:
    """
    Find and normalize the merge fields used by a template.

    For example, both {{ username }} and {{username}} become
    {{username}} in the stored list.
    """

    content = f"{subject}\n{body}"
    names = MERGE_FIELD_PATTERN.findall(content)

    return sorted({f"{{{{{name}}}}}" for name in names})


def validate_merge_fields(subject: str, body: str) -> list[str]:
    """
    Reject fields that the application does not know how to replace.

    Without this check, a typing mistake such as {{usernme}} would be
    saved and later appear unchanged in a real message.
    """

    fields = find_merge_fields(subject, body)
    invalid_fields = [
        field for field in fields if field not in ALLOWED_MERGE_FIELDS
    ]

    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported merge fields: "
                + ", ".join(invalid_fields)
            ),
        )

    return fields


@router.get("", response_model=list[TemplateResponse])
def get_templates() -> list[TemplateResponse]:
    """Return all templates for the management page."""

    return [
        TemplateResponse(**template)
        for template in list_templates()
    ]


@router.get("/{record_id}", response_model=TemplateResponse)
def get_template_by_id(record_id: str) -> TemplateResponse:
    """Return one template."""

    template = get_template(record_id)

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
def post_template(payload: SaveTemplateRequest) -> TemplateResponse:
    """Validate and create a template."""

    name = payload.name.strip()
    subject = payload.subject.strip()
    body = payload.body.strip()

    if template_name_exists(name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A template with that name already exists.",
        )

    merge_fields = validate_merge_fields(subject, body)

    template = create_template(
        name=name,
        subject=subject,
        body=body,
        merge_fields=merge_fields,
    )

    return TemplateResponse(**template)


@router.put("/{record_id}", response_model=TemplateResponse)
def put_template(
    record_id: str,
    payload: SaveTemplateRequest,
) -> TemplateResponse:
    """Validate and update an existing template."""

    if get_template(record_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    name = payload.name.strip()
    subject = payload.subject.strip()
    body = payload.body.strip()

    if template_name_exists(name, excluded_record_id=record_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A template with that name already exists.",
        )

    merge_fields = validate_merge_fields(subject, body)

    template = update_template(
        record_id=record_id,
        name=name,
        subject=subject,
        body=body,
        merge_fields=merge_fields,
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
) -> TemplateResponse:
    """Enable or disable a template."""

    template = set_template_active(record_id, payload.active)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found.",
        )

    return TemplateResponse(**template)