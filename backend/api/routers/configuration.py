"""
Configuration router for dynamic project-type-specific field generation.
Uses LLM to generate appropriate configuration fields based on project type.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.core.config import Config
from backend.core.state_manager import StateManager

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateFieldsRequest(BaseModel):
    project_type: str  # website, ios, android
    requirements: str
    image_path: Optional[str] = None


@router.post("/projects/{project_id}/generate-config-fields")
async def generate_configuration_fields(project_id: str, req: GenerateFieldsRequest):
    """LLM generates configuration fields based on project type and requirements"""
    
    try:
        logger.info(f"[CONFIG] Generating fields for {req.project_type} project: {project_id}")
        
        # VLM Analysis
        vlm_analysis = ""
        if req.image_path:
            try:
                from backend.services.vlm_service import VLMService
                vlm_service = VLMService()
                logger.info(f"[CONFIG] Analyzing reference image: {req.image_path}")
                vlm_analysis = await vlm_service.analyze_image(req.image_path)
                logger.info(f"[CONFIG] VLM Analysis complete")
            except Exception as e:
                logger.error(f"[CONFIG] VLM analysis failed: {e}")
        
        llm = ChatGoogleGenerativeAI(model=Config.ORCHESTRATOR_MODEL, temperature=0.7)
        
        prompt = f"""
        You are an expert software architect and product manager.
        Generate a comprehensive list of configuration fields for a new project.
        
        Project Type: {req.project_type}
        Requirements: {req.requirements}
        
        Reference Image Analysis (Use this to infer design choices):
        {vlm_analysis}
        
        The goal is to gather ALL necessary details from the user to build a perfect application.
        Be exhaustive, specific, and creative.
        
        Generate 15-20 fields covering:
        1. Branding (App Name, Slogan, Primary Color, Logo Style)
        2. UI/UX (Theme, Layout Style, Font Pairings, Animation Level)
        3. Tech Stack (Frontend Framework, Backend Language, Database, Auth Provider)
        4. Platform Specifics (PWA support, Mobile responsiveness, SEO targets)
        5. Business Logic (User Roles, Monetization Model, Target Audience)
        
        For each field, provide:
        - name: unique identifier (snake_case) - MUST BE UNIQUE
        - label: user-friendly label
        - type: text, select, boolean, color, number, file
        - options: list of options (for select type)
        - default: default value (infer from VLM analysis if possible)
        - description: help text
        
        Return ONLY valid JSON as a list of field objects.
        Example:
        [
            {{
                "name": "primary_color",
                "label": "Primary Brand Color",
                "type": "color",
                "default": "#3B82F6",
                "description": "Main color for buttons and highlights"
            }}
        ]
        """
        
        response = await llm.ainvoke(prompt)
        fields_json = response.content
        
        if "```" in fields_json:
            fields_json = fields_json.split("```")[1]
            if fields_json.strip().startswith("json"):
                fields_json = fields_json.strip()[4:].strip()
        
        fields = json.loads(fields_json)
        
        # Post-processing: Ensure unique names and map 'key' to 'name' if needed
        seen_names = set()
        processed_fields = []
        
        for field in fields:
            # Handle potential key/name mismatch from LLM
            if "key" in field and "name" not in field:
                field["name"] = field.pop("key")
            
            base_name = field.get("name", "field")
            final_name = base_name
            counter = 1
            
            while final_name in seen_names:
                counter += 1
                final_name = f"{base_name}_{counter}"
            
            field["name"] = final_name
            seen_names.add(final_name)
            processed_fields.append(field)
            
        logger.info(f"[CONFIG] Generated {len(processed_fields)} fields for {req.project_type}")
        
        return {"fields": processed_fields}
        
    except Exception as e:
        logger.error(f"[CONFIG] Failed to generate fields: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate configuration fields: {str(e)}")


@router.post("/projects/{project_id}/save-configuration")
async def save_configuration(project_id: str, req: SaveConfigRequest):
    """Save project configuration to state"""
    
    try:
        logger.info(f"[CONFIG] Saving configuration for {project_id}")
        
        state_manager = StateManager()
        project = state_manager.load_project(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Save configuration
        if "user_context" not in project:
            project["user_context"] = {}
        
        project["user_context"]["configuration"] = req.configuration
        project["configuration"] = req.configuration  # Store at top level too
        
        state_manager.save_project(project_id, project)
        
        logger.info(f"[CONFIG] Configuration saved for {project_id}")
        
        return {"status": "saved", "configuration": req.configuration}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONFIG] Failed to save configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")


@router.post("/projects/{project_id}/validate-custom-field")
async def validate_custom_field(project_id: str, description: str):
    """Use LLM to generate a custom field from user description"""
    
    try:
        logger.info(f"[CONFIG] Validating custom field: '{description}'")
        
        llm = ChatGoogleGenerativeAI(
            model=Config.ORCHESTRATOR_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.3
        )
        
        prompt = f"""Convert this user request into a configuration field definition.

User Request: "{description}"

Generate a single JSON object with:
- name: field identifier (snake_case, descriptive)
- label: human-readable label
- type: most appropriate type [text, color, file, number, select, checkbox]
- options: array (only if select type makes sense)
- required: boolean (true if seems important)
- default: sensible default value
- description: brief help text

Examples:
- "I need to set a custom font size" → {{"name": "custom_font_size", "type": "number", "label": "Custom Font Size", ...}}
- "Upload background pattern" → {{"name": "background_pattern", "type": "file", "label": "Background Pattern", ...}}

Output ONLY valid JSON object."""

        response = await llm.ainvoke(prompt)
        field_json = response.content.strip()
        
        # Remove markdown if present
        if field_json.startswith("```"):
            field_json = field_json.split("```")[1]
            if field_json.startswith("json"):
                field_json = field_json[4:].strip()
        
        field = json.loads(field_json)
        
        logger.info(f"[CONFIG] Generated custom field: {field.get('name')}")
        
        return {"field": field}
        
    except Exception as e:
        logger.error(f"[CONFIG] Failed to validate custom field: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate field: {str(e)}")
