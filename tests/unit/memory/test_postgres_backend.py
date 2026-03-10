"""Tests for PostgresBackend - SQL injection safety and table validation."""

from __future__ import annotations

import pytest

from syrin.memory.backends.postgres import POSTGRES_AVAILABLE, PostgresBackend


class TestPostgresBackendTableValidation:
    """Test table name validation prevents SQL injection."""

    def test_invalid_table_sql_injection_raises(self) -> None:
        """Table names with SQL injection attempts raise ValueError."""
        if not POSTGRES_AVAILABLE:
            pytest.skip("psycopg2 not installed")
        with pytest.raises(ValueError, match="Invalid table name"):
            PostgresBackend(
                table="memories; DROP TABLE users; --",
                host="localhost",
                database="syrin",
                user="postgres",
                password="",
            )

    def test_invalid_table_semicolon_raises(self) -> None:
        """Table names with semicolons raise ValueError."""
        if not POSTGRES_AVAILABLE:
            pytest.skip("psycopg2 not installed")
        with pytest.raises(ValueError, match="Invalid table name"):
            PostgresBackend(table="foo;bar", host="localhost", database="syrin")

    def test_invalid_table_starts_with_digit_raises(self) -> None:
        """Table names starting with digit raise ValueError."""
        if not POSTGRES_AVAILABLE:
            pytest.skip("psycopg2 not installed")
        with pytest.raises(ValueError, match="Invalid table name"):
            PostgresBackend(table="123invalid", host="localhost", database="syrin")

    def test_invalid_table_special_chars_raises(self) -> None:
        """Table names with special chars raise ValueError."""
        if not POSTGRES_AVAILABLE:
            pytest.skip("psycopg2 not installed")
        with pytest.raises(ValueError, match="Invalid table name"):
            PostgresBackend(table="my-table", host="localhost", database="syrin")

    def test_invalid_table_space_raises(self) -> None:
        """Table names with spaces raise ValueError."""
        if not POSTGRES_AVAILABLE:
            pytest.skip("psycopg2 not installed")
        with pytest.raises(ValueError, match="Invalid table name"):
            PostgresBackend(table="my table", host="localhost", database="syrin")

    def test_valid_table_name_passes_validation(self) -> None:
        """Valid table names pass validation (connection may still fail)."""
        if not POSTGRES_AVAILABLE:
            pytest.skip("psycopg2 not installed")
        # This will attempt to connect; we expect connection to fail or succeed
        # but NOT validation to fail
        try:
            backend = PostgresBackend(
                table="valid_memories",
                host="localhost",
                database="syrin",
                user="postgres",
                password="",
            )
            backend.close()
        except ValueError as e:
            pytest.fail(f"Valid table name should not raise ValueError: {e}")
        # Connection errors (refused, etc.) are acceptable
