#!/usr/bin/env python3
"""
Add Founders Deal plan to MongoDB Atlas
Founders Deal: €29 one-time lifetime license for first 500 users
"""

import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

def add_founders_deal_plan():
    """
    Add the Founders Deal plan to the database
    """
    mongodb_uri = os.environ.get('MONGODB_URI')
    database_name = os.environ.get('MONGODB_DATABASE', 'chatello_saas')
    
    client = MongoClient(
        mongodb_uri, 
        serverSelectionTimeoutMS=10000,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True
    )
    
    db = client[database_name]
    
    # Check if Founders Deal plan already exists
    existing_plan = db.plans.find_one({'name': 'founders'})
    if existing_plan:
        print("⚠️  Founders Deal plan already exists")
        return existing_plan
    
    print("🚀 Adding Founders Deal plan to database...")
    
    # Create Founders Deal plan
    founders_deal_plan = {
        'name': 'founders',
        'display_name': 'Founders Deal - Lifetime',
        'price': 29.0,  # €29 one-time
        'currency': 'EUR',
        'is_lifetime': True,  # NEW: Mark as lifetime deal
        'lifetime_limit': 500,  # NEW: Limited to 500 customers
        'lifetime_sold': 0,  # NEW: Track how many sold so far
        'monthly_requests': 2000,  # Same as Pro plan
        'requests_per_minute': 15,  # Between Pro and Agency
        'requests_per_hour': 300,   # Between Pro and Agency  
        'monthly_budget_eur': 6.0,  # €6/month budget (~4M tokens)
        'cost_per_1k_tokens': 0.0015,  # OpenAI GPT-4o-mini cost
        'max_sites': 5,  # More than Pro, less than Agency
        'features': [
            'ai_included',
            '5_sites',
            'lifetime_license',
            'priority_support', 
            'advanced_features',
            'no_api_key_needed',
            'founders_badge',  # Special badge
            'early_access'     # Early access to new features
        ],
        'is_active': True,
        'is_limited_offer': True,  # NEW: Mark as limited offer
        'offer_expires_at': None,  # Could set expiration date for offer
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'metadata': {
            'description': 'Limited lifetime offer for the first 500 users',
            'marketing_text': 'Get lifetime access for just €29 - Limited to first 500 users!',
            'fomo_text': 'Only available for the first 500 customers',
            'bootstrap_revenue': 14500.0,  # 500 * €29 = €14,500
            'target_conversion': 0.05  # 5% conversion rate target
        }
    }
    
    # Insert the plan
    result = db.plans.insert_one(founders_deal_plan)
    plan_id = result.inserted_id
    
    print(f"✅ Created Founders Deal plan with ID: {plan_id}")
    print(f"💰 Price: €{founders_deal_plan['price']} (one-time)")
    print(f"🎯 Limit: {founders_deal_plan['lifetime_limit']} licenses")
    print(f"💵 Potential Revenue: €{founders_deal_plan['metadata']['bootstrap_revenue']}")
    
    # Create a founders_deal_stats collection to track the offer
    stats_doc = {
        'plan_name': 'founders',
        'plan_id': plan_id,
        'total_limit': 500,
        'sold_count': 0,
        'remaining_count': 500,
        'revenue_generated': 0.0,
        'conversion_rate': 0.0,
        'first_sale_at': None,
        'last_sale_at': None,
        'is_sold_out': False,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    # Check if stats already exist
    existing_stats = db.founders_deal_stats.find_one({'plan_name': 'founders'})
    if not existing_stats:
        db.founders_deal_stats.insert_one(stats_doc)
        print("📊 Created Founders Deal tracking stats")
    
    return founders_deal_plan

def get_founders_deal_status():
    """
    Get current status of Founders Deal offer
    """
    mongodb_uri = os.environ.get('MONGODB_URI')
    database_name = os.environ.get('MONGODB_DATABASE', 'chatello_saas')
    
    client = MongoClient(mongodb_uri)
    db = client[database_name]
    
    # Get plan info
    plan = db.plans.find_one({'name': 'founders'})
    if not plan:
        print("❌ Founders Deal plan not found")
        return None
    
    # Count current Founders Deal licenses
    founders_licenses_count = db.licenses.count_documents({
        'plan_id': plan['_id'],
        'status': {'$in': ['active', 'inactive']}  # Count all non-cancelled
    })
    
    remaining = plan['lifetime_limit'] - founders_licenses_count
    is_available = remaining > 0
    
    print(f"🎯 Founders Deal Status:")
    print(f"   Sold: {founders_licenses_count}/{plan['lifetime_limit']}")
    print(f"   Remaining: {remaining}")
    print(f"   Available: {'Yes' if is_available else 'SOLD OUT'}")
    print(f"   Revenue: €{founders_licenses_count * plan['price']}")
    
    return {
        'plan': plan,
        'sold_count': founders_licenses_count,
        'remaining_count': remaining,
        'is_available': is_available,
        'revenue': founders_licenses_count * plan['price']
    }

if __name__ == "__main__":
    # Add the plan
    plan = add_founders_deal_plan()
    print()
    
    # Show current status
    get_founders_deal_status()