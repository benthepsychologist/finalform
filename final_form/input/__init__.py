"""Form input handling for final-form.

Provides the FormInputClient for managing field_id -> item_id mappings,
and the high-level process_form_submission API for processing canonical
form submissions.
"""

from final_form.input.client import FormInputClient
from final_form.input.process import (
    MissingFormIdError,
    MissingItemMapError,
    UnmappedFieldError,
    process_form_submission,
)

__all__ = [
    "FormInputClient",
    "MissingFormIdError",
    "MissingItemMapError",
    "UnmappedFieldError",
    "process_form_submission",
]
