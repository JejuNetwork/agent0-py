"""
Agent0 SDK - Python SDK for agent portability, discovery and trust based on ERC-8004.
"""

from .core.models import (
    AgentId,
    ChainId,
    Address,
    URI,
    CID,
    Timestamp,
    IdemKey,
    EndpointType,
    TrustModel,
    Endpoint,
    RegistrationFile,
    AgentSummary,
    Feedback,
    SearchParams,
    SearchFeedbackParams,
    ValidationStatus,
    ValidationRequest,
    ValidationResponse,
    ValidationSummary,
    ZERO_BYTES32,
    ZERO_ADDRESS,
)

# Try to import SDK and Agent (may fail if web3 is not installed)
try:
    from .core.sdk import SDK
    from .core.agent import Agent
    from .core.contracts import SUBGRAPH_IDS, build_subgraph_url, get_default_subgraph_url
    _sdk_available = True
except ImportError:
    SDK = None
    Agent = None
    SUBGRAPH_IDS = {}
    build_subgraph_url = None
    get_default_subgraph_url = None
    _sdk_available = False

__version__ = "0.31"
__all__ = [
    "SDK",
    "Agent",
    "AgentId",
    "ChainId", 
    "Address",
    "URI",
    "CID",
    "Timestamp",
    "IdemKey",
    "EndpointType",
    "TrustModel",
    "Endpoint",
    "RegistrationFile",
    "AgentSummary",
    "Feedback",
    "SearchParams",
    "SearchFeedbackParams",
    "ValidationStatus",
    "ValidationRequest",
    "ValidationResponse",
    "ValidationSummary",
    "ZERO_BYTES32",
    "ZERO_ADDRESS",
    "SUBGRAPH_IDS",
    "build_subgraph_url",
    "get_default_subgraph_url",
]
