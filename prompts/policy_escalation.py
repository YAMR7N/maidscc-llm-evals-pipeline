"""
Policy Escalation Analysis Prompt
Analyzes whether a chatbot's policy-driven response led to customer frustration or escalation
"""

from .base import BasePrompt, PromptRegistry
from typing import List

class PolicyEscalationPrompt(BasePrompt):
    """Prompt for analyzing policy-driven escalations in customer-chatbot conversations"""
    
    def get_prompt_text(self, department: str = None) -> str:
        """Return the policy escalation analysis prompt"""
        return """
<Role>
You are responsible for evaluating a conversation between a customer and a chatbot designed to handle customer inquiries. Your primary task is to determine if the chatbot's policy based response(as defined in its system prompt of the chatbot you're evaluating which will be provided below) led the customer to express frustration or to escalate.
</Role>

<POLICY-DRIVEN ESCALATION EVALUATION INSTRUCTIONS>
1. Examine the conversation and the system prompt of the bot you're evaluating. 
 
2. If the customer ever expresses frustration, annoyance, or displeasure specifically about a policy driven answer provided by the bot you're evaluating, then mark CustomerEscalation as true.  

3. Afterwards you must always read the system prompt of the bot you're evaluating and understand which policy the chatbot you're evaluating was following inside the system prompt that caused him to generate the answer that caused customer escalation. 

4. Identify which policy statement(s) from the provided system prompt ("Do X only when the customer does Y") that the bot most likely was following that directly caused the customer's frustration or escalation.  

5. If multiple policies contributed, list them all, separated by semicolons.

6. The policies must be written in the PolicyToCauseEscalation attribute EXACTLY as written inside the system prompt word by word including commas, symbols and literally anything. They must be identical to what's inside the prompt  

7. If the customer never escalated or showed policy-driven frustration, mark CustomerEscalation as false and set PolicyToCauseEscalation to "N/A".
</POLICY-DRIVEN ESCALATION EVALUATION INSTRUCTIONS>

<SystemPromptOfTheBotToEvaluate>

@Prompt@ 

</SystemPromptOfTheBotToEvaluate>

<INPUT DETAILS>

The input is the full multi-turn transcript, including all Customer, Bot, System, Agent, tool-call and attachment lines.

</INPUT DETAILS>

<EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
Return only a JSON object with exactly three keys:

{
  "CustomerEscalation": <boolean>,
  "PolicyToCauseEscalation": "<string>"
   "Justification": "<string>"
}
- CustomerEscalation: true if the customer explicitly expressed frustration or asked for escalation due to policy enforcement; otherwise false.  
,.
- PolicyToCauseEscalation: the exact policy statement(s) from the pasted system prompt that triggered the customer's frustration, or "N/A" if CustomerEscalation is false.

- Justification: if CustomerEscalation is True and PolicyToCauseEscalation is not "N/A", provide a detailed explanation of the reasoning behind the output. If multiple policies are present, provide an explanation for each case. If CustomerEscalation is False, output "N/A"

No additional text or commentary beyond the required fields.
</EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
"""
    
    def get_supported_formats(self) -> List[str]:
        """Policy escalation analysis works with XML format to access system prompts"""
        return ["xml"]
    
    def get_post_processor_class(self):
        """Return the policy escalation post processor"""
        from post_processors.policy_escalation_postprocessing import PolicyEscalationProcessor
        return PolicyEscalationProcessor
    
    def get_days_lookback(self) -> int:
        """Use yesterday's data (1 day)"""
        return 1
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        """Generate policy escalation specific output filename"""
        dept_name = department.lower().replace(' ', '_')
        return f"policy_escalation_{dept_name}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("policy_escalation", PolicyEscalationPrompt) 