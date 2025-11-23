"""
Templates API Router
Endpoints for project templates
"""
from fastapi import APIRouter, HTTPException
from backend.utils.templates import get_templates, get_template_by_id

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
async def list_templates():
    """Get all available project templates"""
    return {
        "templates": get_templates(),
        "count": len(get_templates())
    }


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get specific template configuration"""
    template = get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
