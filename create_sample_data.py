#!/usr/bin/env python3
"""
Create sample customer and license for testing
"""

import os
from pymongo import MongoClient
from datetime import datetime
from mongodb_schema import generate_license_key
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.mongodb')

def create_sample_data():
    mongodb_uri = os.environ.get('MONGODB_URI')
    database_name = os.environ.get('MONGODB_DATABASE', 'chatello_saas')
    
    client = MongoClient(
        mongodb_uri, 
        serverSelectionTimeoutMS=10000,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True
    )
    
    db = client[database_name]
    
    print("👤 Creating sample customer...")
    
    # Create sample customer
    sample_customer = {
        'email': 'test@chatello.io',
        'name': 'Test Customer',
        'company': 'Chatello Test',
        'status': 'active',
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    # Check if customer exists
    existing_customer = db.customers.find_one({'email': 'test@chatello.io'})
    if existing_customer:
        print("⚠️  Customer already exists")
        customer_id = existing_customer['_id']
    else:
        result = db.customers.insert_one(sample_customer)
        customer_id = result.inserted_id
        print(f"✅ Created customer: {sample_customer['email']}")
    
    # Get Pro plan
    pro_plan = db.plans.find_one({'name': 'pro'})
    if not pro_plan:
        print("❌ Pro plan not found!")
        return
    
    print("🔑 Creating sample license...")
    
    # Generate unique license key
    license_key = generate_license_key()
    while db.licenses.find_one({'license_key': license_key}):
        license_key = generate_license_key()
    
    sample_license = {
        'license_key': license_key,
        'customer_id': customer_id,
        'plan_id': pro_plan['_id'],
        'domain': 'test.chatello.io',
        'status': 'active',
        'activated_at': datetime.now(),
        'expires_at': None,  # Unlimited for Pro
        'last_check': None,
        'metadata': {'test': True},
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    result = db.licenses.insert_one(sample_license)
    print(f"✅ Created license: {license_key}")
    print(f"📋 Plan: Pro (AI Included)")
    
    # Also create a Starter license
    starter_plan = db.plans.find_one({'name': 'starter'})
    if starter_plan:
        starter_license_key = generate_license_key()
        while db.licenses.find_one({'license_key': starter_license_key}):
            starter_license_key = generate_license_key()
        
        starter_license = {
            'license_key': starter_license_key,
            'customer_id': customer_id,
            'plan_id': starter_plan['_id'],
            'domain': 'starter.chatello.io',
            'status': 'active',
            'activated_at': datetime.now(),
            'expires_at': None,
            'last_check': None,
            'metadata': {'test': True, 'plan': 'starter'},
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        db.licenses.insert_one(starter_license)
        print(f"✅ Created Starter license: {starter_license_key}")
    
    print("\n🎉 Sample data created successfully!")
    print(f"🧪 Pro License (AI included): {license_key}")
    print(f"🧪 Starter License (BYOK): {starter_license_key}")
    
    return license_key, starter_license_key

if __name__ == "__main__":
    create_sample_data()