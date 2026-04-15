#!/bin/bash
# Fix Nginx chunked encoding issue

echo "Configuring Nginx..."
sudo bash -c 'cat > /etc/nginx/sites-available/default << '\''NGINX_CONF'\''
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
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
NGINX_CONF
'

echo "Testing Nginx..."
sudo nginx -t

echo "Restarting Nginx..."
sudo systemctl restart nginx

echo "Restarting Gunicorn..."
pkill -f gunicorn
sleep 1
cd /home/resume-tool
source venv/bin/activate
gunicorn -w 4 -b 127.0.0.1:5001 app:app --daemon

sleep 2
echo "✓ Done! App should be running at http://167.172.30.30"
