#!/bin/bash
# AutoApply — DigitalOcean Droplet Setup
# Run this after creating a $12/mo Basic Droplet (2GB RAM, 1 vCPU, Ubuntu 24.04)
# 
# Usage: ssh root@your-droplet-ip 'bash -s' < deploy/setup-droplet.sh

set -e

echo "═══ AutoApply — DigitalOcean Setup ═══"

# System updates
apt-get update && apt-get upgrade -y

# Python 3.11
apt-get install -y python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx

# Create app user
useradd -m -s /bin/bash autoapply || true
mkdir -p /home/autoapply/app
cd /home/autoapply/app

# Clone repo (replace with your GitHub URL)
if [ ! -d ".git" ]; then
    echo "Clone your repo: git clone https://github.com/YOUR_USERNAME/autoapply.git ."
    echo "Then re-run this script."
    exit 1
fi

# Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Playwright + Chromium
playwright install chromium --with-deps

# Create data directories
mkdir -p data/outputs/resumes data/outputs/screenshots data/profiles

# Environment file
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env with your Groq API key:"
    echo "  nano /home/autoapply/app/.env"
    echo ""
fi

# Systemd service
cat > /etc/systemd/system/autoapply.service << 'EOF'
[Unit]
Description=AutoApply Backend
After=network.target

[Service]
Type=simple
User=autoapply
WorkingDirectory=/home/autoapply/app/backend
Environment=PATH=/home/autoapply/app/venv/bin:/usr/bin
EnvironmentFile=/home/autoapply/app/.env
ExecStart=/home/autoapply/app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Nginx reverse proxy
cat > /etc/nginx/sites-available/autoapply << 'NGINX'
server {
    listen 80;
    server_name _;  # Replace with your domain

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        
        # CORS for Netlify frontend
        add_header Access-Control-Allow-Origin "https://your-netlify-app.netlify.app" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
    }

    client_max_body_size 10M;
}
NGINX

ln -sf /etc/nginx/sites-available/autoapply /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Fix permissions
chown -R autoapply:autoapply /home/autoapply/app

# Start services
systemctl daemon-reload
systemctl enable autoapply
systemctl start autoapply
systemctl restart nginx

# Firewall
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw --force enable

echo ""
echo "═══ Setup Complete ═══"
echo ""
echo "Next steps:"
echo "1. Edit .env:  nano /home/autoapply/app/.env"
echo "2. Add your Groq API key (free at console.groq.com)"
echo "3. Restart:  systemctl restart autoapply"
echo "4. Test:  curl http://YOUR_DROPLET_IP/health"
echo "5. Add SSL:  certbot --nginx -d your-domain.com"
echo "6. Update netlify.toml with your droplet IP/domain"
echo ""
echo "Logs:  journalctl -u autoapply -f"
echo "Status:  systemctl status autoapply"
