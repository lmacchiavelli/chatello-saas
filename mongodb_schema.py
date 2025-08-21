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
    },
    
    # Historical Analytics collection (new - for daily/monthly tracking)
    'historical_analytics': {
        '_id': 'ObjectId',
        'date': 'datetime',        # Date of the record (start of day)
        'period_type': 'str',      # 'daily', 'monthly'
        'total_customers': 'int',  # Total customers count
        'paying_customers': 'int', # Active paying customers
        'mrr': 'float',           # Monthly Recurring Revenue for that period
        'arr': 'float',           # Annual Recurring Revenue (MRR * 12)
        'new_customers': 'int',   # New customers added this period
        'churned_customers': 'int', # Customers lost this period
        'notes': 'str',           # Admin notes for this period
        'revenue_by_plan': 'dict', # Revenue breakdown by plan
        'auto_events': 'list',    # Automatic events for this day
        'created_at': 'datetime',
        'updated_at': 'datetime'
    },
    
    # Business Events collection (new - automatic event tracking)
    'business_events': {
        '_id': 'ObjectId',
        'event_type': 'str',      # 'new_customer', 'license_created', 'license_cancelled', 'payment_completed', 'milestone'
        'event_date': 'datetime', # When the event occurred
        'customer_id': 'ObjectId', # Optional - related customer
        'license_id': 'ObjectId',  # Optional - related license
        'plan_name': 'str',       # Optional - plan involved
        'amount': 'float',        # Optional - money amount
        'currency': 'str',        # Optional - EUR, USD
        'description': 'str',     # Human readable description
        'auto_generated': 'bool', # True if automatically generated
        'metadata': 'dict',       # Additional event data
        'processed': 'bool',      # If included in daily analytics
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
    ],
    
    'historical_analytics': [
        IndexModel([('date', DESCENDING)]),
        IndexModel([('period_type', ASCENDING)]),
        IndexModel([('date', ASCENDING), ('period_type', ASCENDING)], unique=True)  # Prevent duplicate entries
    ],
    
    'business_events': [
        IndexModel([('event_date', DESCENDING)]),
        IndexModel([('event_type', ASCENDING)]),
        IndexModel([('customer_id', ASCENDING)]),
        IndexModel([('license_id', ASCENDING)]),
        IndexModel([('processed', ASCENDING)]),
        IndexModel([('auto_generated', ASCENDING)])
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


def save_daily_analytics(db, target_date=None, notes=""):
    """
    Save daily analytics snapshot to historical_analytics collection
    """
    from datetime import timezone
    
    if target_date is None:
        target_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate analytics for the specified date
    total_customers = db.customers.count_documents({})
    
    # Get active licenses (paying customers)
    active_licenses_pipeline = [
        {
            '$match': {
                'status': 'active',
                '$or': [
                    {'expires_at': None},
                    {'expires_at': {'$gt': target_date}}
                ]
            }
        },
        {
            '$lookup': {
                'from': 'plans',
                'localField': 'plan_id',
                'foreignField': '_id',
                'as': 'plan'
            }
        },
        {'$unwind': '$plan'}
    ]
    
    active_licenses = list(db.licenses.aggregate(active_licenses_pipeline))
    paying_customers = len(active_licenses)
    
    # Calculate MRR and revenue by plan
    mrr = 0
    revenue_by_plan = {}
    
    for license in active_licenses:
        plan_name = license['plan']['name'].lower()
        plan_price = license['plan'].get('price', 0)
        
        if plan_name not in revenue_by_plan:
            revenue_by_plan[plan_name] = {'revenue': 0, 'count': 0}
        
        revenue_by_plan[plan_name]['count'] += 1
        
        # Skip one-time/lifetime plans from MRR
        if not license['plan'].get('is_lifetime', False) and plan_name != 'founders':
            mrr += plan_price
            revenue_by_plan[plan_name]['revenue'] += plan_price
        else:
            revenue_by_plan[plan_name]['revenue'] += plan_price  # Track total revenue
    
    arr = mrr * 12
    
    # Calculate new customers for this day (simplified - would need better logic in production)
    day_start = target_date
    day_end = target_date.replace(hour=23, minute=59, second=59)
    
    new_customers = db.customers.count_documents({
        'created_at': {'$gte': day_start, '$lte': day_end}
    })
    
    # Calculate churned customers (simplified)
    churned_customers = db.licenses.count_documents({
        'status': 'cancelled',
        'updated_at': {'$gte': day_start, '$lte': day_end}
    })
    
    # Create historical record
    historical_record = {
        'date': target_date,
        'period_type': 'daily',
        'total_customers': total_customers,
        'paying_customers': paying_customers,
        'mrr': round(mrr, 2),
        'arr': round(arr, 2),
        'new_customers': new_customers,
        'churned_customers': churned_customers,
        'notes': notes,
        'revenue_by_plan': revenue_by_plan,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    
    # Use upsert to prevent duplicates
    result = db.historical_analytics.replace_one(
        {'date': target_date, 'period_type': 'daily'},
        historical_record,
        upsert=True
    )
    
    return {
        'success': True,
        'record_id': str(result.upserted_id) if result.upserted_id else 'updated',
        'data': historical_record
    }


def get_historical_analytics(db, days=30, period_type='daily'):
    """
    Retrieve historical analytics data for the specified period
    """
    from datetime import timezone
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Query historical data
    historical_data = list(db.historical_analytics.find({
        'period_type': period_type,
        'date': {'$gte': start_date, '$lte': end_date}
    }).sort('date', -1))  # Most recent first
    
    # Format data for table display
    formatted_data = []
    for record in historical_data:
        formatted_data.append({
            'date': record['date'].strftime('%Y-%m-%d'),
            'total_customers': record['total_customers'],
            'paying_customers': record['paying_customers'],
            'mrr': f"€{record['mrr']:.2f}",
            'arr': f"€{record['arr']:.2f}",
            'new_customers': record.get('new_customers', 0),
            'churned_customers': record.get('churned_customers', 0),
            'notes': record.get('notes', ''),
            'revenue_by_plan': record.get('revenue_by_plan', {})
        })
    
    return formatted_data


def update_historical_notes(db, target_date, notes):
    """
    Update notes for a specific historical record
    """
    from datetime import timezone
    
    # Parse date if it's a string
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    
    result = db.historical_analytics.update_one(
        {'date': target_date, 'period_type': 'daily'},
        {
            '$set': {
                'notes': notes,
                'updated_at': datetime.now(timezone.utc)
            }
        }
    )
    
    return result.modified_count > 0


def create_business_event(db, event_type, description, customer_id=None, license_id=None, plan_name=None, amount=None, currency='EUR', metadata=None):
    """
    Create a new business event that will be automatically included in daily analytics
    """
    from datetime import timezone
    
    # Validate event type
    valid_events = [
        'new_customer',           # Nuovo cliente registrato
        'license_created',        # Nuova licenza creata
        'license_activated',      # Licenza attivata
        'license_cancelled',      # Licenza cancellata
        'payment_completed',      # Pagamento completato
        'payment_failed',         # Pagamento fallito
        'plan_upgraded',          # Upgrade piano
        'plan_downgraded',        # Downgrade piano
        'milestone_reached',      # Milestone raggiunto (es. 100 clienti)
        'marketing_campaign',     # Inizio campagna marketing
        'feature_released',       # Rilascio nuova feature
        'partnership',           # Nuova partnership
        'media_mention',         # Menzione sui media
        'support_ticket',        # Ticket di supporto importante
        'server_issue',          # Problema server
        'maintenance',           # Manutenzione programmata
    ]
    
    if event_type not in valid_events:
        raise ValueError(f"Invalid event_type. Must be one of: {valid_events}")
    
    # Create event document
    event = {
        'event_type': event_type,
        'event_date': datetime.now(timezone.utc),
        'customer_id': customer_id,
        'license_id': license_id,
        'plan_name': plan_name,
        'amount': amount,
        'currency': currency,
        'description': description,
        'auto_generated': True,
        'metadata': metadata or {},
        'processed': False,
        'created_at': datetime.now(timezone.utc)
    }
    
    # Insert event
    result = db.business_events.insert_one(event)
    
    return {
        'success': True,
        'event_id': str(result.inserted_id),
        'event': event
    }


def get_daily_events(db, target_date=None):
    """
    Get all business events for a specific day
    """
    from datetime import timezone
    
    if target_date is None:
        target_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get events for the day
    day_start = target_date
    day_end = target_date.replace(hour=23, minute=59, second=59)
    
    events = list(db.business_events.find({
        'event_date': {'$gte': day_start, '$lte': day_end}
    }).sort('event_date', 1))
    
    return events


def generate_daily_notes(db, target_date=None):
    """
    Generate automatic daily notes based on business events
    """
    events = get_daily_events(db, target_date)
    
    if not events:
        return ""
    
    # Group events by type
    event_groups = {}
    for event in events:
        event_type = event['event_type']
        if event_type not in event_groups:
            event_groups[event_type] = []
        event_groups[event_type].append(event)
    
    # Generate notes based on events
    notes_parts = []
    
    # Priority events first (sales, customers, etc.)
    priority_events = ['new_customer', 'license_created', 'payment_completed', 'milestone_reached']
    
    for event_type in priority_events:
        if event_type in event_groups:
            events_of_type = event_groups[event_type]
            
            if event_type == 'new_customer':
                count = len(events_of_type)
                if count == 1:
                    notes_parts.append(f"🎉 Nuovo cliente: {events_of_type[0]['description']}")
                else:
                    notes_parts.append(f"🎉 {count} nuovi clienti registrati")
            
            elif event_type == 'license_created':
                count = len(events_of_type)
                if count == 1:
                    plan = events_of_type[0].get('plan_name', 'Unknown')
                    notes_parts.append(f"🎫 Nuova licenza {plan.title()}: {events_of_type[0]['description']}")
                else:
                    notes_parts.append(f"🎫 {count} nuove licenze create")
            
            elif event_type == 'payment_completed':
                total_amount = sum(e.get('amount', 0) for e in events_of_type)
                count = len(events_of_type)
                if count == 1:
                    notes_parts.append(f"💰 Pagamento ricevuto: €{events_of_type[0].get('amount', 0)}")
                else:
                    notes_parts.append(f"💰 {count} pagamenti completati (€{total_amount:.2f})")
            
            elif event_type == 'milestone_reached':
                for event in events_of_type:
                    notes_parts.append(f"🏆 {event['description']}")
    
    # Other business events
    other_events = ['plan_upgraded', 'plan_downgraded', 'feature_released', 'marketing_campaign', 'partnership']
    
    for event_type in other_events:
        if event_type in event_groups:
            events_of_type = event_groups[event_type]
            
            if event_type == 'plan_upgraded':
                count = len(events_of_type)
                notes_parts.append(f"⬆️ {count} upgrade piano")
            
            elif event_type == 'plan_downgraded':
                count = len(events_of_type)
                notes_parts.append(f"⬇️ {count} downgrade piano")
            
            elif event_type == 'feature_released':
                for event in events_of_type:
                    notes_parts.append(f"🚀 {event['description']}")
            
            elif event_type == 'marketing_campaign':
                for event in events_of_type:
                    notes_parts.append(f"📢 {event['description']}")
            
            elif event_type == 'partnership':
                for event in events_of_type:
                    notes_parts.append(f"🤝 {event['description']}")
    
    # Technical events
    tech_events = ['server_issue', 'maintenance']
    
    for event_type in tech_events:
        if event_type in event_groups:
            events_of_type = event_groups[event_type]
            
            if event_type == 'server_issue':
                notes_parts.append(f"⚠️ Problemi tecnici risolti")
            
            elif event_type == 'maintenance':
                notes_parts.append(f"🔧 Manutenzione programmata")
    
    # Negative events
    negative_events = ['license_cancelled', 'payment_failed']
    
    for event_type in negative_events:
        if event_type in event_groups:
            events_of_type = event_groups[event_type]
            count = len(events_of_type)
            
            if event_type == 'license_cancelled':
                notes_parts.append(f"😞 {count} licenze cancellate")
            
            elif event_type == 'payment_failed':
                notes_parts.append(f"❌ {count} pagamenti falliti")
    
    # Join all notes with separator
    return " • ".join(notes_parts)


def save_daily_analytics_with_events(db, target_date=None, additional_notes=""):
    """
    Enhanced version of save_daily_analytics that includes automatic events
    """
    from datetime import timezone
    
    if target_date is None:
        target_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get all events for this day
    events = get_daily_events(db, target_date)
    
    # Generate automatic notes
    auto_notes = generate_daily_notes(db, target_date)
    
    # Combine auto notes with additional notes
    combined_notes = []
    if auto_notes:
        combined_notes.append(auto_notes)
    if additional_notes:
        combined_notes.append(additional_notes)
    
    final_notes = " | ".join(combined_notes)
    
    # Calculate analytics for the specified date
    total_customers = db.customers.count_documents({})
    
    # Get active licenses (paying customers)
    active_licenses_pipeline = [
        {
            '$match': {
                'status': 'active',
                '$or': [
                    {'expires_at': None},
                    {'expires_at': {'$gt': target_date}}
                ]
            }
        },
        {
            '$lookup': {
                'from': 'plans',
                'localField': 'plan_id',
                'foreignField': '_id',
                'as': 'plan'
            }
        },
        {'$unwind': '$plan'}
    ]
    
    active_licenses = list(db.licenses.aggregate(active_licenses_pipeline))
    paying_customers = len(active_licenses)
    
    # Calculate MRR and revenue by plan
    mrr = 0
    revenue_by_plan = {}
    
    for license in active_licenses:
        plan_name = license['plan']['name'].lower()
        plan_price = license['plan'].get('price', 0)
        
        if plan_name not in revenue_by_plan:
            revenue_by_plan[plan_name] = {'revenue': 0, 'count': 0}
        
        revenue_by_plan[plan_name]['count'] += 1
        
        # Skip one-time/lifetime plans from MRR
        if not license['plan'].get('is_lifetime', False) and plan_name != 'founders':
            mrr += plan_price
            revenue_by_plan[plan_name]['revenue'] += plan_price
        else:
            revenue_by_plan[plan_name]['revenue'] += plan_price  # Track total revenue
    
    arr = mrr * 12
    
    # Calculate new customers for this day
    day_start = target_date
    day_end = target_date.replace(hour=23, minute=59, second=59)
    
    new_customers = db.customers.count_documents({
        'created_at': {'$gte': day_start, '$lte': day_end}
    })
    
    # Calculate churned customers
    churned_customers = db.licenses.count_documents({
        'status': 'cancelled',
        'updated_at': {'$gte': day_start, '$lte': day_end}
    })
    
    # Format events for storage
    auto_events = []
    for event in events:
        auto_events.append({
            'type': event['event_type'],
            'description': event['description'],
            'time': event['event_date'].strftime('%H:%M'),
            'customer_id': str(event.get('customer_id')) if event.get('customer_id') else None,
            'amount': event.get('amount')
        })
    
    # Create historical record
    historical_record = {
        'date': target_date,
        'period_type': 'daily',
        'total_customers': total_customers,
        'paying_customers': paying_customers,
        'mrr': round(mrr, 2),
        'arr': round(arr, 2),
        'new_customers': new_customers,
        'churned_customers': churned_customers,
        'notes': final_notes,
        'revenue_by_plan': revenue_by_plan,
        'auto_events': auto_events,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    
    # Use upsert to prevent duplicates
    result = db.historical_analytics.replace_one(
        {'date': target_date, 'period_type': 'daily'},
        historical_record,
        upsert=True
    )
    
    # Mark events as processed
    event_ids = [event['_id'] for event in events]
    if event_ids:
        db.business_events.update_many(
            {'_id': {'$in': event_ids}},
            {'$set': {'processed': True}}
        )
    
    return {
        'success': True,
        'record_id': str(result.upserted_id) if result.upserted_id else 'updated',
        'data': historical_record,
        'events_processed': len(events),
        'auto_notes': auto_notes
    }


def check_and_create_milestones(db):
    """
    Check if any milestones have been reached and create events for them
    """
    from datetime import timezone
    
    # Get current stats
    total_customers = db.customers.count_documents({})
    active_licenses = db.licenses.count_documents({'status': 'active'})
    
    # Define milestones
    customer_milestones = [10, 25, 50, 100, 250, 500, 1000]
    license_milestones = [5, 10, 25, 50, 100, 250, 500, 1000]
    
    # Check if we've crossed any customer milestones today
    yesterday_customers = total_customers - db.customers.count_documents({
        'created_at': {'$gte': datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)}
    })
    
    for milestone in customer_milestones:
        if yesterday_customers < milestone <= total_customers:
            # We've crossed this milestone!
            create_business_event(
                db,
                'milestone_reached',
                f"🎉 Raggiunti {milestone} clienti totali!",
                metadata={'milestone_type': 'customers', 'milestone_value': milestone}
            )
    
    # Check license milestones
    yesterday_licenses = active_licenses - db.licenses.count_documents({
        'status': 'active',
        'created_at': {'$gte': datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)}
    })
    
    for milestone in license_milestones:
        if yesterday_licenses < milestone <= active_licenses:
            create_business_event(
                db,
                'milestone_reached',
                f"🎫 Raggiunte {milestone} licenze attive!",
                metadata={'milestone_type': 'licenses', 'milestone_value': milestone}
            )


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