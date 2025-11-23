"""
Project Templates
Pre-configured templates for common project types
"""
from typing import Dict, List, Any
from pydantic import BaseModel


class ProjectTemplate(BaseModel):
    id: str
    name: str
    description: str
    type: str  # web, mobile, api
    icon: str 
    configuration: Dict[str, Any]
    tags: List[str]


# Template Library
TEMPLATES: List[ProjectTemplate] = [
    ProjectTemplate(
        id="ecommerce-web",
        name="E-Commerce Website",
        type="web",
        icon="🛍️",
        description="Modern e-commerce platform with product catalog, shopping cart, and checkout",
        configuration={
            "theme_name": {"value": "Modern Commerce", "type": "text"},
            "primary_color": {"value": "#3B82F6", "type": "color"},
            "secondary_color": {"value": "#10B981", "type": "color"},
            "accent_color": {"value": "#F59E0B", "type": "color"},
            "font": {"value": "Inter", "type": "text"},
            "has_auth": {"value": True, "type": "boolean"},
            "has_payment": {"value": True, "type": "boolean"},
            "has_checkout": {"value": True, "type": "boolean"},
            "features": {"value": ["Product Catalog", "Shopping Cart", "User Accounts", "Payment Gateway", "Order Management"], "type": "array"}
        },
        tags=["ecommerce", "shopping", "payments"]
    ),
    ProjectTemplate(
        id="blog-web",
        name="Blog Platform",
        type="web",
        icon="✍️",
        description="Clean blog platform with articles, comments, and author profiles",
        configuration={
            "theme_name": {"value": "Modern Blog", "type": "text"},
            "primary_color": {"value": "#1F2937", "type": "color"},
            "secondary_color": {"value": "#6366F1", "type": "color"},
            "accent_color": {"value": "#EC4899", "type": "color"},
            "font": {"value": "Merriweather", "type": "text"},
            "has_auth": {"value": True, "type": "boolean"},
            "has_comments": {"value": True, "type": "boolean"},
            "has_tags": {"value": True, "type": "boolean"},
            "features": {"value": ["Article Management", "Comments System", "Author Profiles", "Categories & Tags", "Search"], "type": "array"}
        },
        tags=["blog", "content", "cms"]
    ),
    ProjectTemplate(
        id="saas-dashboard",
        name="SaaS Dashboard",
        type="web",
        icon="📊",
        description="Professional SaaS dashboard with analytics, user management, and settings",
        configuration={
            "theme_name": {"value": "SaaS Pro", "type": "text"},
            "primary_color": {"value": "#7C3AED", "type": "color"},
            "secondary_color": {"value": "#06B6D4", "type": "color"},
            "accent_color": {"value": "#F97316", "type": "color"},
            "font": {"value": "Plus Jakarta Sans", "type": "text"},
            "has_auth": {"value": True, "type": "boolean"},
            "has_analytics": {"value": True, "type": "boolean"},
            "has_billing": {"value": True, "type": "boolean"},
            "features": {"value": ["Analytics Dashboard", "User Management", "Team Collaboration", "Subscription Billing", "API Integration"], "type": "array"}
        },
        tags=["saas", "dashboard", "analytics"]
    ),
    ProjectTemplate(
        id="portfolio-web",
        name="Portfolio Website",
        type="web",
        icon="🎨",
        description="Creative portfolio to showcase projects and skills",
        configuration={
            "theme_name": {"value": "Creative Portfolio", "type": "text"},
            "primary_color": {"value": "#0F172A", "type": "color"},
            "secondary_color": {"value": "#8B5CF6", "type": "color"},
            "accent_color": {"value": "#F472B6", "type": "color"},
            "font": {"value": "Poppins", "type": "text"},
            "has_contact_form": {"value": True, "type": "boolean"},
            "has_gallery": {"value": True, "type": "boolean"},
            "features": {"value": ["Project Showcase", "About Section", "Contact Form", "Skills Display", "Testimonials"], "type": "array"}
        },
        tags=["portfolio", "creative", "personal"]
    ),
    ProjectTemplate(
        id="mobile-app",
        name="Mobile App",
        type="mobile",
        icon="📱",
        description="Cross-platform mobile application with native feel",
        configuration={
            "theme_name": {"value": "Mobile First", "type": "text"},
            "primary_color": {"value": "#2563EB", "type": "color"},
            "secondary_color": {"value": "#059669", "type": "color"},
            "accent_color": {"value": "#DC2626", "type": "color"},
            "platform": {"value": "cross-platform", "type": "select"},
            "has_auth": {"value": True, "type": "boolean"},
            "has_push_notifications": {"value": True, "type": "boolean"},
            "features": {"value": ["User Authentication", "Push Notifications", "Offline Mode", "Camera Integration", "Location Services"], "type": "array"}
        },
        tags=["mobile", "app", "cross-platform"]
    )
]


def get_templates() -> List[Dict[str, Any]]:
    """Get all available templates"""
    return [template.dict() for template in TEMPLATES]


def get_template_by_id(template_id: str) -> Dict[str, Any] | None:
    """Get specific template by ID"""
    for template in TEMPLATES:
        if template.id == template_id:
            return template.dict()
    return None
