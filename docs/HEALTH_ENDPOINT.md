# Health Check Endpoint

The `/health` endpoint provides system health monitoring for external tools like uptime monitors, load balancers, and alerting systems.

## Endpoint

```
GET /health
```

**No authentication required** - This endpoint is intentionally public to allow external monitoring tools to check service availability.

## Response Format

```json
{
  "status": "healthy",
  "timestamp": "2026-01-24T18:30:00.123456",
  "uptime_seconds": 3600.5,
  "checks": {
    "application": {
      "status": "ok",
      "message": "Bot initialized"
    },
    "agents": {
      "status": "ok",
      "message": "6 agents running",
      "count": 6
    },
    "file_system": {
      "status": "ok",
      "message": "Analytics storage accessible",
      "path": "/path/to/data/analytics"
    },
    "broker_api": {
      "status": "ok",
      "message": "Broker API reachable"
    },
    "memory": {
      "status": "ok",
      "message": "145.2 MB (12.3%)",
      "usage_mb": 145.2,
      "usage_percent": 12.3
    }
  }
}
```

## Status Codes

- **200 OK** - System is healthy
- **503 Service Unavailable** - System is unhealthy (one or more critical checks failed)

## Health Checks

### 1. Application
- **OK**: Bot initialized with broker and coordinator
- **Degraded**: Bot not fully initialized
- **Fail**: Initialization error

### 2. Agents
- **OK**: All agents running
- **Degraded**: Some agents not running
- **Fail**: No agents or coordinator error

### 3. File System
- **OK**: Analytics storage writable
- **Degraded**: Analytics disabled
- **Fail**: Storage not accessible

### 4. Broker API
- **OK**: Broker API reachable (or simulation mode)
- **Fail**: API connectivity error

### 5. Memory
- **OK**: < 80% memory usage
- **Degraded**: 80-90% memory usage
- **Fail**: > 90% memory usage (critical)

## Check Status Values

Each check returns one of:
- `ok` - Check passed
- `degraded` - Check passed but with warnings
- `fail` - Check failed

## Usage Examples

### cURL
```bash
curl http://localhost:8000/health
```

### Python
```python
import requests

response = requests.get("http://localhost:8000/health")
if response.status_code == 200:
    print("System healthy")
else:
    print(f"System unhealthy: {response.json()}")
```

### Monitoring with UptimeRobot
1. Create HTTP(s) monitor
2. URL: `http://your-server:8000/health`
3. Keyword Monitor: Look for `"status": "healthy"`

### Docker Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD curl -f http://localhost:8000/health || exit 1
```

### Kubernetes Liveness Probe
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Nginx Load Balancer
```nginx
upstream trading_bot {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    check interval=5000 rise=2 fall=3 timeout=1000 type=http;
    check_http_send "GET /health HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx;
}
```

## Alerting Rules

Recommended alert thresholds:

### Critical Alerts
- Overall status = "unhealthy" for > 1 minute
- Application check = "fail"
- Agents check = "fail"
- Memory > 90% for > 5 minutes

### Warning Alerts
- Agents check = "degraded" (some agents down)
- Memory 80-90%
- File system check = "degraded"

## Example Alert Script

```bash
#!/bin/bash
# health_monitor.sh

HEALTH_URL="http://localhost:8000/health"
WEBHOOK_URL="https://hooks.slack.com/YOUR_WEBHOOK"

response=$(curl -s "$HEALTH_URL")
status=$(echo "$response" | jq -r '.status')

if [ "$status" != "healthy" ]; then
    message="🚨 Trading Bot Unhealthy: $response"
    curl -X POST "$WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\": \"$message\"}"
fi
```

## Cron Monitoring (every 5 minutes)

```cron
*/5 * * * * /path/to/health_monitor.sh
```

## Integration with Post-Market Automation

The health endpoint is checked by the post-market backtest automation. If the system is unhealthy, the backtest is skipped and an alert is generated.

## Security

The health endpoint:
- ✅ Does NOT require authentication (standard practice for health checks)
- ✅ Does NOT expose sensitive data (credentials, positions, P&L)
- ✅ Only exposes operational status

This allows external monitoring tools and load balancers to check health without credentials.

## Testing

Run health endpoint tests:
```bash
python -m unittest tests.test_health_endpoint -v
```

## Troubleshooting

### Health check returns 503

Check which component is failing:
```bash
curl http://localhost:8000/health | jq '.checks'
```

### Memory check always "degraded"

The bot may need more resources. Consider:
- Increasing container/VM memory
- Reducing `TOP_GAINERS_COUNT`
- Reducing `LOOKBACK_DAYS`
- Disabling analytics if not needed

### Broker API check fails

- Verify API keys in `.env`
- Check network connectivity
- Verify Alpaca API status: https://status.alpaca.markets/
