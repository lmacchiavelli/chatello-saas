#!/usr/bin/env python3
"""
Update existing plans with rate limiting fields
One-time script to add requests_per_minute and requests_per_hour
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.environ.get('MONGODB_URI')
DATABASE_NAME = os.environ.get('MONGODB_DATABASE', 'chatello_saas')

def update_plans_with_rate_limits():
    """Update existing plans with rate limit fields"""
    try:
        client = MongoClient(MONGODB_URI)
        db = client[DATABASE_NAME]
        
        print("🔄 Updating plans with rate limiting fields...")
        
        # Define rate limits for each plan
        plan_updates = {
            'starter': {
                'requests_per_minute': 0,  # Unlimited for BYOK
                'requests_per_hour': 0     # Unlimited for BYOK
            },
            'pro': {
                'requests_per_minute': 10,  # 10 requests per minute
                'requests_per_hour': 200    # 200 requests per hour
            },
            'agency': {
                'requests_per_minute': 25,  # 25 requests per minute
                'requests_per_hour': 500    # 500 requests per hour
            }
        }
        
        updated_count = 0
        
        for plan_name, limits in plan_updates.items():
            result = db.plans.update_one(
                {'name': plan_name},
                {
                    '$set': {
                        'requests_per_minute': limits['requests_per_minute'],
                        'requests_per_hour': limits['requests_per_hour'],
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✅ Updated {plan_name} plan:")
                print(f"   - Per minute: {limits['requests_per_minute']}")
                print(f"   - Per hour: {limits['requests_per_hour']}")
                updated_count += 1
            else:
                print(f"⚠️  {plan_name} plan not found or already updated")
        
        print(f"\n🎉 Successfully updated {updated_count} plans with rate limiting!")
        
        # Verify the updates
        print("\n📊 Current plan configurations:")
        for plan in db.plans.find():
            print(f"\n{plan['name'].upper()} Plan:")
            print(f"  Monthly requests: {plan['monthly_requests']}")
            print(f"  Per minute: {plan.get('requests_per_minute', 'Not set')}")
            print(f"  Per hour: {plan.get('requests_per_hour', 'Not set')}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating plans: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Chatello SaaS - Plans Rate Limits Update")
    print("=" * 50)
    
    if not MONGODB_URI:
        print("❌ Error: MONGODB_URI environment variable not set")
        sys.exit(1)
    
    success = update_plans_with_rate_limits()
    
    if success:
        print("\n✅ Update completed successfully!")
        print("🔄 Please restart the admin dashboard to see changes.")
    else:
        print("\n❌ Update failed!")
        sys.exit(1)