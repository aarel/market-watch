# Landing Page Deployment Instructions

## Overview

This landing page provides a public-facing introduction to the Market Watch project while keeping the actual application behind authentication. The recommended deployment uses subdomain routing.

## Deployment Model: Subdomain (Option B)

- **Public landing:** `www.yourdomain.com` or `yourdomain.com`
- **Protected app:** `app.yourdomain.com`

## Prerequisites

1. Domain name with DNS access
2. VPS running nginx
3. Let's Encrypt certbot installed
4. Market Watch app running on `127.0.0.1:8000` via systemd

## Step 1: DNS Configuration

Add an A record for the `app` subdomain:

```
Type: A
Host: app
Value: <your-vps-ip>
TTL: 3600
```

Wait for DNS propagation (check with `dig app.yourdomain.com`).

## Step 2: Deploy Landing Page Files

```bash
# Create landing directory
sudo mkdir -p /var/www/market-watch-landing

# Copy landing page
sudo cp landing/index.html /var/www/market-watch-landing/

# Set ownership
sudo chown -R www-data:www-data /var/www/market-watch-landing

# Set permissions
sudo chmod -R 755 /var/www/market-watch-landing
```

## Step 3: Update Landing Page Content

Edit `/var/www/market-watch-landing/index.html` and replace:

1. `yourdomain.com` → your actual domain
2. `your.email@example.com` → your contact email
3. Add screenshots to the preview section (optional)
4. Update any project-specific details

## Step 4: Configure Nginx

```bash
# Copy nginx config
sudo cp deploy/nginx-subdomain-config.conf /etc/nginx/sites-available/market-watch

# Edit the config file
sudo nano /etc/nginx/sites-available/market-watch

# Replace ALL instances of 'yourdomain.com' with your actual domain
# Update paths if needed

# Enable the site
sudo ln -s /etc/nginx/sites-available/market-watch /etc/nginx/sites-enabled/

# Remove default site if present
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

## Step 5: Obtain SSL Certificates

```bash
# Install certbot if not already installed
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificates for both domains
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d app.yourdomain.com

# Certbot will automatically update the nginx config with cert paths
# Select option 2 (redirect HTTP to HTTPS) when prompted

# Test renewal
sudo certbot renew --dry-run
```

## Step 6: Create Basic Auth for Demo

```bash
# Install apache2-utils for htpasswd
sudo apt install apache2-utils -y

# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd demo

# Enter a strong password when prompted
# This password will be shared with demo users
```

## Step 7: Verify Deployment

### Test Landing Page (Public)
```bash
curl -I https://yourdomain.com
# Should return 200 OK without auth

curl https://yourdomain.com | grep "Market Watch"
# Should return HTML content
```

### Test App Subdomain (Protected)
```bash
# Without auth — should return 401
curl -I https://app.yourdomain.com
# Should return 401 Unauthorized

# With auth — should return 200
curl -u demo:yourpassword https://app.yourdomain.com | head -20
# Should return the app's HTML
```

### Test WebSocket (if used)
```bash
wscat -c wss://app.yourdomain.com/ws --auth demo:yourpassword
# Should connect successfully
```

## Step 8: Set Demo Mode in Application

Edit your VPS `.env` file (not the local one):

```bash
sudo nano /opt/market-watch/.env
```

Add or update:
```
DEMO_MODE=1
API_TOKEN=<your-generated-token>
DISABLE_API_DOCS=1
AUTO_TRADE=false
```

Restart the service:
```bash
sudo systemctl restart market-watch
```

## Verification Checklist

- [ ] Landing page loads at `https://yourdomain.com` without auth
- [ ] Landing page has correct domain/email in content
- [ ] App at `https://app.yourdomain.com` requires basic auth
- [ ] App returns 401 without credentials
- [ ] App loads correctly with demo credentials
- [ ] All /api/* routes are reachable through the app subdomain
- [ ] WebSocket connects successfully
- [ ] HTTPS redirect works (HTTP → HTTPS)
- [ ] HSTS header present (check with curl -I)
- [ ] SSL Labs test shows A rating
- [ ] Demo mode blocks write operations (test in Phase 4)

## Troubleshooting

**Landing page shows 403/404:**
- Check file permissions: `ls -la /var/www/market-watch-landing`
- Check nginx error log: `sudo tail -f /var/log/nginx/market-watch-landing-error.log`

**App subdomain doesn't resolve:**
- Check DNS: `dig app.yourdomain.com`
- Wait 5-10 minutes for DNS propagation
- Check nginx config: `sudo nginx -t`

**Basic auth not working:**
- Verify .htpasswd file exists: `sudo cat /etc/nginx/.htpasswd`
- Check nginx config has correct path to .htpasswd
- Ensure nginx was reloaded after changes

**SSL errors:**
- Check cert paths in nginx config match certbot output
- Run `sudo certbot certificates` to see installed certs
- Ensure all domains are covered by the certificate

**App backend not reachable:**
- Check if uvicorn is running: `sudo systemctl status market-watch`
- Verify it's listening on 127.0.0.1:8000: `sudo ss -tlnp | grep 8000`
- Check nginx can proxy: `curl http://127.0.0.1:8000/api/health`

## Security Notes

- Never commit `.htpasswd` to git
- Use a strong, unique password for demo access
- Keep certbot auto-renewal enabled
- Monitor nginx access logs for suspicious activity
- Rotate demo password periodically
