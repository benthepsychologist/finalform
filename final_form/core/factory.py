"""Factory functions for creating pre-configured components.

Provides convenient functions to create domain routers with
all available processors registered.
"""

from final_form.core.router import DomainRouter
from final_form.domains.questionnaire import QuestionnaireProcessor


def create_router() -> DomainRouter:
    """Create a domain router with all available processors registered.

    Returns:
        A DomainRouter with questionnaire processor (and future domains) registered.
    """
    router = DomainRouter()

    # Register questionnaire domain processor
    router.register(QuestionnaireProcessor())

    # Future: Register other domain processors
    # router.register(LabProcessor())
    # router.register(VitalProcessor())
    # router.register(WearableProcessor())

    return router


def get_default_router() -> DomainRouter:
    """Get the default domain router singleton.

    For most use cases, use create_router() instead to get a fresh instance.
    This function is provided for convenience in simple scripts.

    Returns:
        The default DomainRouter instance.
    """
    return create_router()
