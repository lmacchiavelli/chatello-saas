#!/usr/bin/env python3
"""
Chatello SaaS API - MongoDB Version
License Management & AI Proxy with MongoDB Atlas
Version: 2.0.0 - MongoDB Edition
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
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

# Import MongoDB schema utilities
from mongodb_schema import generate_license_key, check_usage_limit, init_mongodb_collections

# Load environment variables
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

# MongoDB Atlas Configuration
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://username:password@cluster.mongodb.net/')
DATABASE_NAME = os.environ.get('MONGODB_DATABASE', 'chatello_saas')

# AI Provider configuration (unchanged)
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

# Logging setup (unchanged)
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

# MongoDB connection
try:
    mongo_client = MongoClient(
        MONGODB_URI, 
        serverSelectionTimeoutMS=10000,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True
    )
    # Test connection
    mongo_client.admin.command('ping')
    db = mongo_client[DATABASE_NAME]
    app.logger.info('✅ MongoDB Atlas connection successful')
    
    # Initialize collections and indexes
    init_mongodb_collections(db)
    
except Exception as err:
    app.logger.error(f"❌ MongoDB connection failed: {err}")
    mongo_client = None
    db = None

def get_db():
    """Get MongoDB database instance"""
    if db is None:
        raise Exception("MongoDB connection not available")
    return db

# Helper functions for ObjectId conversion
def to_object_id(id_string):
    """Convert string to ObjectId, return None if invalid"""
    try:
        return ObjectId(id_string)
    except (InvalidId, TypeError):
        return None

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable dict"""
    if doc is None:
        return None
    
    # Convert ObjectIds to strings
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc

# License validation decorator
def require_license(f):
    """Decorator to validate license key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        license_key = request.headers.get('X-License-Key')
        if not license_key:
            return jsonify({'error': 'License key required'}), 401
        
        try:
            db = get_db()
            license_doc = db.licenses.find_one({'license_key': license_key, 'status': 'active'})
            
            if not license_doc:
                return jsonify({'error': 'Invalid or inactive license'}), 401
            
            # Check expiration
            if license_doc.get('expires_at') and license_doc['expires_at'] < datetime.now():
                return jsonify({'error': 'License expired'}), 401
            
            # Store license info in g for use in route
            g.license = license_doc
            g.license_id = license_doc['_id']
            
            # Update last_check timestamp
            db.licenses.update_one(
                {'_id': license_doc['_id']},
                {'$set': {'last_check': datetime.now()}}
            )
            
        except Exception as e:
            app.logger.error(f"License validation error: {e}")
            return jsonify({'error': 'License validation failed'}), 500
        
        return f(*args, **kwargs)
    return decorated_function

# API Routes

@app.route('/')
def health_check():
    """Health check endpoint"""
    try:
        db = get_db()
        # Test MongoDB connection
        db.admin.command('ping')
        
        return jsonify({
            'status': 'healthy',
            'version': '2.0.0-mongodb',
            'database': 'MongoDB Atlas',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/health')
def api_health():
    """API health check with more details"""
    try:
        db = get_db()
        
        # Test database operations
        plans_count = db.plans.count_documents({})
        licenses_count = db.licenses.count_documents({})
        customers_count = db.customers.count_documents({})
        
        return jsonify({
            'status': 'healthy',
            'version': '2.0.0-mongodb',
            'database': {
                'type': 'MongoDB Atlas',
                'connection': 'active',
                'collections': {
                    'plans': plans_count,
                    'licenses': licenses_count,
                    'customers': customers_count
                }
            },
            'ai_providers': {
                provider: {'configured': bool(config['api_key'])}
                for provider, config in AI_PROVIDERS.items()
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/validate', methods=['POST'])
def validate_license():
    """Validate license key and return plan information"""
    license_key = request.headers.get('X-License-Key')
    
    if not license_key:
        return jsonify({'error': 'License key required in X-License-Key header'}), 400
    
    try:
        db = get_db()
        
        # Find license with plan and customer info
        license_pipeline = [
            {'$match': {'license_key': license_key}},
            {'$lookup': {
                'from': 'plans',
                'localField': 'plan_id',
                'foreignField': '_id',
                'as': 'plan'
            }},
            {'$lookup': {
                'from': 'customers',
                'localField': 'customer_id',
                'foreignField': '_id',
                'as': 'customer'
            }},
            {'$unwind': '$plan'},
            {'$unwind': '$customer'}
        ]
        
        result = list(db.licenses.aggregate(license_pipeline))
        
        if not result:
            return jsonify({
                'valid': False,
                'error': 'License not found'
            }), 404
        
        license_data = result[0]
        
        # Check status
        if license_data['status'] != 'active':
            return jsonify({
                'valid': False,
                'error': f'License is {license_data["status"]}'
            }), 400
        
        # Check expiration
        if license_data.get('expires_at') and license_data['expires_at'] < datetime.now():
            # Auto-update expired license
            db.licenses.update_one(
                {'_id': license_data['_id']},
                {'$set': {'status': 'expired'}}
            )
            return jsonify({
                'valid': False,
                'error': 'License expired'
            }), 400
        
        # Update last check
        db.licenses.update_one(
            {'_id': license_data['_id']},
            {'$set': {'last_check': datetime.now()}}
        )
        
        # Return license validation response
        response = {
            'valid': True,
            'license': {
                'key': license_data['license_key'],
                'status': license_data['status'],
                'activated_at': license_data.get('activated_at', '').isoformat() if license_data.get('activated_at') else None,
                'expires_at': license_data.get('expires_at', '').isoformat() if license_data.get('expires_at') else None,
                'domain': license_data.get('domain'),
                'last_check': datetime.now().isoformat()
            },
            'plan': {
                'name': license_data['plan']['name'],
                'display_name': license_data['plan']['display_name'],
                'features': license_data['plan']['features'],
                'monthly_requests': license_data['plan']['monthly_requests'],
                'max_sites': license_data['plan']['max_sites']
            },
            'customer': {
                'email': license_data['customer']['email'],
                'name': license_data['customer'].get('name'),
                'company': license_data['customer'].get('company')
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.error(f"License validation error: {e}")
        return jsonify({
            'valid': False,
            'error': 'Validation failed'
        }), 500

@app.route('/api/chat', methods=['POST'])
@require_license
@limiter.limit("100 per hour")
def proxy_ai_chat():
    """Proxy AI chat requests for Pro/Agency users"""
    try:
        db = get_db()
        license_doc = g.license
        
        # Get plan information
        plan_doc = db.plans.find_one({'_id': license_doc['plan_id']})
        if not plan_doc:
            return jsonify({'error': 'Plan not found'}), 500
        
        # Check if plan includes AI (not Starter)
        if 'ai_included' not in plan_doc.get('features', []):
            return jsonify({
                'error': 'AI not included in your plan',
                'plan': plan_doc['name'],
                'message': 'Upgrade to Pro or Agency plan for included AI'
            }), 403
        
        # Check usage limits
        if not check_usage_limit(db, license_doc['_id']):
            return jsonify({
                'error': 'Monthly usage limit exceeded',
                'limit': plan_doc['monthly_requests']
            }), 429
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        messages = data.get('messages', [])
        provider = data.get('api_provider', 'openai').lower()
        model = data.get('model')
        
        if not messages:
            return jsonify({'error': 'Messages required'}), 400
        
        if provider not in AI_PROVIDERS:
            return jsonify({'error': f'Unsupported provider: {provider}'}), 400
        
        # Get provider config
        provider_config = AI_PROVIDERS[provider]
        if not provider_config['api_key']:
            return jsonify({'error': f'{provider} not configured'}), 503
        
        start_time = datetime.now()
        
        # Make AI request based on provider
        if provider == 'openai' or provider == 'deepseek':
            # OpenAI-compatible format
            ai_data = {
                'model': model or provider_config['model'],
                'messages': messages,
                'max_tokens': data.get('max_tokens', 1000),
                'temperature': data.get('temperature', 0.7)
            }
            
            headers = {
                'Authorization': f'Bearer {provider_config["api_key"]}',
                'Content-Type': 'application/json'
            }
            
        elif provider == 'anthropic':
            # Anthropic format
            ai_data = {
                'model': model or provider_config['model'],
                'messages': messages,
                'max_tokens': data.get('max_tokens', 1000)
            }
            
            headers = {
                'x-api-key': provider_config['api_key'],
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'
            }
        
        # Make the request
        response = requests.post(
            provider_config['endpoint'],
            json=ai_data,
            headers=headers,
            timeout=30
        )
        
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log usage
        usage_log = {
            'license_id': license_doc['_id'],
            'endpoint': f'/api/chat/{provider}',
            'tokens_used': 0,  # Would need to extract from AI response
            'response_time_ms': response_time,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'created_at': datetime.now()
        }
        
        db.usage_logs.insert_one(usage_log)
        
        if response.status_code == 200:
            ai_response = response.json()
            
            # Extract token count if available
            if provider in ['openai', 'deepseek'] and 'usage' in ai_response:
                tokens_used = ai_response['usage'].get('total_tokens', 0)
                db.usage_logs.update_one(
                    {'_id': usage_log['_id']},
                    {'$set': {'tokens_used': tokens_used}}
                )
            
            return jsonify({
                'success': True,
                'provider': provider,
                'model': model or provider_config['model'],
                'response': ai_response,
                'usage': {
                    'tokens': tokens_used if 'tokens_used' in locals() else 0,
                    'response_time_ms': response_time
                }
            })
        else:
            app.logger.error(f"AI API error: {response.status_code} - {response.text}")
            return jsonify({
                'error': 'AI service error',
                'details': response.text
            }), response.status_code
            
    except Exception as e:
        app.logger.error(f"Chat proxy error: {e}")
        return jsonify({'error': 'Request failed'}), 500

@app.route('/api/usage/<license_key>')
@limiter.limit("10 per minute")
def get_usage_stats(license_key):
    """Get usage statistics for a license"""
    try:
        db = get_db()
        
        # Find license
        license_doc = db.licenses.find_one({'license_key': license_key})
        if not license_doc:
            return jsonify({'error': 'License not found'}), 404
        
        # Get current month usage
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        next_month = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)
        
        # Usage stats pipeline
        usage_pipeline = [
            {
                '$match': {
                    'license_id': license_doc['_id'],
                    'created_at': {
                        '$gte': start_of_month,
                        '$lt': next_month
                    }
                }
            },
            {
                '$group': {
                    '_id': None,
                    'total_requests': {'$sum': 1},
                    'total_tokens': {'$sum': '$tokens_used'},
                    'avg_response_time': {'$avg': '$response_time_ms'}
                }
            }
        ]
        
        usage_result = list(db.usage_logs.aggregate(usage_pipeline))
        
        # Get plan info
        plan_doc = db.plans.find_one({'_id': license_doc['plan_id']})
        
        current_usage = usage_result[0] if usage_result else {
            'total_requests': 0,
            'total_tokens': 0,
            'avg_response_time': 0
        }
        
        return jsonify({
            'license_key': license_key,
            'plan': plan_doc['name'] if plan_doc else 'unknown',
            'current_month': {
                'requests': current_usage['total_requests'],
                'tokens': current_usage['total_tokens'],
                'avg_response_time_ms': round(current_usage['avg_response_time'] or 0, 2)
            },
            'limits': {
                'monthly_requests': plan_doc['monthly_requests'] if plan_doc else 0,
                'requests_remaining': max(0, plan_doc['monthly_requests'] - current_usage['total_requests']) if plan_doc and plan_doc['monthly_requests'] > 0 else 'unlimited'
            },
            'period': {
                'start': start_of_month.isoformat(),
                'end': next_month.isoformat()
            }
        })
        
    except Exception as e:
        app.logger.error(f"Usage stats error: {e}")
        return jsonify({'error': 'Failed to get usage stats'}), 500

# Admin endpoints for license management
@app.route('/api/admin/customers', methods=['POST'])
def create_customer():
    """Create new customer (admin only - would need auth)"""
    try:
        data = request.get_json()
        if not data or not data.get('email'):
            return jsonify({'error': 'Email required'}), 400
        
        db = get_db()
        
        # Check if customer already exists
        existing = db.customers.find_one({'email': data['email']})
        if existing:
            return jsonify({'error': 'Customer already exists'}), 400
        
        customer_doc = {
            'email': data['email'],
            'name': data.get('name'),
            'company': data.get('company'),
            'notes': data.get('notes'),
            'phone': data.get('phone'),
            'address': data.get('address'),
            'country': data.get('country'),
            'stripe_customer_id': data.get('stripe_customer_id'),
            'paypal_customer_id': data.get('paypal_customer_id'),
            'paddle_subscription_id': data.get('paddle_subscription_id'),
            'status': 'active',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        result = db.customers.insert_one(customer_doc)
        customer_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'success': True,
            'customer': serialize_doc(customer_doc)
        })
        
    except Exception as e:
        app.logger.error(f"Create customer error: {e}")
        return jsonify({'error': 'Failed to create customer'}), 500

@app.route('/api/admin/licenses', methods=['POST'])  
def create_license():
    """Create new license (admin only - would need auth)"""
    try:
        data = request.get_json()
        required_fields = ['customer_id', 'plan_name']
        
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': f'Required fields: {required_fields}'}), 400
        
        db = get_db()
        
        # Get customer and plan
        customer_id = to_object_id(data['customer_id'])
        if not customer_id:
            return jsonify({'error': 'Invalid customer_id'}), 400
        
        customer = db.customers.find_one({'_id': customer_id})
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        plan = db.plans.find_one({'name': data['plan_name']})
        if not plan:
            return jsonify({'error': 'Plan not found'}), 404
        
        # Generate unique license key
        max_attempts = 10
        license_key = None
        
        for _ in range(max_attempts):
            potential_key = generate_license_key()
            if not db.licenses.find_one({'license_key': potential_key}):
                license_key = potential_key
                break
        
        if not license_key:
            return jsonify({'error': 'Failed to generate unique license key'}), 500
        
        license_doc = {
            'license_key': license_key,
            'customer_id': customer_id,
            'plan_id': plan['_id'],
            'domain': data.get('domain'),
            'status': 'active',
            'activated_at': datetime.now(),
            'expires_at': None,  # Null for recurring subscriptions
            'last_check': None,
            'metadata': data.get('metadata', {}),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        result = db.licenses.insert_one(license_doc)
        license_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'success': True,
            'license': serialize_doc(license_doc)
        })
        
    except Exception as e:
        app.logger.error(f"Create license error: {e}")
        return jsonify({'error': 'Failed to create license'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5013)