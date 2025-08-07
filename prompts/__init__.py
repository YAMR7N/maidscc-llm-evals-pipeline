# Prompt implementations
from .base import BasePrompt, PromptRegistry

# Import all prompt implementations to register them
from . import sentiment_analysis
from . import ftr
from . import rule_breaking
from . import false_promises
from . import categorizing
from . import policy_escalation
from . import client_suspecting_ai
from . import clarity_score
from . import legal_allignment
from . import call_request
from . import threatening
from . import category_docs
from . import misprescription
from . import unnecessary_clinic_rec
from . import loss_of_interest

__all__ = ['BasePrompt', 'PromptRegistry']
