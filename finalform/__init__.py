"""finalform: Semantic processing engine for psychological instruments."""

__version__ = "0.1.0"

# Import callable protocol - these imports must come after __version__ to avoid circular import
from finalform.callable import CallableResult, execute

__all__ = ["__version__", "CallableResult", "execute"]
