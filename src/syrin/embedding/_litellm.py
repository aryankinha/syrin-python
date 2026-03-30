"""LiteLLM embedding provider."""

from __future__ import annotations

import os

import litellm

# Default dimensions per model (common models)
_MODEL_DIMENSIONS: dict[str, int] = {
    "cohere/embed-english-v3.0": 1024,
    "cohere/embed-english-v3.1": 1024,
    "cohere/embed-multilingual-v3.0": 1024,
    "cohere/embed-english-v2.0": 4096,
    "cohere/embed-multilingual-v2.0": 768,
    "voyageai/voyage-2": 1024,
    "voyageai/voyage-2-base": 1536,
    "voyageai/voyage-lite-2": 1024,
    "mistral/mistral-embed": 1024,
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "openai/text-embedding-ada-002": 1536,
}


class LiteLLMEmbedding:
    """Any embedding provider via LiteLLM (Cohere, Voyage, Mistral, OpenAI, etc.).

    Supports 50+ embedding models through LiteLLM unified API.
    Uses LITELLM_API_KEY environment variable if api_key not provided.

    Example:
        provider = LiteLLMEmbedding("cohere/embed-english-v3.0")
        embeddings = await provider.embed(["hello world"])
    """

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        batch_size: int = 100,
    ) -> None:
        """Initialize LiteLLM embedding provider.

        Args:
            model: LiteLLM model string (e.g., 'cohere/embed-english-v3.0').
            api_key: Optional API key. Defaults to LITELLM_API_KEY env var.
            batch_size: Max texts per API call. P8: defaults to 100 to avoid
                       payload-size and rate-limit issues with large corpora.
        """
        self._model = model
        self._api_key = api_key or os.getenv("LITELLM_API_KEY")
        self._dimensions = _MODEL_DIMENSIONS.get(model, 1024)
        self._batch_size = batch_size

    @property
    def batch_size(self) -> int:
        """Max texts per API call."""
        return self._batch_size

    @property
    def dimensions(self) -> int:
        """Vector dimensionality."""
        return self._dimensions

    @property
    def model(self) -> str:
        """Model name."""
        return self._model

    @property
    def model_id(self) -> str:
        """Model identifier for cost tracking."""
        return self._model

    async def embed(
        self,
        texts: list[str],
        budget_tracker: object | None = None,
    ) -> list[list[float]]:
        """Embed texts into vectors.

        Args:
            texts: List of text strings to embed.
            budget_tracker: Optional BudgetTracker for cost tracking.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # P8: split into batches to avoid payload-size and rate-limit issues
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]

            kwargs: dict[str, object] = {
                "model": self._model,
                "input": batch,
            }

            if self._api_key:
                kwargs["api_key"] = self._api_key

            response = await litellm.aembedding(**kwargs)

            all_embeddings.extend(item["embedding"] for item in response["data"])

            # Track cost if budget_tracker provided
            if budget_tracker is not None:
                usage = response.get("usage", {})
                token_count = usage.get("prompt_tokens", 0)
                if token_count > 0:
                    from syrin.cost import calculate_embedding_cost

                    cost = calculate_embedding_cost(self._model, token_count)
                    budget_tracker.record_external(  # type: ignore[attr-defined]
                        service="litellm_embedding",
                        cost_usd=cost,
                        metadata={
                            "model": self._model,
                            "token_count": token_count,
                        },
                    )

        return all_embeddings
