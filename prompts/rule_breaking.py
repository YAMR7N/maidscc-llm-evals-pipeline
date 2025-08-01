"""
Rule Breaking prompt implementation
Handles rule violation detection for different departments
"""

from .base import BasePrompt, PromptRegistry
from typing import List, Dict

class RuleBreakingPrompt(BasePrompt):
    """Rule breaking prompt that adapts to different departments"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.department_prompts = self._load_department_prompts()
    
    def _load_department_prompts(self) -> Dict[str, str]:
        """Load department-specific rule breaking prompts"""
        prompts = {}
        
        try:
            from .rule_breaking_prompt_doc import PROMPT as doc_prompt
            prompts['Doctors'] = doc_prompt
        except ImportError:
            pass
            
        try:
            from .rule_breaking_prompt_ccs import PROMPT as ccs_prompt
            prompts['CC Sales'] = ccs_prompt
        except ImportError:
            pass
            
        try:
            from .rule_breaking_prompt_mvr import PROMPT as mvr_prompt
            prompts['MV Resolvers'] = mvr_prompt
        except ImportError:
            pass
            
        try:
            from .rule_breaking_prompt_mvs import PROMPT as mvs_prompt
            prompts['MV Sales'] = mvs_prompt
        except ImportError:
            pass
        
        return prompts
    
    def get_prompt_text(self, department: str = None) -> str:
        """Return rule breaking prompt text for specific department"""
        if department and department in self.department_prompts:
            return self.department_prompts[department]
        
        # Fallback to generic rule breaking prompt
        return self._get_generic_prompt()
    
    def _get_generic_prompt(self) -> str:
        """Generic rule breaking prompt for departments without specific prompts"""
        return """
<system_message>
# PROMPT TO EVALUATE CHATBOT 

<role_task>
## ROLE AND TASK
You are an expert chat evaluator. Your task is to evaluate a chatbot named "Mia", by identifying any Bot messages that violate the "General Rules for Bot" 

NOTE: The "General Rules for Bot" section is added EXACTLY as it's fed to the Chatbot "Mia" prompt, therefore any rule addressed in FIRST PERSON in this section is referring to "Mia" and not YOU.
</role_task>

<instructions>
## INSTRUCTIONS
1. Read the entire conversation but evaluate only the messages whose sender label starts with "Bot" (e.g., "Bot", "Bot (edited)").  
2. Give every Bot message a sequential index starting from 1.  
3. For each Bot message create exactly one JSON object with the fields:
- "index: the number from step 2  
- "content": the exact text sent by the Bot ("" if the Bot turn is empty)
- violated_rules: an array listing every rule number along with Titles that the message violates; leave it empty ([]) if no rule is violated.
- reasoning: maximum 2 lines explaining the choice. 

4. Gather all objects inside an array called messages and include the original chat_id.  
5. Output only the JSON defined in EXPECTED OUTPUT FORMAT. No extra text.

### Important indexing reminder
- Bot indices must stay in perfect lock-step with the source conversation.
- If a Bot line contains only "[Doc/Image]", an emoji, or is blank, it still gets an index.

### Multiple violations
If a single Bot message breaks more than one rule, list all broken rule numbers along with Titles, in violated_rules.
</instructions>

<EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
{
  "messages": [
    {
      "index": 1,
      "content": "Bot message content here",
      "violated_rules": [],
      "reasoning": "Explanation of evaluation"
    }
  ],
  "chat_id": "conversation_id"
}
</EXPECTED OUTPUT TO BE FOLLOWED UNDER ALL CIRCUMSTANCES>
</system_message>
"""
    
    def get_supported_formats(self) -> List[str]:
        """Rule breaking works with JSON format primarily"""
        return ["json"]
    
    def get_post_processor_class(self):
        """Return the rule breaking post processor"""
        from post_processors.rule_analyzer import RuleAnalyzer
        return RuleAnalyzer
    
    def get_model_config(self) -> Dict:
        """Rule breaking uses o4-mini model"""
        return {
            "temperature": 0.0,
            "max_tokens": 4000
        }
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        """Generate rule breaking specific output filename"""
        dept_prefix = self._get_department_prefix(department)
        return f"rule_breaking_{dept_prefix}_{date_str}.csv"
    
    def _get_department_prefix(self, department: str) -> str:
        """Get department prefix for file naming"""
        prefix_map = {
            'Doctors': 'doc',
            'CC Sales': 'ccs', 
            'MV Resolvers': 'mvr',
            'MV Sales': 'mvs',
            'CC Resolvers': 'ccr',
            'Delighters': 'del',
            'African': 'afr',
            'Ethiopian': 'eth',
            'Filipina': 'fil'
        }
        return prefix_map.get(department, department.lower().replace(' ', '_'))

# Register the prompt
PromptRegistry.register("rule_breaking", RuleBreakingPrompt)
PromptRegistry.register("rb", RuleBreakingPrompt)  # Short alias
