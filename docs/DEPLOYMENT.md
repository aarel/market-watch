# Deployment Guide

> Production deployment and operational guide for Market-Watch

## Table of Contents

1. [Quick Start](#quick-start)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Configuration](#configuration)
7. [Monitoring](#monitoring)
8. [Backups](#backups)
9. [Security Hardening](#security-hardening)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Python 3.10+
- Alpaca brokerage account (paper or live)
- API keys from Alpaca dashboard

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/market-watch.git
cd market-watch

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python server.py
```

Access UI at http://localhost:8000

---

## Local Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv

# Activate
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If you have dev dependencies

# Configure for development
cp .env.example .env
```

### Environment Configuration

**`.env` for Development:**
```bash
# Alpaca Credentials
ALPACA_API_KEY=your_paper_key_here
ALPACA_SECRET_KEY=your_paper_secret_here

# Mode
TRADING_MODE=paper
SIMULATION_MODE=false

# Server
API_HOST=127.0.0.1
API_PORT=8000

# Strategy
STRATEGY=momentum
LOOKBACK_DAYS=20
MOMENTUM_THRESHOLD=0.02
SELL_THRESHOLD=-0.01
STOP_LOSS_PCT=0.05

# Trading
AUTO_TRADE=false  # Disable auto-trading in dev
TRADE_INTERVAL_MINUTES=5
MAX_DAILY_TRADES=5

# Watchlist
WATCHLIST_MODE=static
# WATCHLIST set via config API
```

### Running in Development

```bash
# Standard run
python server.py

# With auto-reload (for development)
# Install uvicorn first: pip install uvicorn
uvicorn server:app --reload --host 127.0.0.1 --port 8000

# Run backtests
python -m backtest --download --symbols AAPL,GOOGL --start 2021-01-01
python -m backtest --symbols AAPL,GOOGL --start 2022-01-01 --benchmark SPY

# Simulation mode (no API needed)
SIMULATION_MODE=true python server.py
```

---

## Production Deployment

### System Requirements

**Minimum:**
- 1 CPU core
- 512MB RAM
- 1GB disk space

**Recommended:**
- 2 CPU cores
- 2GB RAM
- 5GB disk space (for historical data caching)

### Step-by-Step Production Setup

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.10 python3.10-venv python3-pip -y

# Create application user
sudo useradd -m -s /bin/bash marketwatch
sudo su - marketwatch
```

#### 2. Application Setup

```bash
# Clone repository
cd /home/marketwatch
git clone https://github.com/yourusername/market-watch.git
cd market-watch

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Edit with production settings
```

#### 3. Production `.env` Configuration

```bash
# Alpaca Credentials
ALPACA_API_KEY=your_live_or_paper_key
ALPACA_SECRET_KEY=your_live_or_paper_secret

# Mode (IMPORTANT: Only set to 'live' when ready!)
TRADING_MODE=paper
SIMULATION_MODE=false

# Server
API_HOST=0.0.0.0  # Listen on all interfaces
API_PORT=8000

# Security
API_TOKEN=your_secure_random_token_here  # Generate with: openssl rand -hex 32
ALLOWED_ORIGINS=https://yourdomain.com

# Strategy
STRATEGY=momentum
LOOKBACK_DAYS=20
MOMENTUM_THRESHOLD=0.02
SELL_THRESHOLD=-0.01
STOP_LOSS_PCT=0.05

# Trading
AUTO_TRADE=true
TRADE_INTERVAL_MINUTES=15  # More conservative in production
MAX_DAILY_TRADES=3  # Limit daily trades

# Data Feed
DATA_FEED=iex  # or 'sip' if you have Algo Trader Plus
```

#### 4. Systemd Service

Create `/etc/systemd/system/marketwatch.service`:

```ini
[Unit]
Description=Market-Watch Trading Bot
After=network.target

[Service]
Type=simple
User=marketwatch
WorkingDirectory=/home/marketwatch/market-watch
Environment="PATH=/home/marketwatch/market-watch/venv/bin"
ExecStart=/home/marketwatch/market-watch/venv/bin/python server.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable marketwatch
sudo systemctl start marketwatch

# Check status
sudo systemctl status marketwatch

# View logs
sudo journalctl -u marketwatch -f
```

#### 5. Reverse Proxy (nginx)

Install nginx:

```bash
sudo apt install nginx -y
```

Create `/etc/nginx/sites-available/marketwatch`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Static files
    location /static {
        alias /home/marketwatch/market-watch/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/marketwatch /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

#### 6. SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

Auto-renewal is configured automatically.

---

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data/historical

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/api/status')"

# Run
CMD ["python", "server.py"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  marketwatch:
    build: .
    container_name: marketwatch
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ALPACA_API_KEY=${ALPACA_API_KEY}
      - ALPACA_SECRET_KEY=${ALPACA_SECRET_KEY}
      - TRADING_MODE=paper
      - STRATEGY=momentum
      - AUTO_TRADE=true
      - API_HOST=0.0.0.0
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  data:
  logs:
```

### Running with Docker

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart

# Update
git pull
docker-compose build
docker-compose up -d
```

---

## Cloud Deployment

### AWS (EC2)

#### 1. Launch EC2 Instance

- **AMI:** Ubuntu 22.04 LTS
- **Instance Type:** t3.small (or t3.micro for paper trading)
- **Storage:** 8GB GP3
- **Security Group:**
  - Port 22 (SSH) - Your IP only
  - Port 80 (HTTP) - 0.0.0.0/0
  - Port 443 (HTTPS) - 0.0.0.0/0

#### 2. Connect and Setup

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip

# Follow production setup steps above
```

#### 3. Elastic IP (Optional)

Assign an Elastic IP for a static IP address.

#### 4. CloudWatch Monitoring

Enable detailed monitoring in EC2 console.

---

### DigitalOcean

#### 1. Create Droplet

- **Image:** Ubuntu 22.04 LTS
- **Plan:** Basic $12/month (2GB RAM)
- **Region:** Choose closest to you
- **Add SSH Key**

#### 2. Setup

```bash
ssh root@your-droplet-ip

# Follow production setup steps
```

#### 3. Floating IP (Optional)

Assign a floating IP for failover capability.

---

### Heroku

#### 1. Create `Procfile`

```
web: python server.py
```

#### 2. Create `runtime.txt`

```
python-3.10.12
```

#### 3. Deploy

```bash
heroku create your-app-name
heroku config:set ALPACA_API_KEY=your_key
heroku config:set ALPACA_SECRET_KEY=your_secret
heroku config:set TRADING_MODE=paper
git push heroku main
```

**Note:** Heroku apps sleep after 30 minutes of inactivity. Use a paid dyno for production.

---

## Configuration

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ALPACA_API_KEY` | - | Alpaca API key (required) |
| `ALPACA_SECRET_KEY` | - | Alpaca secret key (required) |
| `TRADING_MODE` | paper | "paper" or "live" |
| `SIMULATION_MODE` | false | Use fake broker (no API) |
| `API_HOST` | 127.0.0.1 | Server bind address |
| `API_PORT` | 8000 | Server port |
| `API_TOKEN` | - | API authentication token |
| `ALLOWED_ORIGINS` | localhost | CORS allowed origins |
| `STRATEGY` | momentum | Trading strategy |
| `LOOKBACK_DAYS` | 20 | Strategy lookback period |
| `MOMENTUM_THRESHOLD` | 0.02 | Momentum buy threshold |
| `SELL_THRESHOLD` | -0.01 | Momentum sell threshold |
| `STOP_LOSS_PCT` | 0.05 | Stop loss percentage |
| `MAX_POSITION_PCT` | 0.5 | Max position size |
| `AUTO_TRADE` | true | Enable auto-trading |
| `TRADE_INTERVAL_MINUTES` | 5 | Data refresh interval |
| `MAX_DAILY_TRADES` | 5 | Daily trade limit |
| `WATCHLIST_MODE` | top_gainers | "static" or "top_gainers" |
| `DATA_FEED` | iex | "iex" or "sip" |

### Runtime Configuration

Some settings can be changed via API without restart:

```bash
curl -X POST http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "watchlist": ["AAPL", "GOOGL", "MSFT"],
    "momentum_threshold": 0.03,
    "trade_interval_minutes": 10
  }'
```

**Changes are in-memory only and reset on restart.**

---

## Monitoring

### Application Logs

**Systemd:**
```bash
sudo journalctl -u marketwatch -f
```

**Docker:**
```bash
docker-compose logs -f
```

**File-based (add to server.py):**
```python
import logging
logging.basicConfig(
    filename='marketwatch.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Metrics to Monitor

1. **System Health:**
   - CPU usage
   - Memory usage
   - Disk space

2. **Application Metrics:**
   - Uptime
   - Trade execution count
   - API response times
   - Error rates

3. **Trading Metrics:**
   - Portfolio value
   - Daily P&L
   - Win rate
   - Max drawdown

### Alerting

Set up alerts for:
- Service down
- Trade execution failures
- Stop-loss triggers
- Daily loss exceeds threshold
- API errors

**Example with Prometheus + Grafana:**

```python
# Add to server.py
from prometheus_client import Counter, Gauge, generate_latest

trade_counter = Counter('trades_total', 'Total trades executed')
portfolio_value = Gauge('portfolio_value', 'Current portfolio value')

# Update metrics
trade_counter.inc()
portfolio_value.set(account.portfolio_value)
```

---

## Backups

### What to Backup

1. **Configuration:**
   - `.env` file
   - Custom strategy files

2. **Historical Data:**
   - `data/historical/*.csv`

3. **Trade History:**
   - Export via `/api/orders/export`

### Backup Script

Create `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup/marketwatch-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup config
cp /home/marketwatch/market-watch/.env $BACKUP_DIR/

# Backup historical data
cp -r /home/marketwatch/market-watch/data/historical $BACKUP_DIR/

# Backup trade history
curl http://localhost:8000/api/orders/export > $BACKUP_DIR/orders.csv

# Compress
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Keep only last 30 days
find /backup -name "marketwatch-*.tar.gz" -mtime +30 -delete
```

Schedule with cron:

```bash
# Daily at 2 AM
0 2 * * * /home/marketwatch/backup.sh
```

---

## Security Hardening

### 1. API Authentication

Enable token authentication:

```bash
# Generate token
API_TOKEN=$(openssl rand -hex 32)
echo "API_TOKEN=$API_TOKEN" >> .env
```

Include in requests:
```bash
curl -H "Authorization: Bearer $API_TOKEN" http://localhost:8000/api/status
```

### 2. HTTPS Only

Force HTTPS in nginx (shown in production setup).

### 3. Firewall

```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable
```

### 4. Fail2Ban

Protect against brute force:

```bash
sudo apt install fail2ban -y
```

### 5. Regular Updates

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Python dependencies
pip install --upgrade -r requirements.txt
```

### 6. Secrets Management

Never commit `.env` to git. Use environment-specific configs:

```bash
# .env.example (commit this)
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here

# .env (NEVER commit)
ALPACA_API_KEY=actual_key
ALPACA_SECRET_KEY=actual_secret
```

### 7. Principle of Least Privilege

- Run as non-root user
- Use paper trading by default
- Require explicit opt-in for live trading

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u marketwatch -n 50

# Common issues:
# 1. Port already in use
sudo netstat -tulpn | grep 8000
# Kill process or change port

# 2. Missing dependencies
source venv/bin/activate
pip install -r requirements.txt

# 3. Invalid API keys
# Check .env file
```

### Can't Connect to Alpaca

```bash
# Test API connectivity
python -c "import alpaca_trade_api as tradeapi; api = tradeapi.REST('KEY', 'SECRET', 'https://paper-api.alpaca.markets'); print(api.get_account())"

# Check:
# 1. API keys correct
# 2. Internet connectivity
# 3. Alpaca service status
```

### High Memory Usage

```bash
# Check memory
free -h

# If high:
# 1. Reduce watchlist size
# 2. Reduce lookback period
# 3. Clear historical data cache
rm -rf data/historical/*
```

### Trades Not Executing

Check:
1. `AUTO_TRADE=true` in config
2. Market is open
3. Sufficient buying power
4. Risk limits not exceeded
5. Check logs for errors

---

## Operational Checklist

### Daily
- [ ] Check service status
- [ ] Review trade executions
- [ ] Check error logs
- [ ] Verify portfolio value

### Weekly
- [ ] Review performance metrics
- [ ] Check system resources
- [ ] Update watchlist if needed
- [ ] Export trade history

### Monthly
- [ ] Update dependencies
- [ ] Review strategy performance
- [ ] Rotate backups
- [ ] Check disk space

### Before Going Live
- [ ] Run in paper mode for 30+ days
- [ ] Backtest strategy extensively
- [ ] Set conservative limits (stop-loss, position size)
- [ ] Enable all monitoring
- [ ] Test manual trade execution
- [ ] Verify risk controls work
- [ ] Have exit strategy
- [ ] Start with small capital

---

*Last updated: 2025-01-19*
