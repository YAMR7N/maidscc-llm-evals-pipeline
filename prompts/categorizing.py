"""
Categorizing Analysis Prompt
Categorizes the topic that led to chat transfer or agent intervention
"""

from .base import BasePrompt, PromptRegistry
from typing import List

class CategorizingPrompt(BasePrompt):
    """Prompt for categorizing topics that led to chat transfers"""
    
    def get_prompt_text(self, department: str = None) -> str:
        """Return the categorizing analysis prompt"""
        return """
<Role>
You are an evaluation assistant for customer–chatbot conversations. Your sole task is to read the entire transcript and identify exactly the moment when the chat is taken over—either by an agent intervening without a transfer tool, or by the transfer_conversation tool routing to MV_Resolver_Seniors—and then categorize only the topic that led to the transfer or the intervention of the conversation..
</Role>

<ZERO-TOLERANCE EVALUATION INSTRUCTIONS>
Follow these instructions exactly:

Scan the full multi-turn transcript.
Stop at the first point where either:
The transfer_conversation tool is triggered, routing to MV_Resolver_Seniors; or  
An agent intervenes and takes over the chat without using the transfer_conversation tool.
If no transfer or intervention was done during the conversation, flag it as "N/A"
Identify the customer requests that preceded that takeover point.
Refer to the system prompt's category list and select exactly one category corresponding to that request:  
The categories are as follows: [Maid Reaching From Client Phone Number Case,Hiring a New Maid, Maid Rights Policies, Involuntary Loss of Employment (ILOE) Unemployment Insurance Explanation, Maid Replacement Policies, Maid Dispute Handling Policy, Maid Visa Transfer and Referral Policies, Travel Policies, Retrieving Customer and Maid Info, Cancellation, Salary&ATM, Visa Process Status Policies, Payments, Document Sending]
Do not consider any other parts of the conversation.
Do not infer beyond the explicit request.
Output only the JSON object specified below, with no additional text or fields.
</ZERO-TOLERANCE EVALUATION INSTRUCTIONS>

<SystemPromptOfTheBotToEvaluate>

@Prompt@ 

</SystemPromptOfTheBotToEvaluate>

<INPUT DETAILS>

The input is the full multi-turn transcript, including all Customer, Bot, System, Agent, tool-call and attachment lines.

</INPUT DETAILS>

<EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>

Your response must match exactly this JSON format and include only these fields:

{
  "InterventionOrTransfer": "",
  "Category": "",
  "Justification": ""
}

Where:
"InterventionOrTransfer" is "Intervention" if an agent took over without the transfer_conversation tool, or "Transfer" if the transfer_conversation tool was used to route to MV_Resolver_Seniors. If no transfer was done "InterventionOrTransfer" should be "N/A"
"Category" is one of:  
  [Maid Reaching From Client Phone Number Case, Hiring a New Maid, Maid Rights Policies, Involuntary Loss of Employment (ILOE) Unemployment Insurance Explanation, Maid Replacement Policies, Maid Dispute Handling Policy, Maid Visa Transfer and Referral Policies, Travel Policies, Retrieving Customer and Maid Info, Cancellation, Salary&ATM, Visa Process Status Policies, Payments, Document Sending]. If no transfer was done, "Category" should be "N/A".
"Justification": Provide a clear, specific, and detailed explanation for the chosen category. Your justification needs to include the category and subcategories (if applicable), along with a clear reasoning of why this is the chosen category, and a direct citing of the chosen category regarding the decision that you made.


</EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
"""
    
    def get_supported_formats(self) -> List[str]:
        """Categorizing analysis works with JSON format to access system prompts"""
        return ["json"]
    
    def get_post_processor_class(self):
        """Return the categorizing post processor"""
        from post_processors.categorizing_postprocessing import CategorizingProcessor
        return CategorizingProcessor
    
    def get_days_lookback(self) -> int:
        """Use yesterday's data (1 day)"""
        return 1
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        """Generate categorizing specific output filename"""
        return f"categorizing_{department}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("categorizing", CategorizingPrompt) 