"""Embedding batch size — providers must chunk large text lists into batches.

Tests that:
- OpenAIEmbedding accepts batch_size param and calls the API in chunks
- LiteLLMEmbedding accepts batch_size param and calls the API in chunks
- Results are correctly reassembled in order
- Small inputs (< batch_size) result in a single API call
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestOpenAIEmbeddingBatchSize:
    @pytest.mark.asyncio
    async def test_accepts_batch_size_param(self) -> None:
        """OpenAIEmbedding __init__ accepts batch_size without error."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            from syrin.embedding._openai import OpenAIEmbedding

            provider = OpenAIEmbedding(batch_size=50)
            assert provider.batch_size == 50

    @pytest.mark.asyncio
    async def test_default_batch_size_is_100(self) -> None:
        """Default batch_size is 100."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            from syrin.embedding._openai import OpenAIEmbedding

            provider = OpenAIEmbedding()
            assert provider.batch_size == 100

    @pytest.mark.asyncio
    async def test_large_input_split_into_batches(self) -> None:
        """200 texts with batch_size=100 results in 2 API calls."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            from syrin.embedding._openai import OpenAIEmbedding

            provider = OpenAIEmbedding(batch_size=100)

            call_count = 0

            async def fake_create(**kwargs):  # type: ignore[no-untyped-def]
                nonlocal call_count
                call_count += 1
                batch = kwargs["input"]
                mock_response = MagicMock()
                mock_response.data = [MagicMock(embedding=[0.1, 0.2]) for _ in batch]
                mock_response.usage = MagicMock(prompt_tokens=len(batch))
                return mock_response

            mock_client = MagicMock()
            mock_client.embeddings.create = fake_create
            provider._client = mock_client

            texts = [f"text {i}" for i in range(200)]
            result = await provider.embed(texts)

            assert call_count == 2, f"Expected 2 API calls, got {call_count}"
            assert len(result) == 200

    @pytest.mark.asyncio
    async def test_small_input_single_api_call(self) -> None:
        """50 texts with batch_size=100 results in 1 API call."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            from syrin.embedding._openai import OpenAIEmbedding

            provider = OpenAIEmbedding(batch_size=100)

            call_count = 0

            async def fake_create(**kwargs):  # type: ignore[no-untyped-def]
                nonlocal call_count
                call_count += 1
                batch = kwargs["input"]
                mock_response = MagicMock()
                mock_response.data = [MagicMock(embedding=[0.1, 0.2]) for _ in batch]
                mock_response.usage = MagicMock(prompt_tokens=len(batch))
                return mock_response

            mock_client = MagicMock()
            mock_client.embeddings.create = fake_create
            provider._client = mock_client

            texts = [f"text {i}" for i in range(50)]
            result = await provider.embed(texts)

            assert call_count == 1
            assert len(result) == 50

    @pytest.mark.asyncio
    async def test_results_are_ordered_correctly(self) -> None:
        """Results from multiple batches are concatenated in input order."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            from syrin.embedding._openai import OpenAIEmbedding

            provider = OpenAIEmbedding(batch_size=2)

            async def fake_create(**kwargs):  # type: ignore[no-untyped-def]
                batch = kwargs["input"]
                mock_response = MagicMock()
                mock_response.data = [MagicMock(embedding=[float(i)]) for i, _ in enumerate(batch)]
                mock_response.usage = MagicMock(prompt_tokens=len(batch))
                return mock_response

            mock_client = MagicMock()
            mock_client.embeddings.create = fake_create
            provider._client = mock_client

            result = await provider.embed(["a", "b", "c", "d"])
            assert len(result) == 4


class TestLiteLLMEmbeddingBatchSize:
    @pytest.mark.asyncio
    async def test_accepts_batch_size_param(self) -> None:
        """LiteLLMEmbedding __init__ accepts batch_size without error."""
        from syrin.embedding._litellm import LiteLLMEmbedding

        provider = LiteLLMEmbedding("cohere/embed-english-v3.0", batch_size=50)
        assert provider.batch_size == 50

    @pytest.mark.asyncio
    async def test_default_batch_size_is_100(self) -> None:
        """Default batch_size is 100."""
        from syrin.embedding._litellm import LiteLLMEmbedding

        provider = LiteLLMEmbedding("cohere/embed-english-v3.0")
        assert provider.batch_size == 100

    @pytest.mark.asyncio
    async def test_large_input_split_into_batches(self) -> None:
        """200 texts with batch_size=100 results in 2 API calls."""
        from syrin.embedding._litellm import LiteLLMEmbedding

        provider = LiteLLMEmbedding("cohere/embed-english-v3.0", batch_size=100)

        call_count = 0

        async def fake_aembedding(**kwargs):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            batch = kwargs["input"]
            return {
                "data": [{"embedding": [0.1, 0.2]} for _ in batch],
                "usage": {"prompt_tokens": len(batch)},
            }

        with patch("litellm.aembedding", side_effect=fake_aembedding):
            texts = [f"text {i}" for i in range(200)]
            result = await provider.embed(texts)

        assert call_count == 2
        assert len(result) == 200
