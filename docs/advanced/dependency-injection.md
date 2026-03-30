---
title: Dependency Injection
description: Build testable agents with injectable dependencies via RunContext
weight: 230
---

## Hardcoded Dependencies Make Testing Hard

Imagine you have an agent with a tool that queries a database:

```python
class MyAgent(Agent):
    @tool
    def get_user(self, user_id: str) -> str:
        # Hardcoded database connection
        db = Database("production-db")
        return db.get_user(user_id)
```

**Problems:**
- Every test hits the production database
- Can't mock the database for unit tests
- No way to test different database states
- Tool logic is coupled to infrastructure

**The solution:** `RunContext[Deps]` — declare dependencies, inject them at runtime.

## The RunContext Pattern

Syrin's dependency injection uses `RunContext[Deps]`:

```python
from dataclasses import dataclass
from syrin import Agent, tool, RunContext

@dataclass
class MyDeps:
    db: Database
    user_id: str


class MyAgent(Agent):
    @tool
    def get_user(self, ctx: RunContext[MyDeps], user_id: str) -> str:
        # Database injected at runtime
        return ctx.deps.db.get_user(user_id)
```

**What just happened:**
1. You declared `MyDeps` as a dataclass with your dependencies
2. Tools can request `ctx: RunContext[MyDeps]` as their first parameter
3. At runtime, Syrin injects the configured dependencies
4. In tests, you inject mocks

## RunContext Explained

```python
@dataclass
class RunContext(Generic[DepsT]):
    """Context passed to tools when dependency injection is configured."""
    
    deps: DepsT           # Your injected dependencies
    agent_name: str        # Current agent class name
    conversation_id: str    # Current conversation ID
    budget_state: BudgetState | None  # Budget tracking
    retry_count: int      # Retry attempt number
```

### Accessing Dependencies

```python
class MyAgent(Agent):
    @tool
    def search_products(
        self,
        ctx: RunContext[MyDeps],  # Must be first param
        query: str,
        limit: int = 10,
    ) -> str:
        # Access via ctx.deps
        results = ctx.deps.db.search(query, limit=limit)
        
        # Access metadata
        print(f"Agent: {ctx.agent_name}")
        print(f"User: {ctx.deps.user_id}")
        print(f"Conversation: {ctx.conversation_id}")
        
        return str(results)
```

## Setting Up Dependencies

Pass dependencies when creating the agent:

```python
@dataclass
class AppDeps:
    db: Database
    search_client: SearchClient
    user_id: str
    api_keys: dict[str, str]


class MyAgent(Agent):
    @tool
    def search(self, ctx: RunContext[AppDeps], query: str) -> str:
        return ctx.deps.search_client.search(query)


# Create dependencies
deps = AppDeps(
    db=Database("production"),
    search_client=SearchClient(),
    user_id="user123",
    api_keys={"openai": os.getenv("OPENAI_API_KEY")},
)

# Inject into agent
agent = MyAgent(deps=deps)
```

## Testing with Mock Dependencies

This is where DI shines:

```python
import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

from syrin import Agent, RunContext


@dataclass
class AppDeps:
    db: Database
    search_client: SearchClient


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.users = {
            "1": {"name": "Alice", "email": "alice@example.com"},
            "2": {"name": "Bob", "email": "bob@example.com"},
        }
    
    def get_user(self, user_id: str) -> dict | None:
        return self.users.get(user_id)


class MockSearchClient:
    """Mock search client for testing."""
    
    def __init__(self):
        self.searches = []
    
    def search(self, query: str) -> list[dict]:
        self.searches.append(query)
        return [{"id": "1", "title": "Result 1"}]


class MyAgent(Agent):
    @tool
    def get_user(self, ctx: RunContext[AppDeps], user_id: str) -> str:
        user = ctx.deps.db.get_user(user_id)
        if not user:
            return "User not found"
        return f"{user['name']} ({user['email']})"


def test_get_existing_user():
    """Test getting an existing user."""
    # Create mock dependencies
    mock_db = MockDatabase()
    mock_search = MockSearchClient()
    deps = AppDeps(db=mock_db, search_client=mock_search)
    
    # Create agent with mock deps
    agent = MyAgent(deps=deps)
    
    # Test the tool
    result = agent.run("Get user 1")
    
    assert "Alice" in result.content
    assert "alice@example.com" in result.content


def test_get_nonexistent_user():
    """Test getting a user that doesn't exist."""
    mock_db = MockDatabase()
    mock_search = MockSearchClient()
    deps = AppDeps(db=mock_db, search_client=mock_search)
    
    agent = MyAgent(deps=deps)
    
    result = agent.run("Get user 999")
    
    assert "not found" in result.content.lower()


def test_search_called():
    """Test that search was called with correct query."""
    mock_db = MockDatabase()
    mock_search = MockSearchClient()
    deps = AppDeps(db=mock_db, search_client=mock_search)
    
    agent = MyAgent(deps=deps)
    agent.run("Search for Python")
    
    assert "python" in mock_search.searches
```

## Multi-Tenant Agents

Different users get different dependencies:

```python
@dataclass
class TenantDeps:
    tenant_id: str
    db: Database          # Per-tenant database
    permissions: set[str]  # User permissions
    rate_limit: int       # Rate limit for this tenant


class TenantAwareAgent(Agent):
    @tool
    def get_data(self, ctx: RunContext[TenantDeps], resource_id: str) -> str:
        # Check permissions
        if "read" not in ctx.deps.permissions:
            return "Permission denied"
        
        # Query tenant-specific database
        data = ctx.deps.db.query(
            tenant_id=ctx.deps.tenant_id,
            resource_id=resource_id,
        )
        return str(data)


# Create tenant-specific agents
def create_tenant_agent(tenant_id: str, user_role: str) -> TenantAwareAgent:
    permissions = {"read", "write"} if user_role == "admin" else {"read"}
    
    deps = TenantDeps(
        tenant_id=tenant_id,
        db=Database(f"tenant_{tenant_id}"),
        permissions=permissions,
        rate_limit=100 if user_role == "admin" else 10,
    )
    
    return TenantAwareAgent(deps=deps)


# Different agents for different tenants
admin_agent = create_tenant_agent("tenant-1", "admin")
user_agent = create_tenant_agent("tenant-1", "user")
```

## Complex Dependency Graphs

For larger applications, use a dependency container:

```python
from dataclasses import dataclass, field
from typing import Protocol


class Database(Protocol):
    def query(self, sql: str) -> list[dict]: ...


class Cache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl: int) -> None: ...


@dataclass
class AppServices:
    """All application services as dependencies."""
    db: Database
    cache: Cache
    llm_provider: str = "openai"


class ServiceContainer:
    """Builds dependency graphs."""
    
    def __init__(self):
        self._services: dict[type, object] = {}
    
    def register(self, service_type: type, instance: object) -> "ServiceContainer":
        self._services[service_type] = instance
        return self
    
    def build(self) -> AppServices:
        # Build in dependency order
        db = self._services.get(Database) or self._create_db()
        cache = self._services.get(Cache) or self._create_cache()
        
        return AppServices(
            db=db,
            cache=cache,
        )
    
    def _create_db(self) -> Database:
        return PostgresDatabase("prod-db")
    
    def _create_cache(self) -> Cache:
        return RedisCache("redis://localhost")


# In production
container = ServiceContainer()
services = container.build()
agent = MyAgent(deps=services)


# In tests
@pytest.fixture
def test_container():
    container = ServiceContainer()
    container.register(Database, MockDatabase())
    container.register(Cache, MockCache())
    return container.build()


def test_with_fakes(test_container):
    agent = MyAgent(deps=test_container)
    # Test with mocks
```

## Accessing Runtime State

`RunContext` provides more than just your dependencies:

```python
class MyAgent(Agent):
    @tool
    def query(self, ctx: RunContext[MyDeps], sql: str) -> str:
        # Budget state
        if ctx.budget_state:
            remaining = ctx.budget_state.remaining
            if remaining < 0.01:
                return "Budget nearly exhausted"
        
        # Retry count (useful for output validation loops)
        if ctx.retry_count > 0:
            print(f"Retry attempt {ctx.retry_count}")
        
        # Agent name
        print(f"Running on agent: {ctx.agent_name}")
        
        # Conversation ID (for tracing)
        print(f"Conversation: {ctx.conversation_id}")
        
        return ctx.deps.db.query(sql)
```

## Partial Dependencies

Not all dependencies need to be provided upfront:

```python
@dataclass
class FlexibleDeps:
    db: Database | None = None
    cache: Cache | None = None
    api_key: str | None = None


class MyAgent(Agent):
    @tool
    def query(self, ctx: RunContext[FlexibleDeps], sql: str) -> str:
        # Gracefully handle missing dependencies
        if ctx.deps.db is None:
            return "Database not configured"
        
        # Use cache if available
        cache_key = f"query:{hash(sql)}"
        if ctx.deps.cache:
            cached = ctx.deps.cache.get(cache_key)
            if cached:
                return cached
        
        result = ctx.deps.db.query(sql)
        
        if ctx.deps.cache:
            ctx.deps.cache.set(cache_key, result, ttl=300)
        
        return result


# Agent with minimal deps
agent = MyAgent(deps=FlexibleDeps(api_key="..."))

# Or with full deps
agent = MyAgent(deps=FlexibleDeps(
    db=Database("prod"),
    cache=Cache("redis://"),
    api_key="...",
))
```

## Type Safety

The generic type ensures compile-time checking:

```python
@dataclass
class CorrectDeps:
    name: str


class MyAgent(Agent):
    @tool
    def hello(self, ctx: RunContext[CorrectDeps], name: str) -> str:
        # TypeScript-like autocomplete works here
        return f"Hello {name}, I'm {ctx.deps.name}"


# Wrong type - IDE will warn
agent = MyAgent(deps="not a dataclass")  # Type error

# Must provide correct type
agent = MyAgent(deps=CorrectDeps(name="Assistant"))
```

## Fixture Patterns for pytest

```python
import pytest
from dataclasses import dataclass


@dataclass
class TestDeps:
    db: MockDatabase
    cache: MockCache


@pytest.fixture
def mock_deps():
    return TestDeps(
        db=MockDatabase(),
        cache=MockCache(),
    )


@pytest.fixture
def test_agent(mock_deps):
    return MyAgent(deps=mock_deps)


def test_with_fixture(test_agent):
    result = test_agent.run("Get user 1")
    assert "Alice" in result.content
```

## What's Next?

- [Testing](/agent-kit/advanced/testing) — Complete testing patterns
- [Event Bus](/agent-kit/advanced/event-bus) — Domain events
- [Custom Context](/agent-kit/advanced/custom-context) — Custom context management
- [Custom Model](/agent-kit/advanced/custom-model) — Custom LLM providers

## See Also

- [Tools Reference](/agent-kit/agent/tools) — Tool decorator
- [Testing](/agent-kit/advanced/testing) — Mock models and tools
- [Multi-Tenant Patterns](/agent-kit/core/models) — Multi-tenant architectures
