#!/usr/bin/env python3
"""
Test real analytics data from MongoDB
"""

import os
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

def test_real_analytics():
    """Calculate and display real analytics from MongoDB"""
    
    mongodb_uri = os.environ.get('MONGODB_URI')
    client = MongoClient(mongodb_uri)
    db = client.chatello_saas
    
    print("📊 REAL ANALYTICS DATA FROM MONGODB")
    print("=" * 60)
    
    # Get all active licenses with plan info
    active_licenses_pipeline = [
        {
            '$match': {
                'status': 'active',
                '$or': [
                    {'expires_at': None},
                    {'expires_at': {'$gt': datetime.now(timezone.utc)}}
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
    
    # Calculate MRR and one-time revenue
    mrr = 0
    one_time_revenue = 0
    revenue_by_plan = {}
    
    for license in active_licenses:
        plan_name = license['plan']['name'].lower()
        plan_price = license['plan'].get('price', 0)
        
        if plan_name not in revenue_by_plan:
            revenue_by_plan[plan_name] = {'revenue': 0, 'count': 0, 'type': 'recurring'}
        
        revenue_by_plan[plan_name]['count'] += 1
        
        # Check if it's a lifetime/one-time plan
        if license['plan'].get('is_lifetime', False) or plan_name == 'founders':
            one_time_revenue += plan_price
            revenue_by_plan[plan_name]['revenue'] += plan_price
            revenue_by_plan[plan_name]['type'] = 'one-time'
        else:
            # Regular recurring revenue
            mrr += plan_price
            revenue_by_plan[plan_name]['revenue'] += plan_price
    
    print("\n💰 REVENUE METRICS:")
    print(f"   MRR (Monthly Recurring): €{mrr:.2f}")
    print(f"   ARR (Annual Recurring): €{mrr * 12:.2f}")
    print(f"   One-Time Revenue: €{one_time_revenue:.2f}")
    print(f"   Total Active Licenses: {len(active_licenses)}")
    
    print("\n📊 REVENUE BY PLAN:")
    for plan_name, data in revenue_by_plan.items():
        print(f"   {plan_name.title()}:")
        print(f"      Revenue: €{data['revenue']:.2f}")
        print(f"      Customers: {data['count']}")
        print(f"      Type: {data['type']}")
    
    # Get Founders Deal specific stats
    founders_plan = db.plans.find_one({'name': 'founders'})
    if founders_plan:
        founders_licenses = [l for l in active_licenses if l['plan']['name'] == 'founders']
        print("\n🚀 FOUNDERS DEAL STATISTICS:")
        print(f"   Sold: {len(founders_licenses)}/500")
        print(f"   Revenue: €{len(founders_licenses) * 29}")
        print(f"   Remaining: {500 - len(founders_licenses)}")
        print(f"   Progress: {(len(founders_licenses) / 500) * 100:.1f}%")
    
    # Get all plans for reference
    print("\n📋 ALL AVAILABLE PLANS:")
    all_plans = list(db.plans.find())
    for plan in all_plans:
        print(f"   {plan['name'].title()}:")
        print(f"      Price: €{plan.get('price', 0)}")
        print(f"      Type: {'Lifetime' if plan.get('is_lifetime', False) else 'Recurring'}")
        if plan['name'] == 'founders':
            print(f"      Limit: {plan.get('lifetime_limit', 500)} licenses")
    
    # Count total licenses by status
    print("\n📈 LICENSE STATUS BREAKDOWN:")
    statuses = db.licenses.distinct('status')
    for status in statuses:
        count = db.licenses.count_documents({'status': status})
        print(f"   {status.title()}: {count}")
    
    print("\n✅ Analytics calculation complete!")
    print("\n💡 NOTE: To see this in the web interface:")
    print("   1. SSH tunnel: ssh -L 5011:localhost:5011 ubuntu@164.132.56.3")
    print("   2. Open: http://localhost:5011")
    print("   3. Login: admin / ChatelloAdmin2025!")
    print("   4. Navigate to: Analytics")

if __name__ == "__main__":
    test_real_analytics()