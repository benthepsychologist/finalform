"""Questionnaire domain processor.

Handles processing of clinical questionnaires, scales, inventories,
and checklists. This is the primary domain for patient-reported
outcome measures (PROMs).
"""

from final_form.domains.questionnaire.processor import QuestionnaireProcessor

__all__ = [
    "QuestionnaireProcessor",
]
