"""
Utility to format configuration and context data for LLM prompts
"""
from typing import Dict, Any, List


def format_configuration_for_llm(state: Dict[str, Any]) -> str:
    """
    Format configuration, images, and context into a nice prompt section for LLMs.
    
    Args:
        state: Workflow state containing user_context with configuration and images
        
    Returns:
        Formatted string to inject into LLM prompts
    """
    user_context = state.get("user_context", {})
    config = user_context.get("configuration", {})
    images = user_context.get("inspiration_images", [])
    
    if not config and not images:
        return ""
    
    sections = []
    
    # Configuration section
    if config:
        sections.append("**USER CONFIGURATION:**")
        sections.append("The user has specified these design preferences:")
        
        # Group by category
        colors = {k: v for k, v in config.items() if 'color' in k.lower()}
        fonts = {k: v for k, v in config.items() if 'font' in k.lower()}
        ui_style = {k: v for k, v in config.items() if 'style' in k.lower() or 'theme' in k.lower()}
        other = {k: v for k, v in config.items() if k not in colors and k not in fonts and k not in ui_style}
        
        if colors:
            sections.append("\nColors:")
            for key, value in colors.items():
                sections.append(f"  - {key.replace('_', ' ').title()}: {value}")
        
        if fonts:
            sections.append("\nTypography:")
            for key, value in fonts.items():
                sections.append(f"  - {key.replace('_', ' ').title()}: {value}")
        
        if ui_style:
            sections.append("\nUI Style:")
            for key, value in ui_style.items():
                sections.append(f"  - {key.replace('_', ' ').title()}: {value}")
        
        if other:
            sections.append("\nOther Settings:")
            for key, value in other.items():
                if isinstance(value, bool):
                    value = "Yes" if value else "No"
                sections.append(f"  - {key.replace('_', ' ').title()}: {value}")
    
    # Images section
    if images:
        sections.append("\n**INSPIRATION IMAGES:**")
        sections.append(f"The user has provided {len(images)} reference image(s) for design inspiration:")
        for i, img_path in enumerate(images, 1):
            sections.append(f"  {i}. {img_path}")
        sections.append("Use these images to understand the visual aesthetic the user wants.")
    
    if sections:
        sections.insert(0, "\n" + "="*70)
        sections.append("="*70 + "\n")
    
    return "\n".join(sections)


def get_design_guidelines_from_config(config: Dict[str, Any]) -> List[str]:
    """
    Extract concrete design guidelines from configuration.
    
    Args:
        config: User configuration dictionary
        
    Returns:
        List of design guideline strings
    """
    guidelines = []
    
    # Colors
    if "primary_color" in config:
        guidelines.append(f"Use {config['primary_color']} as the primary brand color")
    if "secondary_color" in config:
        guidelines.append(f"Use {config['secondary_color']} as the secondary/accent color")
    
    # Typography
    if "font_family" in config:
        guidelines.append(f"Use {config['font_family']} font family")
    
    # UI Style
    if "ui_style" in config:
        style = config["ui_style"]
        style_map = {
            "Modern": "modern, clean design with smooth transitions and subtle shadows",
            "Minimal": "minimalist design with plenty of whitespace and simple elements",
            "Glassmorphism": "glassmorphism aesthetic with frosted glass effects and transparency",
            "Neumorphism": "neumorphic design with soft shadows and extruded elements",
            "Brutalist": "brutalist design with bold typography and high contrast"
        }
        if style in style_map:
            guidelines.append(f"Apply {style_map[style]}")
    
    # Dark mode
    if config.get("dark_mode"):
        guidelines.append("Implement dark mode support")
    
    # Responsive
    if config.get("responsive"):
        guidelines.append("Ensure responsive design for all screen sizes")
    
    return guidelines


def inject_config_into_prompt(base_prompt: str, state: Dict[str, Any]) -> str:
    """
    Inject configuration and context into an agent's base prompt.
    
    Args:
        base_prompt: The agent's original prompt
        state: Workflow state
        
    Returns:
        Enhanced prompt with configuration injected
    """
    config_section = format_configuration_for_llm(state)
    
    if config_section:
        # Insert after the first paragraph/section
        lines = base_prompt.split('\n\n', 1)
        if len(lines) == 2:
            return lines[0] + '\n\n' + config_section + '\n\n' + lines[1]
        else:
            return base_prompt + '\n\n' + config_section
    
    return base_prompt
