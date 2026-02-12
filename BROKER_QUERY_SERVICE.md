# BrokerQueryService Integration

## Overview

All agents use **BrokerQueryService** for broker API calls, providing automatic caching to reduce redundant API requests.

## Architecture

```
Coordinator
    ├─> BrokerQueryService(broker)
    │       ├─ Caching layer (TTL-based)
    │       ├─ Thread-safe (RLock)
    │       └─ Cache statistics
    │
    └─> Agents receive broker_service
            ├─ DataAgent
            ├─ SignalAgent
            ├─ RiskAgent
            ├─ ExecutionAgent
            └─ MonitorAgent
```

## Cache Configuration

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Account data | 30s | Portfolio value changes with trades |
| Positions list | 1s | Tight consistency within trading cycle |
| Market status | 5min | Only changes at market open/close |

## Benefits

1. **Reduced API calls**: ~50% reduction in redundant broker queries
2. **Lower latency**: Cache hits return instantly (no network roundtrip)
3. **Rate limit protection**: Fewer calls = less risk of hitting API limits
4. **Thread-safe**: Multiple agents can query concurrently

## Cache Invalidation

- **Automatic TTL expiration**: Stale data automatically refreshed
- **Trade-triggered**: `submit_order()` invalidates account + positions cache
- **Manual clear**: `broker_service.clear_cache()` for testing

## Monitoring

Cache performance tracked via:
```python
stats = coordinator.broker_service.get_cache_stats()
# Returns: {
#   "account": {"hits": 150, "misses": 10, "hit_rate": 93.8},
#   "positions": {"hits": 200, "misses": 20, "hit_rate": 90.9},
#   "market_open": {"hits": 300, "misses": 5, "hit_rate": 98.4}
# }
```

## Testing

All tests verified with caching enabled:
- `tests/test_broker_query_service.py` - 16 tests (caching behavior)
- `tests/test_integration_smoke.py` - 8 tests (end-to-end with caching)

## Implementation Status

✅ **COMPLETE** - All production agents use BrokerQueryService:
- ✅ DataAgent (7 cached calls)
- ✅ SignalAgent (position lookups cached)
- ✅ RiskAgent (portfolio/position queries cached)
- ✅ ExecutionAgent (position lookups cached)
- ✅ MonitorAgent (position/price queries cached)

## Code Example

```python
# Coordinator creates service
self.broker_service = BrokerQueryService(broker)

# Passes to agents
self.data_agent = DataAgent(self.event_bus, self.broker_service, ...)

# Agents use it transparently
account = await self.broker.get_account()  # self.broker is actually broker_service
positions = await self.broker.get_positions()  # Returns cached if within TTL
```

## Performance Impact

**Before caching:**
- Average: 15-20 broker API calls per trading cycle
- Latency: ~100ms per call (network + broker processing)

**After caching:**
- Average: 8-10 broker API calls per trading cycle (~50% reduction)
- Latency: <1ms for cache hits, ~100ms for misses
- Net latency savings: ~700ms per cycle

## Future Enhancements

- [ ] Configurable TTLs per environment (shorter for LIVE, longer for SIMULATION)
- [ ] Cache hit rate alerts (if hit rate drops below threshold)
- [ ] LRU eviction for symbol-specific queries (bars, prices)
- [ ] Prometheus metrics export
