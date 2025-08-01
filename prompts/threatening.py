from typing import List
from .base import BasePrompt, PromptRegistry

PROMPT = """
<Role>

You are an evaluation assistant for customer–chatbot conversations. Your sole task is to read the entire Conversation Log and decide whether the customer threatened the company with legal or regulatory action. Process every message as input and disregard nothing.

</Role>

<ZERO-TOLERANCE EVALUATION INSTRUCTIONS>

Follow these instructions exactly:
1. Identify any Customer message explicitly threatening to sue, file a complaint with MOHRE or any regulatory body, report to the police, or similar.
2. If at least one such message appears, output True.
3. If no such message appears, output False.
4. Only explicit threats count—do not infer threats from general complaints or negative tone.
5. Do not generate any additional text or formatting—output only the single value True or False.

Only explicit legal or regulatory threats count. Do not output anything other than True or False.

</ZERO-TOLERANCE EVALUATION INSTRUCTIONS>

<INPUT DETAILS>

Conversation Log: a record of a conversation between a customer and a bot and/or an agent. 

</INPUT DETAILS>

<EXPECTED OUTPUT>
True
False
</EXPECTED OUTPUT>
"""

class ThreateningPrompt(BasePrompt):
    """Threatening prompt for evaluating legal and regulatory threats in conversations"""
    
    def get_prompt_text(self) -> str:
        return PROMPT
    
    def get_supported_formats(self) -> List[str]:
        return ["segmented", "json", "xml", "transparent"]
    
    def get_post_processor_class(self):
        from post_processors.threatening_postprocessing import ThreateningProcessor
        return ThreateningProcessor
    
    def get_days_lookback(self) -> int:
        return 1
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        dept_name = department.lower().replace(' ', '_')
        return f"threatening_{dept_name}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("threatening", ThreateningPrompt)