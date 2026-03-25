---
title: Deployment
description: Production deployment strategies, infrastructure, and operational best practices
weight: 160
---

## The Journey to Production

Your agent works beautifully in development. The CLI is responsive, the playground is handy, and `agent.run()` does exactly what you need.

But production is different. Multiple users. 24/7 availability. Load spikes. Security reviews. Monitoring dashboards. And the dreaded 3 AM wake-up call when something breaks.

This guide walks you through deploying Syrin agents to production—from simple single-server setups to complex multi-region architectures.

## The Production Gap

Development is forgiving:
- Single user, single request
- No authentication needed
- Local resources
- Manual debugging
- Restart on errors

Production demands:
- Multiple concurrent users
- Authentication and authorization
- Scalability under load
- Automated monitoring
- Graceful error handling

Let's close that gap.

## Deployment Patterns

### Pattern 1: Simple Server

For low-traffic applications:

```python
from syrin import Agent, Model, Budget, ServeConfig

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    system_prompt="You are a helpful assistant.",
    budget=Budget(max_cost=10.00),
)

agent.serve(
    config=ServeConfig(
        host="0.0.0.0",
        port=8000,
    )
)
```

**When to use:**
- Low traffic (< 100 requests/day)
- Simple use cases
- Cost-effective for testing
- Single region

**Limitations:**
- Single point of failure
- No horizontal scaling
- Manual restarts on failure

### Pattern 2: Process Manager

For production with basic reliability:

```python
# Using systemd
# /etc/systemd/system/syrin-agent.service

[Unit]
Description=Syrin AI Agent
After=network.target

[Service]
Type=simple
User=syrin
WorkingDirectory=/opt/agent
Environment="OPENAI_API_KEY=your-key"
ExecStart=/usr/bin/python -m agent_server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Start the service:**
```bash
sudo systemctl start syrin-agent
sudo systemctl enable syrin-agent  # Start on boot
```

**When to use:**
- Production workloads
- Need automatic restarts
- Single server is sufficient

### Pattern 3: Container Deployment

For cloud-native deployments:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY . .

# Run as non-root
USER nobody

CMD ["python", "-m", "agent_server"]
```

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent
  template:
    metadata:
      labels:
        app: agent
    spec:
      containers:
        - name: agent
          image: myagent:latest
          ports:
            - containerPort: 8000
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: agent-secrets
                  key: openai-api-key
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "2Gi"
              cpu: "2000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
```

**When to use:**
- Cloud-native infrastructure
- Auto-scaling requirements
- Multi-environment (dev/staging/prod)
- Need high availability

### Pattern 4: Serverless

For event-driven workloads:

```python
# serverless/handler.py
import asyncio
from syrin import Agent, Model

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key=os.environ["OPENAI_API_KEY"]),
    system_prompt="You process requests efficiently.",
)


async def handler(event, context):
    body = json.loads(event["body"])
    result = await agent.arun(body["message"])
    return {
        "statusCode": 200,
        "body": json.dumps({"content": result.content}),
    }


# AWS Lambda
# export HANDLER=serverless.handler.handler
```

**When to use:**
- Event-driven architecture
- Traffic is bursty
- Want pay-per-use pricing
- Can tolerate cold starts

## Security Checklist

Before going to production:

### Authentication

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.security import APIKeyHeader

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")


async def verify_api_key(request: Request, key: str = Depends(api_key_header)):
    if key != os.environ["EXPECTED_API_KEY"]:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key


@app.post("/agent/chat")
async def chat(request: Request, api_key: str = Depends(verify_api_key)):
    # Your logic here
    pass
```

### TLS/HTTPS

Always use HTTPS in production:
- **Reverse proxy** (recommended): Terminate at nginx/Caddy
- **Direct**: Use uvicorn with certs

```python
# uvicorn with TLS
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8443,
    ssl_certfile="/etc/ssl/certs/server.crt",
    ssl_keyfile="/etc/ssl/private/server.key",
)
```

### Secrets Management

Never commit API keys:

```python
# Bad: Hardcoded key
api_key = "sk-12345..."

# Good: Environment variable
api_key = os.environ["OPENAI_API_KEY"]

# Better: Secret manager
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
api_key = client.access_secret_version(name="projects/.../secrets/api-key/versions/latest")
```

## Scaling Strategies

### Horizontal Scaling

With shared state backends:

```python
from syrin import Agent, Model, Memory
from syrin.memory import MemoryBackend

agent = Agent(
    model=Model.OpenAI("gpt-4o", api_key="your-api-key"),
    memory=Memory(backend=MemoryBackend.REDIS, url="redis://shared-redis:6379"),
    budget=Budget(max_cost=10.00),
)
```

**Scaling approach:**
- Add more agent instances behind a load balancer
- All instances share Redis for memory
- Budget tracking remains per-request (configure distributed tracking if needed)

### Vertical Scaling

Optimize single-instance performance:

```yaml
# Kubernetes resource tuning
resources:
  requests:
    memory: "2Gi"      # More memory for large contexts
    cpu: "2000m"       # Faster processing
  limits:
    memory: "4Gi"
    cpu: "4000m"
```

### Auto-Scaling

```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
```

## Monitoring and Observability

### Health Endpoints

```bash
# Liveness (is the server running?)
curl http://localhost:8000/health
# {"status": "ok"}

# Readiness (can it serve requests?)
curl http://localhost:8000/ready
# {"ready": true}
```

### Metrics Export

Add Prometheus metrics:

```python
from prometheus_client import Counter, Histogram, start_http_server

# Request metrics
REQUEST_COUNT = Counter(
    "agent_requests_total",
    "Total requests",
    ["endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "agent_request_latency_seconds",
    "Request latency",
    ["endpoint"]
)

# In your middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    REQUEST_COUNT.labels(
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

### Log Aggregation

Structured logging with correlation IDs:

```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", uuid.uuid4().hex)
    request.state.correlation_id = correlation_id
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

## High Availability

### Multi-Region Deployment

For global high availability, deploy agents across multiple regions:

- **Load balancer** routes traffic to the nearest healthy region
- **Primary region** (e.g., us-east) handles most traffic
- **Replica regions** (e.g., eu-west, ap-south) provide failover
- **Redis** clusters replicate data across regions for shared memory

### Database Replication

For persistent memory and checkpoints:

```yaml
# PostgreSQL primary-replica
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_DB: syrin
      POSTGRES_USER: syrin
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
    volumes:
      - postgres-primary-data:/var/lib/postgresql/data
    command: postgres -c wal_level=replica

  postgres-replica:
    image: postgres:15
    environment:
      POSTGRES_DB: syrin
      POSTGRES_USER: syrin
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD}"
    command: >
      postgres
      -c hot_standby=on
      -c primary_conninfo=host=postgres-primary port=5432
```

## Disaster Recovery

### Backup Strategy

```bash
# Backup checkpoints database
pg_dump -h localhost -U syrin syrin_checkpoints > checkpoints_backup.sql

# Backup to S3
aws s3 cp checkpoints_backup.sql s3://my-backups/checkpoints-$(date +%Y%m%d).sql

# Automated backup schedule
# 0 2 * * * /opt/scripts/backup.sh
```

### Recovery Procedures

1. **Database restoration:**
   ```bash
   pg_restore -h localhost -U syrin -d syrin_checkpoints backups/latest.sql
   ```

2. **Agent state recovery:**
   ```python
   # Restore from checkpoint
   checkpoints = agent.list_checkpoints()
   if checkpoints:
       agent.load_checkpoint(checkpoints[-1])
   ```

## Deployment Checklist

Before every deployment:

### Pre-Deployment
- [ ] Run full test suite
- [ ] Review security scan results
- [ ] Check API key validity
- [ ] Verify backup restoration
- [ ] Review changelog

### Configuration
- [ ] Set production environment variables
- [ ] Configure secrets (not in code)
- [ ] Set resource limits
- [ ] Configure health checks
- [ ] Set up monitoring dashboards

### Infrastructure
- [ ] Verify capacity planning
- [ ] Test scaling behavior
- [ ] Validate network policies
- [ ] Check SSL certificates
- [ ] Test authentication flows

### Post-Deployment
- [ ] Verify health endpoint
- [ ] Check monitoring alerts
- [ ] Test critical user flows
- [ ] Validate budget tracking
- [ ] Set up runbooks

## Environment Configuration

### Development
```bash
export OPENAI_API_KEY="sk-test..."
export LOG_LEVEL="DEBUG"
export ENABLE_PLAYGROUND="true"
```

### Staging
```bash
export OPENAI_API_KEY="sk-staging..."
export LOG_LEVEL="INFO"
export ENABLE_PLAYGROUND="true"
export DEBUG="true"
```

### Production
```bash
export OPENAI_API_KEY="$SECRET_MANAGER:openai-api-key"
export LOG_LEVEL="WARNING"
export ENABLE_PLAYGROUND="false"
export DEBUG="false"
```

## Runbooks

### High Latency

**Symptoms:** Response times > 5 seconds

**Diagnosis:**
```bash
# Check CPU/memory
kubectl top pods

# Check latency to LLM provider
curl -w "%{time_total}\n" -o /dev/null https://api.openai.com/v1/models

# Check agent logs
kubectl logs -f deployment/agent | grep -i latency
```

**Remediation:**
1. Check LLM provider status
2. Scale horizontally if needed
3. Enable circuit breaker if provider is degraded

### High Error Rate

**Symptoms:** > 5% of requests failing

**Diagnosis:**
```bash
# Check error logs
kubectl logs -f deployment/agent | grep -i error

# Check budget exhaustion
curl http://localhost:8000/budget
```

**Remediation:**
1. Identify error patterns
2. Check for budget exhaustion
3. Verify API keys
4. Review rate limit status

### Memory Leak

**Symptoms:** Memory usage grows over time

**Diagnosis:**
```bash
# Monitor memory over time
watch -n 5 'kubectl top pods | grep agent'
```

**Remediation:**
1. Restart the agent
2. Check for unbounded memory growth in code
3. Set memory limits

## See Also

- [Serving: HTTP API](/production/serving-http) — REST API reference
- [Serving: Advanced](/production/serving-advanced) — Production patterns
- [Checkpointing](/production/checkpointing) — State persistence
- [Budget](/core/budget) — Cost management
- [Rate Limiting](/production/rate-limiting) — API quota management
- [Circuit Breaker](/production/circuit-breaker) — Failure protection
