"""Model routing — task classification, media detection, intelligent model selection.

``syrin.router`` routes LLM *calls* to different *models* based on task complexity
or media type.  It is entirely distinct from :class:`~syrin.agent.agent_router.AgentRouter`
(which routes *tasks* to different *agents*).

Quick distinction:

* :class:`~syrin.router.router.ModelRouter` — selects the cheapest capable model for
  each LLM call at runtime (e.g. haiku for simple tasks, opus for complex ones).
* :class:`~syrin.agent.agent_router.AgentRouter` — lets the LLM decide which *agent
  specializations* to spawn and in what order.  Lives in ``syrin.agent``, not here.
"""

from syrin.enums import Media
from syrin.router._embedding_protocol import EmbeddingProvider
from syrin.router.agent_integration import register_model_capabilities
from syrin.router.classifier import (
    ClassificationResult,
    EmbeddingClassifier,
    PromptClassifier,
)
from syrin.router.config import RoutingConfig
from syrin.router.defaults import get_default_profiles
from syrin.router.enums import ComplexityTier, RoutingMode, TaskType
from syrin.router.modality import ModalityDetector
from syrin.router.protocols import ClassifierProtocol
from syrin.router.router import ModelRouter, RoutingReason

__all__ = [
    "ClassifierProtocol",
    "ClassificationResult",
    "EmbeddingProvider",
    "ComplexityTier",
    "get_default_profiles",
    "EmbeddingClassifier",
    "Media",
    "ModelRouter",
    "ModalityDetector",
    "register_model_capabilities",
    "PromptClassifier",
    "RoutingConfig",
    "RoutingMode",
    "RoutingReason",
    "TaskType",
]
