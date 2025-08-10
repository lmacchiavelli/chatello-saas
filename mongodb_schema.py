#!/usr/bin/env python3
"""
Chatello SaaS - MongoDB Schema Definition
Equivalent to database_schema.sql but for MongoDB Atlas
"""

from datetime import datetime, timedelta
import secrets
import hashlib
from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING

# MongoDB Collections Schema
COLLECTIONS_SCHEMA = {
    
    # Plans collection (equivalent to plans table)
    'plans': {
        '_id': 'ObjectId',  # Auto-generated
        'name': 'str',      # starter, pro, agency
        'display_name': 'str',
        'price': 'float',
        'currency': 'str',  # EUR
        'monthly_requests': 'int',
        'max_sites': 'int',  # -1 for unlimited
        'features': 'list',  # Array of feature strings
        'is_active': 'bool',
        'created_at': 'datetime',
        'updated_at': 'datetime'
    },
    
    # Customers collection
    'customers': {
        '_id': 'ObjectId',
        'email': 'str',     # unique
        'name': 'str',
        'company': 'str',
        'notes': 'str',
        'phone': 'str',
        'address': 'str',
        'country': 'str',
        'stripe_customer_id': 'str',
        'paypal_customer_id': 'str',
        'paddle_subscription_id': 'str',  # New for Paddle
        'status': 'str',    # active, inactive, suspended
        'created_at': 'datetime',
        'updated_at': 'datetime'
    },
    
    # Licenses collection
    'licenses': {
        '_id': 'ObjectId',
        'license_key': 'str',   # unique, CHA-XXXX-XXXX format
        'customer_id': 'ObjectId',  # Reference to customers._id
        'plan_id': 'ObjectId',      # Reference to plans._id
        'domain': 'str',
        'status': 'str',    # active, inactive, suspended, expired
        'activated_at': 'datetime',
        'expires_at': 'datetime',  # null for recurring
        'last_check': 'datetime',
        'metadata': 'dict',  # JSON equivalent
        'created_at': 'datetime',
        'updated_at': 'datetime'
    },
    
    # Usage logs collection
    'usage_logs': {
        '_id': 'ObjectId',
        'license_id': 'ObjectId',   # Reference to licenses._id
        'endpoint': 'str',
        'tokens_used': 'int',
        'response_time_ms': 'int',
        'ip_address': 'str',
        'user_agent': 'str',
        'created_at': 'datetime'
    },
    
    # Payments collection
    'payments': {
        '_id': 'ObjectId',
        'customer_id': 'ObjectId',
        'license_id': 'ObjectId',
        'amount': 'float',
        'currency': 'str',
        'status': 'str',    # pending, completed, failed, refunded
        'payment_method': 'str',
        'transaction_id': 'str',
        'provider': 'str',   # paddle, stripe, paypal
        'metadata': 'dict',
        'created_at': 'datetime',
        'updated_at': 'datetime'
    },
    
    # API Keys collection (for Pro/Agency shared keys)
    'api_keys': {
        '_id': 'ObjectId',
        'provider': 'str',      # openai, anthropic, deepseek
        'api_key': 'str',       # encrypted
        'is_active': 'bool',
        'usage_count': 'int',
        'last_used': 'datetime',
        'created_at': 'datetime',
        'updated_at': 'datetime'
    },
    
    # Activity logs collection
    'activity_logs': {
        '_id': 'ObjectId',
        'license_id': 'ObjectId',  # optional
        'customer_id': 'ObjectId', # optional
        'action': 'str',
        'details': 'dict',
        'ip_address': 'str',
        'created_at': 'datetime'
    }
}

# MongoDB Indexes (equivalent to MySQL indexes)
INDEXES = {
    'plans': [
        IndexModel([('name', ASCENDING)]),
        IndexModel([('is_active', ASCENDING)])
    ],
    
    'customers': [
        IndexModel([('email', ASCENDING)], unique=True),
        IndexModel([('status', ASCENDING)]),
        IndexModel([('stripe_customer_id', ASCENDING)]),
        IndexModel([('paddle_subscription_id', ASCENDING)])
    ],
    
    'licenses': [
        IndexModel([('license_key', ASCENDING)], unique=True),
        IndexModel([('customer_id', ASCENDING)]),
        IndexModel([('status', ASCENDING)]),
        IndexModel([('domain', ASCENDING)]),
        IndexModel([('expires_at', ASCENDING)])
    ],
    
    'usage_logs': [
        IndexModel([('license_id', ASCENDING)]),
        IndexModel([('endpoint', ASCENDING)]),
        IndexModel([('created_at', DESCENDING)]),
        IndexModel([('license_id', ASCENDING), ('created_at', DESCENDING)])
    ],
    
    'payments': [
        IndexModel([('customer_id', ASCENDING)]),
        IndexModel([('license_id', ASCENDING)]),
        IndexModel([('status', ASCENDING)]),
        IndexModel([('transaction_id', ASCENDING)])
    ],
    
    'api_keys': [
        IndexModel([('provider', ASCENDING)], unique=True),
        IndexModel([('is_active', ASCENDING)])
    ],
    
    'activity_logs': [
        IndexModel([('license_id', ASCENDING)]),
        IndexModel([('customer_id', ASCENDING)]),
        IndexModel([('action', ASCENDING)]),
        IndexModel([('created_at', DESCENDING)])
    ]
}

def init_mongodb_collections(db):
    """
    Initialize MongoDB collections with indexes and default data
    """
    
    # Create collections and indexes
    for collection_name, indexes in INDEXES.items():
        collection = db[collection_name]
        try:
            collection.create_indexes(indexes)
            print(f"✅ Created indexes for {collection_name}")
        except Exception as e:
            print(f"❌ Error creating indexes for {collection_name}: {e}")
    
    # Insert default plans (equivalent to INSERT INTO plans)
    plans_collection = db.plans
    
    # Check if plans already exist
    if plans_collection.count_documents({}) == 0:
        default_plans = [
            {
                'name': 'starter',
                'display_name': 'Starter - BYOK',
                'price': 2.99,
                'currency': 'EUR',
                'monthly_requests': 0,  # No limit for BYOK
                'requests_per_minute': 0,  # No limit for BYOK
                'requests_per_hour': 0,   # No limit for BYOK
                'monthly_budget_eur': 0,  # No budget - users pay their own API costs
                'cost_per_1k_tokens': 0,  # BYOK users manage their own costs
                'max_sites': 1,
                'features': [
                    'bring_your_own_key',
                    '1_site',
                    'basic_support',
                    'community_access'
                ],
                'is_active': True,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'name': 'pro',
                'display_name': 'Pro - AI Inclusa',
                'price': 7.99,
                'currency': 'EUR',
                'monthly_requests': 1000,
                'requests_per_minute': 10,  # 10 requests per minute
                'requests_per_hour': 200,   # 200 requests per hour
                'monthly_budget_eur': 4.0,  # €4/month budget (~2.6M tokens)
                'cost_per_1k_tokens': 0.0015,  # OpenAI GPT-4o-mini cost
                'max_sites': 3,
                'features': [
                    'ai_included',
                    '3_sites',
                    'priority_support',
                    'advanced_features',
                    'no_api_key_needed'
                ],
                'is_active': True,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            },
            {
                'name': 'agency',
                'display_name': 'Agency - White Label',
                'price': 19.99,
                'currency': 'EUR',
                'monthly_requests': 5000,
                'requests_per_minute': 25,  # 25 requests per minute
                'requests_per_hour': 500,   # 500 requests per hour
                'monthly_budget_eur': 10.0,  # €10/month budget (~6.6M tokens)
                'cost_per_1k_tokens': 0.0015,  # OpenAI GPT-4o-mini cost
                'max_sites': -1,  # Unlimited
                'features': [
                    'ai_included',
                    'unlimited_sites',
                    'white_label',
                    'dedicated_support',
                    'custom_branding',
                    'api_access'
                ],
                'is_active': True,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
        ]
        
        result = plans_collection.insert_many(default_plans)
        print(f"✅ Inserted {len(result.inserted_ids)} default plans")
    else:
        print("⚠️  Plans already exist, skipping default data insertion")


def generate_license_key():
    """
    Generate unique license key (MongoDB equivalent of MySQL stored procedure)
    Format: CHA-XXXX-XXXX-XXXX-XXXX
    """
    segments = []
    for _ in range(4):
        # Generate 8-character hex string
        segment = secrets.token_hex(4).upper()
        segments.append(segment)
    
    return f"CHA-{'-'.join(segments)}"


def check_usage_limit(db, license_id, month=None, year=None):
    """
    Check if license has exceeded monthly usage limit
    MongoDB equivalent of MySQL check_usage_limit function
    """
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    # Get license and plan info
    license_doc = db.licenses.find_one({'_id': license_id})
    if not license_doc:
        return False
    
    plan_doc = db.plans.find_one({'_id': license_doc['plan_id']})
    if not plan_doc:
        return False
    
    # If plan has 0 monthly_requests, it means unlimited (BYOK)
    if plan_doc['monthly_requests'] == 0:
        return True
    
    # Count usage for current month
    usage_count = db.usage_logs.count_documents({
        'license_id': license_id,
        'created_at': {
            '$gte': datetime(year, month, 1),
            '$lt': datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
        }
    })
    
    return usage_count < plan_doc['monthly_requests']


def check_rate_limit_minute(db, license_id):
    """
    Check if license has exceeded per-minute rate limit
    """
    # Get license and plan info
    license_doc = db.licenses.find_one({'_id': license_id})
    if not license_doc:
        return False
    
    plan_doc = db.plans.find_one({'_id': license_doc['plan_id']})
    if not plan_doc:
        return False
    
    # If plan has 0 requests_per_minute, it means unlimited (BYOK)
    if plan_doc.get('requests_per_minute', 0) == 0:
        return True
    
    # Count usage in the last minute
    one_minute_ago = datetime.now() - timedelta(minutes=1)
    usage_count = db.usage_logs.count_documents({
        'license_id': license_id,
        'created_at': {'$gte': one_minute_ago}
    })
    
    return usage_count < plan_doc['requests_per_minute']


def check_rate_limit_hour(db, license_id):
    """
    Check if license has exceeded per-hour rate limit
    """
    # Get license and plan info
    license_doc = db.licenses.find_one({'_id': license_id})
    if not license_doc:
        return False
    
    plan_doc = db.plans.find_one({'_id': license_doc['plan_id']})
    if not plan_doc:
        return False
    
    # If plan has 0 requests_per_hour, it means unlimited (BYOK)
    if plan_doc.get('requests_per_hour', 0) == 0:
        return True
    
    # Count usage in the last hour
    one_hour_ago = datetime.now() - timedelta(hours=1)
    usage_count = db.usage_logs.count_documents({
        'license_id': license_id,
        'created_at': {'$gte': one_hour_ago}
    })
    
    return usage_count < plan_doc['requests_per_hour']


def check_budget_limit(db, license_id, month=None, year=None):
    """
    Check if license has exceeded monthly budget limit (for Pro/Agency plans)
    """
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    # Get license and plan info
    license_doc = db.licenses.find_one({'_id': license_id})
    if not license_doc:
        return False
    
    plan_doc = db.plans.find_one({'_id': license_doc['plan_id']})
    if not plan_doc:
        return False
    
    # If plan has 0 budget, it means unlimited (BYOK)
    monthly_budget = plan_doc.get('monthly_budget_eur', 0)
    if monthly_budget == 0:
        return True
    
    # Calculate current month's token cost
    cost_per_1k_tokens = plan_doc.get('cost_per_1k_tokens', 0.0015)
    
    # Sum total tokens used this month
    pipeline = [
        {
            '$match': {
                'license_id': license_id,
                'created_at': {
                    '$gte': datetime(year, month, 1),
                    '$lt': datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
                }
            }
        },
        {
            '$group': {
                '_id': None,
                'total_tokens': {'$sum': '$tokens_used'}
            }
        }
    ]
    
    result = list(db.usage_logs.aggregate(pipeline))
    total_tokens = result[0]['total_tokens'] if result else 0
    
    # Calculate current cost
    current_cost = (total_tokens / 1000) * cost_per_1k_tokens
    
    return current_cost < monthly_budget


def get_usage_stats(db, license_id, month=None, year=None):
    """
    Get detailed usage statistics for a license
    """
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    # Get license and plan info
    license_doc = db.licenses.find_one({'_id': license_id})
    if not license_doc:
        return None
    
    plan_doc = db.plans.find_one({'_id': license_doc['plan_id']})
    if not plan_doc:
        return None
    
    # Current month usage
    current_month_start = datetime(year, month, 1)
    current_month_end = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    
    # Last hour usage
    one_hour_ago = datetime.now() - timedelta(hours=1)
    
    # Last minute usage
    one_minute_ago = datetime.now() - timedelta(minutes=1)
    
    # Aggregate usage data
    monthly_pipeline = [
        {
            '$match': {
                'license_id': license_id,
                'created_at': {'$gte': current_month_start, '$lt': current_month_end}
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
    
    hourly_count = db.usage_logs.count_documents({
        'license_id': license_id,
        'created_at': {'$gte': one_hour_ago}
    })
    
    minute_count = db.usage_logs.count_documents({
        'license_id': license_id,
        'created_at': {'$gte': one_minute_ago}
    })
    
    monthly_result = list(db.usage_logs.aggregate(monthly_pipeline))
    monthly_data = monthly_result[0] if monthly_result else {
        'total_requests': 0,
        'total_tokens': 0,
        'avg_response_time': 0
    }
    
    # Calculate costs and percentages
    cost_per_1k_tokens = plan_doc.get('cost_per_1k_tokens', 0)
    current_cost = (monthly_data['total_tokens'] / 1000) * cost_per_1k_tokens
    monthly_budget = plan_doc.get('monthly_budget_eur', 0)
    
    return {
        'license_id': str(license_id),
        'plan': plan_doc['name'],
        'current_month': {
            'requests': monthly_data['total_requests'],
            'tokens': monthly_data['total_tokens'],
            'cost_eur': round(current_cost, 4),
            'avg_response_time_ms': round(monthly_data['avg_response_time'] or 0, 2)
        },
        'current_hour': {
            'requests': hourly_count
        },
        'current_minute': {
            'requests': minute_count
        },
        'limits': {
            'monthly_requests': plan_doc['monthly_requests'],
            'requests_per_minute': plan_doc.get('requests_per_minute', 0),
            'requests_per_hour': plan_doc.get('requests_per_hour', 0),
            'monthly_budget_eur': monthly_budget
        },
        'usage_percentages': {
            'requests': round((monthly_data['total_requests'] / plan_doc['monthly_requests'] * 100), 2) if plan_doc['monthly_requests'] > 0 else 0,
            'budget': round((current_cost / monthly_budget * 100), 2) if monthly_budget > 0 else 0
        }
    }


# Example connection and initialization
if __name__ == "__main__":
    # This would be used for testing/setup
    CONNECTION_STRING = "mongodb+srv://username:password@cluster.mongodb.net/"
    
    client = MongoClient(CONNECTION_STRING)
    db = client.chatello_saas
    
    print("🚀 Initializing MongoDB collections...")
    init_mongodb_collections(db)
    
    # Test license key generation
    print(f"📝 Sample license key: {generate_license_key()}")
    
    print("✅ MongoDB setup complete!")