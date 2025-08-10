#!/usr/bin/env python3
"""
Chatello SaaS API - License Management & AI Proxy
Version: 1.0.0
Author: Chatello Team
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import mysql.connector
from mysql.connector import pooling
import requests
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from functools import wraps
import secrets
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# CORS configuration - Allow WordPress sites
CORS(app, origins="*", allow_headers=["Content-Type", "X-License-Key"])

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=lambda: request.headers.get('X-License-Key', get_remote_address()),
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Database configuration
DB_CONFIG = {
    'user': 'chatello_saas',
    'password': 'ChatelloSaaS2025!',
    'host': 'localhost',
    'database': 'chatello_saas',
    'pool_name': 'chatello_pool',
    'pool_size': 10,
    'pool_reset_session': True
}

# AI Provider configuration
AI_PROVIDERS = {
    'openai': {
        'api_key': os.environ.get('OPENAI_API_KEY', ''),
        'endpoint': 'https://api.openai.com/v1/chat/completions',
        'model': 'gpt-4o-mini'
    },
    'anthropic': {
        'api_key': os.environ.get('ANTHROPIC_API_KEY', ''),
        'endpoint': 'https://api.anthropic.com/v1/messages',
        'model': 'claude-3-haiku-20240307'
    },
    'deepseek': {
        'api_key': os.environ.get('DEEPSEEK_API_KEY', ''),
        'endpoint': 'https://api.deepseek.com/v1/chat/completions',
        'model': 'deepseek-chat'
    }
}

# Logging setup
if not os.path.exists('/var/www/flask/chatello-saas/logs'):
    os.makedirs('/var/www/flask/chatello-saas/logs')

file_handler = RotatingFileHandler(
    '/var/www/flask/chatello-saas/logs/api.log',
    maxBytes=10240000,
    backupCount=10
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Chatello SaaS API startup')

# Database connection pool
try:
    db_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
except mysql.connector.Error as err:
    app.logger.error(f"Database pool creation failed: {err}")
    db_pool = None

def get_db():
    """Get database connection from pool"""
    if db_pool:
        return db_pool.get_connection()
    return None

def validate_license(f):
    """Decorator to validate license key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        license_key = request.headers.get('X-License-Key')
        
        if not license_key:
            return jsonify({'error': 'License key required'}), 401
        
        db = get_db()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = db.cursor(dictionary=True)
        try:
            # Check license validity
            cursor.execute("""
                SELECT l.*, p.name as plan_name, p.monthly_requests, p.features
                FROM licenses l
                JOIN plans p ON l.plan_id = p.id
                WHERE l.license_key = %s AND l.status = 'active'
            """, (license_key,))
            
            license_data = cursor.fetchone()
            
            if not license_data:
                return jsonify({'error': 'Invalid or inactive license'}), 401
            
            # Check expiration
            if license_data['expires_at'] and license_data['expires_at'] < datetime.now():
                return jsonify({'error': 'License expired'}), 401
            
            # Store license data for request
            g.license = license_data
            g.db = db
            g.cursor = cursor
            
            return f(*args, **kwargs)
            
        except mysql.connector.Error as err:
            app.logger.error(f"License validation error: {err}")
            return jsonify({'error': 'License validation failed'}), 500
        finally:
            if 'cursor' not in g:
                cursor.close()
                db.close()
    
    return decorated_function

def track_usage(endpoint, tokens_used=0):
    """Track API usage for billing"""
    if hasattr(g, 'license') and hasattr(g, 'cursor'):
        try:
            g.cursor.execute("""
                INSERT INTO usage_logs (license_id, endpoint, tokens_used, created_at)
                VALUES (%s, %s, %s, %s)
            """, (g.license['id'], endpoint, tokens_used, datetime.now()))
            g.db.commit()
        except mysql.connector.Error as err:
            app.logger.error(f"Usage tracking error: {err}")

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/validate', methods=['POST'])
@validate_license
def validate_license_endpoint():
    """Validate license and return plan details"""
    license_data = g.license
    
    # Get current month usage
    g.cursor.execute("""
        SELECT COUNT(*) as requests_count, SUM(tokens_used) as tokens_total
        FROM usage_logs
        WHERE license_id = %s 
        AND MONTH(created_at) = MONTH(CURRENT_DATE())
        AND YEAR(created_at) = YEAR(CURRENT_DATE())
    """, (license_data['id'],))
    
    usage = g.cursor.fetchone()
    
    response = {
        'valid': True,
        'plan': license_data['plan_name'],
        'domain': license_data['domain'],
        'expires_at': license_data['expires_at'].isoformat() if license_data['expires_at'] else None,
        'usage': {
            'requests_used': usage['requests_count'] or 0,
            'requests_limit': license_data['monthly_requests'],
            'tokens_used': usage['tokens_total'] or 0
        },
        'features': json.loads(license_data['features']) if license_data['features'] else []
    }
    
    track_usage('validate')
    g.cursor.close()
    g.db.close()
    
    return jsonify(response)

@app.route('/api/chat', methods=['POST'])
@validate_license
@limiter.limit("100 per hour")
def chat_proxy():
    """Proxy chat requests to AI providers"""
    license_data = g.license
    
    # Check monthly usage limit
    g.cursor.execute("""
        SELECT COUNT(*) as requests_count
        FROM usage_logs
        WHERE license_id = %s 
        AND endpoint = 'chat'
        AND MONTH(created_at) = MONTH(CURRENT_DATE())
        AND YEAR(created_at) = YEAR(CURRENT_DATE())
    """, (license_data['id'],))
    
    usage = g.cursor.fetchone()
    
    if usage['requests_count'] >= license_data['monthly_requests']:
        g.cursor.close()
        g.db.close()
        return jsonify({'error': 'Monthly request limit exceeded'}), 429
    
    # Get request data
    data = request.get_json()
    provider = data.get('provider', 'openai')
    messages = data.get('messages', [])
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)
    
    if provider not in AI_PROVIDERS:
        return jsonify({'error': 'Invalid AI provider'}), 400
    
    if not messages:
        return jsonify({'error': 'Messages required'}), 400
    
    # Make request to AI provider
    provider_config = AI_PROVIDERS[provider]
    
    try:
        if provider == 'anthropic':
            # Anthropic API format
            headers = {
                'x-api-key': provider_config['api_key'],
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            payload = {
                'model': provider_config['model'],
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            }
            
            response = requests.post(
                provider_config['endpoint'],
                headers=headers,
                json=payload,
                timeout=30
            )
            
        else:
            # OpenAI-compatible format (OpenAI, DeepSeek)
            headers = {
                'Authorization': f"Bearer {provider_config['api_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': provider_config['model'],
                'messages': messages,
                'temperature': temperature,
                'max_tokens': max_tokens
            }
            
            # Debug log to check API key
            key_preview = provider_config['api_key'][:50] + '...' if provider_config['api_key'] else 'None'
            app.logger.info(f"Using {provider} key: {key_preview}")
            
            response = requests.post(
                provider_config['endpoint'],
                headers=headers,
                json=payload,
                timeout=30
            )
        
        response.raise_for_status()
        result = response.json()
        
        # Calculate tokens used (approximate)
        tokens_used = len(json.dumps(messages)) // 4 + max_tokens
        
        # Track usage
        track_usage('chat', tokens_used)
        
        # Log successful request
        app.logger.info(f"Chat request from license {license_data['id']} to {provider}")
        
        g.cursor.close()
        g.db.close()
        
        return jsonify({
            'success': True,
            'provider': provider,
            'response': result
        })
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"AI provider request failed: {e}")
        g.cursor.close()
        g.db.close()
        return jsonify({'error': 'AI provider request failed'}), 502
    except Exception as e:
        app.logger.error(f"Chat proxy error: {e}")
        g.cursor.close()
        g.db.close()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/usage', methods=['GET'])
@validate_license
def get_usage():
    """Get detailed usage statistics"""
    license_id = g.license['id']
    
    # Get usage by day for current month
    g.cursor.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as requests,
            SUM(tokens_used) as tokens,
            endpoint
        FROM usage_logs
        WHERE license_id = %s
        AND MONTH(created_at) = MONTH(CURRENT_DATE())
        AND YEAR(created_at) = YEAR(CURRENT_DATE())
        GROUP BY DATE(created_at), endpoint
        ORDER BY date DESC
    """, (license_id,))
    
    daily_usage = g.cursor.fetchall()
    
    # Format response
    usage_data = {}
    for row in daily_usage:
        date_str = row['date'].isoformat()
        if date_str not in usage_data:
            usage_data[date_str] = {
                'requests': 0,
                'tokens': 0,
                'endpoints': {}
            }
        usage_data[date_str]['requests'] += row['requests']
        usage_data[date_str]['tokens'] += row['tokens'] or 0
        usage_data[date_str]['endpoints'][row['endpoint']] = row['requests']
    
    g.cursor.close()
    g.db.close()
    
    return jsonify({
        'license_id': license_id,
        'plan': g.license['plan_name'],
        'monthly_limit': g.license['monthly_requests'],
        'usage': usage_data
    })

@app.route('/api/webhook/payment', methods=['POST'])
def payment_webhook():
    """Handle payment webhooks (Stripe/PayPal)"""
    # Verify webhook signature
    signature = request.headers.get('X-Webhook-Signature')
    if not verify_webhook_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    data = request.get_json()
    event_type = data.get('type')
    
    if event_type == 'payment.succeeded':
        # Extend license expiration
        license_key = data.get('metadata', {}).get('license_key')
        if license_key:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                UPDATE licenses 
                SET expires_at = DATE_ADD(COALESCE(expires_at, NOW()), INTERVAL 1 MONTH),
                    status = 'active'
                WHERE license_key = %s
            """, (license_key,))
            db.commit()
            cursor.close()
            db.close()
            
    elif event_type == 'payment.failed':
        # Suspend license
        license_key = data.get('metadata', {}).get('license_key')
        if license_key:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                UPDATE licenses 
                SET status = 'suspended'
                WHERE license_key = %s
            """, (license_key,))
            db.commit()
            cursor.close()
            db.close()
    
    return jsonify({'received': True})

def verify_webhook_signature(payload, signature):
    """Verify webhook signature"""
    # Implement based on payment provider
    # This is a placeholder
    return True

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'message': str(e.description)}), 429

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5010)