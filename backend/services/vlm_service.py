import base64
from pathlib import Path
from core.config import Config
import logging

logger = logging.getLogger(__name__)

class VLMService:
    def __init__(self):
        self.provider = Config.MODEL_PROVIDER
        self.api_key = Config.GOOGLE_API_KEY # Assuming Google for now as primary VLM
        
    async def analyze_image(self, image_path: str, prompt: str = "Describe the UI/UX design in this image in detail for a developer.") -> str:
        """
        Analyze an image using a VLM.
        """
        try:
            if not Path(image_path).exists():
                return f"Error: Image file not found at {image_path}"

            if self.provider == "google":
                from langchain_google_genai import ChatGoogleGenerativeAI
                from langchain_core.messages import HumanMessage
                
                llm = ChatGoogleGenerativeAI(
                    model=Config.MODEL_NAME, # Use configured model
                    google_api_key=self.api_key,
                    temperature=0.2
                )
                
                # Read image and encode
                with open(image_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode("utf-8")
                
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                        },
                    ]
                )
                
                response = await llm.ainvoke([message])
                return response.content
                
            else:
                return "VLM provider not supported or configured."
                
        except Exception as e:
            logger.error(f"Error in VLM analysis: {e}")
            return f"Error analyzing image: {str(e)}"
