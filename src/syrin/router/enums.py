"""Enums for model routing — task types, modalities, routing modes."""

from __future__ import annotations

from enum import StrEnum


class TaskType(StrEnum):
    """Task type for model routing. Used by PromptClassifier and ModelRouter.

    Note: IMAGE_GENERATION and VIDEO_GENERATION are output intents (what the user
    wants to create), not input classifications. Other values classify input.

    Attributes:
        CODE: Code generation, debugging, review, implementation.
        GENERAL: General conversation, Q&A, chitchat.
        VISION: Image understanding, OCR, image description (input).
        IMAGE_GENERATION: Output intent — create or generate an image.
        VIDEO: Video analysis, transcription (input).
        VIDEO_GENERATION: Output intent — create or generate a video.
        PLANNING: Complex reasoning, task decomposition, strategy.
        REASONING: Math, logic, analytical reasoning.
        CREATIVE: Writing, brainstorming, creative content.
        TRANSLATION: Language translation.
    """

    CODE = "code"
    GENERAL = "general"
    VISION = "vision"
    IMAGE_GENERATION = "image_generation"
    VIDEO = "video"
    VIDEO_GENERATION = "video_generation"
    PLANNING = "planning"
    REASONING = "reasoning"
    CREATIVE = "creative"
    TRANSLATION = "translation"


class ComplexityTier(StrEnum):
    """Prompt complexity tier for model selection. Higher = prefer premium model.

    Attributes:
        LOW: Simple prompts — use cheaper models.
        MEDIUM: Moderate complexity — balance cost/capability.
        HIGH: Complex prompts — prefer premium models.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RoutingMode(StrEnum):
    """How the router selects among capable models.

    Attributes:
        AUTO: Intelligent auto-selection balancing cost and capability (default).
        COST_FIRST: Always use cheapest capable model.
        QUALITY_FIRST: Always use highest-priority capable model.
        MANUAL: Developer provides task type; no auto-classification.
    """

    AUTO = "auto"
    COST_FIRST = "cost_first"
    QUALITY_FIRST = "quality_first"
    MANUAL = "manual"
