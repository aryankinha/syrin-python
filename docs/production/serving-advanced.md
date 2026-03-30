---
title: Serving - Advanced
description: Mount on existing FastAPI apps, middleware, and production patterns
weight: 104
---

## Beyond the Basics

Most guides show `agent.serve(port=8000)` and stop there. But real production systems need more: mounting on existing apps, authentication middleware, multiple servers behind a load balancer, SSL termination, and more.

This page covers advanced serving patterns for production deployments.

## The Problem

Your application likely has:
- Existing FastAPI/Starlette infrastructure
- Authentication middleware
- Rate limiting
- Logging infrastructure
- CORS configuration

Simply calling `agent.serve()` creates a separate server. You need to integrate the agent into your existing stack.

## Mounting on Existing FastAPI Apps

Use `agent.as_router()` to get an APIRouter you can include in any FastAPI app:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from syrin import Agent, Model, Budget

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

agent = Agent(
    model=model,
    system_prompt="You are a helpful assistant.",
    budget=Budget(max_cost=10.00),
)

app = FastAPI(title="My Application")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the agent
app.include_router(agent.as_router(), prefix="/agent")

# Your other routes
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id, "name": "Alice"}

# Run: uvicorn main:app --reload
```

**Endpoints:**
- `POST /agent/chat`
- `POST /agent/stream`
- `GET /agent/health`
- `GET /core/budget`
- `GET /agent/describe`
- `GET /users/{user_id}`

## Custom Prefix

Control the URL path:

```python
app.include_router(agent.as_router(), prefix="/api/v1/chatbot")
```

**Endpoints:**
- `POST /api/v1/chatbot/chat`
- `POST /api/v1/chatbot/stream`
- `GET /api/v1/chatbot/health`

## Custom Middleware

Add request logging, authentication, or rate limiting:

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger("myapp")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health checks
        if request.url.path in ["/health", "/ready"]:
            return await call_next(request)
        
        # Check API key
        api_key = request.headers.get("X-API-Key")
        if not api_key or not validate_key(api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or missing API key"},
            )
        
        return await call_next(request)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        logger.info(
            f"{request.method} {request.url.path} "
            f"-> {response.status_code} ({duration:.3f}s)"
        )
        return response

app = FastAPI()
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)
app.include_router(agent.as_router(), prefix="/agent")
```

## AgentRouter for Multiple Agents

```python
from syrin import Agent, Model, Budget
from syrin.serve import AgentRouter, ServeConfig

model = Model.OpenAI("gpt-4o", api_key="your-api-key")

router = AgentRouter(
    agents=[
        Agent(
            model=model,
            system_prompt="You are a researcher.",
            budget=Budget(max_cost=1.00),
        ),
        Agent(
            model=model,
            system_prompt="You are a writer.",
            budget=Budget(max_cost=1.00),
        ),
    ],
    config=ServeConfig(
        enable_playground=True,
        debug=True,
    ),
)

# Option 1: Use router.serve() (creates new server)
router.serve(port=8000)

# Option 2: Mount on existing app
app.include_router(router.fastapi_router(), prefix="/api/v1")
```

**Endpoints:**
- `POST /api/v1/researcher/chat`
- `POST /api/v1/writer/chat`
- `GET /api/v1/researcher/health`
- `GET /api/v1/writer/health`
- `GET /api/v1/researcher/budget`
- `GET /api/v1/playground/config`

## Playground on Existing App

Enable the web playground with multi-agent selection:

```python
from syrin.serve import AgentRouter, ServeConfig

router = AgentRouter(
    agents=[researcher, writer],
    config=ServeConfig(enable_playground=True, debug=True),
)

app = FastAPI()
app.include_router(router.fastapi_router())

# Playground is available at /playground
# Agent selector shows both researcher and writer
```

**Note**: Static file mounting requires calling `add_playground_static_mount()` on the main app:

```python
from syrin.serve.playground import add_playground_static_mount

app = FastAPI()
app.include_router(router.fastapi_router())
add_playground_static_mount(app, "/playground")  # After include_router
```

## SSL/TLS Termination

Run behind a reverse proxy (recommended) or terminate SSL directly:

### Option 1: Reverse Proxy (Recommended)

```bash
# nginx config
upstream agent_backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl;
    server_name api.myapp.com;
    
    ssl_certificate /etc/ssl/myapp.crt;
    ssl_certificate_key /etc/ssl/myapp.key;
    
    location / {
        proxy_pass http://agent_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 2: Direct HTTPS with Uvicorn

```python
import uvicorn
from fastapi import FastAPI
from syrin import Agent

app = FastAPI()
app.include_router(agent.as_router())

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8443,
    ssl_certfile="cert.pem",
    ssl_keyfile="key.pem",
)
```

## Multi-Worker Considerations

### The Problem

Syrin uses `workers=1` by default. This is intentional because:

- **In-memory state** (conversation history, budget tracking) is per-process
- **Memory backends** configured without persistence lose state across restarts
- **Budget tracking** is in-process

### Solution: Shared Backends

For multi-worker deployments, use shared backends:

```python
from syrin import Agent, Model, Budget, Memory, Context
from syrin.memory import MemoryBackend

agent = Agent(
    model=model,
    memory=Memory(backend=MemoryBackend.REDIS, url="redis://shared-redis:6379"),
    budget=Budget(max_cost=10.00),  # Per-request budget still works
    context=Context(map_backend="file", map_path="/shared/state/context_map.json"),
)
```

**Backend options by feature:**

| Feature | Single Worker | Multi-Worker |
|---------|---------------|--------------|
| Memory | In-memory (default) | Redis, Postgres, file |
| Budget | In-process | Distributed tracking |
| Checkpoints | File (default) | Database, Redis |
| Context map | File (default) | Database |

### Workers with Gunicorn

```python
# gunicorn_config.py
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
```

```bash
gunicorn -c gunicorn_config.py main:app
```

**Warning**: Each worker has separate memory/budget state. Use shared backends.

## Health Checks Behind Load Balancer

### Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: agent
          image: myagent:latest
          ports:
            - containerPort: 8000
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
```

### Custom Readiness Logic

The readiness probe checks if the agent is initialized. For custom logic (e.g., checking model connectivity):

```python
# Extend the app
from fastapi import FastAPI
from syrin import Agent

app = FastAPI()

@app.get("/ready")
async def ready():
    # Custom checks
    try:
        # Check model connectivity
        await model.check_connection()
        return {"ready": True}
    except Exception as e:
        return {"ready": False, "error": str(e)}

app.include_router(agent.as_router())
```

## Rate Limiting

Add rate limiting at the middleware level:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/agent/chat")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def chat(request: Request):
    # Your logic
    pass
```

## Production Checklist

Before going to production:

- [ ] **Authentication**: Add API key or OAuth middleware
- [ ] **TLS**: Terminate SSL at reverse proxy or use uvicorn with certs
- [ ] **CORS**: Configure allowed origins
- [ ] **Rate limiting**: Prevent abuse
- [ ] **Logging**: Structured logging with correlation IDs
- [ ] **Health checks**: Liveness and readiness probes
- [ ] **Monitoring**: Export metrics (Prometheus, Datadog)
- [ ] **Shared backends**: Redis/Postgres for memory if multi-worker
- [ ] **Budget alerts**: Set up alerts when budget is low
- [ ] **Playground disabled**: `enable_playground=False` in production

## See Also

- [Serving: HTTP API](/agent-kit/production/serving-http) — REST API reference
- [Serving: CLI](/agent-kit/production/serving-cli) — Interactive terminal
- [Playground](/agent-kit/production/playground) — Web testing interface
- [Remote Config](/agent-kit/production/remote-config) — Runtime configuration updates
- [Checkpointing](/agent-kit/production/checkpointing) — State persistence
