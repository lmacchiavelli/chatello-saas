#!/bin/bash

# Chatello SaaS Setup Script
# This script sets up the Flask SaaS API

set -e

echo "==================================="
echo "Chatello SaaS API Setup"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Creating Python virtual environment...${NC}"
cd /var/www/flask/chatello-saas
python3 -m venv venv

echo -e "${YELLOW}Step 2: Installing Python dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}Step 3: Creating logs directory...${NC}"
mkdir -p logs
chown -R www-data:www-data /var/www/flask/chatello-saas
chmod -R 755 /var/www/flask/chatello-saas

echo -e "${YELLOW}Step 4: Setting up environment file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}Created .env file from template${NC}"
    echo -e "${RED}IMPORTANT: Edit .env file and add your API keys!${NC}"
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

echo -e "${YELLOW}Step 5: Testing database connection...${NC}"
python3 -c "
import mysql.connector
try:
    conn = mysql.connector.connect(
        host='localhost',
        user='chatello_saas',
        password='ChatelloSaaS2025!',
        database='chatello_saas'
    )
    print('✓ Database connection successful')
    conn.close()
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    exit(1)
"

echo -e "${YELLOW}Step 6: Creating admin user htpasswd...${NC}"
if [ ! -f /etc/nginx/.htpasswd_chatello_admin ]; then
    htpasswd -bc /etc/nginx/.htpasswd_chatello_admin admin ChatelloAdmin2025!
    echo -e "${GREEN}Created admin user for Nginx basic auth${NC}"
else
    echo -e "${GREEN}Admin htpasswd already exists${NC}"
fi

echo -e "${YELLOW}Step 7: Enabling and starting systemd service...${NC}"
systemctl daemon-reload
systemctl enable chatello-saas.service
systemctl restart chatello-saas.service

# Check service status
if systemctl is-active --quiet chatello-saas.service; then
    echo -e "${GREEN}✓ Chatello SaaS service is running${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    journalctl -u chatello-saas.service --no-pager -n 20
    exit 1
fi

echo -e "${YELLOW}Step 8: Setting up Nginx...${NC}"
# Enable site if not already enabled
if [ ! -L /etc/nginx/sites-enabled/api.chatello.io ]; then
    ln -s /etc/nginx/sites-available/api.chatello.io /etc/nginx/sites-enabled/
    echo -e "${GREEN}Enabled api.chatello.io site${NC}"
fi

# Test Nginx configuration
nginx -t
if [ $? -eq 0 ]; then
    systemctl reload nginx
    echo -e "${GREEN}✓ Nginx configuration reloaded${NC}"
else
    echo -e "${RED}✗ Nginx configuration error${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 9: Creating test license...${NC}"
mysql -u chatello_saas -pChatelloSaaS2025! chatello_saas -e "
    -- Create test customer
    INSERT IGNORE INTO customers (email, name, status) 
    VALUES ('test@chatello.io', 'Test User', 'active');
    
    -- Get customer ID
    SET @customer_id = (SELECT id FROM customers WHERE email = 'test@chatello.io');
    
    -- Create test license for Pro plan
    CALL generate_license_key(@customer_id, 2, 'localhost');
"

echo -e "${GREEN}==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Edit /var/www/flask/chatello-saas/.env and add your API keys"
echo "2. Update DNS to point api.chatello.io to this server (164.132.56.3)"
echo "3. Test the API: curl https://api.chatello.io/api/health"
echo "4. Access admin dashboard: https://api.chatello.io/admin/"
echo "   Username: admin"
echo "   Password: ChatelloAdmin2025!"
echo ""
echo "Test license has been created - check database for details"
echo "===================================${NC}"