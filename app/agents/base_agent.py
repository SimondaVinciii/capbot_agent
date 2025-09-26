"""Base agent class for all AI agents."""

import google.generativeai as genai
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from config import config
import logging

# Configure Google AI
genai.configure(api_key=config.GOOGLE_API_KEY)

class BaseAgent(ABC):
    """Abstract base class for all AI agents."""
    
    def __init__(self, name: str, model_name: str = "gemini-2.0-flash"):
        """Initialize the base agent.
        
        Args:
            name: Agent name for identification
            model_name: Google AI model to use
        """
        self.name = name
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        self.logger = logging.getLogger(f"agent.{name}")
        
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results.
        
        Args:
            input_data: Input data for processing
            
        Returns:
            Processing results
        """
        pass
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using Google AI model.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get('temperature', 0.7),
                    max_output_tokens=kwargs.get('max_tokens', 2048),
                    top_p=kwargs.get('top_p', 0.8),
                    top_k=kwargs.get('top_k', 40)
                )
            )
            return response.text
        except Exception as e:
            self.logger.error(f"Error generating text: {e}")
            raise
    
    def log_info(self, message: str):
        """Log info message."""
        self.logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str, error: Exception = None):
        """Log error message."""
        if error:
            self.logger.error(f"[{self.name}] {message}: {error}")
        else:
            self.logger.error(f"[{self.name}] {message}")
    
    def log_debug(self, message: str):
        """Log debug message."""
        self.logger.debug(f"[{self.name}] {message}")

class AgentResult:
    """Standard result object for agent operations."""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, metadata: Dict[str, Any] = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }

