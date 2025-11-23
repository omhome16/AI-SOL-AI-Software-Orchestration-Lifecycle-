import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Configure asyncio for Windows to fix gRPC issues
if sys.platform == "win32":
    # Set Windows-specific event loop policy
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Configure asyncio to handle Windows-specific issues
    try:
        # Set default timeout for asyncio operations
        asyncio.get_event_loop().set_debug(False)
    except RuntimeError:
        # If no event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)


class Config:
    """Central configuration for AI-SOL with environment safety checks."""

    # ========================
    # API KEYS
    # ========================
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    XAI_API_KEY = os.getenv("XAI_API_KEY")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

    # ========================
    # MODEL SETTINGS
    # ========================
    MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "google")
    MODEL_NAME = os.getenv("MODEL_NAME", "models/gemini-2.5-pro")

    try:
        TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
    except ValueError:
        TEMPERATURE = 0.1

    try:
        MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))
    except ValueError:
        MAX_TOKENS = 8000

    # ========================
    # DIRECTORIES
    # ========================
    ENV = os.getenv("ENV", "development")
    WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", f"./workspace/{ENV}"))
    MEMORY_DIR = WORKSPACE_DIR / ".ai-sol"

    # ========================
    # FLAGS
    # ========================
    ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
    ENABLE_CODE_ANALYSIS = os.getenv("ENABLE_CODE_ANALYSIS", "true").lower() == "true"
    ENABLE_INTERRUPTS = os.getenv("ENABLE_INTERRUPTS", "false").lower() == "true"
    try:
        MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    except ValueError:
        MAX_RETRIES = 3

    # ========================
    # METHODS
    # ========================
    @classmethod
    def reload(cls, verbose: bool = False):
        """Reload config values from environment variables."""
        cls.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        cls.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        cls.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        cls.XAI_API_KEY = os.getenv("XAI_API_KEY")
        cls.MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
        cls.GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        cls.GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
        cls.MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "google")
        cls.MODEL_NAME = os.getenv("MODEL_NAME", "models/gemini-2.5-pro")

        try:
            cls.TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
        except ValueError:
            cls.TEMPERATURE = 0.1

        try:
            cls.MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))
        except ValueError:
            cls.MAX_TOKENS = 8000

        cls.ENV = os.getenv("ENV", "development")
        cls.WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", f"./workspace/{cls.ENV}"))
        cls.MEMORY_DIR = cls.WORKSPACE_DIR / ".ai-sol"
        cls.ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
        cls.ENABLE_CODE_ANALYSIS = os.getenv("ENABLE_CODE_ANALYSIS", "true").lower() == "true"

        try:
            cls.MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
        except ValueError:
            cls.MAX_RETRIES = 3

        cls.validate()
        if verbose:
            print(cls.summary())

    @classmethod
    def validate(cls):
        """Ensure configuration is valid and directories exist."""
        provider_keys = {
            "google": cls.GOOGLE_API_KEY,
            "openai": cls.OPENAI_API_KEY,
            "anthropic": cls.ANTHROPIC_API_KEY,
            "xai": cls.XAI_API_KEY,
            "mistral": cls.MISTRAL_API_KEY
        }

        if cls.MODEL_PROVIDER not in provider_keys:
            raise ValueError(f"Unsupported MODEL_PROVIDER: {cls.MODEL_PROVIDER}")

        if not provider_keys[cls.MODEL_PROVIDER]:
            key_name = f"{cls.MODEL_PROVIDER.upper()}_API_KEY"
            raise ValueError(f"{key_name} not found for selected provider '{cls.MODEL_PROVIDER}'")

        try:
            Path(cls.WORKSPACE_DIR).mkdir(parents=True, exist_ok=True)
            Path(cls.MEMORY_DIR).mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise RuntimeError(f"Cannot create workspace directories: {e}")

        return True

    @classmethod
    def _mask_key(cls, key):
        """Show first 4 characters of API key without exposing full key."""
        return f"{key[:4]}****" if key else "❌ Missing"

    @classmethod
    def get_model_provider(cls):
        """Get the current model provider."""
        return cls.MODEL_PROVIDER

    @classmethod
    def get_model_name(cls):
        """Get the current model name."""
        return cls.MODEL_NAME

    @classmethod
    def summary(cls):
        """Display configuration summary."""
        return f"""
AI-SOL Configuration
--------------------
Model Provider   : {cls.MODEL_PROVIDER}
Model Name       : {cls.MODEL_NAME}
Temperature      : {cls.TEMPERATURE}
Max Tokens       : {cls.MAX_TOKENS}

API Keys:
  Google           : {cls._mask_key(cls.GOOGLE_API_KEY)}
  OpenAI           : {cls._mask_key(cls.OPENAI_API_KEY)}
  Anthropic        : {cls._mask_key(cls.ANTHROPIC_API_KEY)}
  XAI              : {cls._mask_key(cls.XAI_API_KEY)}
  Mistral          : {cls._mask_key(cls.MISTRAL_API_KEY)}
  GitHub Token     : {cls._mask_key(cls.GITHUB_TOKEN)}
  GitHub User      : {cls.GITHUB_USERNAME or "❌ Missing"}

Workspace Dir    : {cls.WORKSPACE_DIR}
Memory Dir       : {cls.MEMORY_DIR}
Web Research     : {'Enabled' if cls.ENABLE_WEB_SEARCH else 'Disabled'}
Code Analysis    : {'Enabled' if cls.ENABLE_CODE_ANALYSIS else 'Disabled'}
Max Retries      : {cls.MAX_RETRIES}
"""

# ========================
# Self-test
# ========================
if __name__ == "__main__":
    print(Config.summary())
    Config.validate()
    print("✅ Configuration validated successfully.")
