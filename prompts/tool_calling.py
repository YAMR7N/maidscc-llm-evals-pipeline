"""
Tool Calling (Ghonaim) Evaluation Prompt Integration
"""

from .base import BasePrompt, PromptRegistry
from typing import List

# Reuse the authored prompt text
from .tools_ghonaim import PROMPT as GHONAIM_PROMPT


class ToolCallingPrompt(BasePrompt):
    """Prompt for evaluating tool-calling correctness in conversations"""

    def get_prompt_text(self) -> str:
        # Return the static prompt template. Per-conversation replacement for
        # @LastSkill@ is handled in the pipeline just before calling the LLM.
        return GHONAIM_PROMPT

    def get_supported_formats(self) -> List[str]:
        # Needs XML to leverage system-like structure and include skills metadata
        return ["xml"]

    def get_post_processor_class(self):
        # No post-processing for now
        return None

    def get_days_lookback(self) -> int:
        # Yesterday's data
        return 1

    def get_output_filename(self, department: str, date_str: str) -> str:
        dept_name = department.lower().replace(' ', '_')
        return f"tool_calling_{dept_name}_{date_str}.csv"


# Register the prompt
PromptRegistry.register("tool_calling", ToolCallingPrompt)

