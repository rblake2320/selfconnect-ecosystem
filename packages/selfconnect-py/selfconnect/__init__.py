"""
SelfConnect.ai Python SDK

HTTP client and optional framework adapters for SelfConnect APIs.
"""

from .client import TskClient, SelfConnectError, BudgetExhaustedError, TskInvalidError
from .langchain_handler import SelfConnectCallbackHandler
from ._version import __version__

__all__ = [
    "TskClient",
    "SelfConnectCallbackHandler",
    "SelfConnectError",
    "BudgetExhaustedError",
    "TskInvalidError",
    "__version__",
]
