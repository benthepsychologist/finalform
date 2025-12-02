"""Domain-specific processors for final-form.

Each domain handles a specific category of measurement:
- questionnaire: Clinical questionnaires, scales, inventories, checklists
- lab: Laboratory panels and test results
- vital: Vital signs measurements
- wearable: Wearable device data streams
"""

from final_form.domains.lab import LabProcessor
from final_form.domains.questionnaire import QuestionnaireProcessor
from final_form.domains.vital import VitalProcessor
from final_form.domains.wearable import WearableProcessor

__all__ = [
    "LabProcessor",
    "QuestionnaireProcessor",
    "VitalProcessor",
    "WearableProcessor",
]
