"""
Base prompt interface for all prompt types
Defines the contract that all prompts must implement
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class BasePrompt(ABC):
    """Abstract base class for all prompt types"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def get_prompt_text(self) -> str:
        """Return the actual prompt text to send to the LLM"""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Return list of supported input formats (json, segmented, transparent)"""
        pass
    
    @abstractmethod
    def get_post_processor_class(self):
        """Return the post-processor class for this prompt type"""
        pass
    
    def get_model_config(self) -> Dict[str, Any]:
        """Return model-specific configuration (temperature, max_tokens, etc.)"""
        return {
            "temperature": 0.0,
            "max_tokens": 4000
        }
    
    def get_days_lookback(self) -> int:
        """Return number of days to look back for data (default: 1)"""
        return 1
    
    def preprocess_data(self, raw_data: Any) -> Any:
        """Optional preprocessing of raw data before format conversion"""
        return raw_data
    
    def validate_input(self, formatted_data: Any) -> bool:
        """Validate that formatted data is suitable for this prompt"""
        return True
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        """Generate output filename for this prompt type"""
        return f"{self.name}_{department}_{date_str}.csv"
    
    def should_filter_agent_messages(self) -> bool:
        """Return True if agent messages should be filtered out for this prompt"""
        return False

class PromptRegistry:
    """Registry for managing available prompt types"""
    
    _prompts = {}
    
    @classmethod
    def register(cls, name: str, prompt_class):
        """Register a new prompt type"""
        cls._prompts[name] = prompt_class
    
    @classmethod
    def get_prompt(cls, name: str) -> BasePrompt:
        """Get a prompt instance by name"""
        if name not in cls._prompts:
            raise ValueError(f"Unknown prompt type: {name}")
        return cls._prompts[name](name)
    
    @classmethod
    def get_available_prompts(cls) -> List[str]:
        """Get list of all registered prompt names"""
        return list(cls._prompts.keys())
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a prompt type is registered"""
        return name in cls._prompts
