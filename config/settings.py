"""Global pipeline settings"""
import os
from pathlib import Path

MODELS = {
    "gpt-4o": {"provider": "openai", "temperature": 0.0},
    "o4-mini": {"provider": "openai", "temperature": 0.0},
    "gpt-4o-mini": {"provider": "openai", "temperature": 0.0},
    "gemini-1.5-pro": {"provider": "gemini", "temperature": 0.0},
    "gemini-1.5-flash": {"provider": "gemini", "temperature": 0.0},
    "gemini-2.0-flash-exp": {"provider": "gemini", "temperature": 0.0},
    "gemini-2.5-pro": {"provider": "gemini", "temperature": 0.0},
    "gemini-2.5-flash": {
        "provider": "gemini", 
        "temperature": 0.2,
        "top_p": 1.0,
        "top_k": 40,
        "enable_thinking": False
    }
}

PROCESSING = {
    "max_concurrent_requests": 40,
    "retry_attempts": 3,
    "retry_delay": 2,
    "request_timeout": 60
}

DATA_PROCESSING = {
    "days_lookback": {"default": 1, "fcr": 3},
    "required_headers": ['Conversation ID', 'Customer Name', 'Message Sent Time', 'Sent By', 'TEXT', 'Skill', 'Agent Name', 'Message Type', "Tools", "Tool Creation Date", "Tools Json Output", "Tool SUCCESS"]
}

PATHS = {
    "outputs": "outputs",
    "tableau_exports": "outputs/tableau_exports",
    "preprocessing_output": "outputs/preprocessing_output", 
    "llm_outputs": "outputs/LLM_outputs",
    "rule_breaking": "outputs/rule_breaking",
    "credentials": "credentials.json"
}

FORMATS = ["json", "segmented", "transparent", "xml", "xml3d"]

class Settings:
    def __init__(self):
        self.models = MODELS
        self.processing = PROCESSING
        self.data_processing = DATA_PROCESSING
        self.paths = PATHS
        self.formats = FORMATS
        for path in self.paths.values():
            if not path.endswith('.json'):
                Path(path).mkdir(parents=True, exist_ok=True)
    
    def get_model_config(self, model_name):
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}")
        return self.models[model_name]
    
    def get_days_lookback(self, prompt_type="default"):
        return self.data_processing["days_lookback"].get(prompt_type, self.data_processing["days_lookback"]["default"])
    
    def validate_format(self, format_name):
        if format_name not in self.formats:
            raise ValueError(f"Unsupported format: {format_name}")
        return True
    
    def get_env_var(self, var_name):
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"Required environment variable not set: {var_name}")
        return value

SETTINGS = Settings()
