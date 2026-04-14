#!/bin/bash
# Resume Generator - Automated Deployment Script for Ubuntu Droplet

set -e

echo "🚀 Resume Generator Deployment Script"
echo "======================================"

# Install dependencies
echo "📦 Installing system dependencies..."
apt update
apt install -y python3 python3-pip python3-venv git libreoffice libreoffice-writer nginx

# Setup Python virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Configure Nginx
echo "⚙️ Configuring Nginx..."
cat > /etc/nginx/sites-available/default << 'NGINX_CONFIG'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX_CONFIG

# Verify Nginx config
nginx -t

# Restart Nginx
systemctl restart nginx

# Stop old gunicorn processes
pkill -f gunicorn || true

# Start gunicorn
echo "🎯 Starting Gunicorn..."
gunicorn -w 4 -b 127.0.0.1:5001 app:app --daemon

echo ""
echo "✅ Deployment Complete!"
echo "🌐 Access your app at: http://$(hostname -I | awk '{print $1}')"
echo ""
echo "To view logs:"
echo "  tail -f /var/log/nginx/error.log"
echo ""
echo "To restart app:"
echo "  pkill -f gunicorn && gunicorn -w 4 -b 127.0.0.1:5001 app:app --daemon"
