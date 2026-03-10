"""Model routing — task classification, media detection, intelligent model selection."""

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
