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
In this scenario, you'll act as an agent who works at maids.cc and specializes in reading previous conversations and identifying cases where the client or maid was frustrated or escalated due to the chatbot’s policy-based behavior.
</Role>

<POLICY-DRIVEN ESCALATION EVALUATION INSTRUCTIONS>
Here’s an outline of the services we offer so you can understand the nature of client expectations:
Full-time maid service (Live-in and Live-out):
 We facilitate the hiring of dedicated, professional full-time maids to assist in your home. The housemaids we offer are screened, interviewed, and trained to meet your specific requirements and expectations. We handle everything from selection to transportation — all the client has to do is make the final hire. With our unlimited free replacements, clients are assured of a perfect match.


Visa Processing and Issuing:
 We manage the full visa process for domestic workers, removing paperwork and visits for the client. We promise visa completion within 30 days unless delays occur.


Clients and maids may become frustrated for a wide range of reasons:
Service delay


Poor agent performance


Maid behavior or quality


Replacements


Documentation


Price or payment


Response delays


Misunderstood policies


Being blocked from resolution due to chatbot policy behavior


This prompt focuses specifically on cases where that frustration escalates due to chatbot policy enforcement.
</BACKGROUND CONTEXT>
<POLICY-DRIVEN ESCALATION EVALUATION INSTRUCTIONS>
Examine the full conversation and the system prompt of the bot you’re evaluating.


What qualifies as escalation or frustration:


Persistent Distress
 The customer shows three or more clear and explicit expressions of frustration, anger, or distress about the same issue.
Distress + Direct Escalation Request
 The customer expresses frustration and explicitly asks to speak to a human or escalate.
Severe Escalation Indicators
 Hostile language, threats to cancel, refusal to continue, excessive punctuation or capitalization (e.g., “This is unacceptable!!!”, “You people are a scam???”, “This is illegal”, “This is inappropriate”, “This is not fair”, “I didn’t give you permission to do so”, “I’ve been chasing you!”, “How can a company like this exist”).
Legal Threat Escalation
 If the customer threatens legal action (e.g., contacting the police, filing a complaint with MOHRE, going to court), this should be considered escalation only if the threat is a direct result of a chatbot response that followed a policy from the system prompt.
 If the legal threat was caused by anything outside the bot’s control (e.g., maid behavior, agent actions, document misuse), then do not count it as escalation, and set CustomerEscalation to false and PolicyToCauseEscalation to "N/A".
Emotional or Behavioral Cues
 Clear signs of anger, outrage, or emotional escalation — expressed through tone, punctuation, word choice, or capitalization (e.g., furious, livid, mad, exasperated, boiling, outraged, fuming, “Are you serious???”, “You’ve wasted my time!”, “This is a joke”).
Cancellations or Threats to Cancel
 If the customer expresses a desire to cancel due to poor service or unmet expectations, and the reaction is caused by a policy-following bot reply, treat it as escalation.
What is NOT considered escalation:


Mild or isolated displeasure (e.g., “This is annoying”)


Calm constructive criticism


Survey feedback alone (such as a rage face emoji) without strong supporting language


Any frustration that is only related to insurance policies or coverage explanations


After determining if escalation occurred, review the system prompt of the bot.


Identify which exact policy statement(s) the bot was following when it gave the response that triggered the escalation.


If multiple policies contributed, list them all separated by semicolons.


The policies must be copied EXACTLY as written in the system prompt — including punctuation, symbols, formatting, and line breaks.


If CustomerEscalation is false, set PolicyToCauseEscalation to "N/A" and Justification to "N/A".


If the customer’s frustration is about insurance policy or coverage explanation — regardless of how the bot responded — return "N/A" for both fields and set CustomerEscalation to false.


</POLICY-DRIVEN ESCALATION EVALUATION INSTRUCTIONS>
<SystemPromptOfTheBotToEvaluate>
@Prompt@
</SystemPromptOfTheBotToEvaluate> <INPUT DETAILS>
The input is the full multi-turn transcript, including all Customer, Bot, System, Agent, tool-call, and attachment lines.
</INPUT DETAILS>
<EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
Return only a JSON object with exactly three keys:
json
CopyEdit
{
  "CustomerEscalation": <boolean>,
  "PolicyToCauseEscalation": "<string>",
  "Justification": "<string>"
}

CustomerEscalation: true if the customer explicitly expressed frustration or escalated due to policy enforcement (including legal threats caused by policy); otherwise false.


PolicyToCauseEscalation: the exact policy or policies from the system prompt that caused the frustration or threat, or "N/A" if CustomerEscalation is false.


Justification: if CustomerEscalation is true and PolicyToCauseEscalation is not "N/A", explain clearly how the bot's policy-driven behavior triggered frustration or escalation. If CustomerEscalation is false, return "N/A".


No additional text or commentary beyond the required fields.
</EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>




        """
# """
# <Role>
# You are responsible for evaluating a conversation between a customer and a chatbot designed to handle customer inquiries. Your primary task is to determine if the chatbot's policy based response(as defined in its system prompt of the chatbot you're evaluating which will be provided below) led the customer to express frustration or to escalate.
# </Role>

# <POLICY-DRIVEN ESCALATION EVALUATION INSTRUCTIONS>
# 1. Examine the conversation and the system prompt of the bot you're evaluating. 
 
# 2. If the customer ever expresses frustration, annoyance, or displeasure specifically about a policy driven answer provided by the bot you're evaluating, then mark CustomerEscalation as true.  

# 3. Afterwards you must always read the system prompt of the bot you're evaluating and understand which policy the chatbot you're evaluating was following inside the system prompt that caused him to generate the answer that caused customer escalation. 

# 4. Identify which policy statement(s) from the provided system prompt ("Do X only when the customer does Y") that the bot most likely was following that directly caused the customer's frustration or escalation.  

# 5. If multiple policies contributed, list them all, separated by semicolons.

# 6. The policies must be written in the PolicyToCauseEscalation attribute EXACTLY as written inside the system prompt word by word including commas, symbols and literally anything. They must be identical to what's inside the prompt  

# 7. If the customer never escalated or showed policy-driven frustration, mark CustomerEscalation as false and set PolicyToCauseEscalation to "N/A".
# </POLICY-DRIVEN ESCALATION EVALUATION INSTRUCTIONS>

# <SystemPromptOfTheBotToEvaluate>

# @Prompt@ 

# </SystemPromptOfTheBotToEvaluate>

# <INPUT DETAILS>

# The input is the full multi-turn transcript, including all Customer, Bot, System, Agent, tool-call and attachment lines.

# </INPUT DETAILS>

# <EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
# Return only a JSON object with exactly three keys:

# {
#   "CustomerEscalation": <boolean>,
#   "PolicyToCauseEscalation": "<string>"
#    "Justification": "<string>"
# }
# - CustomerEscalation: true if the customer explicitly expressed frustration or asked for escalation due to policy enforcement; otherwise false.  
# ,.
# - PolicyToCauseEscalation: the exact policy statement(s) from the pasted system prompt that triggered the customer's frustration, or "N/A" if CustomerEscalation is false.

# - Justification: if CustomerEscalation is True and PolicyToCauseEscalation is not "N/A", provide a detailed explanation of the reasoning behind the output. If multiple policies are present, provide an explanation for each case. If CustomerEscalation is False, output "N/A"

# No additional text or commentary beyond the required fields.
# </EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
# """
    
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