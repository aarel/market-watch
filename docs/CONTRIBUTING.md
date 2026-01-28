# Contributing to Market-Watch

> Guidelines for contributing to the Market-Watch trading bot

Thank you for considering contributing to Market-Watch! This document provides guidelines and instructions for contributors.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Code Style](#code-style)
5. [Testing](#testing)
6. [Pull Requests](#pull-requests)
7. [Areas for Contribution](#areas-for-contribution)
8. [Documentation](#documentation)

---

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome constructive feedback
- Focus on what's best for the project
- Show empathy towards other contributors

### Unacceptable Behavior

- Harassment or discriminatory language
- Personal attacks
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- Alpaca paper trading account (for testing)
- Basic understanding of async/await in Python

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/market-watch.git
cd market-watch

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/market-watch.git
```

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if available)
# pip install -r requirements-dev.txt

# Configure for development
cp .env.example .env
# Edit .env with your paper trading API keys

# Run tests (when available)
# pytest

# Start development server
python server.py
```

---

## Development Workflow

### 1. Create a Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
# Or for bug fixes:
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write code
- Add tests (when test framework is available)
- Update documentation
- Follow code style guidelines

### 3. Test Your Changes

```bash
# Run the application
python server.py

# Test in simulation mode
SIMULATION_MODE=true python server.py

# Run backtests
python -m backtest --symbols AAPL --start 2023-01-01

# Manual testing checklist:
# - Start server
# - Check /api/status
# - Execute manual trade
# - View signals
# - Test strategy switching
```

### 4. Commit

```bash
git add .
git commit -m "feat: add new feature description"

# Commit message format:
# feat: new feature
# fix: bug fix
# docs: documentation changes
# refactor: code refactoring
# test: adding tests
# chore: maintenance tasks
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

---

## Code Style

### Python Style Guide

Follow [PEP 8](https://pep8.org/) with these specifics:

**Formatting:**
```python
# Line length: 100 characters (not 79)
# Use 4 spaces for indentation
# Use double quotes for strings (except to avoid escaping)
```

**Naming Conventions:**
```python
# Classes: PascalCase
class MomentumStrategy:
    pass

# Functions/variables: snake_case
def calculate_momentum():
    momentum_value = 0.0

# Constants: UPPER_SNAKE_CASE
MAX_POSITION_PCT = 0.25

# Private: prefix with underscore
def _internal_helper():
    pass
```

**Type Hints:**

Use type hints for all public functions:

```python
from typing import Optional, List, Dict

def analyze(
    symbol: str,
    bars: pd.DataFrame,
    current_price: float,
    position: Optional[Dict] = None
) -> TradingSignal:
    pass
```

**Docstrings:**

Use Google-style docstrings:

```python
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        returns: Series of daily returns
        risk_free_rate: Annual risk-free rate (default: 5%)

    Returns:
        Sharpe ratio as float

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.03])
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe: {sharpe:.2f}")
    """
    pass
```

### Code Organization

**File Structure:**
```
# Group related functionality
agents/
  ├── base.py           # Base classes
  ├── coordinator.py    # Coordinator
  ├── data_agent.py     # Specific agents
  └── ...

strategies/
  ├── base.py           # Abstract interfaces
  ├── momentum.py       # Concrete implementations
  └── ...
```

**Import Order:**
```python
# 1. Standard library
import os
from datetime import datetime

# 2. Third-party packages
import pandas as pd
import numpy as np

# 3. Local imports
from strategies.base import Strategy
import config
```

### Async/Await Guidelines

```python
# Agent methods should be async
async def start(self):
    await super().start()
    self.event_bus.subscribe(MarketDataReady, self._handle_market_data)

# Event handlers should be async
async def _handle_market_data(self, event: MarketDataReady):
    # Process data
    await self.event_bus.publish(SignalGenerated(...))

# Non-async where appropriate (pure computation)
def calculate_momentum(self, bars: pd.DataFrame) -> float:
    return (bars['close'].iloc[-1] - bars['close'].iloc[0]) / bars['close'].iloc[0]
```

---

## Testing

### Test Structure (Future)

When test framework is added:

```
tests/
├── unit/
│   ├── test_strategies.py
│   ├── test_metrics.py
│   └── ...
├── integration/
│   ├── test_agents.py
│   ├── test_event_flow.py
│   └── ...
└── e2e/
    └── test_full_cycle.py
```

### Writing Tests

**Unit Test Example:**
```python
import pytest
from strategies import MomentumStrategy

def test_momentum_strategy_buy_signal():
    """Test that momentum strategy generates buy signal when threshold exceeded."""
    strategy = MomentumStrategy(lookback_days=20, momentum_threshold=0.02)

    # Create test data
    bars = create_test_bars(start_price=100, end_price=103)  # 3% gain

    signal = strategy.analyze(
        symbol='TEST',
        bars=bars,
        current_price=103.0,
        current_position=None
    )

    assert signal.action == SignalType.BUY
    assert signal.strength > 0.02
    assert 'momentum' in signal.reason.lower()
```

**Integration Test Example:**
```python
@pytest.mark.asyncio
async def test_signal_to_execution_flow():
    """Test complete flow from signal generation to execution."""
    # Setup
    broker = FakeBroker()
    event_bus = EventBus()
    signal_agent = SignalAgent(event_bus, broker)
    risk_agent = RiskAgent(event_bus, broker)
    execution_agent = ExecutionAgent(event_bus, broker, risk_agent)

    await signal_agent.start()
    await risk_agent.start()
    await execution_agent.start()

    # Trigger data event
    await event_bus.publish(MarketDataReady(...))

    # Wait and verify
    await asyncio.sleep(0.1)
    assert len(broker.orders) == 1
```

### Manual Testing Checklist

When submitting a PR, verify:

- [ ] Server starts without errors
- [ ] `/api/status` returns valid data
- [ ] Manual trade executes
- [ ] Signals are generated
- [ ] Stop-loss triggers work
- [ ] Config updates via API work
- [ ] WebSocket broadcasts events
- [ ] Backtests run successfully

---

## Pull Requests

### PR Checklist

Before submitting:

- [ ] Code follows style guidelines
- [ ] Docstrings added for new functions
- [ ] Manual testing completed
- [ ] Documentation updated (if needed)
- [ ] Commit messages are descriptive
- [ ] Branch is up to date with main
- [ ] No unnecessary files included

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issue
Fixes #(issue number)

## Testing
How has this been tested?
- [ ] Manual testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated

## Checklist
- [ ] Code follows project style
- [ ] Docstrings added
- [ ] Documentation updated
- [ ] Tests pass
- [ ] No breaking changes (or documented)

## Screenshots (if applicable)
```

### Review Process

1. **Automated Checks** (future):
   - Code style (flake8/black)
   - Tests pass
   - Coverage threshold

2. **Manual Review**:
   - Code quality
   - Design patterns
   - Documentation completeness

3. **Approval**:
   - At least one maintainer approval
   - All comments addressed

4. **Merge**:
   - Squash and merge preferred
   - Delete branch after merge

---

## Areas for Contribution

### High Priority

1. **Testing Framework** (Phase 11)
   - Add pytest infrastructure
   - Write unit tests for strategies
   - Integration tests for agents
   - E2E tests for full trading cycle

2. **Risk Management** (Phase 3)
   - Portfolio-level risk limits
   - Correlation tracking
   - Circuit breakers
   - Enhanced position sizing

3. **Analytics Dashboard** (Phase 4)
   - Real-time charts (equity curve, positions)
   - Performance metrics visualization
   - Trade analysis views

4. **Additional Strategies**
   - VWAP strategy
   - Pairs trading
   - ML-based strategies
   - Sentiment analysis

### Medium Priority

5. **Multi-Broker Support** (Phase 6)
   - Interactive Brokers adapter
   - TD Ameritrade adapter
   - Broker comparison features

6. **Configuration Persistence** (Phase 8)
   - SQLite database for settings
   - Configuration history
   - Profile management

7. **Enhanced Backtesting**
   - Walk-forward analysis
   - Monte Carlo simulation
   - Parameter optimization (genetic algorithms)

### Good First Issues

- Documentation improvements
- Bug fixes
- Adding examples
- Improving error messages
- Adding type hints to existing code
- Code comments and docstrings

---

## Documentation

### When to Update Docs

Update documentation when:
- Adding new features
- Changing APIs
- Adding configuration options
- Fixing bugs that affect usage
- Adding examples

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview and quick start |
| `docs/API.md` | REST and WebSocket API reference |
| `docs/ARCHITECTURE.md` | Technical architecture |
| `docs/STRATEGIES.md` | Strategy documentation |
| `docs/BACKTEST.md` | Backtesting guide |
| `docs/DEPLOYMENT.md` | Deployment instructions |
| `docs/FAQ.md` | Common questions |
| `ROADMAP.md` | Development roadmap |
| `CLAUDE.md` | AI assistant guidance |

### Documentation Style

- Use clear, concise language
- Include code examples
- Add tables for reference data
- Use diagrams where helpful
- Link to related documentation
- Keep up to date with code changes

---

## Git Workflow Summary

```bash
# 1. Sync with upstream
git checkout main
git pull upstream main
git push origin main

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Make changes and commit
git add .
git commit -m "feat: descriptive commit message"

# 4. Push to your fork
git push origin feature/my-feature

# 5. Create Pull Request on GitHub

# 6. Address review feedback
git add .
git commit -m "fix: address review comments"
git push origin feature/my-feature

# 7. After merge, clean up
git checkout main
git pull upstream main
git branch -d feature/my-feature
git push origin --delete feature/my-feature
```

---

## Questions or Problems?

### Getting Help

- **Documentation:** Check docs/ first
- **Issues:** Search existing GitHub issues
- **Discussions:** Use GitHub Discussions for questions
- **Email:** Contact maintainers (if provided)

### Reporting Bugs

Use this template:

```markdown
**Bug Description**
Clear description of the bug.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What should happen.

**Actual Behavior**
What actually happens.

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.10.8]
- Market-Watch Version: [e.g., commit hash or release]
- Trading Mode: [paper/live/simulation]

**Logs**
```
Relevant log output
```
```

### Feature Requests

Use this template:

```markdown
**Problem Description**
What problem does this solve?

**Proposed Solution**
How should it work?

**Alternatives Considered**
Other approaches considered?

**Additional Context**
Screenshots, examples, etc.
```

---

## Recognition

Contributors will be:
- Listed in README.md (if desired)
- Credited in release notes
- Mentioned in documentation

---

Thank you for contributing to Market-Watch! Your contributions help make algorithmic trading more accessible to everyone.

*Last updated: 2025-01-19*
