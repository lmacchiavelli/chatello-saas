#!/usr/bin/env python3
"""
Create a test Founders Deal license directly in MongoDB
"""

import os
from pymongo import MongoClient
from datetime import datetime
from mongodb_schema import generate_license_key
from dotenv import load_dotenv

load_dotenv()

def create_founders_test_license():
    """Create a test license with Founders Deal plan"""
    
    mongodb_uri = os.environ.get('MONGODB_URI')
    client = MongoClient(mongodb_uri)
    db = client.chatello_saas
    
    # Get Founders Deal plan
    founders_plan = db.plans.find_one({'name': 'founders'})
    if not founders_plan:
        print("❌ Founders Deal plan not found!")
        return None
    
    # Get test customer or create one
    test_customer = db.customers.find_one({'email': 'founder.test@chatello.io'})
    if not test_customer:
        test_customer = {
            'name': 'Founder Test User',
            'email': 'founder.test@chatello.io',
            'company': 'Test Company',
            'status': 'active',
            'created_at': datetime.now()
        }
        result = db.customers.insert_one(test_customer)
        test_customer['_id'] = result.inserted_id
        print(f"✅ Created test customer: {test_customer['email']}")
    
    # Generate unique license key
    license_key = generate_license_key()
    while db.licenses.find_one({'license_key': license_key}):
        license_key = generate_license_key()
    
    # Create Founders Deal license
    test_license = {
        'license_key': license_key,
        'customer_id': test_customer['_id'],
        'plan_id': founders_plan['_id'],
        'domain': 'test-founders.chatello.io',
        'status': 'active',
        'activated_at': datetime.now(),
        'expires_at': None,  # Lifetime license
        'last_check': None,
        'metadata': {
            'test': True,
            'plan': 'founders',
            'created_by': 'test_script'
        },
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    result = db.licenses.insert_one(test_license)
    
    print(f"🚀 Created Founders Deal license: {license_key}")
    print(f"📋 Plan: {founders_plan['display_name']}")
    print(f"💰 Price: €{founders_plan['price']} (one-time)")
    print(f"👤 Customer: {test_customer['name']}")
    
    # Check current Founders Deal status
    founders_count = db.licenses.count_documents({
        'plan_id': founders_plan['_id'],
        'status': {'$in': ['active', 'inactive']}
    })
    
    remaining = founders_plan.get('lifetime_limit', 500) - founders_count
    
    print(f"\n📊 Current Founders Deal Status:")
    print(f"   Sold: {founders_count}/{founders_plan.get('lifetime_limit', 500)}")
    print(f"   Remaining: {remaining}")
    print(f"   Revenue: €{founders_count * founders_plan.get('price', 29)}")
    
    return license_key

if __name__ == "__main__":
    license_key = create_founders_test_license()
    if license_key:
        print(f"\n🧪 Test this license key: {license_key}")
        print(f"🌐 Test API validation:")
        print(f"curl -X POST https://api.chatello.io/api/validate -H 'X-License-Key: {license_key}'")