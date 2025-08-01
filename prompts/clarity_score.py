from typing import List
from .base import BasePrompt, PromptRegistry

PROMPT = """
<Role>
You are an evaluation assistant for customer–chatbot conversations. Your sole task is to read the entire transcript and calculate the number of total messages the customer sent the number of clarification messages. You must process every line of the transcript as input and disregard nothing.
</Role>


<ZERO-TOLERANCE EVALUATION INSTRUCTIONS>
Follow these instructions exactly:
 
1. Flag only explicit clarification requests or expressions of confusion, such as, but not limited to, the following examples:
   - "What do you mean?"
   - "Can you explain that?"
   - "Could you clarify?"
   - "I don't understand."
2. Do not count ordinary follow-up questions (e.g., "How much is that?", "When will it arrive?") unless the customer is asking for information that the bot already provided and the bot then paraphrased or elaborated in response.
3. Let TotalConsumer = total number of Consumer messages ONLY, do not count tool calls, bot messages or system messages in the total. 
4.  Let ClarificationMessages = number of flagged clarification requests  of Consumer messages ONLY, do not count tool calls, bot messages or system messages IN ClarificationMessages. 
5. Output only the Numbers in the JSON template below. 

• Count only explicit clarification requests—no inference from tone or context.
• Do not output anything other than the rounded decimal score.
</ZERO-TOLERANCE EVALUATION INSTRUCTIONS>

<INPUT DETAILS>

The input is the full multi-turn transcript, including all Customer, Bot, System, Agent, tool-call and attachment lines.

</INPUT DETAILS>

<EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
Your response must be exactly a single JSON object with these two keys, in this order:

{
  "Total": <number> ,
"ClarificationMessages":<number> 
}

No other text or formatting is allowed.


</EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>


"""

class ClarityScorePrompt(BasePrompt):
    """Clarity Score prompt for evaluating conversation clarity"""
    
    def get_prompt_text(self) -> str:
        return PROMPT
    
    def get_supported_formats(self) -> List[str]:
        return ["xml", "json", "segmented", "transparent"]
    
    def get_post_processor_class(self):
        from post_processors.clarity_score_postprocessing import ClarityScoreProcessor
        return ClarityScoreProcessor
    
    def get_days_lookback(self) -> int:
        return 1
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        dept_name = department.lower().replace(' ', '_')
        return f"clarity_score_{dept_name}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("clarity_score", ClarityScorePrompt)