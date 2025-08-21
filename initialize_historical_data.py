#!/usr/bin/env python3
"""
Initialize historical analytics data for Chatello SaaS
Creates sample data for the last 30 days
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mongodb_schema import save_daily_analytics

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://lmacchiavelli:BINI9RIhBOvjy3eu@chatello.38m5lpq.mongodb.net/?retryWrites=true&w=majority&appName=chatello')
DATABASE_NAME = os.environ.get('MONGODB_DATABASE', 'chatello_saas')

def initialize_historical_data():
    """Initialize historical analytics data for the last 30 days"""
    
    try:
        # Connect to MongoDB
        mongo_client = MongoClient(MONGODB_URI)
        mongo_db = mongo_client[DATABASE_NAME]
        
        print("🔗 Connected to MongoDB Atlas")
        
        # Check if historical data already exists
        existing_count = mongo_db.historical_analytics.count_documents({})
        
        if existing_count > 0:
            print(f"⚠️  Historical data already exists ({existing_count} records)")
            response = input("Do you want to recreate the data? (y/N): ")
            if response.lower() != 'y':
                print("❌ Initialization cancelled")
                return
            
            # Clear existing data
            mongo_db.historical_analytics.delete_many({})
            print("🗑️  Cleared existing historical data")
        
        # Generate data for the last 30 days
        end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        sample_notes = [
            "🚀 Lancio campagna marketing",
            "📈 Crescita organica",
            "🎯 Targeting clienti aziendali", 
            "💡 Miglioramento features",
            "📧 Email marketing campaign",
            "🔍 SEO optimization",
            "🤝 Partnership announcement",
            "🎨 UI/UX improvements",
            "📱 Mobile app release",
            "🎉 Milestone celebration",
            "",  # Some days without notes
            "",
            "🔧 Bug fixes release",
            "📊 Analytics improvements",
            "🌟 Customer testimonials",
        ]
        
        print("📅 Creating historical data for last 30 days...")
        
        for i in range(30):
            target_date = end_date - timedelta(days=i)
            
            # Add some variation to notes
            notes = ""
            if i < len(sample_notes):
                notes = sample_notes[i]
            elif i % 7 == 0:  # Weekly updates
                notes = f"📊 Weekly review - Day {30-i}"
            elif i % 10 == 0:  # Other milestones
                notes = f"🎯 Milestone reached - Day {30-i}"
            
            # Save analytics for this date
            result = save_daily_analytics(mongo_db, target_date=target_date, notes=notes)
            
            if result['success']:
                data = result['data']
                print(f"✅ {target_date.strftime('%Y-%m-%d')}: "
                      f"Customers: {data['total_customers']}, "
                      f"Paying: {data['paying_customers']}, "
                      f"MRR: €{data['mrr']}")
            else:
                print(f"❌ Failed to save data for {target_date.strftime('%Y-%m-%d')}")
        
        # Verify data was created
        final_count = mongo_db.historical_analytics.count_documents({})
        print(f"\n🎉 Successfully created {final_count} historical records!")
        
        # Show latest record
        latest_record = mongo_db.historical_analytics.find_one(
            {'period_type': 'daily'}, 
            sort=[('date', -1)]
        )
        
        if latest_record:
            print(f"📊 Latest record: {latest_record['date'].strftime('%Y-%m-%d')}")
            print(f"   Total Customers: {latest_record['total_customers']}")
            print(f"   Paying Customers: {latest_record['paying_customers']}")
            print(f"   MRR: €{latest_record['mrr']}")
            print(f"   Notes: {latest_record.get('notes', 'No notes')}")
        
    except Exception as e:
        print(f"❌ Error initializing historical data: {e}")
        return False
    
    finally:
        if 'mongo_client' in locals():
            mongo_client.close()
    
    return True

if __name__ == "__main__":
    print("🚀 Chatello SaaS - Historical Data Initialization")
    print("=" * 50)
    
    success = initialize_historical_data()
    
    if success:
        print("\n✅ Historical data initialization completed!")
        print("🌐 You can now view the data in the Admin Dashboard:")
        print("   http://localhost:5011/analytics")
    else:
        print("\n❌ Historical data initialization failed!")
        sys.exit(1)