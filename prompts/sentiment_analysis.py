"""
Sentiment Analysis prompt implementation
Handles NPS scoring based on emotional state changes
"""

from .base import BasePrompt, PromptRegistry
from typing import List

class SentimentAnalysisPrompt(BasePrompt):
    """Sentiment Analysis prompt for NPS scoring"""
    
    def get_prompt_text(self) -> str:
        """Return the SA prompt text from the actual saprompt.py"""
        from .saprompt import PROMPT
        return PROMPT

    def get_supported_formats(self) -> List[str]:
        """SA works with segmented format primarily"""
        return ["segmented", "transparent"]
    
    def get_post_processor_class(self):
        """Return the SA post processor"""
        from post_processors.sentiment_analyzer import SentimentAnalyzer
        return SentimentAnalyzer
    
    def get_days_lookback(self) -> int:
        """SA uses yesterday's data (1 day)"""
        return 1
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        """Generate SA-specific output filename"""
        return f"sa_{department}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("sentiment_analysis", SentimentAnalysisPrompt)
PromptRegistry.register("sa", SentimentAnalysisPrompt)  # Short alias
