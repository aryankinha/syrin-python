"""Embedding-based prompt classification for model routing.

Production features: LRU cache, batch classify, complexity score, system alignment.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from syrin.router._embedding_protocol import EmbeddingProvider
from syrin.router.enums import ComplexityTier, TaskType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_CLASSIFIER_IMPORT_ERROR = (
    "Routing with embedding-based classification requires sentence-transformers. "
    "Install with: uv pip install 'syrin[classifier-embeddings]' (quote for zsh)."
)

# Keyword patterns for image/video generation — no embedding model required
_IMAGE_GEN_PATTERNS = re.compile(
    r"\b(generate|create|draw|make|produce)\s+(?:an?\s+)?(?:picture|image|photo|illustration)\b",
    re.IGNORECASE,
)
_VIDEO_GEN_PATTERNS = re.compile(
    r"\b(generate|create|make|produce)\s+(?:\w+\s+)*(?:video|clip|movie)s?\b",
    re.IGNORECASE,
)


def _keyword_detect_generation(prompt: str) -> tuple[TaskType, float] | None:
    """Detect image/video generation intent via keywords. No sentence-transformers needed.

    Returns (TaskType, confidence) if matched, else None.
    """
    text = (prompt or "").strip()
    if not text:
        return None
    if _VIDEO_GEN_PATTERNS.search(text):
        return (TaskType.VIDEO_GENERATION, 0.80)
    if _IMAGE_GEN_PATTERNS.search(text):
        return (TaskType.IMAGE_GENERATION, 0.80)
    lower = text.lower()
    if re.search(r"\bdraw\s+(?:me\s+)?(?:a|an|the)\s+", lower) or re.search(
        r"\bgenerate\s+(?:an?\s+)?image\s+", lower
    ):
        return (TaskType.IMAGE_GENERATION, 0.80)
    return None


# Improved default examples — more diverse, disambiguate VIDEO vs GENERAL/PLANNING
_DEFAULT_EXAMPLES: dict[TaskType, list[str]] = {
    TaskType.CODE: [
        "write a Python function",
        "debug this code",
        "implement binary search",
        "create a REST API",
        "fix the bug in this function",
        "refactor this into a class",
        "write unit tests",
        "what's wrong with my async await",
        "create a FastAPI endpoint",
        "review this pull request",
    ],
    TaskType.GENERAL: [
        "hello how are you",
        "what is the weather",
        "tell me about yourself",
        "thanks for your help",
        "what is the capital of France",
        "can you explain how this works",
        "summarize the meeting notes",
        "what time is it",
        "what is 2 plus 2",
    ],
    TaskType.VISION: [
        "describe this image",
        "what is in the picture",
        "extract text from this image",
        "what objects are in the photo",
        "OCR this screenshot",
    ],
    TaskType.VIDEO: [
        "summarize this video",
        "what happens in the clip",
        "transcribe this video",
        "analyze the footage",
    ],
    TaskType.IMAGE_GENERATION: [
        "generate an image of a rat",
        "create a picture of a sunset",
        "draw a cat",
        "make an image of a mountain",
        "generate a photo of a dog",
    ],
    TaskType.VIDEO_GENERATION: [
        "create a video of a walking person",
        "generate a short clip of ocean waves",
        "make a video of a bird flying",
    ],
    TaskType.PLANNING: [
        "plan a project",
        "break down the task",
        "create a strategy",
        "plan a 3-day trip",
        "create a migration strategy",
    ],
    TaskType.REASONING: [
        "solve this math problem",
        "prove the following",
        "analyze the logic",
        "what's the probability",
        "compare pros and cons",
    ],
    TaskType.CREATIVE: [
        "write a short story",
        "brainstorm ideas",
        "compose a poem",
        "write a haiku",
    ],
    TaskType.TRANSLATION: [
        "translate to French",
        "convert to Spanish",
        "translate hello world to Japanese",
    ],
}

# For complexity: simple = low model need, complex = high model need
_COMPLEXITY_SIMPLE: list[str] = [
    "hi",
    "hello",
    "thanks",
    "ok",
    "bye",
    "what time",
    "weather",
]
_COMPLEXITY_COMPLEX: list[str] = [
    "implement a distributed system with consensus",
    "prove the following theorem",
    "refactor this codebase for scalability",
    "design an architecture for high availability",
]


@dataclass
class ClassificationResult:
    """Extended classification result for production routing.

    Attributes:
        task_type: Detected task type.
        confidence: Classification confidence [0, 1].
        complexity_score: 0 = use cheap model, 1 = prefer premium. Based on prompt heuristics + embedding.
        complexity_tier: LOW, MEDIUM, or HIGH.
        system_alignment_score: When system_prompt provided, similarity [0, 1]. High = prompt in scope.
        used_fallback: True if confidence < min_confidence.
        latency_ms: Classification latency in milliseconds.
    """

    task_type: TaskType
    confidence: float
    complexity_score: float
    complexity_tier: ComplexityTier
    system_alignment_score: float | None
    used_fallback: bool
    latency_ms: float


def _load_sentence_transformers(
    model_name: str,
    cache_dir: str | None,
) -> object:
    """Lazy load SentenceTransformer. Raises ImportError with install hint if missing."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(_CLASSIFIER_IMPORT_ERROR) from e
    # Suppress BERT "UNEXPECTED embeddings.position_ids" load report (harmless)
    import logging
    import os

    _prev_env = os.environ.get("TRANSFORMERS_VERBOSITY")
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    _loggers: list[tuple[logging.Logger, int]] = []
    try:
        for _name in ("transformers", "sentence_transformers"):
            _log = logging.getLogger(_name)
            _loggers.append((_log, _log.level))
            _log.setLevel(logging.ERROR)
        return SentenceTransformer(model_name, cache_folder=cache_dir)
    finally:
        for _log, _level in _loggers:
            _log.setLevel(_level)
        if _prev_env is not None:
            os.environ["TRANSFORMERS_VERBOSITY"] = _prev_env
        else:
            os.environ.pop("TRANSFORMERS_VERBOSITY", None)


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [0, 1]. Uses max(0, raw) — negative = unrelated, not high confidence."""
    import numpy as np

    na, nb = np.array(a), np.array(b)
    dot = float(np.dot(na, nb))
    norm = float(np.linalg.norm(na) * np.linalg.norm(nb) + 1e-9)
    raw: float = dot / norm
    return max(0.0, raw)


def _complexity_heuristic(prompt: str) -> float:
    """Heuristic complexity score [0, 1]. Fast, no embedding."""
    score = 0.0
    text = prompt.strip().lower()
    # Length (rough: >500 chars = complex)
    if len(text) > 500:
        score += 0.4
    elif len(text) > 200:
        score += 0.2
    elif len(text) < 20:
        score -= 0.2
    # Multiple sentences
    sents = re.split(r"[.!?]+", text)
    if len([s for s in sents if s.strip()]) > 3:
        score += 0.2
    # Technical indicators
    tech = [
        "implement",
        "design",
        "architecture",
        "refactor",
        "debug",
        "prove",
        "algorithm",
        "distributed",
        "scalable",
        "consensus",
        "theorem",
    ]
    if any(t in text for t in tech):
        score += 0.3
    # Question words often simpler
    if text.startswith(("what is", "who is", "when", "where", "how many")) and len(text) < 80:
        score -= 0.1
    return min(1.0, max(0.0, score))


def _to_emb_list(emb: object) -> list[float]:
    """Normalize embedding to list[float]."""
    return emb.tolist() if hasattr(emb, "tolist") else list(emb)  # type: ignore[call-overload, no-any-return]


class EmbeddingClassifier:
    """Embedding-based task classifier. Uses sentence-transformers or EmbeddingProvider."""

    def __init__(
        self,
        *,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        cache_dir: str | None = None,
        examples: dict[TaskType, list[str]] | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self._model_name = model
        self._cache_dir = cache_dir
        self._examples = examples or _DEFAULT_EXAMPLES
        self._embedding_provider = embedding_provider
        self._model: object = None
        self._task_embeddings: dict[TaskType, list[list[float]]] | None = None
        self._simple_emb: list[list[float]] | None = None
        self._complex_emb: list[list[float]] | None = None

    def _encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts to embeddings. Uses provider or sentence-transformers."""
        if self._embedding_provider is not None:
            return [[float(x) for x in e] for e in self._embedding_provider.encode(texts)]
        return [_to_emb_list(e) for e in self._model.encode(texts)]  # type: ignore[attr-defined]

    def _ensure_loaded(self) -> None:
        if self._task_embeddings is not None:
            return
        if self._embedding_provider is not None:
            self._compute_task_embeddings()
            self._simple_emb = self._encode(_COMPLEXITY_SIMPLE)
            self._complex_emb = self._encode(_COMPLEXITY_COMPLEX)
        else:
            self._model = _load_sentence_transformers(self._model_name, self._cache_dir)
            self._compute_task_embeddings()
            self._simple_emb = self._encode(_COMPLEXITY_SIMPLE)
            self._complex_emb = self._encode(_COMPLEXITY_COMPLEX)

    def _compute_task_embeddings(self) -> None:
        texts: list[str] = []
        task_indices: list[TaskType] = []
        for task, prompts in self._examples.items():
            for p in prompts:
                texts.append(p)
                task_indices.append(task)
        embeddings = self._encode(texts)
        self._task_embeddings = {}
        for i, task in enumerate(task_indices):
            if task not in self._task_embeddings:
                self._task_embeddings[task] = []
            self._task_embeddings[task].append(embeddings[i])

    def classify(self, prompt: str) -> tuple[TaskType, float]:
        """Classify prompt into TaskType and return confidence in [0, 1]."""
        self._ensure_loaded()
        prompt_list = self._encode([prompt.strip() or " "])[0]
        return self._classify_from_emb(prompt_list)

    def _classify_from_emb(self, prompt_emb: list[float]) -> tuple[TaskType, float]:
        best_task = TaskType.GENERAL
        best_score = -1.0
        for task, task_embs in (self._task_embeddings or {}).items():
            for te in task_embs:
                score = _cosine_sim(prompt_emb, te)
                if score > best_score:
                    best_score = score
                    best_task = task
        return (best_task, min(1.0, max(0.0, best_score)))

    def classify_embeddings(self, prompts: list[str]) -> list[tuple[TaskType, float]]:
        """Batch classify: one encode() call, then classify each embedding."""
        if not prompts:
            return []
        self._ensure_loaded()
        texts = [(p.strip() or " ") for p in prompts]
        embs = self._encode(texts)
        return [self._classify_from_emb(emb) for emb in embs]

    def complexity_score(self, prompt_emb: list[float]) -> float:
        """Embedding-based complexity [0,1]. Higher = needs premium model."""
        self._ensure_loaded()
        sim_simple = (
            max(_cosine_sim(prompt_emb, se) for se in (self._simple_emb or []))
            if self._simple_emb
            else 0.0
        )
        sim_complex = (
            max(_cosine_sim(prompt_emb, ce) for ce in (self._complex_emb or []))
            if self._complex_emb
            else 0.0
        )
        # More similar to complex examples = higher score
        return min(1.0, max(0.0, (sim_complex - sim_simple + 1) / 2))

    def system_alignment_score(self, prompt_emb: list[float], system_emb: list[float]) -> float:
        """Similarity between prompt and system prompt. High = prompt in scope."""
        return _cosine_sim(prompt_emb, system_emb)


class PromptClassifier(BaseModel):  # type: ignore[explicit-any]
    """Embedding-based prompt classifier for model routing. Production-ready.

    Example::

        classifier = PromptClassifier(
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            min_confidence=0.35,
        )
        task_type, confidence = classifier.classify("write a Python function")

    Features: task detection, complexity score, system alignment, LRU cache, batch.
    """

    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence-transformers embedding model name (e.g. all-MiniLM-L6-v2). "
        "Not the LLM model.",
    )
    cache_dir: str | None = Field(
        default=None,
        description="Cache directory for embedding model. None = HF default.",
    )
    min_confidence: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description=(
            "Below this confidence, use low_confidence_fallback. Raw cosine similarity [0,1]. "
            "Typical correct classification: 0.5–0.8. Ambiguous: 0.2–0.4. "
            "Default 0.35 catches most correct matches. Raise to 0.5 for stricter; lower to 0.2 for permissive."
        ),
    )
    low_confidence_fallback: TaskType = Field(
        default=TaskType.GENERAL,
        description="Task type when confidence < min_confidence.",
    )
    examples: dict[TaskType, list[str]] | None = Field(
        default=None,
        description="Custom task examples. None = use defaults.",
    )
    enable_cache: bool = Field(
        default=True,
        description="Enable LRU cache for classify results. Recommended for production.",
    )
    max_cache_size: int = Field(
        default=1000,
        ge=0,
        description="Max cached prompt hashes. 0 = disable cache.",
    )
    complexity_use_embedding: bool = Field(
        default=True,
        description="Use embedding for complexity; else heuristic only.",
    )
    use_keyword_fallback: bool = Field(
        default=True,
        description="Try keyword-based detection for image/video generation before embeddings. "
        "Works without sentence-transformers.",
    )
    embedding_provider: object = Field(
        default=None,
        description="Optional custom embedding provider. Implement encode(texts: list[str]) -> list[list[float]]. "
        "When set, used instead of sentence-transformers (OpenAI, Cohere, etc.).",
    )

    model_config = {"arbitrary_types_allowed": True}

    _embedding_classifier: EmbeddingClassifier | None = PrivateAttr(default=None)
    _cache: OrderedDict[str, tuple[TaskType, float]] = PrivateAttr(default_factory=OrderedDict)
    _cache_lock: Lock = PrivateAttr(default_factory=Lock)

    @model_validator(mode="after")
    def _validate_cache_dir(self) -> PromptClassifier:
        if self.cache_dir is None:
            return self
        path = os.path.abspath(self.cache_dir)
        if os.path.exists(path):
            if not os.path.isdir(path):
                raise ValueError(f"cache_dir must be a directory, got file: {self.cache_dir!r}")
            if not os.access(path, os.W_OK):
                raise ValueError(f"cache_dir must be writable: {self.cache_dir!r}")
        else:
            parent = os.path.dirname(path)
            if not os.path.exists(parent):
                raise ValueError(f"cache_dir parent does not exist: {parent!r}")
            if not os.access(parent, os.W_OK):
                raise ValueError(f"cache_dir parent must be writable to create: {parent!r}")
        return self

    def _get_embedding_classifier(self) -> EmbeddingClassifier:
        if self._embedding_classifier is None:
            self._embedding_classifier = EmbeddingClassifier(
                model=self.embedding_model,
                cache_dir=self.cache_dir,
                examples=self.examples or _DEFAULT_EXAMPLES,
                embedding_provider=self.embedding_provider,  # type: ignore[arg-type]
            )
        return self._embedding_classifier

    def _cache_key(self, prompt: str, system_prompt: str | None) -> str:
        h = hashlib.sha256((prompt + (system_prompt or "")).encode()).hexdigest()
        return h[:32]

    def _get_cached(self, key: str) -> tuple[TaskType, float] | None:
        if not self.enable_cache or self.max_cache_size <= 0:
            return None
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def _set_cached(self, key: str, value: tuple[TaskType, float]) -> None:
        if not self.enable_cache or self.max_cache_size <= 0:
            return
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_cache_size:
                    self._cache.popitem(last=False)
                self._cache[key] = value

    def classify(self, prompt: str) -> tuple[TaskType, float]:
        """Classify prompt into TaskType and confidence. Uses fallback when confidence < min."""
        key = self._cache_key(prompt, None)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        # Fast path: keyword-based detection for image/video generation (no sentence-transformers)
        if self.use_keyword_fallback:
            kw = _keyword_detect_generation(prompt)
            if kw is not None:
                result = kw
                self._set_cached(key, result)
                return result
        try:
            emb = self._get_embedding_classifier()
            task, confidence = emb.classify(prompt)
            if confidence < self.min_confidence:
                result = (self.low_confidence_fallback, confidence)
            else:
                result = (task, confidence)
            self._set_cached(key, result)
            return result
        except ImportError:
            # Embeddings unavailable: try keyword fallback if enabled, else raise or use fallback
            if self.use_keyword_fallback:
                kw = _keyword_detect_generation(prompt)
                if kw is not None:
                    result = kw
                    self._set_cached(key, result)
                    return result
                result = (self.low_confidence_fallback, 0.0)
                self._set_cached(key, result)
                return result
            raise
        except Exception as e:
            logger.warning("Classification failed, using fallback: %s", e)
            if self.use_keyword_fallback:
                kw = _keyword_detect_generation(prompt)
                if kw is not None:
                    result = kw
                    self._set_cached(key, result)
                    return result
            result = (self.low_confidence_fallback, 0.0)
            self._set_cached(key, result)
            return result

    def classify_extended(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ClassificationResult:
        """Extended classification: task_type, confidence, complexity_score, system_alignment_score.

        Use for production routing when you need higher vs lower model selection
        and/or alignment with system prompt scope.
        """
        t0 = time.perf_counter()
        # Fast path: keyword-based detection (no embeddings needed)
        if self.use_keyword_fallback:
            kw = _keyword_detect_generation(prompt)
            if kw is not None:
                task, confidence = kw
                latency_ms = (time.perf_counter() - t0) * 1000
                return ClassificationResult(
                    task_type=task,
                    confidence=confidence,
                    complexity_score=0.3,
                    complexity_tier=ComplexityTier.LOW,
                    system_alignment_score=None,
                    used_fallback=False,
                    latency_ms=round(latency_ms, 2),
                )
        used_fallback = False
        emb_cls = self._get_embedding_classifier()
        emb_cls._ensure_loaded()

        prompt_clean = prompt.strip() or " "
        prompt_emb = emb_cls._encode([prompt_clean])[0]

        # Task + confidence
        task, confidence = emb_cls.classify(prompt)
        if confidence < self.min_confidence:
            task = self.low_confidence_fallback
            used_fallback = True

        # Complexity
        h_score = _complexity_heuristic(prompt)
        if self.complexity_use_embedding:
            e_score = emb_cls.complexity_score(prompt_emb)
            complexity = 0.5 * h_score + 0.5 * e_score
        else:
            complexity = h_score
        if complexity < 0.33:
            tier = ComplexityTier.LOW
        elif complexity < 0.66:
            tier = ComplexityTier.MEDIUM
        else:
            tier = ComplexityTier.HIGH

        # System alignment
        alignment: float | None = None
        if system_prompt and system_prompt.strip():
            sys_list = emb_cls._encode([system_prompt.strip()])[0]
            alignment = emb_cls.system_alignment_score(prompt_emb, sys_list)

        latency_ms = (time.perf_counter() - t0) * 1000
        return ClassificationResult(
            task_type=task,
            confidence=confidence,
            complexity_score=round(complexity, 4),
            complexity_tier=tier,
            system_alignment_score=alignment,
            used_fallback=used_fallback,
            latency_ms=round(latency_ms, 2),
        )

    def classify_batch(
        self,
        prompts: list[str],
    ) -> list[tuple[TaskType, float]]:
        """Batch classify. Uses single encode() for all prompts needing embedding."""
        if not prompts:
            return []
        results: list[tuple[TaskType, float] | None] = [None] * len(prompts)
        to_embed_indices: list[int] = []
        to_embed_prompts: list[str] = []
        for i, p in enumerate(prompts):
            key = self._cache_key(p, None)
            cached = self._get_cached(key)
            if cached is not None:
                results[i] = cached
                continue
            if self.use_keyword_fallback:
                kw = _keyword_detect_generation(p)
                if kw is not None:
                    results[i] = kw
                    self._set_cached(key, kw)
                    continue
            to_embed_indices.append(i)
            to_embed_prompts.append(p)
        if to_embed_prompts:
            try:
                emb_cls = self._get_embedding_classifier()
                batch_results = emb_cls.classify_embeddings(to_embed_prompts)
                for idx, (task, conf) in zip(to_embed_indices, batch_results, strict=True):
                    if conf < self.min_confidence:
                        res = (self.low_confidence_fallback, conf)
                    else:
                        res = (task, conf)
                    results[idx] = res
                    self._set_cached(self._cache_key(prompts[idx], None), res)
            except Exception as e:
                logger.warning("Batch classification failed, using fallbacks: %s", e)
                for idx in to_embed_indices:
                    if self.use_keyword_fallback:
                        kw = _keyword_detect_generation(prompts[idx])
                        if kw is not None:
                            results[idx] = kw
                            self._set_cached(self._cache_key(prompts[idx], None), kw)
                            continue
                    res = (self.low_confidence_fallback, 0.0)
                    results[idx] = res
                    self._set_cached(self._cache_key(prompts[idx], None), res)
        return [r for r in results if r is not None]

    def warmup(self) -> None:
        """Load the model explicitly. Call before first classify to avoid latency spike."""
        self._get_embedding_classifier()._ensure_loaded()

    def clear_cache(self) -> None:
        """Clear classification cache. Use when examples or config change."""
        with self._cache_lock:
            self._cache.clear()
