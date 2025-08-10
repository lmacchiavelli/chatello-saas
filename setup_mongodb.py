#!/usr/bin/env python3
"""
Chatello SaaS - MongoDB Setup Script
Run this script to initialize MongoDB Atlas database
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime
from mongodb_schema import init_mongodb_collections, generate_license_key
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_mongodb():
    """Setup MongoDB Atlas database with collections and sample data"""
    
    # Get MongoDB URI from environment
    mongodb_uri = os.environ.get('MONGODB_URI')
    database_name = os.environ.get('MONGODB_DATABASE', 'chatello_saas')
    
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in environment variables")
        print("Create .env file with your MongoDB Atlas connection string")
        return False
    
    try:
        print("🔗 Connecting to MongoDB Atlas...")
        # SSL/TLS configuration for older systems
        client = MongoClient(
            mongodb_uri, 
            serverSelectionTimeoutMS=10000,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas successfully!")
        
        # Get database
        db = client[database_name]
        print(f"📁 Using database: {database_name}")
        
        # Initialize collections and indexes
        print("🚀 Initializing collections and indexes...")
        init_mongodb_collections(db)
        
        # Create sample data for testing
        create_sample_data = input("\n🎯 Create sample customer and license for testing? (y/N): ").lower() == 'y'
        
        if create_sample_data:
            # Create sample customer
            sample_customer = {
                'email': 'test@chatello.io',
                'name': 'Test Customer',
                'company': 'Chatello Test',
                'status': 'active',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            customer_result = db.customers.insert_one(sample_customer)
            print(f"👤 Created sample customer: {sample_customer['email']}")
            
            # Get Pro plan
            pro_plan = db.plans.find_one({'name': 'pro'})
            
            if pro_plan:
                # Generate unique license key
                license_key = generate_license_key()
                while db.licenses.find_one({'license_key': license_key}):
                    license_key = generate_license_key()
                
                sample_license = {
                    'license_key': license_key,
                    'customer_id': customer_result.inserted_id,
                    'plan_id': pro_plan['_id'],
                    'domain': 'test.chatello.io',
                    'status': 'active',
                    'activated_at': datetime.now(),
                    'expires_at': None,
                    'last_check': None,
                    'metadata': {'test': True},
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }
                
                db.licenses.insert_one(sample_license)
                print(f"🔑 Created sample license: {license_key}")
                print(f"📋 Plan: Pro (AI Included)")
        
        # Display summary
        print("\n" + "="*50)
        print("📊 DATABASE SETUP COMPLETE")
        print("="*50)
        
        # Count documents in each collection
        collections_stats = {}
        for collection_name in ['plans', 'customers', 'licenses', 'usage_logs', 'payments', 'api_keys', 'activity_logs']:
            count = db[collection_name].count_documents({})
            collections_stats[collection_name] = count
            print(f"📁 {collection_name}: {count} documents")
        
        print("\n🎉 MongoDB Atlas is ready for Chatello SaaS!")
        print(f"🔗 Connection: {mongodb_uri.split('@')[1].split('/')[0]}")  # Hide credentials
        print(f"💾 Database: {database_name}")
        
        if create_sample_data:
            print(f"\n🧪 Test with sample license: {license_key}")
            print("   Use this license key in your WordPress plugin for testing")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def test_connection():
    """Test MongoDB connection and basic operations"""
    mongodb_uri = os.environ.get('MONGODB_URI')
    database_name = os.environ.get('MONGODB_DATABASE', 'chatello_saas')
    
    if not mongodb_uri:
        print("❌ MONGODB_URI not set")
        return False
    
    try:
        print("🧪 Testing MongoDB Atlas connection...")
        # SSL/TLS configuration for older systems
        client = MongoClient(
            mongodb_uri, 
            serverSelectionTimeoutMS=10000,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        # Test ping
        client.admin.command('ping')
        print("✅ Ping successful")
        
        # Test database operations
        db = client[database_name]
        
        # Test collections
        collections = db.list_collection_names()
        print(f"📂 Collections: {', '.join(collections) if collections else 'None'}")
        
        # Test sample queries
        plans_count = db.plans.count_documents({})
        customers_count = db.customers.count_documents({})
        licenses_count = db.licenses.count_documents({})
        
        print(f"📊 Plans: {plans_count}, Customers: {customers_count}, Licenses: {licenses_count}")
        
        # Test license validation
        sample_license = db.licenses.find_one()
        if sample_license:
            print(f"🔑 Sample license found: {sample_license['license_key']}")
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Chatello SaaS - MongoDB Atlas Setup")
    print("="*40)
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_connection()
    else:
        setup_mongodb()