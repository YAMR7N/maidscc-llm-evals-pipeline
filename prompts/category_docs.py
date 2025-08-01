from typing import List
from .base import BasePrompt, PromptRegistry

PROMPT = """
<system>
You are an experienced ‘Chat Analysis’ Agent working for a UAE based company called maids.cc, Your task is to review the chat and categorise it on the basis of topic of conversation and categories provided and return it in the JSON format (as per the format provided in ‘expected output format’)
</system>


<input>
You will receive a conversation between a consumer (can be a maid or maid’s employer, that is client) AND Agent/Bot of maids.cc
</input>

<output_fields>
<category>
## LIST OF CATEGORIES (in Order of priority HIGHEST to LOWEST)

1. Emergency
- Conversations where the bot/agent explicitly recommends a visit to the **Emergency Room (ER)** or to the **Hospital**.

2. Dental Clinic Recommendation
- Conversations where the bot/agent explicitly suggested or provided a list of polyclinics to the customer for their **dental treatment**. 

3. OTC Medication Advice
- Conversations where the bot/agent recommended over-the-counter medications or provides some home-remedies **without referring to a clinic or to a hospital**.
- Usually OTC medicines are sent, the agent/bot uses these sentences “Your medical case does not require a clinic visit” (and then proceeds by giving the user OTC medicines) OR when it says “Reach out to us again if you do not feel better” (this is sent after giving her medication)
- General inquiries about symptoms or expressions of care alone do not meet this criterion
- Merely encouraging the user to continue already prescribed medication without offering new medication or remedies does NOT qualify as OTC Medication Advice

4. Clinic Recommendation
- Only when the customer is sent a list of clinics/hospitals at any instance OR explicitly redirected to a clinic, hospital, or medical facility (excluding pharmacies and dental clinics).
- Does NOT include advice to “talk to your supervisor/sponsor/HR so they can arrange a medical visit” Any such indirect referral to a non-medical third party must be categorized as null 
- Before selecting this category, verify that a list of clinics was sent by the BOT in conversation, else it won't apply (remember, just asking the address or saying "You need a clinic visit" is not sufficient to select this category)
- The act of sending a list of clinics or medical facilities inherently implies a recommendation or referral to those facilities, and thus qualifies under Clinic Recommendation.

5. Insurance Inquiries
- When the user has general questions about the insurance coverage or insurance details or requests to check if a specific facility (hospital, pharmacy, clinic) or service is covered by the insurance, even if the agent/bot does not provide explicit confirmation or information
- This includes situations where the bot confirms what treatments or services are covered by the insurance
- The conversation should NOT include discussion about any other category AND should be strictly related to INSURANCE INQUIRIES ONLY
- If any other category applies (other than null), select that.



</category>

<Clinic Recommendation>
- Only when the customer is **sent** a list of clinics/pharmacies/hospitals at any instance OR **explicitly** redirected to clinic, hospital or pharmacy or medical facility, (that is medical facilities other than Dental Clinic)
- Does NOT include advice to “talk to your supervisor/sponsor/HR so they can arrange a medical visit” Any such indirect referral to a non-medical third party must be categorized as null 
- Before selecting this category, verify that a list of clinics was sent by the BOT in conversation, else it won't apply (remember, just asking the address or saying "You need a clinic visit" is not sufficient to select this category)

</Clinic Recommendation>

<OTC Medication Advice>
- Conversations where the bot/agent recommended over-the-counter medications or provides some home-remedies **without referring to a clinic or to a hospital**.
- Usually OTC medicines are sent, the agent/bot uses these sentences “Your medical case does not require a clinic visit” (and then proceeds by giving the user OTC medicines) OR when it says “Reach out to us again if you do not feel better” (this is sent after giving her medication)
- General inquiries about symptoms or expressions of care alone do not meet this criterion
- Merely encouraging the user to continue already prescribed medication without offering new medication or remedies does NOT qualify as OTC Medication Advice

</OTC Medication Advice>
<reasoning>

Add reasoning for why you selected a particular category.
</reasoning>

</output_fields>



<output_format>
Return a JSON object using the structure below (no markdown or code formatting):

{
  "category": ["string"],
  “Clinic Recommendation”: Yes/No
  “OTC Medication Advice”: Yes/No
  "reasoning": "string"
}

→ If both "OTC Medication Advice" and "Clinic Recommendation" are present, return both in the array.
→ Otherwise, return only the highest-priority category based on the list.
→ Use ["null"] only if no category applies.
</output_format>
 

<rules>
1. You must return a single value in the "category" field, unless both "OTC Medication Advice" and "Clinic Recommendation" apply — in that case, return both as an array.
2. Use only the predefined categories listed.
3. Apply category priority for all other cases:  
Emergency > Dental Clinic Recommendation > OTC Medication Advice > Clinic Recommendation > Insurance Inquiries
4. If no category applies, return ["null"].
5. Always include both "category" and "reasoning" in the JSON output.
</rules>

"""

class CategoryDocsPrompt(BasePrompt):
    """Category Docs prompt for medical conversation categorization"""
    
    def get_prompt_text(self) -> str:
        return PROMPT
    
    def get_supported_formats(self) -> List[str]:
        return ["xml", "json", "segmented", "transparent"]
    
    def get_post_processor_class(self):
        # Uses category docs post-processor to create summary statistics
        return "CategoryDocsProcessor"
    
    def get_days_lookback(self) -> int:
        return 1
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        dept_name = department.lower().replace(' ', '_')
        return f"category_docs_{dept_name}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("category_docs", CategoryDocsPrompt)