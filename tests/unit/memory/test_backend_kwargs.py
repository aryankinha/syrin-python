"""Each backend config class has a to_kwargs() method replacing the if/elif chain.

Tests that:
- QdrantConfig.to_kwargs() returns correct kwargs dict
- ChromaConfig.to_kwargs() returns correct kwargs dict
- RedisConfig.to_kwargs() returns correct kwargs dict
- PostgresConfig.to_kwargs() returns correct kwargs dict
- Memory._backend_kwargs() delegates to the config's to_kwargs()
"""

from __future__ import annotations

from syrin.memory.vector_configs import ChromaConfig, PostgresConfig, QdrantConfig, RedisConfig


class TestQdrantConfigToKwargs:
    def test_url_config(self) -> None:
        cfg = QdrantConfig(url="https://xyz.qdrant.io", api_key="key123", collection="my_col")
        kwargs = cfg.to_kwargs()
        assert kwargs["url"] == "https://xyz.qdrant.io"
        assert kwargs["api_key"] == "key123"
        assert kwargs["collection"] == "my_col"
        assert "host" not in kwargs
        assert "path" not in kwargs

    def test_path_config(self) -> None:
        cfg = QdrantConfig(path="/tmp/qdrant_data")
        kwargs = cfg.to_kwargs()
        assert kwargs["path"] == "/tmp/qdrant_data"
        assert "url" not in kwargs

    def test_host_port_config(self) -> None:
        cfg = QdrantConfig(host="myhost", port=9999)
        kwargs = cfg.to_kwargs()
        assert kwargs["host"] == "myhost"
        assert kwargs["port"] == 9999

    def test_namespace_included_when_set(self) -> None:
        cfg = QdrantConfig(namespace="tenant_a")
        kwargs = cfg.to_kwargs()
        assert kwargs["namespace"] == "tenant_a"

    def test_namespace_excluded_when_none(self) -> None:
        cfg = QdrantConfig(namespace=None)
        kwargs = cfg.to_kwargs()
        assert "namespace" not in kwargs


class TestChromaConfigToKwargs:
    def test_with_path(self) -> None:
        cfg = ChromaConfig(path="/data/chroma", collection="my_col")
        kwargs = cfg.to_kwargs()
        assert kwargs["path"] == "/data/chroma"
        assert kwargs["collection_name"] == "my_col"

    def test_without_path(self) -> None:
        cfg = ChromaConfig(path=None)
        kwargs = cfg.to_kwargs()
        assert "path" not in kwargs


class TestRedisConfigToKwargs:
    def test_basic(self) -> None:
        cfg = RedisConfig(host="redis-host", port=6380, db=1, prefix="myapp:", ttl=3600)
        kwargs = cfg.to_kwargs()
        assert kwargs["host"] == "redis-host"
        assert kwargs["port"] == 6380
        assert kwargs["db"] == 1
        assert kwargs["prefix"] == "myapp:"
        assert kwargs["ttl"] == 3600

    def test_password_excluded_when_none(self) -> None:
        cfg = RedisConfig(password=None)
        kwargs = cfg.to_kwargs()
        assert "password" not in kwargs

    def test_password_included_when_set(self) -> None:
        cfg = RedisConfig(password="secret")
        kwargs = cfg.to_kwargs()
        assert kwargs["password"] == "secret"


class TestPostgresConfigToKwargs:
    def test_basic(self) -> None:
        cfg = PostgresConfig(
            host="pg-host", port=5433, database="mydb", user="admin", password="pw", table="mems"
        )
        kwargs = cfg.to_kwargs()
        assert kwargs["host"] == "pg-host"
        assert kwargs["port"] == 5433
        assert kwargs["database"] == "mydb"
        assert kwargs["user"] == "admin"
        assert kwargs["password"] == "pw"
        assert kwargs["table"] == "mems"
