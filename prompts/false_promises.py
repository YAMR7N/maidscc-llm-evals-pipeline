"""
False Promises Analysis Prompt
Analyzes if the bot made any false promises that contradict the system prompt instructions
"""

from .base import BasePrompt, PromptRegistry
from typing import List

class FalsePromisesPrompt(BasePrompt):
    """Prompt for analyzing false promises in bot conversations"""
    
    def get_prompt_text(self, department: str = None) -> str:
        """Return the false promises analysis prompt"""
        return """
<Role>
You are an evaluation assistant for customer–chatbot conversations. Your sole task is to evaluate whether the chatbot promised or performed an action — and whether that action aligns with the system prompt, especially in terms of correct tool usage. Do not flag or evaluate factual errors, general information, or clarification messages. Focus strictly on action-related responses. Your focus is purely to check whether the appropriate tool was called, should’ve or shouldn’t have been called.

</Role>

<ZERO-TOLERANCE EVALUATION INSTRUCTIONS>
Follow these instructions exactly: 

Ignore any line or part of the conversation starting with “Agent”, and focus only on lines starting with “Bot”
Ignore all false information that is not related to tool calling or action taking. We do not care about informational messages, messages describing operational procedures (e.g. “we’ll handle … ) that are general and not actionable by the bot.
In this context, we define promise as the following : “The bot told the customer that the bot itself will take an active action that is tool based and the tool that was triggered is relevant for the specific action that it promised the customer”.
If the bot told the customer that an action by the bot itself will be taken but the bot did not call the relevant tool for this specific action, then flag this as a “RogueAnswer”. If the bot called the proper tool, then flag this as a “NormalAnswer”.
If the bot made no promises (i.e. actionable promises but the bot itself), do not proceed with the analysis and flag the field madePromise as No, and everything else as “N/A”.
</ZERO-TOLERANCE EVALUATION INSTRUCTIONS>


<INPUT DETAILS>

Input is a conversation log (JSON, XML) between a consumer and a maids.cc representative (Agent, Bot, or System). The conversation array includes entries with these fields: sender, type (private, normal, transfer message, or tool), and tool (only present if type is 'tool').

</INPUT DETAILS>

<SystemPromptOfTheBotToEvaluate>

@Prompt@ 

</SystemPromptOfTheBotToEvaluate>

<EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>

Your response will be a list of chatResolution and resolutionJustification. One resolution for each chat. Remember that the chatResolution should be “RogueAnswer” if this chat contains any false promises as described above.


1. The first attribute should be whether a promise was made or not. If no promise was made and the conversation was purely informational with no actionable requests, this field should be No. Otherwise (i.e. an actionable request / promise was made), this field should be Yes
2. The second attribute should be the promise itself that the bot promised the client word for word without any assumptions and inferences
3. The third attribute is “RogueAnswer” or “NormalAnswer” where it indicates whether the chatbot you’re evaluating has made a false promise according to the rules described above. If “madePromise” was No, this field should be “N/A”.
4. The fourth attribute is a justification of the chatResolution, containing the policy that was followed, should’ve been followed, and if necessary, the policy that it contradicts if the chatResolution is “RogueAnswer” as described above. If no such policy exists, output “N/A”. Strictly ignore the agent’s answers. In addition to the policy, you should include an explanation or justification of the thought process and the analysis you did to come up with the result of chatResolution. If “madePromise” was No, the entirety of "resolutionJustification" should be “N/A”.

{
“madePromise” : “”,
“Promise”: , 
"chatResolution": ,
  "resolutionJustification": 
    {
      "policy to be followed: "",
      "explanation": ""
    }
  
}

</EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>



"""
    
    def get_supported_formats(self) -> List[str]:
        """False promises analysis works with JSON format to access system prompts"""
        return ["json"]
    
    def get_post_processor_class(self):
        """Return None - no specific post processor for false promises yet"""
        return None
    
    def get_days_lookback(self) -> int:
        """Use yesterday's data (1 day)"""
        return 1
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        """Generate false promises specific output filename"""
        return f"false_promises_{department}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("false_promises", FalsePromisesPrompt) 