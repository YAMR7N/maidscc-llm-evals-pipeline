"""
Loss of Interest prompt implementation
Dynamically adjusts prompt based on department and last skill in the conversation
Supports multiple departments with skill-based prompt selection
"""

from .base import BasePrompt, PromptRegistry
from typing import List, Dict, Optional

class LossOfInterestPrompt(BasePrompt):
    """Dynamic prompt that adapts based on department and last skill"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.department_prompts = self._load_department_prompts()
    
    def _load_department_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load prompts organized by department and skill"""
        return {
            "filipina": self._load_filipina_prompts(),
            # Add more departments here in the future
            # "african": self._load_african_prompts(),
            # "ethiopian": self._load_ethiopian_prompts(),
        }
    
    def _load_filipina_prompts(self) -> Dict[str, str]:
        """Load Filipina-specific skill prompts (case-insensitive matching)"""
        return {
            # Outside Pending Facephoto
            "filipina_outside_pending_facephoto": """<system>
  <GeneralContext>
    You are analyzing full WhatsApp conversations between a Filipino maid applicant and the maids.at chatbot. Each conversation includes the entire application flow — from initial contact through photo request. The maid must confirm willingness to join or state that her contract ends within 40 days to proceed to profile submission.


    Your goal is to determine why the maid did not provide her profile picture. The bot may have requested the photo multiple times or only once — this does not change the task. Analyze the entire conversation to find the most likely reason.
  </GeneralContext>


  <Instructions>
  1. Analyze the full chat history. Do not base conclusions solely on the last message or photo request.
  2. Identify the most likely reason for why the profile picture was not submitted.
  3. If a delay is due to a fixed future event (e.g., contract expiry, vacation, ticket, documents), treat it as the primary reason — even if the applicant says they'll send the photo "later."
  4. Only use "Stopped Answering – No Reason Specified" if:
     - The maid did not reply to the face photo request,
     - And no other cause is implied or stated earlier in the chat.
  5. Subcategory Guidelines:
     5.1. Do not create a new subcategory unless absolutely necessary. Review all existing subcategories first to ensure none apply.
     5.2. If a new subcategory must be created:
         - It must express only one clear idea (never combine multiple causes).
         - It must be short, task-specific, and logically reusable.
         - It must fit cleanly under an existing Reason Category.
         - Do not use slashes, hyphens, abstract concepts, or emotional/psychological terms.
   6.  Always prefer specific over generic reasons.
</Instructions>



  <OutputFormat>
    OEC Country: [Maid's current working country]
    Reason Category: [From categories below]
    Reason Subcategory: [Most specific applicable subcategory]
    Explanation: [Concise explanation of why the maid did not provide her profile picture]
  </OutputFormat>


  <ReasonCategories>
    1. Legitimacy Issues
      - Suspected Scam
      - Lack of Branch in Philippines


    2. Pending Employer Release
      - Payment Required
      - Waiting Replacement
      - Waiting Contract Expiry
      - Waiting Exit Documents
      - Waiting Employer's Ticket
      - Pending Discussion with Employer


    3. Financial Concerns
      - Salary
      - Cash Advance
      - Deductions Objection
      - Application Fees / Medical


    4. Cancelled
      - Found Another Job
      - No Reason Specified
      - Family Disapproval


    5. Alternative Job Preferences
      - Seeking Another Position
      - Annual Vacation
      - Doesn't want to work in UAE


    6. Stopped Answering
      - Stopped Answering – No Reason Specified
      - Will Share Later


    7. Misunderstanding in Application Process
      - Processing Timeline Concerns
      - Applying for someone else
      - Doesn't like the hustle process
      - Thinks She's Blacklisted


    8. Vacation Plans
      - Vacation Plans


    9. Application Concerns
      - Not eligible
      - Not Ready


    10. Other
      - Other
  </ReasonCategories>


  <ReasonSubcategoryExplanations>
    <SuspectedScam>
      Only if the maid is showing she does not want to share her face photo because she's scared, or asking a lot about our legitimacy or suspected we're scam. Or if the maid asks to speak to human instead of computer / AI.
    </SuspectedScam>
    <LackOfBranchInPhilippines>
      Only if the maid is worried or hesitant because we don't have a physical branch in the Philippines.
    </LackOfBranchInPhilippines>


    <PaymentRequired>
      Only if the maid has not yet shared her profile picture because her employer or agency is requesting payment for releasing her.
    </PaymentRequired>
    <WaitingReplacement>
      Only if the maid mentions that she will join us after her replacement arrives.
    </WaitingReplacement>
    <WaitingContractExpiry>
      Only if the maid says anything similar to: "When my contract finishes" or "After I finish here" or "When I'm ready."
    </WaitingContractExpiry>
    <WaitingExitDocuments>
      Only when the maid mentions that she's waiting for her exit visa or release/exit documents from her employer to send her profile picture.
    </WaitingExitDocuments>
    <WaitingEmployersTicket>
      Only if the maid mentions that she is waiting for her employer to book her a ticket, and she's planning to join us instead of going home to the Philippines first.
    </WaitingEmployersTicket>
    <PendingDiscussionWithEmployer>
      Only if the maid says she will first talk to her employer or needs to check with them before proceeding.
    </PendingDiscussionWithEmployer>


    <Salary>
      Only if the maid did not like the salary.
    </Salary>
    <CashAdvance>
      Only if the maid didn't like that there is no cash assistance/advance, signing bonus, or pocket money.
    </CashAdvance>
    <DeductionsObjection>
      Only if the maid shows concerns about the starting salary being 1500 AED.
    </DeductionsObjection>
    <ApplicationFeesMedical>
      When the maid mentions she does not have enough money to apply.
    </ApplicationFeesMedical>


    <FoundAnotherJob>
      Only if the applicant clearly says they have or are applying to another job or employer now, or thanks us for the offer while indicating they accepted another job after applying.
    </FoundAnotherJob>
    <NoReasonSpecified>
      Only if the maid explicitly said she wants to cancel her application with us and there is no reason at all that can be analyzed.
    </NoReasonSpecified>
    <FamilyDisapproval>
      Only if the maid does not share a face photo because her family does not want her to work abroad or cross country.
    </FamilyDisapproval>


    <SeekingAnotherPosition>
      Only if the maid does not provide her face photo because she wants a different job than a housemaid. (Examples include: cleaner / live out / part time / nurse / nanny…)
    </SeekingAnotherPosition>
    <AnnualVacation>
      Only if the maid does not provide her face photo since she wants an annual vacation instead of every 2 years.
    </AnnualVacation>
    <DoesntWantToWorkInUAE>
      Only if she mentions she herself does not want a job in UAE.
    </DoesntWantToWorkInUAE>


    <StoppedAnsweringNoReasonSpecified>
      Only if the maid does not reply at all to the bot asking her to share her face photo nor has any conversations or messages prior that show why she did not share. This should only be classified if the maid actually does not answer at all with no other apparent reason.
    </StoppedAnsweringNoReasonSpecified>
    <WillShareLater>
      Only if the maid said she will share later her face photo, but never did. This should be labeled only if there is no other apparent reason why she has not yet shared it yet.
    </WillShareLater>


    <ProcessingTimelineConcerns>
      Only if the applicant asks how long the process takes or how long we need to process their documents/visa, and does not provide a date even when asked.
    </ProcessingTimelineConcerns>
    <ApplyingForSomeoneElse>
      Only if the maid does not provide a copy of her face photo since she is asking for a friend or relative.
    </ApplyingForSomeoneElse>
    <DoesntLikeHustleProcess>
      Only if the maid does not like or has serious concerns about how we're going to hire her from her current country to Dubai (the hustling process), or is scared from cross-country.
    </DoesntLikeHustleProcess>
    <ThinksShesBlacklisted>
      Only if the maid has not provided her profile picture due to concerns that she may no longer be eligible for a Dubai visa—such as being banned or having previous issues with her former sponsor in the UAE.
    </ThinksShesBlacklisted>


    <VacationPlans>
      Only if the applicant explicitly mentions an intention to go on vacation or return to their home country (e.g., "I will go home first," "after my vacation," "returning to Philippines on X date", "I have reentry", "do you accept reentry") at any point in the chat history; and subsequently doesn't indicate a change of plan to join directly or via cross-country from their current country without returning home first.
    </VacationPlans>


    <NotEligible>
      Only if the maid is not eligible to join since she does not meet our age limit.
    </NotEligible>
    <NotReady>
      Only if the applicant seems like she's still not yet ready to provide us with her profile picture such as when she says that she'll share her profile picture when she's ready, and there is no other apparent reason in the chat. If you see another reason, prioritize it over Not Ready.
    </NotReady>


    <Other>
      Only if you're unsure what to classify the maid, and she doesn't match or is not close to any of the above categories.
    </Other>
  </ReasonSubcategoryExplanations>
</system>""",
            
            # Outside Pending Passport
            "filipina_outside_pending_passport": """<system>
  <GeneralContext>
    You are analyzing full WhatsApp conversations between a Filipino maid applicant and the maids.at chatbot. Each conversation includes the full application flow — from the moment the maid first applied, submitted her profile picture, and reached the stage where the chatbot requested her passport picture.

    To reach the passport stage, the maid must have provided her profile picture and either confirmed her willingness to join us or mentioned that her current contract will end within 40 days.

    Your task is to determine the most likely reason why the maid did not provide her passport picture. Analyze the entire conversation for context — the reason may appear earlier in the conversation, not just after the request. Do not stop at "unresponsive"; always look for the underlying blocker.
  </GeneralContext>

  <Definitions>
    1. "Active OEC" means a valid Overseas Employment Certificate.
    2. "Null" file means the maid submitted a document, but it was expired — this does not imply she's asking for help.
  </Definitions>

  <Instructions>
    1. Analyze the full chat history. Do not base conclusions solely on the last message or passport request.
    2. Identify the most likely reason for why the passport picture was not submitted.
    3. If a delay is due to a fixed future event (e.g., contract expiry, vacation, ticket, documents), treat it as the primary reason — even if the applicant says they'll send the passport "later."
    4. Only use "Stopped Answering – No Reason Specified" if:
       - The maid did not reply to the passport photo request,
       - And no other cause is implied or stated earlier in the chat.
    5. Subcategory Guidelines:
       5.1. Do not create a new subcategory unless absolutely necessary. Review all existing subcategories first to ensure none apply.
       5.2. If a new subcategory must be created:
           - It must express only one clear idea (never combine multiple causes).
           - It must be short, task-specific, and logically reusable.
           - It must fit cleanly under an existing Reason Category.
           - Do not use slashes, hyphens, abstract concepts, or emotional/psychological terms.
       5.3. If a maid cannot proceed due to employer observation, control, or restrictions on communication, classify the case under an appropriate employer-related subcategory (e.g., Pending Discussion with Employer).
  </Instructions>

  <OutputFormat>
    OEC Country: [Maid's current working country]
    Reason Category: [From categories below]
    Reason Subcategory: [Most specific applicable subcategory]
    Explanation: [Concise explanation of why the maid did not provide her passport picture]
  </OutputFormat>

  <ReasonCategories>
    1. Legitimacy Issues
      - Suspected Scam
      - Lack Of Branch in Philippines

    2. Pending Employer Release
      - Payment Required
      - Waiting Replacement
      - Waiting Contract Expiry
      - Waiting Exit Documents
      - Waiting Employer's Ticket
      - Pending Discussion with Employer
      - Not Ready

    3. Financial Concerns
      - Salary
      - Cash Advance
      - Deductions Objection
      - Application Fees / Medical

    4. Cancelled
      - Found Another Job
      - No Reason Specified
      - Family Disapproval

    5. Alternative Job Preferences
      - Seeking Another Position
      - Annual Vacation
      - Doesn't want to work in UAE

    6. Stopped Answering
      - Stopped Answering – No Reason Specified
      - Will Share Later

    7. Misunderstanding in Application Process
      - Processing Timeline Concerns
      - Applying for someone else
      - Doesn't like the hustle process
      - Thinks She's Blacklisted

    8. Vacation Plans
      - Vacation Plans

    9. Passport with Employer
      - Passport with Employer

    10. Other
      - Other
  </ReasonCategories>

  <ReasonSubcategoryExplanations>
    <SuspectedScam>
      Only if the maid is showing she does not want to share her passport picture because she's scared, or asking a lot about our legitimacy or suspected we're scam. Or if the maid asks to speak to human instead of computer / AI.
    </SuspectedScam>
    <LackOfBranchInPhilippines>
      Only if the maid is worried or hesitant because we don't have a physical branch in the Philippines.
    </LackOfBranchInPhilippines>

    <PaymentRequired>
      Only if the maid has not yet shared her passport picture because her employer or agency is requesting payment for releasing her.
    </PaymentRequired>
    <WaitingReplacement>
      Only if the maid mentions that she will join us after her replacement arrives.
    </WaitingReplacement>
    <WaitingContractExpiry>
      Only if the maid says anything similar to: "When my contract finishes" or "After I finish here" or "When I'm ready."
    </WaitingContractExpiry>
    <WaitingExitDocuments>
      Only when the maid mentions that she's waiting for her exit visa or release/exit documents from her employer to send her passport picture.
    </WaitingExitDocuments>
    <WaitingEmployersTicket>
      Only if the maid mentions that she is waiting for her employer to book her a ticket, and she's planning to join us instead of going home to the Philippines first.
    </WaitingEmployersTicket>
    <PendingDiscussionWithEmployer>
      Only if the maid says she will first talk to her employer or needs to check with them before proceeding.
    </PendingDiscussionWithEmployer>
    <NotReady>
      Only if the applicant seems like she's still not yet ready to provide us with her passport picture such as when she says that she'll share her passport picture when she's ready, and there is no other apparent reason in the chat. If you see another reason, prioritize it over Not Ready.
    </NotReady>

    <Salary>
      Only if the maid did not like the salary.
    </Salary>
    <CashAdvance>
      Only if the maid didn't like that there is no cash assistance/advance, signing bonus, or pocket money.
    </CashAdvance>
    <DeductionsObjection>
      Only if the maid shows concerns about the starting salary being 1500 AED.
    </DeductionsObjection>
    <ApplicationFeesMedical>
      When the maid mentions she does not have enough money to apply.
    </ApplicationFeesMedical>

    <FoundAnotherJob>
      Only if the applicant clearly says they have or are applying to another job or employer now, or thanks us for the offer while indicating they accepted another job after applying.
    </FoundAnotherJob>
    <NoReasonSpecified>
      Only if the maid explicitly said she wants to cancel her application with us and there is no reason at all that can be analyzed.
    </NoReasonSpecified>
    <FamilyDisapproval>
      Only if the maid does not share a passport photo because her family does not want her to work abroad or cross country.
    </FamilyDisapproval>

    <SeekingAnotherPosition>
      Only if the maid does not provide her passport photo because she wants a different job than a housemaid. (Examples include: cleaner / live out / part time / nurse / nanny…)
    </SeekingAnotherPosition>
    <AnnualVacation>
      Only if the maid does not provide her passport photo since she wants an annual vacation instead of every 2 years.
    </AnnualVacation>
    <DoesntWantToWorkInUAE>
      Only if she mentions she herself does not want a job in UAE.
    </DoesntWantToWorkInUAE>

    <StoppedAnsweringNoReasonSpecified>
      Only if the maid does not reply at all to the bot asking her to share her passport photo nor has any conversations or messages prior that show why she did not share. This should only be classified if the maid actually does not answer at all with no other apparent reason.
    </StoppedAnsweringNoReasonSpecified>
    <WillShareLater>
      Only if the maid said she will share later her passport photo, or that she's not at home now, but never shared it. This should be labeled only if there is no other apparent reason why she has not yet shared it yet.
    </WillShareLater>

    <ProcessingTimelineConcerns>
      Only if the applicant asks how long the process takes or how long we need to process their documents/visa, and does not provide a date even when asked.
    </ProcessingTimelineConcerns>
    <ApplyingForSomeoneElse>
      Only if the maid does not provide a copy of her passport photo since she is asking for a friend or relative.
    </ApplyingForSomeoneElse>
    <DoesntLikeHustleProcess>
      Only if the maid does not like or has serious concerns about how we're going to hire her from her current country to Dubai (the hustling process), or is scared from cross-country.
    </DoesntLikeHustleProcess>
    <ThinksShesBlacklisted>
      Only if the maid has not provided her passport picture due to concerns that she may no longer be eligible for a Dubai visa—such as being banned or having previous issues with her former sponsor in the UAE.
    </ThinksShesBlacklisted>

    <VacationPlans>
      Only if the maid hasn't yet provided a date because she's asking a lot about joining from the Philippines, or joining using reentry, or said she wants to go on vacation/home first.
    </VacationPlans>

    <PassportWithEmployer>
      Only when the applicant doesn't send us her passport picture because her employer is holding her passport.
    </PassportWithEmployer>

    <Other>
      Only if you're unsure what to classify the maid, and she doesn't match or is not close to any of the above categories.
    </Other>
  </ReasonSubcategoryExplanations>
</system>""",
            
            # Outside UAE Pending Joining Date
            "filipina_outside_uae_pending_joining_date": """<system>
  <GeneralContext>
    You are reviewing chat conversations between a Filipino maid applicant and the maids.at chatbot (Phoebe). The applicant is a Filipina currently residing in a country outside the UAE and Philippines (examples: KSA, Kuwait, Oman, Qatar, Bahrain, Malaysia…). She was asked to provide her expected joining date but did not provide one.

    Your task is to analyze the full chat dialogue and determine why the applicant did not provide her expected joining date.
  </GeneralContext>

  <Instructions>
    1. Analyze the entire conversation, including indirect replies in Tagalog or informal English.
    2. Determine the most likely reason the maid did not provide her expected joining date.
    3. Always select one — and only one — subcategory that logically belongs to its Reason Category.
    4. If no clear reason is found, classify as "Other" under both Reason Category and Reason Subcategory.
    5. Do not leave any field blank — output must always include Country, Reason Category, Reason Subcategory, and Explanation.
    6. Do not generate multiple categories or subcategories per case.
    7. Do not infer vacation intent based only on the bot's repeated reminders (e.g., "text us before your employer books a ticket"). The maid must mention it herself.
    8. Prioritize specific or implied reasons from the chat over vague or ambiguous explanations.
    9. Subcategory Naming Rules:
        9.1 Use natural English phrasing with proper spacing and punctuation (e.g., "Waiting Contract Expiry", not "WaitingContractExpiry").
        9.2 Do not use PascalCase, camelCase, snake_case, or paraphrased formats.
        9.3 Use only the subcategory labels exactly as written in the <ReasonSubcategoryExplanations> block.
  </Instructions>

  <OutputFormat>
    Country: [The country where the applicant is currently located]
    Reason Category: [Select the correct main category]
    Reason Subcategory: [Select the one matching subcategory from the selected category]
    Explanation: [1–2 sentence explanation describing why the maid did not provide the joining date, based on her chat]
  </OutputFormat>

  <ReasonCategories>
    1. Pending Employer Release  
    2. Financial Concerns  
    3. Alternative Job Preferences  
    4. Cancelled  
    5. Legitimacy Issues  
    6. Vacation Plans  
    7. Stopped Answering – No Reason Specified  
    8. Date Provided Already  
    9. Application Concerns  
    10. Other
  </ReasonCategories>

  <ReasonSubcategoryExplanations>
    <Payment Required>
      Only if the maid has not yet provided an expected date to join because her employer or agency is requesting payment for releasing her.
    </Payment Required>
    <Waiting Replacement>
      Only if the maid mentions that she will join us after her replacement arrives.
    </Waiting Replacement>
    <Waiting Contract Expiry>
      Only if the maid says anything similar to: "When my contract finishes" or "After I finish here" or "when I'm ready" — and never provides a specific month/year. If no other cause is found, this becomes the default explanation.
    </Waiting Contract Expiry>
    <Waiting Exit Documents>
      Only when the maid mentions that she's waiting for her exit visa or release/exit documents from her employer to join us.
    </Waiting Exit Documents>
    <Waiting Employer's Ticket>
      Only if the maid mentions that she is waiting for her employer to book her a ticket, and she's planning to join us directly (not going home to the Philippines first).
    </Waiting Employer's Ticket>
    <Pending Discussion with Employer>
      Only if the maid says she needs to talk to her employer before providing a joining date.
    </Pending Discussion with Employer>
    <Not Ready>
      Only if the applicant seems like she's still not yet ready to provide us a date, and no other apparent reason is found in the chat.
    </Not Ready>

    <Salary>
      Only if the maid did not like the salary.
    </Salary>
    <Cash Advance>
      Only if the maid didn't like that there is no cash assistance/advance, signing bonus, or pocket money.
    </Cash Advance>
    <Deductions Objection>
      Only if the maid shows concerns about the starting salary being 1500 AED.
    </Deductions Objection>

    <Seeking Another Job>
      Only if the maid does not provide an expected date to join because she wants a different job than housemaid. (Examples include: cleaner, live out, part-time, nurse, etc.)
    </Seeking Another Job>
    <Annual Vacation>
      Only if the maid does not provide an expected date to join since she wants an annual vacation instead of every 2 years.
    </Annual Vacation>

    <Found Another Job>
      Only if the applicant clearly says they have another job or employer now, or thanks us for the offer while indicating they accepted another job after applying.
    </Found Another Job>
    <No Reason Specified>
      Only if the maid explicitly said she wants to cancel her application with us and provides no analyzable reason.
    </No Reason Specified>

    <Suspected Scam>
      Only if the maid is showing she does not want to share her joining date because she's scared, or asking a lot about our legitimacy or suspected we're a scam. Or if the maid asks to speak to a human instead of computer / AI.
    </Suspected Scam>
    <Lack of Branch in Philippines>
      Only if the maid is unsure or hesitant because we do not have a branch in the Philippines.
    </Lack of Branch in Philippines>

    <Vacation Plans>
      Only if the maid hasn't yet provided a date because she's asking a lot about joining from the Philippines, using reentry, or has said she plans to go home for vacation first.
    </Vacation Plans>

    <Stopped Answering – No Reason Specified>
      Only if the maid does not answer at all after being asked about the joining date, and there is no other mention or hint of a reason.
    </Stopped Answering – No Reason Specified>

    <Date Provided Already>
      Use this if the maid mentions a specific contract expiry date (month/year), flight ticket date, or any relevant date of leaving her employer's house. Prioritize this over all other reasons.
    </Date Provided Already>

    <Processing Timeline Concerns>
      Only if the applicant asks how long the process takes or how long we need to process their documents/visa, and does not provide a date even when asked.
    </Processing Timeline Concerns>
    <Not Eligible>
      Only if the maid is not eligible to join since she does not meet our age limit.
    </Not Eligible>
    <Applying for Someone Else>
      Only if the maid does not provide an expected date to join because she is asking on behalf of a friend or relative.
    </Applying for Someone Else>
    <Maid in Philippines>
      Use this if the maid seems to be currently in the Philippines, even though the dataset should only contain maids outside UAE and Philippines.
    </Maid in Philippines>
    <Maid in UAE>
      Use this if the maid seems to be currently in the UAE, despite the dataset's expectation that she is in a third country.
    </Maid in UAE>

    <Other>
      Only if you're unsure what to classify the maid, and she doesn't match or come close to any of the defined categories.
    </Other>
  </ReasonSubcategoryExplanations>
</system>""",
            
            # In Philippines Pending Valid Visa
            "filipina_in_phl_pending_valid_visa": """<system>
  <GeneralContext>
    You are reviewing chat conversations between a Filipino maid applicant and the maids.at chatbot. Each applicant is currently located in the Philippines and was asked to provide a photo of their active visa (residency, iqama, or re-entry permit) from another country in order to qualify for employment.

    The applicants in this batch did not send the required visa photo. Your task is to analyze all the chat dialogue of each maid's User ID and determine the most likely reason why she did not send it. This output will be used to analyze drop-off points in the hiring funnel and improve recruitment flow.
  </GeneralContext>

  <Instructions>
    1. Analyze all chats related to each maid as a single case.
    2. Determine the most likely reason the maid did not send a photo of her visa.
    3. If the reason cannot be determined, use the category: "Other".
    4. Extract the last working country (OEC Country) based on what the maid said (e.g., "I last worked in Saudi Arabia" → OEC Country = Saudi Arabia).
    5. The subcategory must always logically belong to its selected Reason Category.
    6. Output must never include multiple subcategories or categories at once.
    7. Consider the full context of the conversation(s) before concluding.
    8. Focus on why the maid didn't send the visa — not whether the bot asked (assume the request was made).
    9. Use concise and evidence-based explanations (reference what the maid said or did).
    10. Return only the completed outcome specified.
    11. Do not create new categories. If necessary, you may create new subcategories under existing categories — but never create duplicate or redundant labels.
    12. Subcategory Naming Rules:
        12.1. Use natural English phrasing with proper spacing and punctuation (e.g., "No Active Visa", not "NoActiveVisa").
        12.2. Do not return PascalCase, camelCase, snake_case, or hyphenated formats.
        12.3. Always use the exact subcategory labels from the <ReasonSubcategoryExplanations> block.
        12.4. Never paraphrase or merge concepts across multiple labels (e.g., do not invent labels like "Specific Working Arrangement Preference" or "Unclear Document Requirements").
  </Instructions>

  <OutputFormat>
    OEC Country: [The maid's last working country based on her chat — the last country she was in before returning to the Philippines]
    Reason Category: [Choose the correct main category]
    Reason Subcategory: [Choose the one most likely subcategory within the category]
    Explanation: [1–2 sentence explanation describing why the maid did not submit her active visa document, based on her chat history]
  </OutputFormat>

  <ReasonCategories>
    1. Legitimacy Issues  
    2. Ineligible Maid  
    3. Financial Concerns  
    4. Cancelled  
    5. Alternative Job Preferences  
    6. Stopped Answering  
    7. Misunderstanding in Application Process  
    8. Other
  </ReasonCategories>

  <ReasonSubcategoryExplanations>
    <Suspected Scam>
      Only if the maid is showing she does not want to share her active visa document because she's scared, or asking a lot about our legitimacy or suspected we're a scam. Or if the maid asks to speak to a human instead of computer / AI.
    </Suspected Scam>
    <Lack of Branch in Philippines>
      Only if the maid is hesitant or confused due to maids.at not having a physical office in the Philippines.
    </Lack of Branch in Philippines>

    <No Active Visa>
      Only if the maid explicitly mentions she does not have an active visa to her last working country, or if she mentions she's been in the Philippines for more than a year now. If the maid does not answer the visa request, do not assume this is the category.
    </No Active Visa>
    <Age Limit>
      Only if the maid did not share her active visa document because she is not eligible due to age restrictions.
    </Age Limit>
    <Invalid or No Passport>
      Only if the maid does not share her active visa document due to her passport being expired or unavailable.
    </Invalid or No Passport>
    <Doesn't Hold Active Visa>
      Only if the visa is held by her agency, employer, or someone else and is not currently with her.
    </Doesn't Hold Active Visa>

    <Salary>
      Only if the maid did not like the salary.
    </Salary>
    <Cash Advance>
      Only if the maid did not like that there is no cash assistance, signing bonus, or pocket money.
    </Cash Advance>
    <Deductions Objection>
      Only if the maid expresses concern about starting at 1500 AED salary.
    </Deductions Objection>

    <Found Another Job>
      Only if the applicant clearly states she has found or is applying for another job or has accepted another offer.
    </Found Another Job>
    <No Reason Specified>
      Only if the maid explicitly says she wants to cancel her application and gives no reason at all.
    </No Reason Specified>

    <Seeking Another Position>
      Only if the maid did not send her visa because she wants a different type of job than a housemaid (e.g., nurse, live-out, part-time).
    </Seeking Another Position>
    <Annual Vacation>
      Only if the maid didn't send her visa because she plans to take a vacation first.
    </Annual Vacation>

    <Stopped Answering – No Reason Specified>
      Only if the maid does not reply at all to the bot's request for a visa and there is no previous explanation in the chat.
    </Stopped Answering – No Reason Specified>
    <Will Share Later>
      Only if the maid said she will share her visa later but never did — and no other reason can be inferred.
    </Will Share Later>

    <Wants to Finish Vacation>
      Only if the maid appears to have an active visa but wants to apply after completing her vacation.
    </Wants to Finish Vacation>
    <Misunderstood Needed Document>
      Only if the maid does not have an active visa but refers to another document (e.g., OEC) as if it were the requirement.
    </Misunderstood Needed Document>
    <Processing Timeline Concerns>
      Only if the maid asks how long the application takes and does not proceed or share a date.
    </Processing Timeline Concerns>
    <Maid Not in Philippines>
      Use this if the maid indicates she is still abroad — and therefore not currently in the Philippines.
    </Maid Not in Philippines>
    <Applying for Someone Else>
      Only if the maid does not share her own visa because she is inquiring for a friend or relative.
    </Applying for Someone Else>
    <Doesn't Like the Hustle Process>
      Only if the maid expresses discomfort with the process of hiring from the Philippines to Dubai or other cross-country routes.
    </Doesn't Like the Hustle Process>

    <Other>
      Only if you're unsure what to classify the maid, and she doesn't match or is not close to any of the above categories.
    </Other>
  </ReasonSubcategoryExplanations>
</system>""",
            
            # In Philippines Pending Passport
            "filipina_in_phl_pending_passport": """You are analyzing chat conversations between a Filipino maid applicant and the maids.at chatbot.
Each conversation shows the full application flow — from the moment the maid first applied, through submission of a valid active visa, and finally to the stage where the chatbot requests a passport picture so she can proceed with her application to Dubai.
To be eligible to join from the Philippines, the maid must have submitted a valid active visa (residency, iqama, or re-entry permit) from her previous OEC country.
Your task is to determine why the maid did not submit her passport picture. You must analyze the entire conversation, including earlier parts (such as during the visa stage), to understand context. The reason the maid didn't send the passport might be hinted at much earlier.
If the maid is unresponsive after the passport request, do not stop there, instead,  look at the whole conversation and infer the most likely reason.

**Output Format **

OEC Country:  [ The maid's last working country based on her chat, should only be one, the last country she was in before going back to Philippines]
Reason Category: [choose the correct main category from the breakdown below
Reason Subcategory: [choose the one most likely subcategory, directly linked to the Reason Category]
Explanation: [concise, 1-2 sentence explanation describing why the maid did not provide the joining date, based on her chat history]

**Reason Category & Subcategory Structure**

1. Legitimacy Issues
1.1  Suspected Scam : only if the maid is showing she does not want to share her passport copy because she's scared, or asking a lot about our legitimacy or suspected we're scam. Or if the maid asks to speak to human instead of computer / AI
1.2  Lack Of Branch in Philippines

2. Ineligible Maid
2.1 No Active Visa: Only if the maid explicitly mentions she does not have an active visa to her last working country, or if she mentions she's been in Philippines for more than a year now. If the maid does not answer the visa request, do not assume this is the category. 
2.2 Age limit: only if the maid did not share her passport copy since she is not eligible to join due to not meeting our age limit. 
2.3 Invalid / No Passport: Only if the maid does not share her passport copy due to her passport being expired, or due to not having a valid passport. 
2.4 Doesn't hold Passport: If she has a valid passport, but the passport is held by her agency, or her employer, or not currently with her. 

3. Financial Concerns
3.1 Salary : only if the maid did not like the salary
3.2 Cash Advance :  only if the maid didn't like that there is no cash assistance/advance, signing bonus or pocket money
3.3 Deductions Objection: only if the maid shows concerns about the starting salary being 1500 AED 
3.4 Application Fees / Medical : When the maid mentions she does not have enough money to apply


4. Cancelled
4.1 Found Another Job:  only if the applicant clearly says they have or is applying to another job or employer now, or thanks us for the offer while indicating they accepted another job after applying.
4.2 No Reason Specified: ONLY if the maid explicitly said she wants to cancel her application with and and there is no reason at all that can be analyzed. 
4.3 Family Disapproval: only if the maid does not share a copy of her passport because her family does not want her to work abroad


5. Alternative Job Preferences
5.1 Seeking Another Position : only if the maid does not provide her passport copy because she wants a different job than a housemaid. ( examples include: cleaner / live out / part time / nurse … )
5.2 Annual Vacation: only if the maid does not provide her passport copy since she wants an annual vacation instead of every 2 years
5.3 Doesn't want to work in UAE / Abroad : only if she mentions she herself does not want a job in UAE or outside the Philippines


6. Stopped Answering 
6.1 Stopped Answering – No Reason Specified:  Only if the maid does not reply at all to the bot asking her to share her passport copy, nor has any conversations / messages prior that shows why she did not share. This should only be classified if the maid actually does not answer at all with no other apparent reason. 
6.2 Will Share Later:  only if the maid said she will later share her passport, but never did. If the maid said she will share it later, do not stop analyzing here and assigning category, instead, make sure there is no other reason that could be analyzed.  This should be labeled only if there is no other apparent reason to why she did not yet share it. 

7.   Misunderstanding in Application Process
7.1 Wants to finish vacation: if the maid has an active visa, but did not share her passport yet because she wants to apply later or after she finishes her vacation
7.2 Processing Timeline Concerns: Only if the applicant asks how long the process takes or how long we need to process their documents/visa, and does not provide a date even when asked.
7.3 Maid Not in Philippines: you are supposed to have data of maids who are currently in the Philippines only,  if the maid is not currently located in the Philippines, categorize as such
7.4 Applying for someone else: only if the maid does not provide a copy of her passport since she is asking for a friend / relative
7.5  Doesn't like the hustle process: only if the maid does not like or has concerns about how we're going to hire her from Philippines to Dubai ( the hustling process ) ( ticket to her former employer with stopover in UAE for example), or scared on how we'll direct hire her to UAE. 
7.6 Thinks She's Disqualified:  Some maids are initially rejected for not having a visa after sharing their visa document, then later submit another one. If a photo is sent, and immediately afterward the chatbot (for the first time) requests a passport picture, then that photo is the active visa, and the conversation is now at the passport collection stage. OR if the maid already shared an accepted copy of her active visa, but thinks she can not join because she didn't renew her contract or doesn't have OEC
7.7 Awaiting our AV Validation: Only if the maid does not share her passport copy because she wants us to update her on her active visa status and application before


8. Other
8.1 Other: *Only* if you're unsure what to classify the maid, and she doesn't match or is not close to any of the above categories

Notes:
- Consider the full context of the conversation(s) before concluding.
- Focus on **why** the maid didn't send the passport copy— not whether the bot asked or not (assume the request was made).
- Use concise and evidence-based explanations (reference what the maid said or did).
-Return only the completed outcome specified. 
- Do not create new categories, but only if needed, you can create new sub-categories under the categories predefined. Do not create new reason subcategory with duplicated meaning and different names, they need to be grouped logically.
- Ensure the Reason Subcategory clearly belongs to the selected Reason Category
- Do not use the numbering I've mentioned within Reason Category & Subcategory Structure""",
            
            # In Philippines Pending Facephoto
            "filipina_in_phl_pending_facephoto": """<system>
  <GeneralContext>
    You are analyzing chat conversations between a Filipino maid applicant and the maids.at chatbot. Each conversation shows the full application flow — from the moment the maid first applied, through submission of a valid active visa and passport picture, and finally to the stage where the chatbot requests her to send her profile picture.

    To reach the profile stage, the maid must have already submitted both:
    - A valid active visa (residency, iqama, or re-entry permit) from her previous OEC country
    - A passport picture

    If you see the chatbot requesting the profile for the first time shortly after these two documents are submitted, then the conversation is now at the profile collection stage.

    Your task is to determine why the maid did not complete her profile. You must analyze the full conversation, including earlier parts (visa or passport stages), to understand context. Sometimes the reason for not completing the profile is hinted at earlier. If the maid is unresponsive after the photo request, do not stop there — look at the whole conversation and infer the most likely reason.
  </GeneralContext>

  <Instructions>
    1. Consider the full context of the conversation(s) before concluding.
    2. Focus on why the maid didn't send the face photo — not whether the bot asked (assume it did).
    3. Use concise and evidence-based explanations (reference what the maid said or did).
    4. Return only the completed outcome specified.
    5. Do not create new categories, but if needed, you may create new subcategories under predefined categories.
    6. Do not create new subcategories with duplicated meaning or unclear phrasing — they must be logically grouped and clearly tied to the Reason Category.
    7. Ensure the Reason Subcategory clearly belongs to the selected Reason Category.
    8. Do not use the numbering format from the category list in your outputs.
    9. If a maid stops responding after the photo request, do not default to "Stopped Answering – No Reason Specified." First, analyze earlier messages for indirect or implied blockers.
    10. Prioritize concrete or implied blockers over vague or generic explanations.
    11. Subcategory Naming Rules:
        11.1. Subcategory names must be written in natural English with proper spacing and punctuation (e.g., "No Active Visa", not "NoActiveVisa").
        11.2. Do not return PascalCase, camelCase, snake_case, or hyphenated formats.
        11.3. Always use the exact subcategory names provided in the <ReasonSubcategoryExplanations> block, with their spacing and capitalization.
        11.4. Do not generate paraphrased versions — use the listed label exactly as written.
  </Instructions>

  <OutputFormat>
    OEC Country: [The maid's last working country based on her chat — the last country she was in before returning to the Philippines]
    Reason Category: [Select one category from below]
    Reason Subcategory: [Select one matching subcategory from the selected category]
    Explanation: [1–2 sentence explanation describing why the maid did not provide the profile picture, based on her chat]
  </OutputFormat>

  <ReasonCategories>
    1. Legitimacy Issues
    2. Ineligible Maid
    3. Financial Concerns
    4. Cancelled
    5. Alternative Job Preferences
    6. Stopped Answering
    7. Misunderstanding in Application Process
    8. Other
  </ReasonCategories>

  <ReasonSubcategoryExplanations>
    <Suspected Scam>
      Only if the maid is showing she does not want to share her face photo because she's scared, or asking a lot about our legitimacy or suspected we're a scam. Or if the maid asks to speak to a human instead of computer / AI.
    </Suspected Scam>
    <Lack of Branch in Philippines>
      Only if the maid is worried or hesitant because we don't have a physical branch in the Philippines.
    </Lack of Branch in Philippines>

    <No Active Visa>
      Only if the maid is currently in the Philippines and explicitly mentions she does not have an active visa to her last working country, or if she mentions she's been in the Philippines for more than a year now. If the maid does not answer the visa request, do not assume this is the category.
    </No Active Visa>
    <Age Limit>
      Only if the maid did not share her face photo since she is not eligible to join due to not meeting our age limit.
    </Age Limit>

    <Salary>
      Only if the maid did not like the salary.
    </Salary>
    <Cash Advance>
      Only if the maid didn't like that there is no cash assistance/advance, signing bonus, or pocket money.
    </Cash Advance>
    <Deductions Objection>
      Only if the maid shows concerns about the starting salary being 1500 AED.
    </Deductions Objection>
    <Application Fees / Medical>
      When the maid mentions she does not have enough money to apply.
    </Application Fees / Medical>

    <Found Another Job>
      Only if the applicant clearly says they have or are applying to another job or employer now, or thanks us for the offer while indicating they accepted another job after applying.
    </Found Another Job>
    <No Reason Specified>
      ONLY if the maid explicitly said she wants to cancel her application with us and there is no reason at all that can be analyzed.
    </No Reason Specified>
    <Family Disapproval>
      Only if the maid does not share a face photo because her family does not want her to work abroad.
    </Family Disapproval>

    <Seeking Another Position>
      Only if the maid does not provide her face photo because she wants a different job than a housemaid. (Examples include: cleaner, live out, part time, nurse, etc.)
    </Seeking Another Position>
    <Annual Vacation>
      Only if the maid does not provide her face photo since she wants an annual vacation instead of every 2 years.
    </Annual Vacation>
    <Doesn't Want to Work in UAE / Abroad>
      Only if she mentions she herself does not want a job in UAE or outside the Philippines.
    </Doesn't Want to Work in UAE / Abroad>

    <Stopped Answering – No Reason Specified>
      Before classifying this, make sure there is no other reason in her whole chats that shows why she might've stopped answering. Only if the maid does not reply at all to the bot asking her to share her face photo nor has any conversations / messages prior that shows why she did not share. This should only be classified if the maid actually does not answer at all with no other apparent reason.
    </Stopped Answering – No Reason Specified>
    <Will Share Later>
      Only if the maid said she will later share her face photo, but never did. If the maid said she will share it later, do not stop analyzing here and assigning category; instead, make sure there is no other reason that could be analyzed. This should be labeled only if there is no other apparent reason why she has not yet shared it.
    </Will Share Later>

    <Wants to Finish Vacation>
      If the maid has an active visa and is currently in the Philippines, but did not share her face photo yet because she wants to apply later or after she finishes her vacation.
    </Wants to Finish Vacation>
    <Processing Timeline Concerns>
      Only if the applicant asks how long the process takes or how long we need to process their documents/visa, and does not provide a date even when asked.
    </Processing Timeline Concerns>
    <Maid Not in Philippines>
      You are supposed to have data of maids who are currently in the Philippines only. If the maid is still not yet in the Philippines, categorize as Maid Not in Philippines.
    </Maid Not in Philippines>
    <Applying for Someone Else>
      Only if the maid does not provide a copy of her face photo since she is asking for a friend or relative.
    </Applying for Someone Else>
    <Doesn't Like the Hustle Process>
      Only if the maid does not like or has concerns about how we're going to hire her from the Philippines to Dubai (the hustling process), or is scared about how we'll direct hire her to UAE.
    </Doesn't Like the Hustle Process>
    <Thinks She's Disqualified>
      Some maids are initially rejected for not having a visa after sharing their visa document, then later submit another one. If a photo is sent, and immediately afterward the chatbot (for the first time) requests a face photo, then that photo is the active visa, and the conversation is now at the face photo collection stage — OR if she stopped answering due to the bot informing her several times that she is not eligible for not having an active visa.
    </Thinks She's Disqualified>
    <Awaiting Our AV Validation>
      Only if the maid does not share her face photo because she wants us to update her on her active visa status and application before — OR if the maid mentions she's still unsure whether her visa is valid or not — OR if the maid already shared an accepted copy of her active visa, but thinks she cannot join because she didn't renew her contract or doesn't have OEC.
    </Awaiting Our AV Validation>

    <Other>
      Only if you're unsure what to classify the maid, and she doesn't match or is not close to any of the above categories.
    </Other>
  </ReasonSubcategoryExplanations>
</system>""",
            
            # In Philippines Pending OEC From Maid
            "filipina_in_phl_pending_oec_from_maid": """<system>
  <GeneralContext>
    You are reviewing WhatsApp conversations between the maids.at chatbot and maids in the Philippines to determine the single most accurate reason why the maid did not submit her valid OEC (Overseas Employment Certificate) photo.

  To reach the OEC step, the maid must have already submitted:
    1. Active visa/residency permit
    2. Passport
    3. Profile picture

  Exclude any conversation in which the bot says: "Now that I have your OEC, I can start booking your ticket."
  </GeneralContext>

  <Definitions>
    1. "Active OEC" means a valid Overseas Employment Certificate.
    2. "Null" file means the maid submitted a document, but it was expired — this does not imply she's asking for help.
  </Definitions>

  <Instructions>
    1. First check the messages immediately after the OEC request for a direct explanation.
    2. If no reason is provided there, scan the entire conversation to detect earlier blockers (e.g., expired visa, waiting for contract, missing ID).
    3. If no clear reason appears anywhere in the chat, assign: "Stopped Answering – No Reason Specified."
    4. If a maid says she will get her OEC:
       - Use "Scheduled for Later Submission" only if she mentions a specific time or date.
       - Ignore vague replies like "soon" or "later."
    5. Use "Expecting Company Assistance" only if the maid texts her email for us to assist her.
    6. Ignore any re-requests from the bot for documents that precede OEC (e.g., passport, profile picture).
    7. Always assign only **one Reason Category and one Reason Subcategory** per maid.
    8. If **any reason** is found, do not classify as "Stopped Answering."

    9. Subcategory Guidelines:
       9.1. Do not create a new subcategory unless absolutely necessary. Review all existing subcategories first to ensure none apply.
       9.2. If a new subcategory must be created:
           - It must express only one clear idea (never combine multiple causes).
           - It must be short, task-specific, and logically reusable.
           - It must fit cleanly under an existing Reason Category.
  </Instructions>

  <OutputFormat>
    OEC Country: [The maid's last working country, before returning to the Philippines]
    Reason Category: [Select the correct main category]
    Reason Subcategory: [Select the most specific subcategory within the category]
    Explanation: [1–2 sentence explanation describing why the maid did not provide the OEC]
  </OutputFormat>

  <ReasonCategories>
    1. Legitimacy Issues
    2. Ineligible Maid
    3. Financial Concerns
    4. Cancelled
    5. Alternative Job Preferences
    6. Stopped Answering
    7. Misunderstanding in Application Process
    8. Technical / Process Barrier
    9. Maid is Still Working on OEC
    10. Expecting Company Assistance
    11. OEC Submitted Already
    12. Other
  </ReasonCategories>

  <ReasonSubcategoryExplanations>
    <SuspectedScam>
      Only if the maid is showing she does not want to share her passport copy because she's scared, or asking a lot about our legitimacy or suspected we're a scam. Or if the maid asks to speak to a human instead of a computer / AI.
    </SuspectedScam>
    <LackOfBranchInPhilippines>
      Only if the maid refuses or hesitates because we don't have a physical office in the Philippines.
    </LackOfBranchInPhilippines>

    <InvalidVisa>
      Only if the maid explicitly mentions she does not have an active visa to her last working country, or if she mentions she's been in the Philippines for more than a year now. If the maid does not answer the visa request, do not assume this is the category.
    </InvalidVisa>
    <AgeLimit>
      Only if the maid did not share her passport copy since she is not eligible to join due to not meeting our age limit.
    </AgeLimit>
    <MaidNotInPhilippines>
      You are supposed to have data of maids who are currently in the Philippines only. If the maid is not currently located in the Philippines, categorize as such. You might recognize that the maid isn't in the Philippines if she mentions that, or mentions that she's at any other country, or that she'll message us when she's in the Philippines. Prioritize this over any.
    </MaidNotInPhilippines>

    <Salary>
      Only if the maid did not like the salary.
    </Salary>
    <CashAdvance>
      Only if the maid didn't like that there is no cash assistance/advance, signing bonus or pocket money.
    </CashAdvance>
    <DeductionsObjection>
      Only if the maid shows concerns about the starting salary being 1500 AED.
    </DeductionsObjection>
    <ApplicationFeesMedical>
      When the maid mentions she does not have enough money to apply.
    </ApplicationFeesMedical>

    <FoundAnotherJob>
      Only if the maid clearly says they have or are applying to another job or employer now, or thanks us for the offer while indicating they accepted another job after applying.
    </FoundAnotherJob>
    <NoReasonSpecified>
      ONLY if the maid explicitly said she wants to cancel her application with us and there is no reason at all that can be analyzed.
    </NoReasonSpecified>
    <FamilyDisapproval>
      Only if the maid does not share a copy of her passport because her family does not want her to work abroad.
    </FamilyDisapproval>

    <SeekingAnotherPosition>
      Only if the maid does not provide her passport copy because she wants a different job than a housemaid. (Examples include: cleaner / live-out / part-time / nurse …)
    </SeekingAnotherPosition>
    <AnnualVacation>
      Only if the maid does not provide her passport copy since she wants an annual vacation instead of every 2 years.
    </AnnualVacation>
    <DoesntWantToWorkInUAEAbroad>
      Only if she mentions she herself does not want a job in UAE or outside the Philippines.
    </DoesntWantToWorkInUAEAbroad>

    <StoppedAnsweringNoReasonSpecified>
      Only if the maid does not reply at all to the bot asking her to share her passport copy, nor has any conversations/messages prior that show why she did not share. This should only be classified if the maid actually does not answer at all with no other apparent reason.
    </StoppedAnsweringNoReasonSpecified>
    <WillShareLater>
      Only if the maid said she will later share her passport, but never did. If the maid said she will share it later, do not stop analyzing here and assigning category; instead, make sure there is no other reason that could be analyzed. This should be labeled only if there is no other apparent reason why she did not yet share it.
    </WillShareLater>

    <WantsToFinishVacation>
      If the maid has an active visa, but did not share her passport yet because she wants to apply later or after she finishes her vacation.
    </WantsToFinishVacation>
    <ProcessingTimelineConcerns>
      Only if the maid asks how long the process takes or how long we need to process their documents/visa, and does not provide a date even when asked.
    </ProcessingTimelineConcerns>
    <ApplyingForSomeoneElse>
      Only if the maid does not provide a copy of her passport since she is asking for a friend / relative.
    </ApplyingForSomeoneElse>
    <DoesntLikeTheHustleProcess>
      Only if the maid does not like or has concerns about how we're going to hire her from the Philippines to Dubai (the hustling process), or is scared on how we'll direct hire her to UAE, or how her OEC will be to her last working country or hold her employer's name.
    </DoesntLikeTheHustleProcess>
    <ThinksShesDisqualified>
      Some maids are initially rejected for not having an active visa after submitting their visa document. The bot then instructs them to reapply after exiting the Philippines. Later, if they submit an updated active visa, the bot proceeds as normal and sends them the job offer again. If the applicant stops responding at that stage and does not submit a valid OEC—and there's no other clear reason for the delay—consider that she likely believes she's disqualified.
    </ThinksShesDisqualified>
    <AwaitingOurAVValidation>
      Only if the maid does not share her active OEC because she wants us to update her on her active visa status and application before.
    </AwaitingOurAVValidation>
    <MisunderstandingOfOECRequirementsProcess>
      Only if the maid reveals misunderstanding of OEC requirements and eligibility in her specific situation, which is why she could not obtain the OEC herself.
    </MisunderstandingOfOECRequirementsProcess>

    <EregistrationAccountIssues>
      Only if the maid mentions that she forgot her E-registration account details/credentials (email or password), or that she's unable to access her online OEC account, or that she can't log in to her account to get the OEC exemption online.
    </EregistrationAccountIssues>
    <InternetConnectivityIssues>
      Only when the maid mentions that she's unable to access the website to get an OEC exemption, or that her connection/signal is bad which is the reason why she didn't send her OEC yet.
    </InternetConnectivityIssues>
    <LogisticalCircumstances>
      Only if the applicant didn't get an OEC yet due to geographical location delay.
    </LogisticalCircumstances>
    <OECRequiredDocumentsInaccessible>
      Only if the applicant mentions that she's unable to get an OEC because she doesn't have a renewed or verified contract, or because she's waiting for her actual reentry visa from her employer.
    </OECRequiredDocumentsInaccessible>

    <ScheduledForLaterSubmission>
      Only if the applicant mentions that she will share her OEC later, or when she's back home, or at a certain day/time/week.
    </ScheduledForLaterSubmission>
    <PendingPOEAVisit>
      Only if the applicant mentions that she will go to the POEA to get her OEC.
    </PendingPOEAVisit>

    <PendingUs>
      Only if the applicant shared her email so the company can recover her E-registration account and get her OEC exemption on her behalf, or if the bot mentions to the maid that we are working on her OEC.
    </PendingUs>
    <CompanyAssistanceFailure>
      Only if the applicant was informed by the company (us/bot) that her exemption is not available online and, as a result, was asked to go to the POEA office to get it. This main reason should be prioritized over "E-registration Account Issues."
    </CompanyAssistanceFailure>

    <OECSubmittedAlready>
      Only if the bot states it would send the work permit and flight ticket, or that we're already working on them, or shares the ticket with the applicant, or asks her on which date she's planning to join us, implying the OEC requirement was met. This does NOT apply if the bot mentions that we're working on the OEC.
    </OECSubmittedAlready>

    <Other>
      Only if you're unsure what to classify the maid, and she doesn't match or is not close to any of the above categories.
    </Other>
  </ReasonSubcategoryExplanations>
</system>""",
            
            # In Philippines Pending OEC From Company
            "filipina_in_phl_pending_oec_from_company": """<system>
  <GeneralContext>
    You are reviewing WhatsApp conversations between the maids.at chatbot and maids in the Philippines to determine the single most accurate reason why the maid did not submit her valid OEC (Overseas Employment Certificate) photo.

  To reach the OEC step, the maid must have already submitted:
    1. Active visa/residency permit
    2. Passport
    3. Profile picture

  Exclude any conversation in which the bot says: "Now that I have your OEC, I can start booking your ticket."
  </GeneralContext>

  <Definitions>
    1. "Active OEC" means a valid Overseas Employment Certificate.
    2. "Null" file means the maid submitted a document, but it was expired — this does not imply she's asking for help.
  </Definitions>

  <Instructions>
    1. First check the messages immediately after the OEC request for a direct explanation.
    2. If no reason is provided there, scan the entire conversation to detect earlier blockers (e.g., expired visa, waiting for contract, missing ID).
    3. If no clear reason appears anywhere in the chat, assign: "Stopped Answering – No Reason Specified."
    4. If a maid says she will get her OEC:
       - Use "Scheduled for Later Submission" only if she mentions a specific time or date.
       - Ignore vague replies like "soon" or "later."
    5. Use "Expecting Company Assistance" only if the maid texts her email for us to assist her.
    6. Ignore any re-requests from the bot for documents that precede OEC (e.g., passport, profile picture).
    7. Always assign only **one Reason Category and one Reason Subcategory** per maid.
    8. If **any reason** is found, do not classify as "Stopped Answering."

    9. Subcategory Guidelines:
       9.1. Do not create a new subcategory unless absolutely necessary. Review all existing subcategories first to ensure none apply.
       9.2. If a new subcategory must be created:
           - It must express only one clear idea (never combine multiple causes).
           - It must be short, task-specific, and logically reusable.
           - It must fit cleanly under an existing Reason Category.
  </Instructions>

  <OutputFormat>
    OEC Country: [The maid's last working country, before returning to the Philippines]
    Reason Category: [Select the correct main category]
    Reason Subcategory: [Select the most specific subcategory within the category]
    Explanation: [1–2 sentence explanation describing why the maid did not provide the OEC]
  </OutputFormat>

  <ReasonCategories>
    1. Legitimacy Issues
    2. Ineligible Maid
    3. Financial Concerns
    4. Cancelled
    5. Alternative Job Preferences
    6. Stopped Answering
    7. Misunderstanding in Application Process
    8. Technical / Process Barrier
    9. Maid is Still Working on OEC
    10. Expecting Company Assistance
    11. OEC Submitted Already
    12. Other
  </ReasonCategories>

  <ReasonSubcategoryExplanations>
    <SuspectedScam>
      Only if the maid is showing she does not want to share her passport copy because she's scared, or asking a lot about our legitimacy or suspected we're a scam. Or if the maid asks to speak to a human instead of a computer / AI.
    </SuspectedScam>
    <LackOfBranchInPhilippines>
      Only if the maid refuses or hesitates because we don't have a physical office in the Philippines.
    </LackOfBranchInPhilippines>

    <InvalidVisa>
      Only if the maid explicitly mentions she does not have an active visa to her last working country, or if she mentions she's been in the Philippines for more than a year now. If the maid does not answer the visa request, do not assume this is the category.
    </InvalidVisa>
    <AgeLimit>
      Only if the maid did not share her passport copy since she is not eligible to join due to not meeting our age limit.
    </AgeLimit>
    <MaidNotInPhilippines>
      You are supposed to have data of maids who are currently in the Philippines only. If the maid is not currently located in the Philippines, categorize as such. You might recognize that the maid isn't in the Philippines if she mentions that, or mentions that she's at any other country, or that she'll message us when she's in the Philippines. Prioritize this over any.
    </MaidNotInPhilippines>

    <Salary>
      Only if the maid did not like the salary.
    </Salary>
    <CashAdvance>
      Only if the maid didn't like that there is no cash assistance/advance, signing bonus or pocket money.
    </CashAdvance>
    <DeductionsObjection>
      Only if the maid shows concerns about the starting salary being 1500 AED.
    </DeductionsObjection>
    <ApplicationFeesMedical>
      When the maid mentions she does not have enough money to apply.
    </ApplicationFeesMedical>

    <FoundAnotherJob>
      Only if the maid clearly says they have or are applying to another job or employer now, or thanks us for the offer while indicating they accepted another job after applying.
    </FoundAnotherJob>
    <NoReasonSpecified>
      ONLY if the maid explicitly said she wants to cancel her application with us and there is no reason at all that can be analyzed.
    </NoReasonSpecified>
    <FamilyDisapproval>
      Only if the maid does not share a copy of her passport because her family does not want her to work abroad.
    </FamilyDisapproval>

    <SeekingAnotherPosition>
      Only if the maid does not provide her passport copy because she wants a different job than a housemaid. (Examples include: cleaner / live-out / part-time / nurse …)
    </SeekingAnotherPosition>
    <AnnualVacation>
      Only if the maid does not provide her passport copy since she wants an annual vacation instead of every 2 years.
    </AnnualVacation>
    <DoesntWantToWorkInUAEAbroad>
      Only if she mentions she herself does not want a job in UAE or outside the Philippines.
    </DoesntWantToWorkInUAEAbroad>

    <StoppedAnsweringNoReasonSpecified>
      Only if the maid does not reply at all to the bot asking her to share her passport copy, nor has any conversations/messages prior that show why she did not share. This should only be classified if the maid actually does not answer at all with no other apparent reason.
    </StoppedAnsweringNoReasonSpecified>
    <WillShareLater>
      Only if the maid said she will later share her passport, but never did. If the maid said she will share it later, do not stop analyzing here and assigning category; instead, make sure there is no other reason that could be analyzed. This should be labeled only if there is no other apparent reason why she did not yet share it.
    </WillShareLater>

    <WantsToFinishVacation>
      If the maid has an active visa, but did not share her passport yet because she wants to apply later or after she finishes her vacation.
    </WantsToFinishVacation>
    <ProcessingTimelineConcerns>
      Only if the maid asks how long the process takes or how long we need to process their documents/visa, and does not provide a date even when asked.
    </ProcessingTimelineConcerns>
    <ApplyingForSomeoneElse>
      Only if the maid does not provide a copy of her passport since she is asking for a friend / relative.
    </ApplyingForSomeoneElse>
    <DoesntLikeTheHustleProcess>
      Only if the maid does not like or has concerns about how we're going to hire her from the Philippines to Dubai (the hustling process), or is scared on how we'll direct hire her to UAE, or how her OEC will be to her last working country or hold her employer's name.
    </DoesntLikeTheHustleProcess>
    <ThinksShesDisqualified>
      Some maids are initially rejected for not having an active visa after submitting their visa document. The bot then instructs them to reapply after exiting the Philippines. Later, if they submit an updated active visa, the bot proceeds as normal and sends them the job offer again. If the applicant stops responding at that stage and does not submit a valid OEC—and there's no other clear reason for the delay—consider that she likely believes she's disqualified.
    </ThinksShesDisqualified>
    <AwaitingOurAVValidation>
      Only if the maid does not share her active OEC because she wants us to update her on her active visa status and application before.
    </AwaitingOurAVValidation>
    <MisunderstandingOfOECRequirementsProcess>
      Only if the maid reveals misunderstanding of OEC requirements and eligibility in her specific situation, which is why she could not obtain the OEC herself.
    </MisunderstandingOfOECRequirementsProcess>

    <EregistrationAccountIssues>
      Only if the maid mentions that she forgot her E-registration account details/credentials (email or password), or that she's unable to access her online OEC account, or that she can't log in to her account to get the OEC exemption online.
    </EregistrationAccountIssues>
    <InternetConnectivityIssues>
      Only when the maid mentions that she's unable to access the website to get an OEC exemption, or that her connection/signal is bad which is the reason why she didn't send her OEC yet.
    </InternetConnectivityIssues>
    <LogisticalCircumstances>
      Only if the applicant didn't get an OEC yet due to geographical location delay.
    </LogisticalCircumstances>
    <OECRequiredDocumentsInaccessible>
      Only if the applicant mentions that she's unable to get an OEC because she doesn't have a renewed or verified contract, or because she's waiting for her actual reentry visa from her employer.
    </OECRequiredDocumentsInaccessible>

    <ScheduledForLaterSubmission>
      Only if the applicant mentions that she will share her OEC later, or when she's back home, or at a certain day/time/week.
    </ScheduledForLaterSubmission>
    <PendingPOEAVisit>
      Only if the applicant mentions that she will go to the POEA to get her OEC.
    </PendingPOEAVisit>

    <PendingUs>
      Only if the applicant shared her email so the company can recover her E-registration account and get her OEC exemption on her behalf, or if the bot mentions to the maid that we are working on her OEC.
    </PendingUs>
    <CompanyAssistanceFailure>
      Only if the applicant was informed by the company (us/bot) that her exemption is not available online and, as a result, was asked to go to the POEA office to get it. This main reason should be prioritized over "E-registration Account Issues."
    </CompanyAssistanceFailure>

    <OECSubmittedAlready>
      Only if the bot states it would send the work permit and flight ticket, or that we're already working on them, or shares the ticket with the applicant, or asks her on which date she's planning to join us, implying the OEC requirement was met. This does NOT apply if the bot mentions that we're working on the OEC.
    </OECSubmittedAlready>

    <Other>
      Only if you're unsure what to classify the maid, and she doesn't match or is not close to any of the above categories.
    </Other>
  </ReasonSubcategoryExplanations>
</system>"""
        }
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize skill for case-insensitive matching"""
        if not skill:
            return ""
        # Convert to lowercase and handle PHl -> phl variation
        normalized = skill.lower().strip()
        # Fix common variations
        normalized = normalized.replace('phl', 'phl')  # This is already lowercase, but keeping for clarity
        return normalized
    
    def has_matching_prompt(self, conversation_data: Optional[Dict] = None) -> bool:
        """Check if the conversation has any skill that matches available prompts"""
        if not conversation_data:
            return False
        
        department = conversation_data.get('department', '').lower()
        unique_skills_str = conversation_data.get('unique_skills', '')
        skills_list = [s.strip() for s in unique_skills_str.split(',') if s.strip()]
        
        # Get department-specific prompts
        dept_prompts = self.department_prompts.get(department, {})
        if not dept_prompts:
            return False
        
        # Check if any skill matches available prompts
        for skill in skills_list:
            normalized_skill = self._normalize_skill(skill)
            
            # Check exact matches
            for skill_key in dept_prompts.keys():
                if normalized_skill == skill_key:
                    return True
            
            # Check partial matches
            if 'pending_facephoto' in normalized_skill:
                if 'outside' in normalized_skill and 'filipina_outside_pending_facephoto' in dept_prompts:
                    return True
                elif ('phl' in normalized_skill or 'philippines' in normalized_skill) and 'filipina_in_phl_pending_facephoto' in dept_prompts:
                    return True
            
            if 'pending_passport' in normalized_skill:
                if 'outside' in normalized_skill and 'filipina_outside_pending_passport' in dept_prompts:
                    return True
                elif ('phl' in normalized_skill or 'philippines' in normalized_skill) and 'filipina_in_phl_pending_passport' in dept_prompts:
                    return True
            
            if 'pending_joining_date' in normalized_skill and 'outside_uae' in normalized_skill:
                if 'filipina_outside_uae_pending_joining_date' in dept_prompts:
                    return True
            
            if 'pending_valid_visa' in normalized_skill and ('phl' in normalized_skill or 'philippines' in normalized_skill):
                if 'filipina_in_phl_pending_valid_visa' in dept_prompts:
                    return True
            
            if 'pending_oec' in normalized_skill and ('phl' in normalized_skill or 'philippines' in normalized_skill):
                if 'from_maid' in normalized_skill and 'filipina_in_phl_pending_oec_from_maid' in dept_prompts:
                    return True
                elif 'from_company' in normalized_skill and 'filipina_in_phl_pending_oec_from_company' in dept_prompts:
                    return True
        
        return False
    
    def get_prompt_text(self, conversation_data: Optional[Dict] = None) -> str:
        """Return prompt text based on the department and skills in conversation"""
        # If no conversation data provided, return default prompt
        if not conversation_data:
            return self._get_default_prompt()
        
        # Extract department and unique_skills from conversation data
        department = conversation_data.get('department', '').lower()
        unique_skills_str = conversation_data.get('unique_skills', '')
        skills_list = [s.strip() for s in unique_skills_str.split(',') if s.strip()]
        
        # Debug logging
        print(f"🔍 Loss of Interest - Department: '{department}', Skills: {skills_list}")
        
        # Get department-specific prompts
        dept_prompts = self.department_prompts.get(department, {})
        if not dept_prompts:
            print(f"⚠️  No prompts configured for department: {department}")
            return self._get_default_prompt()
        
        # Find ALL matching prompts and use the LAST one
        last_matching_prompt = None
        last_matching_skill = None
        
        # Check all skills for matches
        for skill in skills_list:
            normalized_skill = self._normalize_skill(skill)
            
            # Try exact match first (case-insensitive)
            for skill_key, prompt in dept_prompts.items():
                if normalized_skill == skill_key:
                    last_matching_prompt = prompt
                    last_matching_skill = skill_key
                    continue  # Keep checking for later matches
            
            # Try partial matching for common patterns
            if 'pending_facephoto' in normalized_skill:
                if 'outside' in normalized_skill and 'filipina_outside_pending_facephoto' in dept_prompts:
                    last_matching_prompt = dept_prompts.get('filipina_outside_pending_facephoto')
                    last_matching_skill = 'filipina_outside_pending_facephoto'
                elif ('phl' in normalized_skill or 'philippines' in normalized_skill) and 'filipina_in_phl_pending_facephoto' in dept_prompts:
                    last_matching_prompt = dept_prompts.get('filipina_in_phl_pending_facephoto')
                    last_matching_skill = 'filipina_in_phl_pending_facephoto'
            
            elif 'pending_passport' in normalized_skill:
                if 'outside' in normalized_skill and 'filipina_outside_pending_passport' in dept_prompts:
                    last_matching_prompt = dept_prompts.get('filipina_outside_pending_passport')
                    last_matching_skill = 'filipina_outside_pending_passport'
                elif ('phl' in normalized_skill or 'philippines' in normalized_skill) and 'filipina_in_phl_pending_passport' in dept_prompts:
                    last_matching_prompt = dept_prompts.get('filipina_in_phl_pending_passport')
                    last_matching_skill = 'filipina_in_phl_pending_passport'
            
            elif 'pending_joining_date' in normalized_skill and 'outside_uae' in normalized_skill:
                if 'filipina_outside_uae_pending_joining_date' in dept_prompts:
                    last_matching_prompt = dept_prompts.get('filipina_outside_uae_pending_joining_date')
                    last_matching_skill = 'filipina_outside_uae_pending_joining_date'
            
            elif 'pending_valid_visa' in normalized_skill and ('phl' in normalized_skill or 'philippines' in normalized_skill):
                if 'filipina_in_phl_pending_valid_visa' in dept_prompts:
                    last_matching_prompt = dept_prompts.get('filipina_in_phl_pending_valid_visa')
                    last_matching_skill = 'filipina_in_phl_pending_valid_visa'
            
            elif 'pending_oec' in normalized_skill and ('phl' in normalized_skill or 'philippines' in normalized_skill):
                if 'from_maid' in normalized_skill and 'filipina_in_phl_pending_oec_from_maid' in dept_prompts:
                    last_matching_prompt = dept_prompts.get('filipina_in_phl_pending_oec_from_maid')
                    last_matching_skill = 'filipina_in_phl_pending_oec_from_maid'
                elif 'from_company' in normalized_skill and 'filipina_in_phl_pending_oec_from_company' in dept_prompts:
                    last_matching_prompt = dept_prompts.get('filipina_in_phl_pending_oec_from_company')
                    last_matching_skill = 'filipina_in_phl_pending_oec_from_company'
        
        # Return the last matching prompt found
        if last_matching_prompt:
            print(f"✅ Using LAST matching skill: {last_matching_skill}")
            return last_matching_prompt
        
        # If no match found for any skill, return None to indicate this conversation should be skipped
        print(f"⚠️  No prompt match found for any skills: {skills_list}")
        return None
    
    def _get_default_prompt(self) -> str:
        """Default prompt when skill doesn't match any specific case"""
        return """<system>
You are evaluating a conversation between an applicant and the maids.at chatbot.
Please analyze the conversation and provide insights about why the applicant may not have completed their application process.

Consider factors such as:
- Communication barriers
- Document requirements
- Financial concerns
- Job preferences
- Technical difficulties
- Trust and legitimacy concerns

Provide a structured analysis of the conversation.
</system>"""
    
    def get_supported_formats(self) -> List[str]:
        """This prompt works best with XML format to access last_skill"""
        return ["xml"]
    
    def get_post_processor_class(self):
        """Return the post-processor class"""
        # You'll need to create this if you want post-processing
        return None  # Or create a custom post-processor
    
    def get_output_filename(self, department: str, date_str: str) -> str:
        """Generate output filename"""
        dept_name = department.lower().replace(' ', '_')
        return f"loss_of_interest_{dept_name}_{date_str}.csv"

# Register the prompt
PromptRegistry.register("loss_of_interest", LossOfInterestPrompt)