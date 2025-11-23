"""
Project branding helper utilities.
Provides functions to incorporate project name into agent prompts and outputs.
"""

from typing import Dict, Any


def add_branding_context(prompt: str, state: Dict[str, Any]) -> str:
    """
    Add project branding context to an agent prompt.
    
    Args:
        prompt: Original agent prompt
        state: Workflow state containing project information
        
    Returns:
        Enhanced prompt with project name branding context
    """
    project_name = state.get("project_name") or state.get("user_context", {}).get("project_name", "the project")
    project_type = state.get("user_context", {}).get("project_type", "application")
    
    branding_prefix = f"""
**PROJECT BRANDING CONTEXT:**
- Project Name: "{project_name}"
- Project Type: {project_type}

**IMPORTANT INSTRUCTIONS:**
1. Incorporate the project name "{project_name}" naturally throughout your analysis and recommendations
2. When suggesting component names, file names, or identifiers, use variations of "{project_name}"
3. In UI/UX design recommendations, consider "{project_name}" as the brand identity
4. Use "{project_name}" in example content, placeholder text, and mock data
5. Ensure all generated content feels personalized to "{project_name}"

---

"""
    
    return branding_prefix + prompt


def format_with_project_name(text: str, project_name: str) -> str:
    """
    Format text to include project name where appropriate.
    
    Args:
        text: Text to format
        project_name: Name of the project
        
    Returns:
        Formatted text with project name incorporated
    """
    replacements = {
        "the application": f"{project_name}",
        "the project": f"{project_name}",
        "the system": f"{project_name}",
        "the app": f"{project_name}",
        "this project": f"{project_name}",
        "your project": f"{project_name}",
    }
    
    formatted_text = text
    for old, new in replacements.items():
        # Case-insensitive replacement
        formatted_text = formatted_text.replace(old, new)
        formatted_text = formatted_text.replace(old.capitalize(), new)
    
    return formatted_text


def get_branded_examples(project_name: str, project_type: str) -> Dict[str, Any]:
    """
    Generate branded examples based on project name and type.
    
    Args:
        project_name: Name of the project
        project_type: Type of project (website, ios, android)
        
    Returns:
        Dictionary of branded examples
    """
    # Convert project name to various formats
    snake_case = project_name.lower().replace(" ", "_")
    kebab_case = project_name.lower().replace(" ", "-")
    camel_case = ''.join(word.capitalize() for word in project_name.split())
    
    examples = {
        "package_name": snake_case,
        "class_name": camel_case,
        "file_prefix": kebab_case,
        "namespace": camel_case,
        "app_title": project_name,
    }
    
    if project_type == "website":
        examples.update({
            "domain_suggestion": f"{kebab_case.com",
            "meta_title": f"{project_name} - Your Solution",
            "component_examples": [
                f"{camel_case}Header",
                f"{camel_case}Footer",
                f"{camel_case}Dashboard"
            ]
        })
    elif project_type == "ios":
        examples.update({
            "bundle_id": f"com.{snake_case}.app",
            "app_name": project_name,
            "scheme_name": snake_case,
            "target_name": camel_case
        })
    elif project_type == "android":
        examples.update({
            "package_name": f"com.{snake_case}",
            "app_name": project_name,
            "module_name": snake_case,
            "activity_examples": [
                f"{camel_case}MainActivity",
                f"{camel_case}SplashActivity"
            ]
        })
    
    return examples
