"""
LLM-powered markdown formatter for agent outputs.
Converts structured Pydantic models to human-readable, context-aware markdown documents.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.core.config import Config

logger = logging.getLogger(__name__)


class MarkdownFormatter:
    """Intelligent markdown formatter using LLM for context-aware document generation."""
    
    def __init__(self):
        """Initialize the markdown formatter with Google Gemini."""
        try:
            # Use Google Gemini via config
            self.llm = ChatGoogleGenerativeAI(
                model=Config.ORCHESTRATOR_MODEL,  # Use faster model for formatting
                google_api_key=Config.GOOGLE_API_KEY,
                temperature=0.3
            )
            self.use_llm = True
            logger.info("[INIT] LLM formatter initialized with Google Gemini")
        except Exception as e:
            logger.warning(f"[WARN] LLM not available ({e}), will use simple formatting")
            self.llm = None
            self.use_llm = False
        
    async def format(self, stage_name: str, output: Dict[str, Any], project_type: str = "website") -> str:
        """
        Convert agent output to beautiful markdown.
        
        Args:
            stage_name: Name of the workflow stage (requirements, architecture, etc.)
            output: Raw agent output with Pydantic models
            project_type: Type of project (website, ios, android)
            
        Returns:
            Formatted markdown string
        """
        try:
            # If LLM not available, use fallback immediately
            if not self.use_llm:
                logger.info(f"[INFO] Using fallback formatter for {stage_name} (no LLM)")
                return self._fallback_format(stage_name, output)
            
            logger.info(f"[FORMAT] Formatting {stage_name} output with LLM (project_type={project_type})")
            
            # Get context-specific prompt
            context_prompt = self._get_context_prompt(project_type)
            
            # Prepare data for LLM
            formatted_data = self._serialize_pydantic(output)
            
            # Build full prompt
            prompt = f"""{context_prompt}

**Stage**: {stage_name.capitalize()}
**Project Type**: {project_type}

**Raw Agent Output**:
```json
{json.dumps(formatted_data, indent=2, default=str)}
```

**Instructions**:
1. Convert this into a clear, professional markdown document
2. Use proper headings (##, ###) for organization
3. Format lists as bullet points or numbered lists  
4. Use tables for structured data (features, requirements, timelines)
5. Add brief descriptions to make content scannable
6. Highlight priorities (High/Medium/Low) with **bold** or colors
7. Make it easy for humans to read and understand
8. Include emojis where appropriate for visual appeal

Output ONLY the markdown content. No meta-commentary."""

            # Get LLM response
            response = await self.llm.ainvoke(prompt)
            markdown_content = response.content
            
            # Add metadata header
            final_content = f"""# {stage_name.capitalize()} Analysis

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Project Type**: {project_type.capitalize()}

---

{markdown_content}
"""
            
            logger.info(f"[SUCCESS] LLM formatted {stage_name} ({len(final_content)} chars)")
            return final_content
            
        except Exception as e:
            logger.error(f"[ERROR] LLM formatting failed for {stage_name}: {e}", exc_info=True)
            return self._fallback_format(stage_name, output)
    
    def _get_context_prompt(self, project_type: str) -> str:
        """Get context-specific formatting instructions based on project type."""
        prompts = {
            "website": """Create a professional web development requirements document.
Focus on: UI/UX design, responsive layouts, browser compatibility, accessibility, SEO.
Use tables for feature lists, include design mockup sections, highlight modern web patterns.""",
            
            "ios": """Create an iOS app requirements document following Apple's guidelines.
Focus on: SwiftUI/UIKit components, iOS-specific features, App Store requirements, HIG compliance.
Include: Target iOS versions, Required permissions, App lifecycle, Push notifications.""",
            
            "android": """Create an Android app requirements document following Material Design.
Focus on: Jetpack Compose, Material Design 3, Play Store guidelines, Android architecture.
Include: Target SDK, Runtime permissions, App architecture (MVVM/MVI), Notifications."""
        }
        return prompts.get(project_type, prompts["website"])
    
    def _serialize_pydantic(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Pydantic models to JSON-serializable dictionaries."""
        result = {}
        
        for key, value in output.items():
            # Skip internal fields
            if key in ['success', 'status', 'steps_completed']:
                continue
            
            # Handle Pydantic model
            if hasattr(value, 'dict'):
                result[key] = value.dict()
            # Handle list of models
            elif isinstance(value, list):
                result[key] = [
                    item.dict() if hasattr(item, 'dict') else item
                    for item in value
                ]
            # Handle dictionaries
            elif isinstance(value, dict):
                result[key] = {
                    k: v.dict() if hasattr(v, 'dict') else v
                    for k, v in value.items()
                }
            # Handle primitives
            else:
                result[key] = value
        
        return result
    
    def _fallback_format(self, stage_name: str, output: Dict[str, Any]) -> str:
        """Simple fallback formatter if LLM fails."""
        logger.warning(f"Using fallback formatter for {stage_name}")
        
        content = f"# {stage_name.capitalize()} Analysis\n\n"
        content += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
        
        for key, value in output.items():
            if key in ['success', 'status', 'steps_completed']:
                continue
            
            section_title = key.replace('_', ' ').title()
            content += f"## {section_title}\n\n"
            
            if isinstance(value, list):
                for idx, item in enumerate(value, 1):
                    if hasattr(item, 'dict'):
                        item_dict = item.dict()
                        content += f"### Item {idx}\n\n"
                        for k, v in item_dict.items():
                            if isinstance(v, list):
                                content += f"**{k.replace('_', ' ').title()}**:\n"
                                for sub in v:
                                    content += f"- {sub}\n"
                                content += "\n"
                            else:
                                content += f"**{k.replace('_', ' ').title()}**: {v}\n\n"
                    else:
                        content += f"- {item}\n"
                content += "\n"
            elif hasattr(value, 'dict'):
                value_dict = value.dict()
                for k, v in value_dict.items():
                    content += f"**{k.replace('_', ' ').title()}**: {v}\n\n"
            else:
                content += f"{value}\n\n"
        
        return content


# Singleton instance
_formatter = None

def get_markdown_formatter() -> MarkdownFormatter:
    """Get or create the global markdown formatter instance."""
    global _formatter
    if _formatter is None:
        _formatter = MarkdownFormatter()
    return _formatter
