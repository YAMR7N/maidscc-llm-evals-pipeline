"""
Client Suspecting AI prompt implementation
Evaluates whether customers explicitly questioned if they were talking to a bot
"""

from .base import BasePrompt, PromptRegistry
from typing import List

PROMPT = """
<Role>
You are an evaluation assistant for customer–chatbot conversations. Your sole task is to read the entire Conversation Log and decide whether the customer thought they were talking to a bot. Process every message as input and disregard nothing.
</Role>

<ZERO-TOLERANCE EVALUATION INSTRUCTIONS>

Follow these instructions exactly:
1. Identify any Customer message that explicitly questions the agent's humanity (for example "Are you a bot?", "Transfer me to a human", "I want a real person").
2. If at least one such message appears, output True.
3. If no such message appears, output False.
4. Do not infer bot suspicion from tone or context—only explicit references count.
5. Do not generate any additional text or formatting—output only the single value True or False.
</system>
Only explicit bot‐suspicion messages count—no inference from tone or context.
Do not output anything other than True or False.
</ZERO-TOLERANCE EVALUATION INSTRUCTIONS>
<INPUT DETAILS>
Conversation Log is a JSON array of messages, each with fields:
timestamp
sender (e.g. "Customer" or "Bot")
type ("normal", "private", "transfer", or "tool")
content (the message text)
tool (only if type is "tool")
</INPUT DETAILS>
<EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>

True  

False

</EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>


"""

class ClientSuspectingAiPrompt(BasePrompt):
    """Client Suspecting AI prompt for evaluating bot suspicion"""
    
    def get_prompt_text(self) -> str:
        """Return the Client Suspecting AI prompt text"""
        return PROMPT

    def get_supported_formats(self) -> List[str]:
        """Client Suspecting AI works with JSON format primarily"""
        return ["json", "segmented", "transparent"]
    
    def get_post_processor_class(self):
        """Return the Client Suspecting AI post processor"""
        from post_processors.client_suspecting_ai_postprocessing import ClientSuspectingAiProcessor
        return ClientSuspectingAiProcessor
    
    def get_days_lookback(self) -> int:
        """Client Suspecting AI uses yesterday's data (1 day)"""
        return 1
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        """Generate Client Suspecting AI-specific output filename"""
        dept_name = department.lower().replace(' ', '_')
        return f"client_suspecting_ai_{dept_name}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("client_suspecting_ai", ClientSuspectingAiPrompt)